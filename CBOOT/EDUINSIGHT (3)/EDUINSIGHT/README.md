# EDUINSIGHT

Analítica del aprendizaje a partir de las dudas que los estudiantes le hacen a un chatbot académico.

## Cómo correrlo

```bash
python -m venv venv
# Windows: venv\Scripts\activate   |   Linux/Mac: source venv/bin/activate
pip install -r requirements.txt
streamlit run Inicio.py
```

La primera vez se crea `database/eduinsight.db` y se cargan ~320 preguntas de prueba
desde `data/preguntas.csv` para que el dashboard tenga datos.

### IA (gratis)

Abre el **Chatbot**, despliega **🔑 Activar IA** en la barra lateral y pega la key de
cualquiera de estos servicios (la app detecta cuál es):

| Servicio | Dónde sacar la key | Empieza con |
|---|---|---|
| DeepSeek | platform.deepseek.com → API keys | `sk-` |
| Grok (xAI) | console.x.ai → API Keys | `xai-` |
| GitHub Models | github.com/settings/tokens → Fine-grained token con permiso *Models: read* | `github_pat_` |
| OpenRouter | openrouter.ai → Keys | `sk-or-` |
| Gemini | aistudio.google.com → Get API key | `AIza` |
| Groq | console.groq.com → API Keys | `gsk_` |

La key se guarda sola en `.env`. Si no hay key, si no hay internet o si se acaba el
límite gratis, el chatbot responde con la base de conocimiento local (y usa Ollama si está
corriendo).

**No subas el archivo `.env` a GitHub**: ya está en `.gitignore`.

### Información del Tec (atención a alumnos)

El bot también contesta trámites y servicios: becas, ubicación de Servicios Escolares, del
módulo de inglés y de la biblioteca, apertura y pago de inglés, constancias, reinscripción,
SII, credencial, servicio social, residencias, titulación y contacto.

Las respuestas se capturan en la página **Información Tec** de la app (o en
`data/institucional.json`). **Si una respuesta está vacía, el bot no inventa**: le dice al
alumno a qué área acudir. La IA tiene prohibido inventar datos de la escuela.

### Bot de Telegram (opcional)

El bot usa el mismo Tutor Tec (misma IA, mismos botones) y guarda las preguntas en la
misma base de datos, así que aparecen en el dashboard.

1. En Telegram, habla con **@BotFather**, escribe `/newbot` y sigue los pasos.
2. Copia el token en `.env`: `TELEGRAM_TOKEN=123456789:ABC...`
3. Abre **INICIAR_TELEGRAM.bat** (puede correr al mismo tiempo que la página web).
4. Busca tu bot en Telegram y escríbele `/start`.

Comandos del bot: `/materias`, `/tec`, `/matricula 23680000`, `/semestre 5`, `/nuevo`.

## Estructura

| Archivo | Qué hace |
|---|---|
| `Inicio.py` | Página principal y navegación |
| `pages/1_Chatbot.py` | Interfaz de conversación |
| `pages/2_Dashboard.py` | Panel de analítica |
| `core/chatbot.py` | Coordina: clasificar → responder → guardar |
| `core/classifier.py` | Detecta materia y tema (palabras clave, y la IA si no encuentra) |
| `core/ia_client.py` | Conexión con la IA: Grok, GitHub Models, OpenRouter, Gemini o Groq, y Ollama como respaldo |
| `core/analytics.py` | Estadísticas y tendencias |
| `core/graph.py` | Grafo de conceptos (prerrequisitos + temas preguntados juntos) |
| `core/recommendations.py` | Recomendaciones institucionales |
| `telegram_bot.py` | Bot de Telegram conectado al mismo chatbot |
| `core/institucional.py` | Respuestas de trámites y servicios del Tec |
| `pages/3_Informacion_Tec.py` | Página para capturar la información del Tec |
| `data/institucional.json` | Respuestas de atención a alumnos (se llenan desde la app) |
| `database/db.py` | Conexión con SQLite |
| `database/schema.sql` | Tablas |
| `data/temas.json` | 7 materias y 73 temas, con palabras clave y prerrequisitos |
| `data/conocimientos.json` | Explicación, ejemplo y recursos por tema |
| `data/preguntas.csv` | Datos de prueba |

## Agregar una materia o tema

1. En `data/temas.json` agrega el tema con sus palabras clave (sin acentos) y prerrequisitos.
2. En `data/conocimientos.json` agrega su explicación, ejemplo y recursos.
3. Listo: el clasificador, el grafo y el dashboard lo toman solos.

## Reparto sugerido (5 integrantes)

| # | Módulo | Archivos |
|---|---|---|
| 1 | Interfaz | `Inicio.py`, `pages/1_Chatbot.py` |
| 2 | IA y clasificación | `core/classifier.py`, `core/chatbot.py`, `core/ia_client.py` |
| 3 | Base de datos | `database/`, `data/` |
| 4 | Analítica | `core/analytics.py`, `core/graph.py`, `core/recommendations.py`, `pages/2_Dashboard.py` |
| 5 | Integración | Pruebas, README, presentación |
