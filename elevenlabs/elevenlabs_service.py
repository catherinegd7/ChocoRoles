# elevenlabs_service.py
# Toda la lógica de comunicación con ElevenLabs va aquí

import os
import httpx
from dotenv import load_dotenv

load_dotenv()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB")
ELEVENLABS_MODEL_ID = os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")

ELEVENLABS_URL = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"


async def text_to_speech(text: str) -> bytes:
    """
    Llama a ElevenLabs y devuelve el audio en bytes (MP3).
    El frontend lo recibe y lo reproduce directamente.
    """
    if not ELEVENLABS_API_KEY or ELEVENLABS_API_KEY == "sk_pon_tu_key_aqui":
        raise ValueError("API key de ElevenLabs no configurada en el archivo .env")

    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }

    payload = {
        "text": text,
        "model_id": ELEVENLABS_MODEL_ID,
        "voice_settings": {
            "stability": 0.5,           # Qué tan consistente suena la voz
            "similarity_boost": 0.8,    # Qué tan fiel al voice original
            "style": 0.35,               # Un poco de expresividad, no exagerada
            "use_speaker_boost": True,  # Mejora la claridad (útil para ruido de camión)
        },
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(ELEVENLABS_URL, headers=headers, json=payload)

    if response.status_code != 200:
        raise Exception(f"ElevenLabs error {response.status_code}: {response.text}")

    return response.content  # bytes del MP3
