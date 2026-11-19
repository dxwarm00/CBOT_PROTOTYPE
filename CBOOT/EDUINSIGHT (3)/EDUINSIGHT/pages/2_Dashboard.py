"""Panel de analítica académica."""

import plotly.express as px
import streamlit as st

from core import analytics, graph, recommendations, ui
from database import db

st.set_page_config(page_title="Panel · EDUINSIGHT", page_icon=ui.FAVICON,
                   layout="wide")
db.inicializar_db()
ui.aplicar_estilo()

ui.encabezado(
    "Panel de analítica académica",
    "Qué preguntan los alumnos, qué les cuesta entender y qué puede hacer la institución.",
)

df_total = db.obtener_consultas()
if df_total.empty:
    st.info("Todavía no hay consultas registradas.")
    st.stop()

# ---------- Filtros ----------
with st.sidebar:
    ui.titulo_lateral("Filtros")
    materias = st.multiselect("Materia", sorted(df_total["materia"].dropna().unique()),
                              placeholder="Todas")
    semestres = st.multiselect("Semestre",
                               sorted(df_total["semestre"].dropna().unique().astype(int)),
                               placeholder="Todos")
    periodo = st.selectbox("Periodo", ["Todo", "Últimos 7 días", "Últimos 14 días",
                                       "Últimos 30 días"])
    dias = {"Todo": None, "Últimos 7 días": 7, "Últimos 14 días": 14,
            "Últimos 30 días": 30}[periodo]

df = analytics.filtrar(df_total, materias, semestres, dias)
if df.empty:
    st.warning("No hay datos con esos filtros.")
    st.stop()

# ---------- Indicadores ----------
k = analytics.indicadores(df)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Consultas", k["consultas"])
c2.metric("Estudiantes", k["estudiantes"])
c3.metric("Temas", k["temas"])
c4.metric("Tema más consultado", k["tema_top"])

st.write("")
tab1, tab2, tab3, tab4 = st.tabs([":material/bar_chart: Resumen",
                                  ":material/hub: Grafo de conceptos",
                                  ":material/tips_and_updates: Recomendaciones",
                                  ":material/table: Datos"])

# ---------- Resumen ----------
with tab1:
    izq, der = st.columns(2)
    with izq:
        ui.seccion("Temas con más dudas")
        por_tema = analytics.consultas_por_tema(df).head(10)
        fig = px.bar(por_tema, x="consultas", y="tema", color="materia", orientation="h",
                     color_discrete_map=ui.COLOR_MATERIA)
        fig.update_layout(yaxis=dict(categoryorder="total ascending", title=""),
                          xaxis_title="Consultas")
        st.plotly_chart(ui.estilo_grafica(fig, 400), theme=None, width="stretch")
    with der:
        ui.seccion("Consultas por materia")
        fig = px.pie(df, names="materia", hole=0.55, color="materia",
                     color_discrete_map=ui.COLOR_MATERIA)
        fig.update_traces(textinfo="percent", marker=dict(line=dict(color="#fff", width=2)))
        st.plotly_chart(ui.estilo_grafica(fig, 400), theme=None, width="stretch")

    izq, der = st.columns(2)
    with izq:
        ui.seccion("Consultas por día")
        fig = px.area(analytics.consultas_por_dia(df), x="dia", y="consultas",
                      color_discrete_sequence=["#2B3A55"])
        fig.update_traces(line=dict(width=2.5), fillcolor="rgba(124,194,66,0.22)")
        fig.update_layout(xaxis_title="", yaxis_title="Consultas")
        st.plotly_chart(ui.estilo_grafica(fig, 320), theme=None, width="stretch")
    with der:
        ui.seccion("¿A qué hora preguntan?")
        fig = px.bar(analytics.consultas_por_hora(df), x="hora", y="consultas",
                     color_discrete_sequence=["#7CC242"])
        fig.update_layout(xaxis_title="Hora del día", yaxis_title="Consultas")
        st.plotly_chart(ui.estilo_grafica(fig, 320), theme=None, width="stretch")

    ui.seccion("Temas que más cuesta entender",
               "Veces que un alumno pidió que se lo explicaran otra vez "
               "(más fácil, paso a paso u otro ejemplo).")
    dif = analytics.temas_dificiles(df)
    if dif.empty:
        st.info("Todavía no hay re-explicaciones registradas.")
    else:
        fig = px.bar(dif.head(8), x="tema", y="reexplicaciones", color="materia",
                     color_discrete_map=ui.COLOR_MATERIA, hover_data=["consultas", "%_reexplicacion"])
        fig.update_layout(xaxis_title="", yaxis_title="Re-explicaciones")
        st.plotly_chart(ui.estilo_grafica(fig, 320), theme=None, width="stretch")

    tramites = df[df["materia"] == "Servicios del Tec"]
    ui.seccion("Trámites que más preguntan",
               "Preguntas de atención a alumnos: becas, inglés, constancias, ubicaciones...")
    if tramites.empty:
        st.info("Todavía no hay preguntas de trámites.")
    else:
        conteo = tramites["tema"].value_counts().reset_index()
        conteo.columns = ["trámite", "preguntas"]
        fig = px.bar(conteo, x="preguntas", y="trámite", orientation="h",
                     color_discrete_sequence=["#F97316"])
        fig.update_layout(yaxis=dict(categoryorder="total ascending", title=""))
        st.plotly_chart(ui.estilo_grafica(fig, 300), theme=None, width="stretch")

    ui.seccion("Temas en aumento", "Últimas 2 semanas comparadas con las 2 anteriores.")
    tend = analytics.tendencia_temas(df).head(8)
    st.dataframe(
        tend, width="stretch", hide_index=True,
        column_config={
            "tema": "Tema", "materia": "Materia",
            "reciente": st.column_config.NumberColumn("Últimas 2 semanas", format="%d"),
            "anterior": st.column_config.NumberColumn("2 semanas antes", format="%d"),
            "cambio_%": st.column_config.NumberColumn("Cambio", format="%+d%%"),
        },
    )

# ---------- Grafo ----------
with tab2:
    ui.seccion("Grafo de conceptos",
               "Cada círculo es un tema (más grande = más dudas). Las líneas continuas son "
               "prerrequisitos y las punteadas unen temas que los mismos alumnos preguntaron.")
    f1, f2 = st.columns([2, 1])
    min_co = f1.slider("Mínimo de alumnos en común para mostrar una relación", 1, 6, 3)
    ver_co = f2.toggle("Mostrar temas preguntados juntos", value=True)
    G = graph.construir_grafo(df, min_coocurrencia=min_co)
    st.plotly_chart(graph.figura_grafo(G, ver_co), theme=None, width="stretch")

    ui.seccion("Temas puente",
               "Temas de los que dependen muchos otros: si un alumno se atora aquí, se atora "
               "en lo que sigue.")
    puentes = graph.temas_puente(G)
    cols = st.columns(len(puentes) or 1)
    for col, (tema, valor) in zip(cols, puentes):
        with col:
            ui.tarjeta(tema, f"Centralidad {valor:.2f}<br>{G.nodes[tema]['consultas']} consultas")

# ---------- Recomendaciones ----------
with tab3:
    recs = recommendations.generar(df)
    ui.seccion("Acciones sugeridas",
               "Generadas automáticamente a partir de los datos, ordenadas por prioridad.")
    if not recs:
        st.success("No hay alertas con los datos actuales.")
    izq, der = st.columns(2)
    for i, r in enumerate(recs):
        with (izq if i % 2 == 0 else der):
            ui.recomendacion(r)

# ---------- Datos ----------
with tab4:
    columnas = ["fecha", "matricula", "semestre", "materia", "tema", "pregunta", "fuente"]
    ui.seccion("Consultas registradas")
    st.dataframe(df[columnas].sort_values("fecha", ascending=False),
                 width="stretch", hide_index=True,
                 column_config={"fecha": st.column_config.DatetimeColumn(
                     "Fecha", format="DD/MM/YYYY HH:mm")})
    st.download_button("Descargar CSV", df[columnas].to_csv(index=False).encode("utf-8"),
                       "consultas_eduinsight.csv", "text/csv", icon=":material/download:")
