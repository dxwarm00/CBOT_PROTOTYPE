"""Conexión con la IA.

Acepta la API key de cualquiera de estos servicios gratuitos y detecta cuál es
por cómo empieza la key:

  xai-...    -> Grok (xAI)   (console.x.ai)         modelo: grok-4.7
  github_pat_ / ghp_ -> GitHub Models (github.com/settings/tokens) modelo: openai/gpt-4.1
  sk-or-...  -> OpenRouter   (openrouter.ai)        modelo: openrouter/free
  AIza...    -> Gemini       (aistudio.google.com)  modelo: gemini-3.8-flash
  sk-...     -> DeepSeek     (platform.deepseek.com)  modelo: deepseek-flash
  gsk_...    -> Groq         (console.groq.com)     modelo: llama-3.3-70b-versatile

Orden de uso:
  1. La API de la key guardada en .env (IA_API_KEY)
  2. Ollama local, si está corriendo
  (con IA_PROVEEDOR=ollama en .env, Ollama va primero)
  3. Ninguna -> el chatbot responde con la base de conocimiento local

Para usar otro modelo, agrega en .env:  IA_MODEL=nombre-del-modelo
"""

import os
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent.parent

PROVEEDORES = {
    "xai": {
        "nombre": "Grok (xAI)",
        "prefijo": "xai-",
        "url": "https://api.x.ai/v1/chat/completions",
        "modelo": "grok-4.7",
    },
    "github": {
        "nombre": "GitHub Models",
        "prefijo": ("github_pat_", "ghp_"),
        "url": "https://models.github.ai/inference/chat/completions",
        "modelo": "openai/gpt-4.1",
    },
    "openrouter": {
        "nombre": "OpenRouter",
        "prefijo": "sk-or-",
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "modelo": "openrouter/free",
    },
    "gemini": {
        "nombre": "Gemini",
        "prefijo": "AIza",
        "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "modelo": "gemini-3.8-flash",
    },
    "groq": {
        "nombre": "Groq",
        "prefijo": "gsk_",
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "modelo": "llama-3.3-70b-versatile",
    },
    # va al final porque su key empieza con "sk-" (igual que el inicio de OpenRouter "sk-or-")
    "deepseek": {
        "nombre": "DeepSeek",
        "prefijo": "sk-",
        "url": "https://api.deepseek.com/chat/completions",
        "modelo": "deepseek-flash",
    },
}

def _cargar_env():
    """Lee el archivo .env sin necesitar librerías extra."""
    archivo = BASE_DIR / ".env"
    if not archivo.exists():
        return
    for linea in archivo.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        valor = valor.strip().strip('"').strip("'")
        if valor:
            os.environ.setdefault(clave.strip(), valor)


_cargar_env()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
# IA_PROVEEDOR=ollama -> usa Ollama aunque haya una API key guardada
PREFERIR_OLLAMA = os.getenv("IA_PROVEEDOR", "").lower() == "ollama"

# GROQ_API_KEY y DEEPSEEK_API_KEY se aceptan también por compatibilidad
API_KEY = (os.getenv("IA_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
           or os.getenv("GROQ_API_KEY", ""))
MODELO_FORZADO = os.getenv("IA_MODEL") or ""

_estado = {"proveedor": None, "revisado": False, "ultimo_error": None}


def detectar_proveedor(key):
    for clave, p in PROVEEDORES.items():
        if key.startswith(p["prefijo"]):  # prefijo puede ser texto o tupla
            return clave
    return None


def _modelo(prov):
    return MODELO_FORZADO or PROVEEDORES[prov]["modelo"]


def _post(url, mensajes, prov, temperatura):
    """Hace la petición. Si la respuesta no es JSON (algo en medio la interceptó,
    por ejemplo un proxy del sistema), reintenta una vez ignorando los proxies."""
    cuerpo = {
        "model": _modelo(prov),
        "messages": mensajes,
        "temperature": temperatura,
        "max_tokens": 1500,
    }
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    r = requests.post(url, headers=headers, json=cuerpo, timeout=45)
    if "json" not in r.headers.get("Content-Type", ""):
        sesion = requests.Session()
        sesion.trust_env = False   # no usar proxies configurados en Windows
        try:
            r2 = sesion.post(url, headers=headers, json=cuerpo, timeout=45)
            if "json" in r2.headers.get("Content-Type", ""):
                return r2
        except requests.RequestException:
            pass
    return r


# ---------------- APIs tipo OpenAI (OpenRouter, Gemini, Groq) ----------------
def _api(prov, prompt, sistema, temperatura, historial):
    p = PROVEEDORES[prov]
    mensajes = []
    if sistema:
        mensajes.append({"role": "system", "content": sistema})
    mensajes.extend(historial or [])
    mensajes.append({"role": "user", "content": prompt})
    try:
        r = _post(p["url"], mensajes, prov, temperatura)
        if r.status_code == 429:
            _estado["ultimo_error"] = f"Se alcanzó el límite gratis de {p['nombre']}, espera un minuto."
            return None
        if r.status_code >= 400:
            # se muestra el mensaje real de la API para saber qué falló
            try:
                detalle = r.json()
                detalle = detalle.get("error", detalle)
                if isinstance(detalle, dict):
                    detalle = detalle.get("message", str(detalle))
            except ValueError:
                detalle = r.text
            _estado["ultimo_error"] = f"{p['nombre']} respondió error {r.status_code}: {str(detalle)[:200]}"
            return None
        try:
            datos = r.json()
        except ValueError:
            _estado["ultimo_error"] = (
                f"{p['nombre']} no respondió con datos de IA (llegó una página web). "
                "Puede que la red WiFi esté bloqueando o pidiendo iniciar sesión; "
                f"prueba con datos del celular. Inicio de la respuesta: {r.text[:120]!r}"
            )
            return None
        try:
            texto = datos["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            _estado["ultimo_error"] = f"{p['nombre']} respondió algo inesperado: {str(datos)[:200]}"
            return None
        _estado["ultimo_error"] = None
        return (texto or "").strip() or None
    except requests.exceptions.SSLError:
        _estado["ultimo_error"] = (f"Error de certificado con {p['nombre']}: la red o el antivirus "
                                   "está interceptando la conexión. Prueba con datos del celular.")
        return None
    except requests.exceptions.Timeout:
        _estado["ultimo_error"] = f"{p['nombre']} tardó demasiado en responder. Intenta de nuevo."
        return None
    except requests.RequestException as e:
        _estado["ultimo_error"] = f"No se pudo conectar con {p['nombre']}: {type(e).__name__}: {str(e)[:150]}"
        return None


# ---------------- Ollama ----------------
def _ollama_disponible():
    try:
        return requests.get(f"{OLLAMA_URL}/api/tags", timeout=1.5).ok
    except requests.RequestException:
        return False


def _ollama(prompt, sistema, temperatura, historial):
    # /api/generate no recibe mensajes, así que se pega la conversación al prompt
    if historial:
        previo = "\n".join(
            f"{'Alumno' if m['role'] == 'user' else 'Asistente'}: {m['content']}" for m in historial
        )
        prompt = f"Conversación previa:\n{previo}\n\nAlumno: {prompt}"
    try:
        r = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "system": sistema or "",
                "stream": False,
                "options": {"temperature": temperatura},
            },
            timeout=180,  # la primera respuesta tarda porque Ollama carga el modelo
        )
        r.raise_for_status()
        return r.json().get("response", "").strip()
    except requests.RequestException:
        return None


# ---------------- Interfaz pública ----------------
def proveedor():
    """Regresa 'openrouter', 'gemini', 'groq', 'ollama' o None."""
    if not _estado["revisado"]:
        prov = detectar_proveedor(API_KEY) if API_KEY else None
        if PREFERIR_OLLAMA and _ollama_disponible():
            _estado["proveedor"] = "ollama"
        elif prov:
            _estado["proveedor"] = prov
        elif _ollama_disponible():
            _estado["proveedor"] = "ollama"
        _estado["revisado"] = True
    return _estado["proveedor"]


def redetectar():
    """Vuelve a buscar la IA (por ejemplo, si abriste Ollama después de la app)."""
    _estado.update(proveedor=None, revisado=False, ultimo_error=None)
    return disponible()


def disponible():
    return proveedor() is not None


def nombre():
    p = proveedor()
    if p in PROVEEDORES:
        return f"{PROVEEDORES[p]['nombre']} ({_modelo(p)})"
    if p == "ollama":
        return f"Ollama ({OLLAMA_MODEL})"
    return "Sin IA"


def ultimo_error():
    return _estado["ultimo_error"]


def generar(prompt, sistema=None, temperatura=0.3, historial=None):
    """historial: lista de {"role": "user"/"assistant", "content": "..."}"""
    p = proveedor()
    if p in PROVEEDORES:
        respuesta = _api(p, prompt, sistema, temperatura, historial)
        if respuesta is None and _ollama_disponible():
            respuesta = _ollama(prompt, sistema, temperatura, historial)
        return respuesta
    if p == "ollama":
        return _ollama(prompt, sistema, temperatura, historial)
    return None


def guardar_key(key):
    """Guarda la key en .env y la activa sin reiniciar la app.
    Regresa el nombre del servicio detectado, o None si la key no se reconoce."""
    global API_KEY
    key = key.strip().strip('"').strip("'")
    prov = detectar_proveedor(key)
    if not prov:
        return None
    archivo = BASE_DIR / ".env"
    lineas = archivo.read_text(encoding="utf-8").splitlines() if archivo.exists() else []
    lineas = [l for l in lineas if not l.strip().startswith(("IA_API_KEY", "GROQ_API_KEY"))]
    lineas.insert(0, f"IA_API_KEY={key}")
    archivo.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    os.environ["IA_API_KEY"] = key
    API_KEY = key
    _estado.update(proveedor=None, revisado=False, ultimo_error=None)
    return PROVEEDORES[prov]["nombre"]


def probar():
    """Hace una pregunta mínima para confirmar que la key funciona."""
    return generar("Responde solo: ok", temperatura=0) is not None
