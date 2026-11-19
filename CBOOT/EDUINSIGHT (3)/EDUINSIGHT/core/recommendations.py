"""Genera recomendaciones institucionales a partir de la analítica.

Son reglas simples y explicables (para que en la presentación se pueda
justificar cada recomendación):

1. Tema con mucha demanda           -> abrir tutoría o asesoría.
2. Tema que va en aumento           -> taller de reforzamiento pronto.
3. Tema con dudas en su prerrequisito -> reforzar primero la base.
4. Estudiante con muchas dudas      -> canalizar a tutoría individual.
"""

from core import analytics
from core.graph import TEMAS


def _prerrequisitos(tema):
    for temas in TEMAS.values():
        if tema in temas:
            return temas[tema]["prerrequisitos"]
    return []


def generar(df, umbral_demanda=0.12, umbral_aumento=80, umbral_estudiante=8):
    recs = []
    if df.empty:
        return recs

    por_tema = analytics.consultas_por_tema(df)
    total = len(df)
    conteo = dict(zip(por_tema["tema"], por_tema["consultas"]))

    # 1. Alta demanda
    for _, r in por_tema.iterrows():
        proporcion = r["consultas"] / total
        if proporcion >= umbral_demanda:
            recs.append({
                "prioridad": "Alta",
                "tipo": "Tutoría",
                "tema": r["tema"],
                "materia": r["materia"],
                "detalle": f"Concentra el {proporcion:.0%} de todas las consultas "
                           f"({r['consultas']}). Se sugiere abrir asesoría grupal.",
            })

    # 2. Temas en aumento
    tend = analytics.tendencia_temas(df)
    for _, r in tend.iterrows():
        if r["cambio_%"] >= umbral_aumento and r["reciente"] >= 10:
            recs.append({
                "prioridad": "Media",
                "tipo": "Taller",
                "tema": r["tema"],
                "materia": r["materia"],
                "detalle": f"Las dudas subieron {r['cambio_%']:.0f}% en las últimas 2 semanas "
                           f"({int(r['anterior'])} → {int(r['reciente'])}). Posible tema de examen próximo.",
            })

    # 3. Cadena de prerrequisitos
    promedio = total / max(len(conteo), 1)
    for tema, n in conteo.items():
        for pre in _prerrequisitos(tema):
            if n > promedio and conteo.get(pre, 0) > promedio * 0.7:
                recs.append({
                    "prioridad": "Media",
                    "tipo": "Material de apoyo",
                    "tema": pre,
                    "materia": next(m for m, t in TEMAS.items() if pre in t),
                    "detalle": f"Muchas dudas en **{tema}** y también en su base **{pre}**. "
                               f"Conviene reforzar {pre} antes de avanzar.",
                })

    # 5. Temas donde piden re-explicación seguido
    dif = analytics.temas_dificiles(df)
    for _, r in dif.iterrows():
        if r["%_reexplicacion"] >= 25 and r["reexplicaciones"] >= 5:
            recs.append({
                "prioridad": "Alta",
                "tipo": "Revisar enseñanza",
                "tema": r["tema"],
                "materia": r["materia"],
                "detalle": f"En el {r['%_reexplicacion']:.0f}% de las consultas los alumnos pidieron "
                           f"que se lo explicaran otra vez. Conviene revisar cómo se enseña en clase "
                           f"(más ejemplos o práctica guiada).",
            })

    # 4. Estudiantes que preguntan mucho
    top = analytics.estudiantes_con_mas_dudas(df, n=50)
    for _, r in top[top["consultas"] >= umbral_estudiante].iterrows():
        recs.append({
            "prioridad": "Baja",
            "tipo": "Seguimiento",
            "tema": "-",
            "materia": "-",
            "detalle": f"El estudiante {r['matricula']} hizo {r['consultas']} consultas "
                       f"en {r['temas_distintos']} temas. Sugerir tutoría individual.",
        })

    orden = {"Alta": 0, "Media": 1, "Baja": 2}
    return sorted(recs, key=lambda x: orden[x["prioridad"]])
