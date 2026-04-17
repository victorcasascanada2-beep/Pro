# ia_engine.py — Motor IA con Claude en Vertex AI (Anthropic)
#
# Modos de conexión:
#   - Cloud Run (ADC):       conectar_vertex(creds_dict=None)
#   - Local / Streamlit:     conectar_vertex(creds_dict=dict(st.secrets["google"]))
#
# Modelo: ajusta CLAUDE_MODEL al que hayas contratado en Vertex AI.
# La búsqueda de comparables usa web_search tool si el modelo la soporta.

import io
import base64
from PIL import Image, ImageOps

import config_prompt

# ── Dependencias Anthropic ─────────────────────────────────────────────────
try:
    from anthropic import AnthropicVertex
    _HAS_ANTHROPIC = True
except ImportError:
    _HAS_ANTHROPIC = False

# ── Dependencias Google Auth (modo local con service account) ──────────────
try:
    from google.oauth2 import service_account
    import google.auth.transport.requests
    _HAS_GOOGLE_AUTH = True
except ImportError:
    _HAS_GOOGLE_AUTH = False

# ── Configuración ──────────────────────────────────────────────────────────
CLAUDE_MODEL    = "claude-sonnet-4-5@20251001"  # Ajusta al modelo de tu contrato Vertex
VERTEX_LOCATION = "us-east5"                    # Región con Claude habilitado en Vertex
VERTEX_PROJECT  = "subida-fotos-drive"          # Tu proyecto GCP


# ─────────────────────────────────────────────────────────────────────────────
# CONEXIÓN
# ─────────────────────────────────────────────────────────────────────────────

def conectar_vertex(creds_dict=None):
    """
    Devuelve un cliente AnthropicVertex.

    creds_dict=None  → Cloud Run/ADC: las credenciales se infieren del entorno.
    creds_dict!=dict → Local/Streamlit: service account desde st.secrets["google"].
    """
    if not _HAS_ANTHROPIC:
        raise ImportError("Instala: pip install anthropic[vertex]")

    if creds_dict is None:
        # Cloud Run: Application Default Credentials (sin credenciales explícitas)
        return AnthropicVertex(
            project_id=VERTEX_PROJECT,
            region=VERTEX_LOCATION,
        )

    # Local / Streamlit: service account JSON
    if not _HAS_GOOGLE_AUTH:
        raise ImportError("Instala: pip install google-auth")

    pk = str(creds_dict.get("private_key", ""))
    clean_key = pk.strip().strip('"').strip("'").replace("\\n", "\n")

    auth_info = {
        "type": "service_account",
        "project_id": creds_dict.get("project_id", VERTEX_PROJECT),
        "private_key": clean_key,
        "client_email": creds_dict.get("client_email"),
        "token_uri": "https://oauth2.googleapis.com/token",
    }

    google_creds = service_account.Credentials.from_service_account_info(
        auth_info,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    # Refresca el token antes de pasárselo a AnthropicVertex
    request = google.auth.transport.requests.Request()
    google_creds.refresh(request)

    return AnthropicVertex(
        project_id=auth_info["project_id"],
        region=VERTEX_LOCATION,
        credentials=google_creds,
    )


# ─────────────────────────────────────────────────────────────────────────────
# UTILIDADES DE IMAGEN
# ─────────────────────────────────────────────────────────────────────────────

def _normalizar_imagen_a_jpeg_bytes(uploaded_file, max_side=800, quality=60) -> bytes:
    img = Image.open(uploaded_file)
    img = ImageOps.exif_transpose(img)
    img = img.convert("RGB")

    w, h = img.size
    scale = max(w, h) / float(max_side)
    if scale > 1.0:
        new_w = int(round(w / scale))
        new_h = int(round(h / scale))
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue()


def _imagen_a_bloque(data: bytes) -> dict:
    """Convierte bytes JPEG al formato de imagen de la Anthropic Messages API."""
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": "image/jpeg",
            "data": base64.b64encode(data).decode("utf-8"),
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# LLAMADAS AL MODELO
# ─────────────────────────────────────────────────────────────────────────────

def _extraer_texto(message) -> str:
    """Extrae todo el texto plano de una respuesta Anthropic Messages."""
    partes = []
    for bloque in message.content:
        if hasattr(bloque, "text"):
            partes.append(bloque.text)
        elif isinstance(bloque, dict) and bloque.get("type") == "text":
            partes.append(bloque["text"])
    return "\n".join(partes)


def _tasacion_sin_busqueda(client, prompt_tasacion: str, fotos_sorted) -> str:
    """
    Paso 1 – Tasación estable SIN búsqueda web.
    Envía el prompt de texto + todas las imágenes a Claude.
    """
    content = [{"type": "text", "text": prompt_tasacion}]
    for f in fotos_sorted:
        data = _normalizar_imagen_a_jpeg_bytes(f)
        content.append(_imagen_a_bloque(data))

    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4096,
        temperature=0.05,
        messages=[{"role": "user", "content": content}],
    )
    return _extraer_texto(message)


def _comparables_con_busqueda(client, prompt_comparables: str) -> str:
    """
    Paso 2 – Comparables de mercado.
    Usa web_search tool si el modelo lo soporta; si no, responde sin búsqueda.
    """
    try:
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2048,
            temperature=0.0,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{"role": "user", "content": prompt_comparables}],
        )
        return _extraer_texto(message)
    except Exception:
        # Fallback: respuesta sin búsqueda web
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2048,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt_comparables}],
        )
        return _extraer_texto(message)


# ─────────────────────────────────────────────────────────────────────────────
# FLUJO PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def realizar_peritaje(client, marca, modelo, anio, horas, observaciones, lista_fotos):
    """
    Flujo completo:
      1) TASACIÓN (sin búsqueda) → precio estable
      2) COMPARABLES (con búsqueda si disponible) → tabla de justificación
    """
    fotos_sorted = sorted(lista_fotos, key=lambda f: getattr(f, "name", ""))

    prompt_tasacion    = config_prompt.obtener_prompt_tasacion(marca, modelo, anio, horas, observaciones)
    prompt_comparables = config_prompt.obtener_prompt_comparables(marca, modelo, anio, horas)

    tasacion_txt = _tasacion_sin_busqueda(client, prompt_tasacion, fotos_sorted)

    try:
        comparables_txt = _comparables_con_busqueda(client, prompt_comparables)
    except Exception as e:
        comparables_txt = (
            "BLOQUE: COMPARABLES_TABLA\n"
            "| WEB | MODELO | AÑO | HORAS | PRECIO |\n"
            "|---|---|---|---|---|\n"
            f"| Error | {str(e)} | N/D | N/D | N/D |\n"
        )

    return f"{tasacion_txt}\n\n{comparables_txt}"
