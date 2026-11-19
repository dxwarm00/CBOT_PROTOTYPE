"""Cálculo de estadísticas a partir de las consultas guardadas."""

import pandas as pd


def filtrar(df, materias=None, semestres=None, dias=None):
    if df.empty:
        return df
    if materias:
        df = df[df["materia"].isin(materias)]
    if semestres:
        df = df[df["semestre"].isin(semestres)]
    if dias:
        limite = df["fecha"].max() - pd.Timedelta(days=dias)
        df = df[df["fecha"] >= limite]
    return df


def indicadores(df):
    if df.empty:
        return {"consultas": 0, "estudiantes": 0, "temas": 0, "tema_top": "-"}
    return {
        "consultas": len(df),
        "estudiantes": df["estudiante_id"].nunique(),
        "temas": df["tema"].nunique(),
        "tema_top": df["tema"].value_counts().idxmax(),
    }


def consultas_por_tema(df):
    return (
        df.groupby(["materia", "tema"]).size()
        .reset_index(name="consultas")
        .sort_values("consultas", ascending=False)
    )


def consultas_por_dia(df):
    return (
        df.assign(dia=df["fecha"].dt.date)
        .groupby("dia").size()
        .reset_index(name="consultas")
    )


def consultas_por_hora(df):
    return df.groupby(df["fecha"].dt.hour).size().reset_index(name="consultas").rename(
        columns={"fecha": "hora"}
    )


def tendencia_temas(df, dias=14):
    """Compara los últimos `dias` contra los `dias` anteriores.
    Un cambio positivo significa que el tema se está preguntando más."""
    if df.empty:
        return pd.DataFrame(columns=["tema", "materia", "reciente", "anterior", "cambio_%"])
    fin = df["fecha"].max()
    corte = fin - pd.Timedelta(days=dias)
    inicio = corte - pd.Timedelta(days=dias)

    reciente = df[df["fecha"] > corte].groupby(["tema", "materia"]).size()
    anterior = df[(df["fecha"] > inicio) & (df["fecha"] <= corte)].groupby(["tema", "materia"]).size()

    t = pd.concat([reciente.rename("reciente"), anterior.rename("anterior")], axis=1).fillna(0)
    t["cambio_%"] = ((t["reciente"] - t["anterior"]) / t["anterior"].replace(0, 1) * 100).round(0)
    return t.reset_index().sort_values("cambio_%", ascending=False)


def estudiantes_con_mas_dudas(df, n=10):
    return (
        df.groupby(["matricula", "semestre"])
        .agg(consultas=("id", "count"), temas_distintos=("tema", "nunique"))
        .reset_index()
        .sort_values("consultas", ascending=False)
        .head(n)
    )


def temas_dificiles(df):
    """Temas donde los alumnos pidieron que se los explicaran otra vez
    (más fácil, paso a paso, otro ejemplo). Es una señal de que el tema cuesta."""
    seg = df[df["fuente"] == "seguimiento"]
    if seg.empty:
        return pd.DataFrame(columns=["tema", "materia", "reexplicaciones", "consultas", "%_reexplicacion"])
    r = seg.groupby(["tema", "materia"]).size().rename("reexplicaciones")
    total = df.groupby(["tema", "materia"]).size().rename("consultas")
    t = pd.concat([r, total], axis=1).dropna().reset_index()
    t["%_reexplicacion"] = (t["reexplicaciones"] / t["consultas"] * 100).round(0)
    return t.sort_values("reexplicaciones", ascending=False)
