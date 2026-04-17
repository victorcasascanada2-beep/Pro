# Tasador Agrícola Noroeste — Claude en Vertex AI

## Cambios respecto a la versión Gemini
- `ia_engine.py` ahora usa **Anthropic Claude** vía `AnthropicVertex` (SDK `anthropic[vertex]`).
- Se elimina la dependencia de `google-genai`.

## Configurar el modelo
En `ia_engine.py`, ajusta la constante `CLAUDE_MODEL` al nombre exacto
que aparece en tu contrato de Vertex AI, por ejemplo:

```python
CLAUDE_MODEL    = "claude-sonnet-4-5@20251001"
VERTEX_LOCATION = "us-east5"   # región habilitada en tu proyecto
VERTEX_PROJECT  = "subida-fotos-drive"
```

## Ejecución local (Streamlit)
Crea `.streamlit/secrets.toml`:

```toml
[google]
project_id    = "subida-fotos-drive"
client_email  = "mi-sa@subida-fotos-drive.iam.gserviceaccount.com"
private_key   = "-----BEGIN RSA PRIVATE KEY-----\n..."
# ... resto de campos del service account JSON
```

Luego:
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Despliegue en Cloud Run
El código detecta automáticamente Cloud Run mediante la variable `K_SERVICE`.
En ese entorno usa **Application Default Credentials (ADC)** — no necesita secrets.

```bash
gcloud builds submit --config cloudbuild.yaml
```

La cuenta de servicio de Cloud Run debe tener el rol:
`roles/aiplatform.user` en el proyecto GCP.
