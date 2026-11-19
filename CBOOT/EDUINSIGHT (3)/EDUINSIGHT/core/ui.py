"""Estilos visuales compartidos por todas las páginas de EDUINSIGHT.

Estilo: fondo verde menta suave, tarjetas blancas muy redondeadas, botones tipo
píldora y acento verde lima. El logo está en assets/logo.png.
"""

import base64
from functools import lru_cache
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent
LOGO = BASE_DIR / "assets" / "logo.png"
LOGO_REDONDO = BASE_DIR / "assets" / "logo_redondo.png"
FAVICON = str(BASE_DIR / "assets" / "favicon.png")

# Colores
LIMA = "#B5E655"
LIMA_FUERTE = "#5DAE1F"
TINTA = "#1F2937"
GRIS = "#6B7280"
AMARILLO = "#FFB401"   # del logo
AZUL_LOGO = "#2B3A55"  # del logo

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');

html, body, [class*="css"], .stMarkdown, button, input, textarea {
    font-family: 'Plus Jakarta Sans', 'Segoe UI', sans-serif !important;
}

/* Fondo con brillo verde suave, como la referencia */
[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(900px 500px at 15% -10%, #E3F4D2 0%, transparent 60%),
        radial-gradient(800px 500px at 100% 0%, #EAF6E4 0%, transparent 55%),
        #F2F6EF;
}
[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 1.6rem; padding-bottom: 7rem; max-width: 1150px; }

/* ---------- Tarjetas ---------- */
.edu-card {
    background: rgba(255,255,255,.92); border: 1px solid #E5ECE1; border-radius: 24px;
    padding: 1.15rem 1.25rem; height: 100%;
    box-shadow: 0 8px 24px rgba(31, 41, 55, 0.05);
}
.edu-card h4 { margin: 0 0 .35rem 0; font-size: 1.02rem; font-weight: 700; color: #1F2937; }
.edu-card p  { margin: 0; color: #6B7280; font-size: .92rem; line-height: 1.5; }
.edu-icono {
    width: 42px; height: 42px; border-radius: 999px; display: flex; align-items: center;
    justify-content: center; margin-bottom: .7rem; font-size: 1.25rem;
    background: #EEF7E3; color: #3F7F12;
}
.material-symbols-rounded {
    font-family: 'Material Symbols Rounded'; font-weight: normal; font-style: normal;
    line-height: 1; letter-spacing: normal; text-transform: none; display: inline-block;
    white-space: nowrap; direction: ltr; -webkit-font-feature-settings: 'liga';
    font-feature-settings: 'liga'; -webkit-font-smoothing: antialiased;
}
.edu-icono .material-symbols-rounded { font-size: 22px; }

/* Tarjeta promocional verde lima */
.edu-promo {
    background: linear-gradient(135deg, #D7F59C 0%, #B5E655 55%, #9FD846 100%);
    border-radius: 26px; padding: 1.4rem 1.6rem; color: #1F2937;
    box-shadow: 0 14px 34px rgba(93, 174, 31, 0.25);
    display: flex; align-items: center; gap: 1.1rem; margin-bottom: 1.2rem;
}
.edu-promo img { width: 64px; height: 64px; border-radius: 18px; flex-shrink: 0;
                 box-shadow: 0 6px 16px rgba(0,0,0,.12); }
.edu-promo .kicker { font-size: .72rem; letter-spacing: .14em; text-transform: uppercase;
                     font-weight: 700; opacity: .65; }
.edu-promo h1 { font-size: 1.65rem !important; font-weight: 800 !important; margin: .1rem 0 0 0 !important;
                padding: 0 !important; color: #1F2937 !important; line-height: 1.15; }
.edu-promo p { margin: .3rem 0 0 0; color: #2F3B1F; font-size: .95rem; }

/* Titular grande de dos tonos */
.edu-titular { font-size: 2.6rem; line-height: 1.1; font-weight: 800; color: #1F2937;
               margin: .2rem 0 1.1rem 0; letter-spacing: -.02em; }
.edu-titular span { font-weight: 300; color: #6B7280; }
.edu-saludo { display: inline-flex; align-items: center; gap: .6rem; background: #fff;
              border: 1px solid #E5ECE1; border-radius: 999px; padding: .3rem .9rem .3rem .3rem;
              font-weight: 600; font-size: .9rem; color: #1F2937; }
.edu-saludo img { width: 30px; height: 30px; border-radius: 999px; }

/* ---------- Portada del chat ---------- */
.edu-hero { text-align: center; padding: 1.2rem 0 1.4rem 0; }
.edu-halo {
    width: 150px; height: 150px; margin: 0 auto 1.4rem auto; border-radius: 999px;
    display: flex; align-items: center; justify-content: center;
    background: radial-gradient(circle, rgba(181,230,85,.55) 0%, rgba(181,230,85,.18) 55%, rgba(181,230,85,0) 72%);
    box-shadow: 0 0 0 14px rgba(181,230,85,.12), 0 0 0 30px rgba(181,230,85,.07);
}
.edu-halo img { width: 92px; height: 92px; border-radius: 26px;
                box-shadow: 0 10px 26px rgba(93,174,31,.35); }
.edu-hero h1 { font-size: 2.7rem !important; font-weight: 300 !important; color: #1F2937 !important;
               line-height: 1.12 !important; padding: 0 !important; letter-spacing: -.02em; }
.edu-hero h1 b { font-weight: 800; }
.edu-hero p { color: #6B7280; margin-top: .6rem; }

/* Barra superior compacta del chat */
.edu-topbar { display: flex; justify-content: center; margin-bottom: 1rem; }
.edu-topbar div { display: inline-flex; align-items: center; gap: .5rem; background: #fff;
                  border: 1px solid #E5ECE1; border-radius: 999px; padding: .35rem 1rem .35rem .35rem;
                  font-weight: 700; font-size: .92rem; color: #1F2937;
                  box-shadow: 0 6px 18px rgba(31,41,55,.05); }
.edu-topbar img { width: 28px; height: 28px; border-radius: 999px; }

/* ---------- Métricas ---------- */
div[data-testid="stMetric"] {
    background: rgba(255,255,255,.92); border: 1px solid #E5ECE1; border-radius: 22px;
    padding: 1rem 1.2rem; box-shadow: 0 8px 24px rgba(31, 41, 55, 0.05);
}
div[data-testid="stMetricLabel"] p { color: #6B7280 !important; font-weight: 600; font-size: .85rem; }
div[data-testid="stMetricValue"] { color: #1F2937; font-weight: 800;
                                   font-size: clamp(1.25rem, 1.6vw, 1.85rem); }
div[data-testid="stMetricValue"] * { white-space: normal !important; overflow: visible !important;
                                     text-overflow: clip !important; word-break: keep-all; }

div[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 22px; }

/* ---------- Chat ---------- */
div[data-testid="stChatMessage"] {
    background: rgba(255,255,255,.95); border: 1px solid #E5ECE1; border-radius: 24px;
    padding: 1rem 1.2rem; margin-bottom: .8rem; margin-right: 6%;
    box-shadow: 0 8px 24px rgba(31, 41, 55, 0.05);
}
div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
    flex-direction: row-reverse; background: #1F2937; border-color: #1F2937;
    margin-left: auto; margin-right: 0; width: fit-content; max-width: 85%;
}
div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) p,
div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) li {
    color: #fff !important;
}
[data-testid="stChatMessageAvatarUser"] { background: #B5E655 !important; color: #1F2937 !important; }
[data-testid="stChatMessageAvatarImage"] img,
[data-testid="stChatMessageAvatarImage"] { border-radius: 12px !important; }
div[data-testid="stChatMessage"] pre { border-radius: 16px; }

/* Caja para escribir */
div[data-testid="stChatInput"] {
    border-radius: 24px !important; border: 1px solid #DCE8D3 !important;
    background: #fff !important; box-shadow: 0 12px 34px rgba(31, 41, 55, 0.10);
}
div[data-testid="stChatInput"] button {
    background: #B5E655 !important; border-radius: 999px !important; color: #1F2937 !important;
}

/* Etiqueta de tema */
.edu-chip { display: inline-block; font-size: .74rem; font-weight: 600; padding: .25rem .7rem;
            border-radius: 999px; background: #EEF7E3; color: #3F7F12; margin-top: .25rem; }
.edu-chip.gris { background: #F1F3F0; color: #6B7280; }

/* ---------- Botones tipo píldora ---------- */
.stButton button, .stDownloadButton button {
    border-radius: 999px; font-weight: 600; border: 1px solid #E0E9DA;
    background: #fff; color: #1F2937; transition: all .15s ease;
    box-shadow: 0 4px 12px rgba(31,41,55,.04);
}
.stButton button:hover, .stDownloadButton button:hover {
    border-color: #B5E655; background: #B5E655; color: #1F2937; transform: translateY(-1px);
}
.stButton button[kind="primary"] { background: #1F2937; color: #fff; border-color: #1F2937; }
.stButton button[kind="primary"]:hover { background: #B5E655; color: #1F2937; border-color: #B5E655; }

/* Enlaces a páginas como píldoras */
a[data-testid="stPageLink-NavLink"] {
    border-radius: 999px; background: #1F2937; padding: .45rem 1rem !important;
    width: fit-content;
}
a[data-testid="stPageLink-NavLink"] p, a[data-testid="stPageLink-NavLink"] span { color: #fff !important; }
a[data-testid="stPageLink-NavLink"]:hover { background: #5DAE1F; }

/* ---------- Barra lateral ---------- */
section[data-testid="stSidebar"] { background: rgba(255,255,255,.85); border-right: 1px solid #E5ECE1; }
.edu-side-title { font-size: .72rem; letter-spacing: .12em; text-transform: uppercase;
                  color: #9CA3AF; font-weight: 700; margin: .5rem 0 .4rem 0; }
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a { border-radius: 999px; }

/* Entradas de texto y selects redondeados */
div[data-baseweb="input"], div[data-baseweb="select"] > div { border-radius: 14px !important; }

/* Pestañas como píldoras */
[data-testid="stTabs"] [role="tablist"] { gap: .45rem; border-bottom: none !important; box-shadow: none !important; }
[data-testid="stTab"] {
    background: #fff; border-radius: 999px !important; padding: .45rem 1.05rem !important;
    border: 1px solid #E5ECE1 !important; font-weight: 600; height: auto !important;
}
[data-testid="stTab"]::after, [data-testid="stTab"]::before { display: none !important; }
[data-testid="stTab"][aria-selected="true"] { background: #1F2937; border-color: #1F2937 !important;
                                              box-shadow: none !important; }
[data-testid="stTab"][aria-selected="true"] * { color: #fff !important; }
[data-testid="stTab"]:hover { border-color: #B5E655 !important; }

#MainMenu, footer, [data-testid="stDecoration"] { visibility: hidden; }
</style>
"""


@lru_cache(maxsize=4)
def _img64(ruta):
    return base64.b64encode(Path(ruta).read_bytes()).decode()


def logo_html(ruta=LOGO_REDONDO):
    return f"data:image/png;base64,{_img64(str(ruta))}"


def aplicar_estilo():
    st.markdown(CSS, unsafe_allow_html=True)
    try:
        st.logo(str(LOGO_REDONDO), size="large")
    except Exception:
        pass


def encabezado(titulo, subtitulo="", kicker="EDUINSIGHT"):
    """Tarjeta verde lima con el logo (estilo 'Unlock Study Pro' de la referencia)."""
    st.markdown(
        f"""<div class="edu-promo">
              <img src="{logo_html()}">
              <div>
                <div class="kicker">{kicker}</div>
                <h1>{titulo}</h1>
                {f'<p>{subtitulo}</p>' if subtitulo else ''}
              </div>
            </div>""",
        unsafe_allow_html=True,
    )


def tarjeta(titulo, texto, icono=None):
    icono_html = (f'<div class="edu-icono"><span class="material-symbols-rounded">{icono}'
                  f'</span></div>' if icono else "")
    st.markdown(f'<div class="edu-card">{icono_html}<h4>{titulo}</h4><p>{texto}</p></div>',
                unsafe_allow_html=True)


def chip(texto, gris=False):
    st.markdown(f'<span class="edu-chip{" gris" if gris else ""}">{texto}</span>',
                unsafe_allow_html=True)


def titulo_lateral(texto):
    st.sidebar.markdown(f'<div class="edu-side-title">{texto}</div>', unsafe_allow_html=True)


def seccion(titulo, descripcion=""):
    st.markdown(f"<h4 style='margin:1.3rem 0 .1rem 0;font-weight:700'>{titulo}</h4>",
                unsafe_allow_html=True)
    if descripcion:
        st.caption(descripcion)


# ---------- Gráficas ----------
PALETA = ["#2B3A55", "#7CC242", "#FFB401", "#2BB3A0", "#E5527A", "#8B5CF6"]
COLOR_MATERIA = {"Programación": "#2B3A55", "Cálculo": "#7CC242",
                 "Base de Datos": "#FFB401", "Métodos Numéricos": "#2BB3A0",
                 "Química": "#E5527A", "Tópicos Avanzados de Programación": "#8B5CF6",
                 "Lenguajes y Autómatas": "#0EA5E9", "Otras materias": "#9CA3AF",
                 "Servicios del Tec": "#F97316"}


def estilo_grafica(fig, alto=360):
    """Aplica el mismo estilo a todas las gráficas de Plotly."""
    fig.update_layout(
        template="plotly_white", colorway=PALETA, height=alto,
        margin=dict(l=10, r=10, t=10, b=10),
        font=dict(family="Plus Jakarta Sans, Segoe UI, sans-serif", color="#1F2937", size=13),
        legend=dict(orientation="h", y=-0.18, title_text=""),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        hoverlabel=dict(font_family="Plus Jakarta Sans, Segoe UI, sans-serif"),
    )
    fig.update_xaxes(gridcolor="#E3EADF", zeroline=False)
    fig.update_yaxes(gridcolor="#E3EADF", zeroline=False)
    return fig


COLOR_PRIORIDAD = {"Alta": ("#FDECEF", "#C2264B"), "Media": ("#FFF4DB", "#9A6400"),
                   "Baja": ("#EEF7E3", "#3F7F12")}


def recomendacion(r):
    fondo, texto = COLOR_PRIORIDAD[r["prioridad"]]
    materia = f" · {r['materia']}" if r["materia"] != "-" else ""
    tema = r["tema"] if r["tema"] != "-" else "Seguimiento individual"
    st.markdown(
        f"""<div class="edu-card" style="margin-bottom:.8rem">
              <span class="edu-chip" style="background:{fondo};color:{texto}">
                Prioridad {r['prioridad'].lower()}</span>
              <span class="edu-chip gris">{r['tipo']}</span>
              <h4 style="margin-top:.6rem">{tema}<span style="color:#9CA3AF;font-weight:500">{materia}</span></h4>
              <p>{r['detalle'].replace('**', '')}</p>
            </div>""",
        unsafe_allow_html=True,
    )
