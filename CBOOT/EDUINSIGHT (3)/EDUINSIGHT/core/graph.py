"""Construye el grafo de relaciones entre conceptos.

- Nodos: temas. Tamaño = número de consultas. Color = materia.
- Aristas continuas: prerrequisitos (definidos en temas.json).
- Aristas punteadas: temas que un mismo estudiante preguntó juntos
  (co-ocurrencia). Entre más estudiantes, más gruesa la línea.
"""

import json
from itertools import combinations
from pathlib import Path

import networkx as nx
import plotly.graph_objects as go

BASE_DIR = Path(__file__).resolve().parent.parent
TEMAS = json.loads((BASE_DIR / "data" / "temas.json").read_text(encoding="utf-8"))

COLORES = ["#2B3A55", "#7CC242", "#FFB401", "#2BB3A0", "#E5527A", "#8B5CF6", "#0EA5E9", "#F97316"]


def construir_grafo(df, min_coocurrencia=2):
    G = nx.Graph()
    conteo = df["tema"].value_counts().to_dict() if not df.empty else {}

    for materia, temas in TEMAS.items():
        for tema, info in temas.items():
            G.add_node(tema, materia=materia, consultas=conteo.get(tema, 0))

    for temas in TEMAS.values():
        for tema, info in temas.items():
            for pre in info["prerrequisitos"]:
                if pre in G:
                    G.add_edge(pre, tema, tipo="prerrequisito", peso=1)

    if not df.empty:
        pares = {}
        for _, grupo in df.groupby("estudiante_id"):
            for a, b in combinations(sorted(set(grupo["tema"].dropna())), 2):
                pares[(a, b)] = pares.get((a, b), 0) + 1
        for (a, b), n in pares.items():
            if n < min_coocurrencia:
                continue
            if G.has_edge(a, b):
                G[a][b]["coocurrencia"] = n
            else:
                G.add_edge(a, b, tipo="coocurrencia", peso=n)
    return G


def temas_puente(G, n=5):
    """Temas más 'centrales': si se atoran ahí, afecta a muchos otros."""
    sub = nx.Graph([(u, v) for u, v, d in G.edges(data=True) if d["tipo"] == "prerrequisito"])
    if sub.number_of_nodes() == 0:
        return []
    c = nx.betweenness_centrality(sub)
    return sorted(c.items(), key=lambda x: x[1], reverse=True)[:n]


def figura_grafo(G, mostrar_coocurrencia=True):
    pos = nx.spring_layout(G, seed=7, k=0.9)
    materias = list(TEMAS.keys())
    color_de = {m: COLORES[i % len(COLORES)] for i, m in enumerate(materias)}
    fig = go.Figure()

    # aristas
    max_peso = max([d.get("peso", 1) for _, _, d in G.edges(data=True)] or [1])
    for u, v, d in G.edges(data=True):
        if d["tipo"] == "coocurrencia" and not mostrar_coocurrencia:
            continue
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        es_pre = d["tipo"] == "prerrequisito"
        fig.add_trace(go.Scatter(
            x=[x0, x1], y=[y0, y1], mode="lines", hoverinfo="none", showlegend=False,
            line=dict(
                width=2 if es_pre else 1 + 4 * d["peso"] / max_peso,
                color="#888" if es_pre else "rgba(150,150,150,0.45)",
                dash="solid" if es_pre else "dot",
            ),
        ))

    # nodos, una traza por materia para que salga la leyenda
    max_c = max([G.nodes[n]["consultas"] for n in G] or [1]) or 1
    for materia in materias:
        nodos = [n for n in G if G.nodes[n]["materia"] == materia]
        fig.add_trace(go.Scatter(
            x=[pos[n][0] for n in nodos],
            y=[pos[n][1] for n in nodos],
            mode="markers+text",
            name=materia,
            text=nodos,
            textposition="top center",
            marker=dict(
                size=[18 + 40 * G.nodes[n]["consultas"] / max_c for n in nodos],
                color=color_de[materia],
                line=dict(width=1, color="white"),
            ),
            customdata=[G.nodes[n]["consultas"] for n in nodos],
            hovertemplate="<b>%{text}</b><br>Consultas: %{customdata}<extra></extra>",
        ))

    fig.update_layout(
        height=560, margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        legend=dict(orientation="h", y=-0.05),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig
