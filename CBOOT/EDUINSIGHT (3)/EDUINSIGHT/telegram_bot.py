"""Bot de Telegram para Tutor Tec.

Usa exactamente el mismo cerebro que la página web (core/chatbot.py):
misma IA (Ollama o API), mismos botones y las preguntas se guardan en la misma
base de datos, así que aparecen en el dashboard.

Cómo usarlo:
  1. En Telegram habla con @BotFather, escribe /newbot y sigue los pasos.
     Te da un token parecido a 123456789:ABCdef...
  2. Pon el token en el archivo .env:   TELEGRAM_TOKEN=123456789:ABCdef...
  3. Ejecuta INICIAR_TELEGRAM.bat (o:  python telegram_bot.py)
  4. Busca tu bot en Telegram y escríbele /start

No necesita librerías extra: solo requests (que ya usa la app).
"""

import html
import os
import re
import time
from collections import defaultdict, deque

import requests

from core import ia_client  # carga el .env
from core.chatbot import responder
from database import db

TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()
API = os.getenv("TELEGRAM_API", "https://api.telegram.org")

BIENVENIDA = (
    "Hola, soy <b>Tutor Tec</b>, el asistente académico del Tecnológico de Cuautla.\n\n"
    "Escríbeme tu duda con tus palabras, o pregúntame por trámites del Tec "
    "(becas, inglés, constancias). Por ejemplo:\n"
    "<i>no entiendo la recursividad</i>\n"
    "<i>¿cómo hago un join en SQL?</i>\n\n"
    "Debajo de cada respuesta te dejo botones para que te lo explique más fácil, "
    "paso a paso, con otro ejemplo o con un ejercicio.\n\n"
    "Comandos:\n"
    "/materias - ver las materias y sus temas\n"
    "/tec - becas, inglés, constancias y otros trámites del Tec\n"
    "/matricula 23680000 - registra tu matrícula\n"
    "/semestre 5 - registra tu semestre\n"
    "/nuevo - empezar una conversación nueva"
)

BOTONES = [
    ("Más fácil", "sencillo", "Explícamelo más fácil"),
    ("Paso a paso", "pasos", "Explícamelo paso a paso"),
    ("Otro ejemplo", "ejemplo", "Dame otro ejemplo"),
    ("Ejercicio", "ejercicio", "Ponme un ejercicio para practicar"),
]
SOLUCION = ("Ver solución", "solucion", "Muéstrame la solución")
TEXTO_ACCION = {accion: texto for _, accion, texto in BOTONES + [SOLUCION]}


# ---------- Estado de cada conversación ----------
def _estado_nuevo():
    return {"tema": None, "accion": None, "historial": deque(maxlen=6),
            "matricula": None, "semestre": None, "contador": {}}


conversaciones = defaultdict(_estado_nuevo)


# ---------- Telegram ----------
def llamar(metodo, **datos):
    try:
        r = requests.post(f"{API}/bot{TOKEN}/{metodo}", json=datos, timeout=40)
        return r.json()
    except (requests.RequestException, ValueError) as e:
        print(f"[!] Error con Telegram ({metodo}): {e}")
        return {"ok": False}


def markdown_a_html(texto):
    """Convierte el markdown de las respuestas al HTML que acepta Telegram."""
    bloques = []

    def guardar_codigo(m):
        bloques.append(f"<pre>{html.escape(m.group(1).strip(chr(10)))}</pre>")
        return f"\x00{len(bloques) - 1}\x00"

    texto = re.sub(r"```[a-zA-Z]*\n?(.*?)```", guardar_codigo, texto, flags=re.S)
    texto = html.escape(texto, quote=False)
    texto = re.sub(r"`([^`]+)`", r"<code>\1</code>", texto)
    texto = re.sub(r"^#{1,6}\s*(.+)$", r"<b>\1</b>", texto, flags=re.M)
    texto = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", texto)
    texto = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", texto)
    texto = re.sub(r"(?<!\w)_(?!\s)(.+?)(?<!\s)_(?!\w)", r"<i>\1</i>", texto)
    texto = re.sub(r"^\s*[-*]\s+", "• ", texto, flags=re.M)
    for i, b in enumerate(bloques):
        texto = texto.replace(f"\x00{i}\x00", b)
    return texto


def teclado(estado, opciones=None):
    if opciones:
        filas, fila = [], []
        for tipo, valor in opciones:
            dato = f"{tipo[0]}:{valor}".encode("utf-8")[:64].decode("utf-8", "ignore")
            fila.append({"text": valor, "callback_data": dato})   # Telegram: máx. 64 bytes
            if len(fila) == 2:
                filas.append(fila)
                fila = []
        if fila:
            filas.append(fila)
        return {"inline_keyboard": filas}
    if not estado["tema"]:
        return None
    fila1 = [{"text": t, "callback_data": a} for t, a, _ in BOTONES[:2]]
    fila2 = [{"text": t, "callback_data": a} for t, a, _ in BOTONES[2:]]
    filas = [fila1, fila2]
    if estado["accion"] == "ejercicio":
        filas.append([{"text": SOLUCION[0], "callback_data": SOLUCION[1]}])
    return {"inline_keyboard": filas}


def enviar(chat_id, texto, botones=None):
    """Envía en HTML; si Telegram lo rechaza, lo manda como texto normal.
    Los mensajes largos se parten (límite de Telegram: 4096 caracteres)."""
    partes = [texto[i:i + 3500] for i in range(0, len(texto), 3500)] or [""]
    for n, parte in enumerate(partes):
        extra = {"reply_markup": botones} if botones and n == len(partes) - 1 else {}
        r = llamar("sendMessage", chat_id=chat_id, text=markdown_a_html(parte),
                   parse_mode="HTML", **extra)
        if not r.get("ok"):
            llamar("sendMessage", chat_id=chat_id, text=parte, **extra)


# ---------- Lógica ----------
def atender(chat_id, texto, usuario, accion=None):
    estado = conversaciones[chat_id]
    t = texto.strip()

    if t.startswith("/start"):
        llamar("sendMessage", chat_id=chat_id, text=BIENVENIDA, parse_mode="HTML")
        return
    if t.startswith("/materias"):
        t = "¿Qué materias manejas?"
    elif t.startswith("/tec"):
        t = "Servicios del Tec"
    elif t.startswith("/nuevo"):
        conversaciones[chat_id] = _estado_nuevo() | {
            "matricula": estado["matricula"], "semestre": estado["semestre"]}
        enviar(chat_id, "Listo, empezamos de nuevo. ¿Cuál es tu duda?")
        return
    elif t.startswith("/matricula"):
        partes = t.split()
        if len(partes) == 2 and partes[1].isdigit():
            estado["matricula"] = partes[1]
            enviar(chat_id, f"Matrícula registrada: **{partes[1]}**")
        else:
            enviar(chat_id, "Escríbela así: /matricula 23680000")
        return
    elif t.startswith("/semestre"):
        partes = t.split()
        if len(partes) == 2 and partes[1].isdigit() and 1 <= int(partes[1]) <= 12:
            estado["semestre"] = int(partes[1])
            enviar(chat_id, f"Semestre registrado: **{partes[1]}**")
        else:
            enviar(chat_id, "Escríbelo así: /semestre 5")
        return
    elif t.startswith("/"):
        enviar(chat_id, "No conozco ese comando. Usa /start para ver la ayuda.")
        return

    llamar("sendChatAction", chat_id=chat_id, action="typing")
    matricula = estado["matricula"] or f"TG{usuario}"
    respuesta, info = responder(
        t, matricula, "ISC", estado["semestre"], usar_ia=True,
        tema_actual=estado["tema"], historial=list(estado["historial"]), accion=accion,
        contador=estado["contador"],
    )

    estado["historial"].append({"role": "user", "content": t})
    estado["historial"].append({"role": "assistant", "content": respuesta[:1200]})
    opciones = info.get("opciones")
    if info["tema"] and info["tema"] != "Otros temas":
        estado["tema"], estado["accion"] = info["tema"], info["accion"]
        respuesta += f"\n\n_{info['materia']} · {info['tema']}_"

    # los botones de ayuda solo van si la respuesta fue de un tema (no en "No estoy diseñado...")
    botones = teclado(estado, opciones) if (opciones or info["tema"]) else None
    enviar(chat_id, respuesta, botones)
    print(f"[{time.strftime('%H:%M:%S')}] {matricula}: {t[:60]!r} -> "
          f"{info['tema'] or 'fuera de tema'} ({info['respondio']})")


def main():
    if not TOKEN:
        print("Falta TELEGRAM_TOKEN en el archivo .env\n"
              "Sácalo hablando con @BotFather en Telegram (/newbot).")
        return

    yo = llamar("getMe")
    if not yo.get("ok"):
        print("No se pudo conectar con Telegram. Revisa el token y el internet.")
        print(yo)
        return

    db.inicializar_db()
    print(f"Bot @{yo['result']['username']} funcionando.")
    print(f"IA: {ia_client.nombre()}")
    print("Deja esta ventana abierta. Para detenerlo: Ctrl + C\n")

    ultimo = 0
    while True:
        r = llamar("getUpdates", offset=ultimo + 1, timeout=30,
                   allowed_updates=["message", "callback_query"])
        if not r.get("ok"):
            time.sleep(3)
            continue
        for upd in r["result"]:
            ultimo = upd["update_id"]
            try:
                if "callback_query" in upd:
                    cb = upd["callback_query"]
                    llamar("answerCallbackQuery", callback_query_id=cb["id"])
                    dato = cb["data"]
                    chat_id = cb["message"]["chat"]["id"]
                    if dato.startswith("t:"):        # eligió un tema del temario
                        texto, accion = f"Explícame {dato[2:]}", None
                    elif dato.startswith("m:"):      # eligió una materia
                        texto, accion = f"¿Qué temas tiene {dato[2:]}?", None
                    elif dato.startswith("i:"):      # eligió un trámite del Tec
                        texto, accion = dato[2:], None
                    else:                            # botón de ayuda (más fácil, etc.)
                        accion = dato
                        texto = TEXTO_ACCION.get(accion, "Explícamelo más fácil")
                    enviar(chat_id, f"_{texto}_")
                    atender(chat_id, texto, cb["from"]["id"], accion=accion)
                elif "message" in upd and "text" in upd["message"]:
                    m = upd["message"]
                    atender(m["chat"]["id"], m["text"], m["from"]["id"])
            except Exception as e:  # que un error en un mensaje no tumbe el bot
                print(f"[!] Error atendiendo un mensaje: {e}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nBot detenido.")
