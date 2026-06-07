# whatsapp_service.py
# Genera audio con ElevenLabs y lo manda como nota de voz por WhatsApp Business API

import os
import httpx
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "key.env"))

# ── CREDENCIALES ──────────────────────────────────────────────────────────────
WA_TOKEN           = os.getenv("WA_TOKEN")
WA_PHONE_NUMBER_ID = os.getenv("WA_PHONE_NUMBER_ID")
WA_NUMERO_DESTINO  = os.getenv("WA_NUMERO_DESTINO")

ELEVENLABS_API_KEY  = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "9Godp7dNohUvXk6qp0gS")
ELEVENLABS_MODEL_ID = os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")

WA_BASE = "https://graph.facebook.com/v19.0"


# ── PASO 1: Generar audio con ElevenLabs ─────────────────────────────────────
async def _generar_audio(texto: str) -> bytes:
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY,
    }
    payload = {
        "text": texto,
        "model_id": ELEVENLABS_MODEL_ID,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.8,
            "style": 0.35,
            "use_speaker_boost": True,
        },
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(url, headers=headers, json=payload)
    if r.status_code != 200:
        raise Exception(f"ElevenLabs error {r.status_code}: {r.text}")
    return r.content  # bytes MP3


# ── PASO 2: Subir el audio a WhatsApp Media ───────────────────────────────────
async def _subir_audio_wa(audio_bytes: bytes) -> str:
    """Sube el MP3 a la API de WhatsApp y devuelve el media_id."""
    url = f"{WA_BASE}/{WA_PHONE_NUMBER_ID}/media"
    headers = {"Authorization": f"Bearer {WA_TOKEN}"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            url,
            headers=headers,
            files={
                "file":          ("alerta.mp3", audio_bytes, "audio/mpeg"),
                "messaging_product": (None, "whatsapp"),
                "type":          (None, "audio/mpeg"),
            },
        )
    if r.status_code not in (200, 201):
        raise Exception(f"WhatsApp media upload error {r.status_code}: {r.text}")
    return r.json()["id"]  # media_id


# ── PASO 3: Enviar nota de voz ─────────────────────────────────────────────────
async def _enviar_audio_wa(media_id: str, numero: str) -> dict:
    url = f"{WA_BASE}/{WA_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WA_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "audio",
        "audio": {"id": media_id},
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.post(url, headers=headers, json=payload)
    if r.status_code not in (200, 201):
        raise Exception(f"WhatsApp send error {r.status_code}: {r.text}")
    return r.json()


# ── FUNCIÓN PRINCIPAL ─────────────────────────────────────────────────────────
async def enviar_alerta_whatsapp(texto: str, numero: str | None = None) -> dict:
    """
    Genera el audio con ElevenLabs y lo manda como nota de voz por WhatsApp.
    Si no se pasa `numero`, usa WA_NUMERO_DESTINO del key.env.
    """
    destino = numero or WA_NUMERO_DESTINO
    if not destino:
        raise ValueError("No hay número de destino configurado.")

    print(f"🎙️  Generando audio para: {texto[:60]}…")
    audio = await _generar_audio(texto)

    print(f"📤 Subiendo audio a WhatsApp Media API…")
    media_id = await _subir_audio_wa(audio)

    print(f"📲 Enviando nota de voz a {destino}…")
    result = await _enviar_audio_wa(media_id, destino)

    print(f"✅ Enviado. Message ID: {result.get('messages', [{}])[0].get('id', '?')}")
    return result
