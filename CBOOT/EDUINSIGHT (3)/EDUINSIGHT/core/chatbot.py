"""Coordina el proceso de respuesta:
pregunta -> clasificar -> (¿es seguimiento del tema anterior?) -> responder -> guardar.

El chatbot funciona como tutor:
- Recuerda de qué tema se está hablando, así que entiende "explícamelo mejor"
  o "dame otro ejemplo" sin que el alumno repita el tema.
- Tiene "acciones" para explicar de distintas formas: más fácil, paso a paso,
  otro ejemplo, ejercicio y solución.
- Si hay IA (Groq/Ollama) la usa; si no, arma la respuesta con la base local.
"""

import json
import re
from pathlib import Path

from core import ia_client, institucional
from core.classifier import (TEMAS, clasificar, detectar_materia, normalizar, parece_educativa,
                             pide_materias, pide_temario)
from database import db

BASE_DIR = Path(__file__).resolve().parent.parent
CONOCIMIENTOS = json.loads((BASE_DIR / "data" / "conocimientos.json").read_text(encoding="utf-8"))

FUERA_DE_TEMA = "No estoy diseñado para este tipo de preguntas."
MATERIAS = list(TEMAS.keys())
LISTA_MATERIAS = ", ".join(MATERIAS[:-1]) + " y " + MATERIAS[-1]
OTRA_MATERIA, OTRO_TEMA = "Otras materias", "Otros temas"

# Frases que indican qué tipo de ayuda pide el alumno (el orden importa)
ACCIONES = [
    ("solucion", ["solucion", "como se resuelve", "la respuesta", "resultado del ejercicio"]),
    ("ejercicio", ["ejercicio", "practicar", "un reto", "ponme algo"]),
    ("pasos", ["paso a paso", "pasos", "por partes"]),
    ("ejemplo", ["otro ejemplo", "ejemplo", "caso real", "para que sirve"]),
    ("sencillo", ["mas facil", "mas sencillo", "mas simple", "no entiendo", "no entendi",
                  "no le entiendo", "no le entendi", "explicamelo", "explica mejor", "explicalo mejor",
                  "no me quedo claro", "otra forma", "como si tuviera", "sigo sin"]),
]

# ---------- Conversación natural (sí, no, gracias, hola...) ----------
AFIRMACIONES = ["si", "sip", "simon", "si porfa", "si por favor", "va", "vale", "ok", "okay",
                "dale", "claro", "porfa", "por favor", "esta bien", "de acuerdo", "sale", "orale",
                "aja", "ya", "listo", "adelante", "yes", "si quiero", "si gracias", "ya lo hice",
                "ya lo intente", "ya termine", "andale", "sii", "siii", "obvio"]
NEGACIONES = ["no", "nel", "nop", "nope", "no gracias", "asi esta bien", "no por ahora",
              "ahorita no", "nah", "mejor no", "todavia no", "aun no", "no quiero"]
ENTENDIDO = ["ya entendi", "ya le entendi", "entendi", "entendido", "ya quedo", "quedo claro",
             "ya me quedo claro", "ahora si entendi", "ya le agarre", "ya capte", "ya lo entendi"]
SALUDOS = ["hola", "holi", "buenas", "buenos dias", "buenas tardes", "buenas noches", "hey",
           "que tal", "que onda", "hello", "hi"]
GRACIAS = ["gracias", "muchas gracias", "mil gracias", "te pasaste", "thanks", "grax", "gracias tutor"]
DESPEDIDAS = ["adios", "bye", "nos vemos", "hasta luego", "chao", "hasta pronto", "me voy"]

# Qué se ofrece después de cada tipo de respuesta: (acción que se hará si dice "sí", pregunta)
OFERTAS = {
    None: ("pasos", "¿Quieres que te lo explique paso a paso?"),
    "sencillo": ("ejemplo", "¿Quieres que te ponga un ejemplo?"),
    "pasos": ("ejercicio", "¿Te pongo un ejercicio para practicar?"),
    "ejemplo": ("ejercicio", "¿Quieres intentar un ejercicio?"),
    "ejercicio": ("solucion", "Cuando lo intentes, dime y te muestro la solución."),
    "solucion": (None, "¿Tienes alguna otra duda?"),
}


def _es(texto, frases, max_palabras=4):
    """True si el mensaje es (o empieza con) alguna de las frases y es corto."""
    t = " ".join(normalizar(texto).split())
    if len(t.split()) > max_palabras:
        return False
    return any(t == f or t.startswith(f + " ") for f in frases)


INSTRUCCIONES = {
    "sencillo": "El alumno NO entendió. Explícalo de una forma DIFERENTE y más sencilla que antes: "
                "usa una analogía de la vida diaria, sin tecnicismos, en máximo 6 líneas.",
    "pasos": "Explícalo paso a paso, en una lista numerada de 3 a 6 pasos, cada paso en una línea.",
    "ejemplo": "Da un ejemplo NUEVO, distinto a los anteriores y corto. Después explica en 2 o 3 "
               "líneas qué hace cada parte.",
    "ejercicio": "Propón UN solo ejercicio corto para practicar, nivel principiante. NO des la "
                 "solución; dile que la puede pedir cuando lo intente.",
    "solucion": "Da la solución del último ejercicio que propusiste y explica cada paso brevemente.",
}


def sistema(semestre):
    return (
        "Eres Tutor Tec, el asistente académico del Instituto Tecnológico de Cuautla. "
        f"Hablas con un alumno de {semestre or 'algún'} semestre de Ingeniería.\n"
        "Reglas:\n"
        "- Explica como un buen compañero que sabe enseñar: español sencillo y cercano, frases "
        "cortas. Si usas un término técnico, explícalo en la misma oración.\n"
        "- Si no hay una instrucción especial, usa esta estructura: **En pocas palabras**, "
        "**Imagínalo así** (una analogía de la vida diaria), **Cómo funciona**, **Ejemplo** (el "
        "código va en bloques ```), **Errores comunes**, y termina con una pregunta corta.\n"
        "- La primera explicación de un tema debe ser COMPLETA (hasta 30 líneas): qué es, para "
        "qué sirve, cómo funciona, un ejemplo resuelto y los errores más comunes. Las respuestas "
        "de seguimiento (más fácil, otro ejemplo) son más cortas. Usa títulos cortos, negritas y "
        "listas para que se lea fácil.\n"
        "- NO uses emojis ni emoticones en ninguna parte de la respuesta.\n"
        "- Si el alumno pide que le hagas la tarea completa, guíalo con pistas en vez de "
        "darle todo resuelto.\n"
        "- Si el alumno no entendió, explícalo de otra manera; no repitas lo mismo.\n"
        f"- Tus materias principales son: {LISTA_MATERIAS}. También puedes responder cualquier "
        "otra duda educativa o escolar (ciencias, matemáticas, ingeniería, idiomas, historia, "
        "técnicas de estudio).\n"
        "- NUNCA inventes datos de la escuela (edificios, fechas, costos, horarios, becas, "
        "trámites). Si te preguntan algo así, di que lo consulten en Servicios Escolares.\n"
        "- Si el alumno responde con mensajes cortos de conversación (sí, no, ok, gracias, ya "
        "entendí, hola), contéstale de forma natural según lo que venían platicando; eso NO es "
        "fuera de tema. Si dice que sí a algo que le ofreciste, hazlo.\n"
        "- Si la pregunta NO es educativa (chismes, deportes, entretenimiento, temas personales, "
        "bromas, contenido inapropiado, etc.), responde únicamente: FUERA"
    )


# Rangos Unicode de emojis y símbolos decorativos
_EMOJIS = re.compile(
    "[\U0001F000-\U0001FAFF\U0001F900-\U0001F9FF\u2600-\u27BF\u2B00-\u2BFF"
    "\uFE0F\u200D\u20E3]+ ?"
)


def sin_emojis(texto):
    """Quita emojis de la respuesta (la IA a veces los pone aunque se le pida que no)."""
    # solo se quita el emoji (y el espacio que lo sigue); la sangría del código no se toca
    return _EMOJIS.sub("", texto).strip()


def detectar_accion(texto):
    t = f" {normalizar(texto)} "
    for accion, frases in ACCIONES:
        if any(f" {f} " in t for f in frases):
            return accion
    return None


def materia_de(tema):
    return next((m for m, temas in TEMAS.items() if tema in temas), None)


def descripcion_tema(tema):
    """Resumen de una línea del tema (del material local o de temas.json)."""
    info = CONOCIMIENTOS.get(tema)
    if info:
        return info["explicacion"].split(". ")[0].rstrip(".") + "."
    materia = materia_de(tema)
    return TEMAS.get(materia, {}).get(tema, {}).get("descripcion", "")


# ---------------- Respuestas sin IA ----------------
def respuesta_local(tema, accion=None, vez=0):
    """vez = cuántas veces ya se pidió esta misma acción sobre este tema.
    Así cada vez sale una explicación distinta en lugar de repetir la misma."""
    info = CONOCIMIENTOS.get(tema)
    if not info:
        # Temas que se explican a fondo con IA. Sin IA: la primera vez se da el resumen y,
        # si pide más, se apoya en el tema base que sí tiene material (ej. JOINs -> SQL).
        base = next((p for p in TEMAS.get(materia_de(tema), {}).get(tema, {})
                     .get("prerrequisitos", []) if p in CONOCIMIENTOS), None)
        if accion and base:
            return (f"Para **{tema}** necesito la IA activada, pero mientras tanto te ayudo con "
                    f"su tema base, **{base}**, que te va a servir para entenderlo:\n\n"
                    + respuesta_local(base, accion, vez))
        return (f"### {tema}\n\n{descripcion_tema(tema)}\n\n"
                "Este tema lo explico a fondo con la IA (con ejemplos, pasos y ejercicios). "
                "Actívala en la barra lateral con tu API key de DeepSeek o con Ollama.")

    if accion == "sencillo":
        if vez == 0:
            return f"Va, te lo explico de otra forma.\n\n{info['sencillo2']}"
        if vez == 1:
            return f"Vamos todavía más simple.\n\n{info['sencillo3']}"
        if vez == 2:
            pasos = "\n".join(f"{i}. {p}" for i, p in enumerate(info["pasos"], 1))
            return (f"Probemos con algo muy concreto. Fíjate en este ejemplo:\n"
                    f"```\n{info['ejemplo3']}\n```\n{info['ejemplo3_nota']}\n\n"
                    f"Y estos son los pasos que se siguen:\n{pasos}")
        return (f"Veo que **{tema}** te está costando, y es normal: a muchos les pasa. "
                "Ya te lo expliqué de varias formas, así que te propongo otra ruta:\n\n"
                "1. Usa **Paso a paso** y ve cada paso con calma.\n"
                "2. Haz el **Ejercicio** aunque no te salga completo; equivocarse también enseña.\n"
                "3. Lleva tu duda a una **asesoría** con tu profe o un compañero: "
                "explicado en persona muchas veces se entiende mejor.\n\n"
                f"**Tip:** {info['recursos'][0]}.")

    if accion == "pasos":
        pasos = "\n".join(f"{i}. {p}" for i, p in enumerate(info["pasos"], 1))
        if vez == 0:
            return f"**{tema} paso a paso**\n\n{pasos}"
        if vez == 1:
            return (f"Apliquemos los pasos a un caso real:\n```\n{info['ejemplo3']}\n```\n"
                    f"{info['ejemplo3_nota']}\n\n**Los pasos:**\n{pasos}")
        if vez == 2:
            return (f"Ahora sigamos los pasos con otro caso distinto:\n```\n{info['ejemplo2']}\n```\n"
                    f"{info['ejemplo2_nota']}\n\n**Fíjate en el paso 1:** {info['pasos'][0]}")
        return ("Ya vimos los pasos con varios ejemplos. Lo que más ayuda ahora es que tú "
                f"los apliques. **Pista para empezar:** {info['pasos'][0]}")

    if accion == "ejemplo":
        if vez == 0:
            return f"**Otro ejemplo:**\n```\n{info['ejemplo2']}\n```\n{info['ejemplo2_nota']}"
        if vez == 1:
            return f"**Uno más:**\n```\n{info['ejemplo3']}\n```\n{info['ejemplo3_nota']}"
        return "Ya te mostré todos los ejemplos que tengo de este tema. Lo que más ayuda ahora es practicar."

    if accion == "ejercicio":
        if vez == 0:
            return f"**Ejercicio de {tema}**\n\n{info['ejercicio']}\n\nInténtalo primero."
        return (f"Ya tienes este ejercicio pendiente:\n\n{info['ejercicio']}\n\n"
                f"**Pista:** {info['pasos'][0]}")

    if accion == "solucion":
        return (f"**Solución:**\n```\n{info['solucion']}\n```\n"
                f"Si te salió distinto pero funciona, también está bien. "
                f"**Para seguir practicando:** {info['recursos'][-1].lower()}.")

    return (
        f"### {tema}\n\n"
        f"**En pocas palabras:** {info['sencillo']}\n\n"
        f"**Ahora más formal:** {info['explicacion']}\n\n"
        f"**Ejemplo:**\n```\n{info['ejemplo']}\n```"
    )


def respuesta_temario(materia):
    temas = list(TEMAS[materia].keys())
    lineas = []
    for t in temas:
        lineas.append(f"- **{t}**: {descripcion_tema(t)}")
    return (f"En **{materia}** puedo ayudarte con estos temas:\n\n" + "\n".join(lineas) +
            "\n\n¿Cuál quieres repasar? Elige uno abajo o escríbeme tu duda.")


def respuesta_materias():
    lineas = [f"- **{m}**: {', '.join(list(t.keys())[:4])}{'...' if len(t) > 4 else ''}"
              for m, t in TEMAS.items()]
    return ("Estas son las materias con las que te puedo ayudar:\n\n" + "\n".join(lineas) +
            "\n\nElige una para ver todos sus temas.")


# ---------------- Respuestas con IA ----------------
def respuesta_ia(pregunta, tema, accion, semestre, historial, vez=0, materia_ctx=None,
                 forzar=False):
    partes = []
    if materia_ctx and not tema:
        partes.append(f"[Contexto: el alumno viene preguntando sobre la materia {materia_ctx}.]")
    if forzar:
        partes.append("[Esta pregunta SÍ es educativa: es parte de la conversación. Respóndela "
                      "completa; no respondas FUERA.]")
    if tema and tema not in CONOCIMIENTOS:
        partes.append(f"[Tema: {tema} (materia {materia_de(tema)}). De qué trata: "
                      f"{descripcion_tema(tema)}]")
    if tema and tema in CONOCIMIENTOS:
        info = CONOCIMIENTOS[tema]
        apoyo = f"[Tema: {tema}. Material de apoyo: {info['explicacion']}"
        # cada vez se sugiere una idea distinta para que no repita la misma comparación
        if accion is None:
            apoyo += f" Analogía sugerida: {info['sencillo']}"
        elif accion == "sencillo" and vez < 2:
            apoyo += f" Idea que puedes usar: {info['sencillo2' if vez == 0 else 'sencillo3']}"
        partes.append(apoyo + "]")
    if accion:
        instruccion = INSTRUCCIONES[accion]
        if vez > 0 and accion in ("pasos", "ejemplo", "ejercicio"):
            instruccion += (" Usa un caso o ejemplo con datos y contexto DIFERENTES a los anteriores "
                            "(por ejemplo de la escuela, de una tienda, de un videojuego o de una "
                            "app), para que la respuesta no se parezca a las que ya diste.")
        if vez > 0:
            instruccion += (
                f" OJO: es la vez número {vez + 1} que el alumno pide esto. Tus explicaciones "
                "anteriores están en la conversación: NO repitas ninguna analogía, ejemplo ni "
                "frase que ya usaste. Usa una idea completamente distinta y todavía más simple, "
                "como para alguien de secundaria, y más corta."
            )
        if accion == "sencillo" and vez >= 3:
            instruccion += (" Además, dile con empatía que es normal que cueste y sugiérele "
                            "practicar con un ejercicio o pedir asesoría.")
        partes.append(f"[Instrucción especial: {instruccion}]")
    partes.append(pregunta)
    temperatura = 0.85 if (vez > 0 or accion in ("sencillo", "ejemplo")) else 0.5
    return ia_client.generar("\n".join(partes), sistema=sistema(semestre),
                             historial=historial, temperatura=temperatura)


# ---------------- Punto de entrada ----------------
def responder(pregunta, matricula, carrera="ISC", semestre=None, usar_ia=True,
              tema_actual=None, historial=None, accion=None, contador=None):
    """Regresa (respuesta, info).

    tema_actual: tema del que se venía hablando (para entender seguimientos).
    historial:   últimos mensajes [{"role", "content"}] para que la IA tenga contexto.
    accion:      'sencillo', 'pasos', 'ejemplo', 'ejercicio' o 'solucion' (botones).
    contador:    dict donde se cuenta cuántas veces se pidió cada acción por tema
                 (lo guarda la página o el bot por cada alumno). Sirve para no repetir.
    """
    contador = contador if contador is not None else {}
    accion = accion or detectar_accion(pregunta)
    # en seguimientos ("más fácil") y mensajes de plática ("sí", "gracias") no hace falta
    # preguntarle a la IA de qué tema es: así responde más rápido
    platica = any(_es(pregunta, f, 6) for f in
                  (AFIRMACIONES, NEGACIONES, ENTENDIDO, SALUDOS, GRACIAS, DESPEDIDAS))
    entrada_tec = institucional.buscar(pregunta)
    menu_tec = institucional.pide_menu(pregunta)
    clasif = clasificar(pregunta, usar_ia=not ((tema_actual and accion) or platica
                                               or entrada_tec or menu_tec))
    hay_ia = usar_ia and ia_client.disponible()
    seguimiento = False
    clasif.update(accion=None, respondio="base local", opciones=None)

    oferta = contador.get("_oferta")

    # 0. Mensajes de conversación (solo si no trae un tema concreto)
    if clasif["tema"] is None and not accion:
        if _es(pregunta, SALUDOS, 3):
            return "¡Hola! ¿En qué tema te puedo ayudar hoy?", clasif
        if _es(pregunta, GRACIAS, 5):
            contador["_oferta"] = None
            return "¡De nada! Si te surge otra duda, aquí estoy.", clasif
        if _es(pregunta, DESPEDIDAS, 4):
            contador["_oferta"] = None
            return "¡Suerte con tus estudios! Aquí estaré cuando tengas otra duda.", clasif
        if _es(pregunta, ENTENDIDO, 6):
            if tema_actual:
                contador["_oferta"] = "ejercicio"
                return (f"¡Qué bien! Para que no se te olvide, lo mejor es practicar. "
                        f"¿Quieres un ejercicio de **{tema_actual}**?"), clasif
            return "¡Qué bien! ¿Tienes alguna otra duda?", clasif
        if _es(pregunta, NEGACIONES, 4):
            contador["_oferta"] = None
            return "Va. Si tienes otra duda, escríbela cuando quieras.", clasif
        if _es(pregunta, AFIRMACIONES, 4):
            if oferta and tema_actual:
                accion = oferta              # hace lo que se le ofreció
            elif not (usar_ia and ia_client.disponible()):
                return "¡Claro! Escríbeme tu duda o elige una materia para ver sus temas.", clasif

    # 0.5 Información del Tec (becas, edificios, inglés, constancias...): nunca se inventa.
    # Tiene prioridad si la pregunta suena a trámite o lugar ("¿dónde está la biblioteca?"),
    # aunque alguna palabra coincida con un tema de clase ("biblioteca" en programación).
    if entrada_tec and clasif["tema"] and institucional.parece_tramite(pregunta):
        clasif.update(tema=None, materia=None)
    if clasif["tema"] is None and (menu_tec or entrada_tec):
        contador["_oferta"] = None
        if menu_tec and not entrada_tec:
            texto, opciones = institucional.menu()
            clasif.update(opciones=opciones)
            return texto, clasif
        respuesta = institucional.responder(entrada_tec)
        clasif.update(materia=institucional.MATERIA, respondio="información del Tec")
        est_id = db.obtener_o_crear_estudiante(matricula, carrera, semestre)
        db.guardar_consulta(est_id, pregunta, respuesta, institucional.MATERIA,
                            entrada_tec["titulo"], 1.0, "institucional")
        return respuesta, clasif

    # 1. ¿Pregunta qué materias hay, o qué temas tiene una materia?
    materia = detectar_materia(pregunta)
    if clasif["tema"] is None and pide_materias(pregunta):
        clasif.update(tema=None, opciones=[("materia", m) for m in MATERIAS])
        return respuesta_materias(), clasif
    sigue_misma_materia = accion and tema_actual and materia_de(tema_actual) == materia
    if materia and clasif["tema"] is None and not sigue_misma_materia:
        clasif.update(materia=materia, tema=None,
                      opciones=[("tema", t) for t in TEMAS[materia]])
        contador["_materia"] = materia
        return respuesta_temario(materia), clasif

    # 2. ¿Sigue hablando del tema anterior o es una pregunta nueva?
    pregunta_nueva = (len(pregunta.split()) >= 5 and parece_educativa(pregunta) and not accion)
    if clasif["tema"] is None and tema_actual and not pregunta_nueva:
        seguimiento = True
        clasif.update(tema=tema_actual, materia=materia_de(tema_actual), confianza=1.0)
    elif clasif["tema"] and clasif["tema"] == tema_actual and accion:
        seguimiento = True
    elif clasif["tema"] and clasif["tema"] != tema_actual:
        # Tema nuevo: la primera respuesta siempre es la explicación completa
        accion = None

    # 3. No es de ningún tema registrado
    materia_ctx = contador.get("_materia")
    if clasif["tema"] is None:
        if hay_ia:
            # la IA decide: si es educativa la contesta, si no, responde FUERA
            respuesta = respuesta_ia(pregunta, None, None, semestre, historial,
                                     materia_ctx=materia_ctx)
            es_fuera = respuesta is not None and respuesta.strip().upper().startswith("FUERA")
            if es_fuera and (materia_ctx or parece_educativa(pregunta)):
                # venían hablando de una materia o suena a pregunta de escuela:
                # los modelos pequeños a veces se equivocan, así que se le vuelve a pedir
                respuesta = respuesta_ia(pregunta, None, None, semestre, historial,
                                         materia_ctx=materia_ctx, forzar=True)
                es_fuera = respuesta is not None and respuesta.strip().upper().startswith("FUERA")
            if respuesta and not es_fuera:
                materia_guardar = materia_ctx or OTRA_MATERIA
                clasif.update(materia=materia_guardar, tema=OTRO_TEMA, confianza=0.5,
                              respondio=ia_client.nombre())
                respuesta = sin_emojis(respuesta)
                contador["_oferta"] = None
                est_id = db.obtener_o_crear_estudiante(matricula, carrera, semestre)
                db.guardar_consulta(est_id, pregunta, respuesta, materia_guardar, OTRO_TEMA,
                                    0.5, "ia")
                return respuesta, clasif
            if es_fuera:
                return FUERA_DE_TEMA, clasif
        if parece_educativa(pregunta) or materia_ctx:
            return (f"Ese tema todavía no está en mi base de conocimiento. Por ahora te puedo "
                    f"ayudar con {LISTA_MATERIAS}. Si activas la IA, también puedo responder "
                    f"dudas de otras materias."), clasif
        return FUERA_DE_TEMA, clasif

    clasif["accion"] = accion
    contador["_materia"] = clasif["materia"]
    clave = f"{clasif['tema']}|{accion}"
    vez = contador.get(clave, 0) if accion else 0

    respuesta = None
    if hay_ia:
        respuesta = respuesta_ia(pregunta, clasif["tema"], accion, semestre, historial, vez)
        if respuesta and respuesta.strip().upper().startswith("FUERA"):
            # el tema sí es de una materia: la IA se equivocó, se le vuelve a pedir
            respuesta = respuesta_ia(pregunta, clasif["tema"], accion, semestre, historial, vez,
                                     forzar=True)
            if respuesta and respuesta.strip().upper().startswith("FUERA"):
                respuesta = None          # si insiste, contesta la base local
        if respuesta:
            clasif["respondio"] = ia_client.nombre()

    if not respuesta:
        if (seguimiento and not accion and len(pregunta.split()) >= 4
                and not parece_educativa(pregunta)):
            return FUERA_DE_TEMA, {**clasif, "tema": None}
        if seguimiento and not accion:
            # no se entendió la pregunta: no se guarda, para no ensuciar la analítica
            return (
                f"Seguimos con **{clasif['tema']}**. No estoy seguro de qué parte quieres "
                "que te explique. Usa los botones de abajo o escríbeme algo como "
                "*\"explícamelo más fácil\"* o *\"dame otro ejemplo\"*. Si es de otro tema, "
                "escríbelo con más detalle."
            ), clasif
        else:
            respuesta = respuesta_local(clasif["tema"], accion, vez)

    respuesta = sin_emojis(respuesta)
    if accion:
        contador[clave] = vez + 1
    if clasif["respondio"] == "base local" and clasif["tema"] not in CONOCIMIENTOS:
        contador["_oferta"] = None
    elif clasif["respondio"] == "base local":
        siguiente, pregunta_oferta = OFERTAS.get(accion, (None, ""))
        if accion == "sencillo" and vez >= 3:
            siguiente, pregunta_oferta = "ejercicio", "¿Quieres intentar el ejercicio?"
        if accion == "ejemplo" and vez >= 2:
            siguiente, pregunta_oferta = "ejercicio", "¿Quieres intentar un ejercicio?"
        respuesta += f"\n\n{pregunta_oferta}" if pregunta_oferta else ""
        contador["_oferta"] = siguiente
    else:
        contador["_oferta"] = None      # con IA, ella misma entiende el "sí" por el historial
    est_id = db.obtener_o_crear_estudiante(matricula, carrera, semestre)
    db.guardar_consulta(
        est_id, pregunta, respuesta, clasif["materia"], clasif["tema"],
        clasif["confianza"], "seguimiento" if seguimiento else clasif["fuente"],
    )
    return respuesta, clasif
