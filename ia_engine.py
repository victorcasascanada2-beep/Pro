# ia_engine.py — VERSIÓN EXTENDIDA (MÁXIMA CALIDAD DE SALIDA)
import io
import random
import time
from typing import List, Dict, Any, Optional

from google import genai
from google.oauth2 import service_account
from PIL import Image, ImageOps

import config_prompt

# Tipado opcional de google.genai
try:
    from google.genai import types

    _HAS_TYPES = True
except Exception:
    _HAS_TYPES = False


# ============================================================
# 1. OBJETO DE CARGA EN MEMORIA
# ============================================================
class InMemoryUpload:
    def __init__(self, data: bytes, name: str = "foto.jpg", mime: str = "image/jpeg"):
        self.data = data
        self.name = name
        self.type = mime

    def read(self) -> bytes:
        return self.data


def preparar_fotos_para_ai(fotos_state: List[Dict[str, Any]]) -> List[InMemoryUpload]:
    return [InMemoryUpload(f["data"], f.get("name", "foto.jpg"), f.get("type", "image/jpeg")) for f in fotos_state]


# ============================================================
# 2. CONEXIÓN A VERTEX AI
# ============================================================
def conectar_vertex(creds_dict=None):
    # --- MODO LOCAL ---
    if creds_dict:
        # Extraemos y limpiamos la clave privada
        pk = str(creds_dict.get("private_key", "")).replace("\\n", "\n").strip()

        auth_info = {
            "type": "service_account",
            "project_id": creds_dict.get("project_id"),
            "private_key": pk,
            "client_email": creds_dict.get("client_email"),
            "token_uri": "https://oauth2.googleapis.com/token",
        }

        # La clave de la dualidad: el SCOPE maestro
        google_creds = service_account.Credentials.from_service_account_info(
            auth_info,
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )

        return genai.Client(
            vertexai=True,
            project=auth_info["project_id"],
            location="us-central1",
            credentials=google_creds
        )

    # --- MODO NUBE (Cloud Run) ---
    return genai.Client(
        vertexai=True,
        project="subida-fotos-drive",  # Tu ID de proyecto real
        location="us-central1"
    )


# ============================================================
# 3. UTILIDADES DE IMAGEN
# ============================================================
def _normalizar_imagen_a_jpeg_bytes(uploaded_file, max_side: int = 1280) -> bytes:
    if hasattr(uploaded_file, "read"):
        raw = uploaded_file.read()
    else:
        raw = uploaded_file if isinstance(uploaded_file, bytes) else b""

    with Image.open(io.BytesIO(raw)) as img:
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGB")
        w, h = img.size
        scale = max(w, h) / float(max_side)
        if scale > 1.0:
            img = img.resize((int(w / scale), int(h / scale)), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85, optimize=True)
        return buf.getvalue()


# ============================================================
# 4. FLUJO DE PERITAJE (CON MÁS TOKENS Y BÚSQUEDA)
# ============================================================
def realizar_peritaje(client, marca, modelo, anio, horas, observaciones, lista_fotos):
    # 1. Ordenar fotos
    try:
        fotos_sorted = sorted(lista_fotos, key=lambda f: f.name if hasattr(f, 'name') else f.get('name', ''))
    except:
        fotos_sorted = lista_fotos

    # 2. Preparar fotos para Gemini (Máximo 15 fotos para más detalle)
    parts = []
    for f in fotos_sorted[:15]:
        raw_data = f.read() if hasattr(f, "read") else (f["data"] if isinstance(f, dict) else f)
        img_bytes = _normalizar_imagen_a_jpeg_bytes(raw_data)

        if _HAS_TYPES:
            parts.append(types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"))
        else:
            parts.append({"inline_data": {"data": img_bytes, "mime_type": "image/jpeg"}})

    # 3. Obtener Prompts
    prompt_tasacion = config_prompt.obtener_prompt_tasacion(marca, modelo, anio, horas, observaciones)
    prompt_comparables = config_prompt.obtener_prompt_comparables(marca, modelo, anio, horas)

    # 4. Configuración de Generación (MÁXIMOS TOKENS: 8192)
    # Usamos Gemini 2.0 Flash para la tasación visual y Pro para la búsqueda de mercado
    cfg_peritaje = {
        "temperature": 0.1,
        "max_output_tokens": 4096,  # <--- Aquí tienes el chorro de tokens
    }

    print("🚀 Iniciando Peritaje Multimodal...")
    res_tasacion = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[prompt_tasacion, *parts],
        config=cfg_peritaje
    )

    print("🔍 Buscando Comparables en Google Search...")
    cfg_search = {
        "tools": [{"google_search": {}}],
        "temperature": 0.0,
        "max_output_tokens": 4096,
    }

    try:
        res_comparables = client.models.generate_content(
            model="gemini-2.5-pro",  # Flash es más rápido para Search
            contents=[prompt_comparables],
            config=cfg_search
        )
        comparables_txt = res_comparables.text
    except Exception as e:
        comparables_txt = f"\n⚠️ Error en búsqueda: {str(e)}"

    return f"{res_tasacion.text}\n\n{comparables_txt}"


def extraer_precio_ia(texto, etiqueta):
    try:
        import re
        # Este patrón busca la etiqueta, admite espacios, dos puntos
        # y captura el primer número que encuentre (aunque tenga puntos o comas)
        patron = rf"{etiqueta}.*?(\d[\d\.,]*)"
        match = re.search(patron, texto, re.IGNORECASE)

        if match:
            # Limpiamos el número: quitamos puntos de miles y pasamos coma a punto decimal
            valor_limpio = match.group(1).replace(".", "").replace(",", ".")
            return float(valor_limpio)

        print(f"⚠️ No se encontró la etiqueta {etiqueta} en el informe.")
        return None
    except Exception as e:
        print(f"❌ Error extrayendo {etiqueta}: {e}")
        return None