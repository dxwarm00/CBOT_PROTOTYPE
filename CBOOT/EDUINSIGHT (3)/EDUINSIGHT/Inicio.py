"""EDUINSIGHT - Página principal.

Ejecutar con:  streamlit run Inicio.py
"""

import streamlit as st

from core import analytics, ia_client, ui
from database import db

st.set_page_config(page_title="EDUINSIGHT", page_icon=ui.FAVICON, layout="wide")
db.inicializar_db()
ui.aplicar_estilo()

df = db.obtener_consultas()
k = analytics.indicadores(df)

# ---------- Saludo y titular ----------
st.markdown(
    f"""<div class="edu-saludo"><img src="{ui.logo_html()}">Hola, bienvenido a EDUINSIGHT</div>
        <div class="edu-titular">¿Necesitas ayuda<br><span>estudiando</span> hoy?</div>""",
    unsafe_allow_html=True,
)

a, b, _ = st.columns([1.2, 1.2, 3])
a.page_link("pages/1_Chatbot.py", label="Hacer una pregunta", icon=":material/forum:")
b.page_link("pages/2_Dashboard.py", label="Ver el panel", icon=":material/monitoring:")
st.write("")

# ---------- Tarjeta lima ----------
ui.encabezado(
    "Analítica del aprendizaje",
    "Convertimos las dudas de los estudiantes en información para mejorar la enseñanza.",
    kicker="Instituto Tecnológico de Cuautla",
)

# ---------- Accesos ----------
c1, c2, c3 = st.columns(3)
with c1:
    ui.tarjeta("Tutor Tec",
               "Explica tus dudas con ejemplos, paso a paso y con ejercicios para practicar.",
               icono="school")
with c2:
    ui.tarjeta("Panel de analítica",
               "Qué temas cuestan más, cómo se relacionan y qué acciones conviene tomar.",
               icono="insights")
with c3:
    ui.tarjeta("Bot de Telegram",
               "El mismo tutor desde Telegram; sus preguntas también llegan al panel.",
               icono="send")

# ---------- Números ----------
ui.seccion("En números")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Consultas registradas", k["consultas"])
m2.metric("Estudiantes", k["estudiantes"])
m3.metric("Temas detectados", k["temas"])
m4.metric("Tema con más dudas", k["tema_top"])

ui.seccion("Cómo funciona")
p1, p2, p3 = st.columns(3)
with p1:
    ui.tarjeta("1. El alumno pregunta",
               "Escribe su duda con sus palabras en la página o en Telegram.", icono="edit_note")
with p2:
    ui.tarjeta("2. Se clasifica la duda",
               "Cada pregunta se identifica por materia y tema, y se guarda solo con la "
               "matrícula.", icono="category")
with p3:
    ui.tarjeta("3. La escuela decide",
               "Con los datos se abren tutorías, talleres o material de apoyo donde hace falta.",
               icono="task_alt")

# ---------- Barra lateral ----------
with st.sidebar:
    ui.titulo_lateral("Estado del sistema")
    if ia_client.disponible():
        st.success(f"IA conectada: {ia_client.nombre()}", icon=":material/check_circle:")
    else:
        st.info("IA sin activar. Actívala desde el chatbot; mientras, se usa la base local.",
                icon=":material/info:")
    st.write("")
    if st.button("Reiniciar datos de prueba", width="stretch", icon=":material/restart_alt:"):
        db.reiniciar_db()
        st.rerun()
