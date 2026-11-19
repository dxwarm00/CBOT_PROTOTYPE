"""Identifica la materia y el tema de una pregunta.

Primero intenta con palabras clave (rápido y sin internet). Si no encuentra
nada claro y hay IA disponible (Groq u Ollama), le pide a la IA que elija un tema.
"""

import json
import re
import unicodedata
from pathlib import Path

from core import ia_client

BASE_DIR = Path(__file__).resolve().parent.parent
TEMAS = json.loads((BASE_DIR / "data" / "temas.json").read_text(encoding="utf-8"))


def normalizar(texto):
    """Minúsculas, sin acentos y sin signos raros."""
    texto = unicodedata.normalize("NFD", texto.lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9ñ ]", " ", texto)


# Otras formas de llamar a cada materia
ALIAS_MATERIA = {
    "Programación": ["programacion", "fundamentos de programacion", "programar"],
    "Cálculo": ["calculo", "calculo diferencial", "calculo integral"],
    "Base de Datos": ["base de datos", "bases de datos", "bd", "fundamentos de base de datos"],
    "Métodos Numéricos": ["metodos numericos", "numericos"],
    "Química": ["quimica"],
    "Tópicos Avanzados de Programación": ["topicos avanzados de programacion", "topicos avanzados",
                                          "topicos", "tap"],
    "Lenguajes y Autómatas": ["lenguajes y automatas", "lenguajes automatas", "automatas",
                              "compiladores", "lya"],
}

FRASES_TEMARIO = ["temas", "temario", "que se ve", "que veo", "que vemos", "que lleva",
                  "que incluye", "que abarca", "de que trata", "unidades", "que contiene",
                  "que tiene", "que aprendo", "que se aprende", "contenido"]
FRASES_MATERIAS = ["que materias", "cuales materias", "materias tienes", "materias puedes",
                   "materias manejas", "en que materias", "que sabes"]

# Palabras que suelen aparecer en preguntas de escuela (para distinguirlas de las que no lo son)
PALABRAS_EDUCATIVAS = [
    "explica", "explicame", "no entiendo", "no le entiendo", "duda", "dudas", "que es", "que son", "como se", "como funciona", "como hago",
    "como resuelvo", "para que sirve", "diferencia entre", "ejemplo", "ejercicio", "tarea",
    "examen", "materia", "tema", "clase", "formula", "calcular", "resolver", "definicion",
    "concepto", "teoria", "metodo", "algoritmo", "codigo", "programa", "ecuacion", "problema",
    "estudiar", "aprender", "profe", "profesor", "unidad", "practica", "proyecto",
    "fisica", "historia", "biologia", "ingles", "matematicas", "algebra", "estadistica",
    "probabilidad", "electronica", "circuito", "redes", "sistemas operativos", "contabilidad",
]


def _contiene(texto, frases):
    t = f" {normalizar(texto)} "
    return any(f" {f} " in t for f in frases)


def detectar_materia(texto):
    """Regresa la materia mencionada en el texto, o None."""
    t = f" {normalizar(texto)} "
    mejor = None
    for materia, alias in ALIAS_MATERIA.items():
        for a in alias + [normalizar(materia).strip()]:
            if f" {a} " in t and (mejor is None or len(a) > mejor[1]):
                mejor = (materia, len(a))
    return mejor[0] if mejor else None


def pide_temario(texto):
    return _contiene(texto, FRASES_TEMARIO)


def pide_materias(texto):
    return _contiene(texto, FRASES_MATERIAS)


def parece_educativa(texto):
    return _contiene(texto, PALABRAS_EDUCATIVAS)


def lista_temas():
    """[(materia, tema), ...]"""
    return [(m, t) for m, temas in TEMAS.items() for t in temas]


def clasificar_por_reglas(pregunta):
    texto = f" {normalizar(pregunta)} "
    puntajes = []
    for materia, temas in TEMAS.items():
        for tema, info in temas.items():
            puntos = 0
            # el nombre del tema también cuenta como palabra clave (vale más)
            nombre = re.sub(r"\s+", " ", normalizar(tema)).strip()
            if f" {nombre} " in texto:
                puntos += 3 + nombre.count(" ")
            for palabra in info["palabras"]:
                if f" {palabra} " in texto:
                    # las frases largas pesan más que una palabra suelta
                    puntos += 1 + palabra.count(" ")
            if puntos:
                puntajes.append((puntos, materia, tema))

    if not puntajes:
        return None

    puntajes.sort(reverse=True)
    mejor, materia, tema = puntajes[0]
    total = sum(p for p, _, _ in puntajes)
    return {"materia": materia, "tema": tema, "confianza": round(mejor / total, 2), "fuente": "reglas"}


def clasificar_con_ia(pregunta):
    opciones = "\n".join(f"- {m} | {t}" for m, t in lista_temas())
    prompt = (
        "Clasifica la pregunta de un estudiante en UNO de estos temas.\n"
        f"{opciones}\n- Ninguno | Ninguno\n\n"
        f"Pregunta: {pregunta}\n\n"
        "Responde solo con el formato: Materia | Tema"
    )
    salida = ia_client.generar(prompt, temperatura=0)
    if not salida:
        return None
    for materia, tema in lista_temas():
        if tema.lower() in salida.lower():
            return {"materia": materia, "tema": tema, "confianza": 0.6, "fuente": "ia"}
    return None


def clasificar(pregunta, usar_ia=True):
    """Regresa dict con materia, tema, confianza y fuente. Si no sabe, tema=None."""
    resultado = clasificar_por_reglas(pregunta)
    if resultado:
        return resultado
    resultado = clasificar_con_ia(pregunta) if usar_ia else None
    if resultado:
        return resultado
    return {"materia": None, "tema": None, "confianza": 0.0, "fuente": "sin_clasificar"}
