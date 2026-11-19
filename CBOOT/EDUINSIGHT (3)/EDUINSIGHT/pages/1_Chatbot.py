"""Interfaz de conversación con el chatbot académico (Tutor Tec)."""

import streamlit as st

from core import ia_client, ui
from core.chatbot import responder
from core.classifier import TEMAS
from database import db

st.set_page_config(page_title="Tutor Tec · EDUINSIGHT", page_icon=ui.FAVICON,
                   layout="centered")
db.inicializar_db()
ui.aplicar_estilo()
st.markdown("<style>.block-container{max-width:900px;}</style>", unsafe_allow_html=True)

AVATAR = str(ui.LOGO_REDONDO)

# Píldoras de materia: cada una muestra el temario de esa materia
ICONOS_MATERIA = {
    "Programación": ":material/code:", "Cálculo": ":material/functions:",
    "Base de Datos": ":material/database:", "Métodos Numéricos": ":material/calculate:",
    "Química": ":material/science:", "Tópicos Avanzados de Programación": ":material/devices:",
    "Lenguajes y Autómatas": ":material/account_tree:",
}
NOMBRE_CORTO = {"Tópicos Avanzados de Programación": "Tópicos Avanzados"}
SUGERENCIAS = [(NOMBRE_CORTO.get(m, m), f"¿Qué temas tiene {m}?", ICONOS_MATERIA.get(m, ":material/school:"))
               for m in TEMAS] + [("Servicios del Tec", "Servicios del Tec", ":material/apartment:")]

BOTONES = [
    ("Más fácil", "Explícamelo más fácil", "sencillo", ":material/lightbulb:"),
    ("Paso a paso", "Explícamelo paso a paso", "pasos", ":material/format_list_numbered:"),
    ("Otro ejemplo", "Dame otro ejemplo", "ejemplo", ":material/sync:"),
    ("Ejercicio", "Ponme un ejercicio para practicar", "ejercicio", ":material/edit_note:"),
]

# ---------- Estado ----------
if "mensajes" not in st.session_state:
    st.session_state.mensajes = []
    st.session_state.contador = {}
    st.session_state.tema_actual = None
    st.session_state.ultima_accion = None


def pedir(texto, accion=None):
    """Guarda una petición para procesarla en la siguiente ejecución."""
    st.session_state.pendiente = (texto, accion)


# ---------- Barra lateral ----------
with st.sidebar:
    ui.titulo_lateral("Tus datos")
    matricula = st.text_input("Matrícula", value="23680000")
    semestre = st.selectbox("Semestre", list(range(1, 10)), index=2)

    ui.titulo_lateral("Inteligencia artificial")
    hay_ia = ia_client.disponible()
    usar_ia = st.toggle("Usar IA", value=hay_ia, disabled=not hay_ia)
    if hay_ia:
        st.caption(f"Conectado a {ia_client.nombre()}")
        if ia_client.ultimo_error():
            st.warning(ia_client.ultimo_error(), icon=":material/warning:")
    else:
        st.caption("No se detectó ninguna IA. Si usas Ollama, ábrelo y presiona Reintentar.")
        if st.button("Reintentar", width="stretch", icon=":material/autorenew:"):
            if ia_client.redetectar():
                st.rerun()
            else:
                st.error(f"No encontré Ollama en {ia_client.OLLAMA_URL}. Revisa que esté "
                         "abierto (ícono de la llama junto al reloj).")
        with st.expander("Activar IA con API key", expanded=False, icon=":material/key:"):
            st.markdown(
                "Pega la key de cualquiera de estos servicios:\n"
                "- **DeepSeek**: platform.deepseek.com, API keys (`sk-`)\n"
                "- **Grok (xAI)**: console.x.ai, API Keys (`xai-`)\n"
                "- **GitHub Models**: github.com/settings/tokens, token con permiso "
                "*Models: read* (`github_pat_`)\n"
                "- **OpenRouter**: openrouter.ai, Keys (`sk-or-`)\n"
                "- **Gemini**: aistudio.google.com, Get API key (`AIza`)\n"
                "- **Groq**: console.groq.com, API Keys (`gsk_`)"
            )
            key = st.text_input("API key", type="password", placeholder="Pega aquí tu key")
            if st.button("Guardar y activar", width="stretch", icon=":material/bolt:"):
                servicio = ia_client.guardar_key(key)
                if not servicio:
                    st.error("No reconozco esa key. Debe empezar con sk- (DeepSeek), xai-, "
                             "github_pat_, ghp_, sk-or-, AIza o gsk_")
                elif ia_client.probar():
                    st.success(f"IA activada con {servicio}.")
                    st.rerun()
                else:
                    st.error(ia_client.ultimo_error() or "No funcionó la key.")

    if st.session_state.tema_actual:
        ui.titulo_lateral("Tema actual")
        st.markdown(f"**{st.session_state.tema_actual}**")
        st.caption("Para preguntar de otro tema, solo escríbelo.")

    st.write("")
    if st.button("Nueva conversación", width="stretch", icon=":material/add_comment:",
                 type="primary"):
        del st.session_state.mensajes
        st.rerun()

# ---------- Portada o barra superior ----------
if not st.session_state.mensajes:
    st.markdown(
        f"""<div class="edu-hero">
              <div class="edu-halo"><img src="{ui.logo_html()}"></div>
              <h1>¿En qué te puedo<br><b>ayudar hoy?</b></h1>
              <p>Elige una materia para ver sus temas, pregúntame tu duda con tus palabras
                 o consulta trámites y servicios del Tec.</p>
            </div>""",
        unsafe_allow_html=True,
    )
    for fila in range(0, len(SUGERENCIAS), 4):
        cols = st.columns(4)
        for j, (materia, pregunta_ej, icono) in enumerate(SUGERENCIAS[fila:fila + 4]):
            cols[j].button(materia, key=f"sug{fila + j}", on_click=pedir, args=(pregunta_ej,),
                           width="stretch", icon=icono, help=pregunta_ej)
else:
    st.markdown(
        f"""<div class="edu-topbar"><div><img src="{ui.logo_html()}">Tutor Tec</div></div>""",
        unsafe_allow_html=True,
    )

# ---------- Conversación ----------
for m in st.session_state.mensajes:
    with st.chat_message(m["rol"], avatar=AVATAR if m["rol"] == "assistant" else None):
        st.markdown(m["texto"])
        if m.get("tema"):
            ui.chip(f"{m['materia']} · {m['tema']}")
            st.caption(f"Respondió: {m['respondio']}")
        if m.get("aviso"):
            st.caption(m["aviso"])

# Botones del temario: aparecen si el último mensaje trae opciones
ultimo = st.session_state.mensajes[-1] if st.session_state.mensajes else {}
if ultimo.get("opciones"):
    st.caption("Elige una opción")
    ops = ultimo["opciones"]
    for fila in range(0, len(ops), 3):
        cols = st.columns(3)
        for j, (tipo, valor) in enumerate(ops[fila:fila + 3]):
            texto = {"tema": f"Explícame {valor}", "materia": f"¿Qué temas tiene {valor}?",
                     "info": valor}[tipo]
            cols[j].button(NOMBRE_CORTO.get(valor, valor), key=f"op_{fila + j}", on_click=pedir,
                           args=(texto,), width="stretch",
                           icon=ICONOS_MATERIA.get(valor, ":material/info:" if tipo == "info"
                                                   else ":material/arrow_forward:"))

# Botones de ayuda sobre el tema actual
if st.session_state.tema_actual and not ultimo.get("opciones"):
    st.caption(f"¿Necesitas más ayuda con {st.session_state.tema_actual}?")
    botones = list(BOTONES)
    if st.session_state.ultima_accion == "ejercicio":
        botones.append(("Ver solución", "Muéstrame la solución", "solucion",
                        ":material/check_circle:"))
    cols = st.columns(len(botones))
    for col, (etiqueta, texto, accion, icono) in zip(cols, botones):
        col.button(etiqueta, key=f"b_{accion}", on_click=pedir, args=(texto, accion),
                   width="stretch", icon=icono)

# ---------- Procesar pregunta ----------
pregunta = st.chat_input("Escribe tu duda...")
accion = None
if "pendiente" in st.session_state:
    pregunta, accion = st.session_state.pop("pendiente")

if pregunta:
    # contexto para la IA: los últimos mensajes (sin el saludo)
    historial = [
        {"role": m["rol"], "content": m["texto"][:1200]}
        for m in st.session_state.mensajes[-6:]
    ]
    st.session_state.mensajes.append({"rol": "user", "texto": pregunta})
    with st.chat_message("user"):
        st.markdown(pregunta)

    with st.chat_message("assistant", avatar=AVATAR):
        with st.spinner("Pensando cómo explicártelo..."):
            respuesta, info = responder(
                pregunta, matricula, "ISC", semestre, usar_ia,
                tema_actual=st.session_state.tema_actual,
                historial=historial, accion=accion,
                contador=st.session_state.setdefault("contador", {}),
            )

    mensaje = {"rol": "assistant", "texto": respuesta, "opciones": info.get("opciones")}
    if info["tema"] and info["tema"] != "Otros temas":
        st.session_state.tema_actual = info["tema"]
        st.session_state.ultima_accion = info["accion"]
        mensaje.update(tema=info["tema"], materia=info["materia"], respondio=info["respondio"])
        if usar_ia and info["respondio"] == "base local" and ia_client.ultimo_error():
            mensaje["aviso"] = f"No se pudo usar la IA: {ia_client.ultimo_error()}"

    st.session_state.mensajes.append(mensaje)
    st.rerun()
