"""Información del Tec (atención a alumnos): becas, ubicaciones, inglés, constancias...

Las respuestas viven en data/institucional.json y se editan desde la página
"Información del Tec" de la app (o directo en el archivo).

Regla importante: si una respuesta todavía no está capturada, el bot NO inventa;
dice a dónde acudir. Nunca se le pide a la IA que conteste estos datos.
"""

import json
from pathlib import Path

from core.classifier import normalizar

ARCHIVO = Path(__file__).resolve().parent.parent / "data" / "institucional.json"
MATERIA = "Servicios del Tec"

FRASES_MENU = ["servicios del tec", "informacion del tec", "tramites", "tramite",
               "atencion a alumnos", "que informacion tienes del tec", "info del tec"]


def cargar():
    try:
        return json.loads(ARCHIVO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def guardar(entradas):
    ARCHIVO.write_text(json.dumps(entradas, ensure_ascii=False, indent=2), encoding="utf-8")


VACIAS = {"de", "del", "el", "la", "los", "las", "a", "al", "mi", "mis", "un", "una", "en", "y",
          "que", "se", "me", "lo", "para", "por", "con"}

# Palabras que indican que preguntan por un trámite o un lugar (no por un tema de clase)
PISTAS_TRAMITE = ["donde", "edificio", "ubicacion", "ubicado", "horario", "cuando", "costo",
                  "cuesta", "precio", "pagar", "pago", "abren", "cierran", "tramite", "sacar",
                  "solicitar", "requisitos", "fecha", "fechas", "convocatoria", "inscribirme"]


def _palabras(texto):
    return [w for w in normalizar(texto).split() if w not in VACIAS]


def buscar(pregunta):
    """Regresa la entrada que mejor coincide con la pregunta, o None.
    Una frase clave cuenta si todas sus palabras importantes están en la pregunta,
    sin importar el orden ni los artículos ("pagar el inglés" = "pagar inglés")."""
    texto = set(_palabras(pregunta))
    mejor, puntos_mejor = None, 0
    for e in cargar():
        puntos = 0
        claves = e.get("palabras", []) + [e.get("titulo", "")]
        for p in claves:
            ws = _palabras(p)
            if ws and all(w in texto for w in ws):
                puntos += len(ws) + (2 if p == e.get("titulo") else 0)
        if puntos > puntos_mejor:
            mejor, puntos_mejor = e, puntos
    return mejor


def parece_tramite(pregunta):
    return any(w in PISTAS_TRAMITE for w in normalizar(pregunta).split())


def pide_menu(pregunta):
    t = f" {' '.join(normalizar(pregunta).split())} "
    return any(f" {f} " in t for f in FRASES_MENU)


def responder(entrada):
    """Arma la respuesta. Si no hay dato capturado, dice a dónde ir (sin inventar)."""
    respuesta = (entrada.get("respuesta") or "").strip()
    if respuesta:
        nota = f"\n\n*Información actualizada: {entrada['actualizado']}*" if entrada.get("actualizado") else ""
        return f"**{entrada['titulo']}**\n\n{respuesta}{nota}"
    return (f"Todavía no tengo registrada la información de: **{entrada['titulo']}**. "
            f"Para no darte un dato equivocado, te recomiendo preguntar en "
            f"{entrada.get('donde_preguntar') or 'Servicios Escolares'}.")


def menu():
    entradas = cargar()
    lineas = [f"- {e['titulo']}" for e in entradas]
    return ("Te puedo orientar con estos trámites y servicios del Tec:\n\n" + "\n".join(lineas) +
            "\n\nElige uno abajo o escríbeme tu pregunta."), [("info", e["titulo"]) for e in entradas]
