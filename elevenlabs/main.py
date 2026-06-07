# main.py
# Servidor principal — corre con: uvicorn main:app --reload --port 8000

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from mock_data import get_all_alerts, get_alert_by_id, build_voice_script
from elevenlabs_service import text_to_speech
from whatsapp_service import enviar_alerta_whatsapp

app = FastAPI(title="Order Rescue API", version="1.0.0")

# CORS: permite que el archivo conductor.html llame a esta API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción cambiar por el dominio real
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "Order Rescue API corriendo", "version": "1.0.0"}


@app.get("/alerts")
def list_alerts():
    """
    Devuelve todas las alertas activas para la ruta del conductor.
    Cuando el Rol 1 termine MongoDB, este endpoint usará la DB real.
    """
    return get_all_alerts()


@app.get("/alerts/{alert_id}")
def get_alert(alert_id: str):
    """
    Devuelve una alerta específica por ID.
    """
    alert = get_alert_by_id(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")
    return alert


@app.get("/alerts/{alert_id}/audio")
async def get_alert_audio(alert_id: str):
    """
    Endpoint principal para ElevenLabs.
    1. Busca la alerta por ID
    2. Genera el guión de voz empático
    3. Llama a ElevenLabs
    4. Devuelve el MP3 al frontend (el conductor lo escucha en su celular)
    """
    alert = get_alert_by_id(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")

    script = build_voice_script(alert)

    try:
        audio_bytes = await text_to_speech(script)
    except ValueError as e:
        # API key no configurada
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error en ElevenLabs: {str(e)}")

    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={"Content-Disposition": f"inline; filename=alerta_{alert_id}.mp3"},
    )


@app.post("/alerts/{alert_id}/whatsapp")
async def send_alert_whatsapp(alert_id: str, numero: str | None = None):
    """
    Genera el audio de la alerta con ElevenLabs y lo manda
    como nota de voz por WhatsApp Business API.
    - numero: opcional, sobreescribe el destino del key.env
    """
    alert = get_alert_by_id(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")

    script = build_voice_script(alert)

    try:
        result = await enviar_alerta_whatsapp(script, numero)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error enviando WhatsApp: {str(e)}")

    return {
        "ok": True,
        "alert_id": alert_id,
        "cliente": alert["cliente"],
        "mensaje": script,
        "whatsapp": result,
    }


@app.get("/alerts/{alert_id}/script")
def get_alert_script(alert_id: str):
    """
    Devuelve el texto del guión sin convertir a audio.
    Útil para revisar qué dirá la voz antes de gastar créditos.
    """
    alert = get_alert_by_id(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")
    return {"alert_id": alert_id, "script": build_voice_script(alert)}
