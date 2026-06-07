# elevenlabs_service.py
# Toda la lógica de comunicación con ElevenLabs va aquí

import os
import random
import httpx
from dotenv import load_dotenv

# Carga key.env si existe, si no carga .env normal
_key_env = os.path.join(os.path.dirname(__file__), "key.env")
_dot_env = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(_key_env):
    load_dotenv(_key_env)
else:
    load_dotenv(_dot_env)

ELEVENLABS_API_KEY  = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_MODEL_ID = os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")

# Agrega aquí los Voice IDs que quieran usar
# Consíguelos en ElevenLabs → Voice Library → tres puntos → Use
VOICE_IDS = [
    os.getenv("ELEVENLABS_VOICE_ID", "9Godp7dNohUvXk6qp0gS"),  # voz principal del .env
    # "EXAVITQu4vr4xnSDxMaL",  # descomenta para agregar más voces
    # "ErXwobaYiN019PkySvjV",
]


async def text_to_speech(text: str) -> bytes:
    """
    Llama a ElevenLabs con una voz aleatoria de VOICE_IDS y devuelve el audio en bytes (MP3).
    """
    if not ELEVENLABS_API_KEY or ELEVENLABS_API_KEY == "sk_pon_tu_key_aqui":
        raise ValueError("API key de ElevenLabs no configurada en el archivo key.env o .env")

    voice_id = random.choice(VOICE_IDS)
    print(f"🎙 Voz seleccionada: {voice_id}")

    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }

    payload = {
        "text": text,
        "model_id": ELEVENLABS_MODEL_ID,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.8,
            "style": 0.35,
            "use_speaker_boost": True,
        },
    }

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, headers=headers, json=payload)

    if response.status_code != 200:
        raise Exception(f"ElevenLabs error {response.status_code}: {response.text}")

    return response.content
