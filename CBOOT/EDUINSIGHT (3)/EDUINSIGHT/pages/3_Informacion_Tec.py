"""Página para capturar la información del Tec que contesta el bot
(becas, ubicaciones, inglés, constancias...). Lo que se guarda aquí lo usan
la página del chatbot y el bot de Telegram al momento."""

import re
from datetime import date

import pandas as pd
import streamlit as st

from core import institucional, ui
from database import db

st.set_page_config(page_title="Información del Tec · EDUINSIGHT", page_icon=ui.FAVICON,
                   layout="wide")
db.inicializar_db()
ui.aplicar_estilo()

ui.encabezado(
    "Información del Tec",
    "Lo que captures aquí es lo que el bot contesta sobre trámites y servicios. "
    "Si una respuesta está vacía, el bot no inventa: manda al alumno a preguntar al área indicada.",
    kicker="Atención a alumnos",
)

entradas = institucional.cargar()
capturadas = sum(1 for e in entradas if (e.get("respuesta") or "").strip())
c1, c2, c3 = st.columns(3)
c1.metric("Temas de atención", len(entradas))
c2.metric("Con respuesta capturada", capturadas)
c3.metric("Pendientes", len(entradas) - capturadas)

ui.seccion("Respuestas",
           "Edita directo en la tabla. Las palabras clave van separadas por comas y sirven para "
           "reconocer la pregunta (no importan acentos ni mayúsculas). Puedes agregar filas nuevas "
           "al final.")

tabla = pd.DataFrame([{
    "titulo": e.get("titulo", ""),
    "respuesta": e.get("respuesta", ""),
    "donde_preguntar": e.get("donde_preguntar", ""),
    "actualizado": e.get("actualizado", ""),
    "pregunta_ejemplo": e.get("pregunta_ejemplo", ""),
    "palabras": ", ".join(e.get("palabras", [])),
} for e in entradas])

editada = st.data_editor(
    tabla, num_rows="dynamic", width="stretch", hide_index=True, height=520,
    column_config={
        "titulo": st.column_config.TextColumn("Tema", required=True, width="medium"),
        "respuesta": st.column_config.TextColumn(
            "Respuesta del bot", width="large",
            help="Ejemplo: 'Servicios Escolares está en el edificio X, planta baja. "
                 "Horario: lunes a viernes de 9:00 a 14:00.'"),
        "donde_preguntar": st.column_config.TextColumn(
            "Si no hay respuesta, ir a...", width="medium"),
        "actualizado": st.column_config.TextColumn(
            "Actualizado", width="small", help="Fecha en que verificaste el dato, ej. 19/11/2026"),
        "pregunta_ejemplo": st.column_config.TextColumn("Pregunta de ejemplo", width="medium"),
        "palabras": st.column_config.TextColumn("Palabras clave", width="large"),
    },
)

a, b, _ = st.columns([1, 1.3, 3])
if a.button("Guardar cambios", type="primary", icon=":material/save:", width="stretch"):
    nuevas = []
    for _, fila in editada.fillna("").iterrows():
        titulo = str(fila["titulo"]).strip()
        if not titulo:
            continue
        ident = re.sub(r"[^a-z0-9]+", "_", institucional.normalizar(titulo)).strip("_")
        nuevas.append({
            "id": ident,
            "titulo": titulo,
            "pregunta_ejemplo": str(fila["pregunta_ejemplo"]).strip() or f"{titulo}?",
            "palabras": [p.strip() for p in str(fila["palabras"]).split(",") if p.strip()],
            "respuesta": str(fila["respuesta"]).strip(),
            "donde_preguntar": str(fila["donde_preguntar"]).strip() or "Servicios Escolares",
            "actualizado": str(fila["actualizado"]).strip(),
        })
    institucional.guardar(nuevas)
    st.success(f"Guardado. {len(nuevas)} temas de atención.", icon=":material/check_circle:")
    st.rerun()

if b.button("Marcar fecha de hoy en las que tienen respuesta", icon=":material/event:",
            width="stretch"):
    hoy = date.today().strftime("%d/%m/%Y")
    for e in entradas:
        if (e.get("respuesta") or "").strip():
            e["actualizado"] = hoy
    institucional.guardar(entradas)
    st.rerun()

ui.seccion("Probar", "Escribe una pregunta como la haría un alumno y mira qué contestaría el bot.")
prueba = st.text_input("Pregunta de prueba", placeholder="¿En qué edificio está la biblioteca?")
if prueba:
    e = institucional.buscar(prueba)
    if e:
        st.caption(f"Reconocida como: {e['titulo']}")
        st.markdown(institucional.responder(e))
    else:
        st.warning("No coincide con ningún tema de atención. Agrega palabras clave al tema que "
                   "corresponda.")
