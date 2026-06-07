# Order Rescue — Módulo ElevenLabs (Notificaciones de Voz)

Notificaciones de voz para conductores usando ElevenLabs TTS.
Se conecta a los CSVs de datos para generar alertas con scores de riesgo reales.

---

## Requisitos

- Python 3.12
- Los CSVs `Datos_Limpios_ChocoRoles_parte_*.csv` en la carpeta `backend/`
- `data_processor.py` del folder `Gemini API` copiado aquí mismo
- API key de ElevenLabs (Plan Creator, cuenta de Damaris)

---

## Setup (solo la primera vez)

**1. Entra a la carpeta:**
```bash
cd ChocoRoles/elevenlabs
```

**2. Instala dependencias:**
```bash
py -m pip install fastapi uvicorn python-dotenv httpx pymongo certifi pandas
```

**3. Copia `data_processor.py` del folder `Gemini API` aquí:**
```bash
copy "..\Gemini API\data_processor.py" "data_processor.py"
```

**4. Configura el archivo `.env`:**
```
ELEVENLABS_API_KEY=sk_tu_key_aqui
ELEVENLABS_VOICE_ID=tu_voice_id_aqui
ELEVENLABS_MODEL_ID=eleven_multilingual_v2
```
> La API key está con Damaris. El Voice ID es el de la voz elegida en ElevenLabs.

---

## Correr el servidor

```bash
py -m uvicorn main:app --reload --port 8000
```

La primera vez tarda ~10 segundos cargando los CSVs. Cuando veas esto está listo:

```
✓ 20 alertas cargadas desde CSVs
INFO: Uvicorn running on http://127.0.0.1:8000
```

---

## Probar que funciona

| URL | Qué hace |
|-----|----------|
| `http://localhost:8000/alerts` | Lista todas las alertas con scores reales |
| `http://localhost:8000/alerts/alert_001/script` | Ve el guión de voz sin gastar créditos |
| `http://localhost:8000/alerts/alert_001/audio` | Genera y descarga el MP3 con ElevenLabs |

**Frontend del conductor:**
Abre `conductor.html` directo en el navegador (doble clic). Se conecta solo al backend.

---

## Archivos

```
elevenlabs/
├── main.py                 — servidor FastAPI, endpoints
├── elevenlabs_service.py   — llamadas a la API de ElevenLabs
├── mock_data.py            — carga datos de CSVs y genera guiones de voz
├── data_processor.py       — copiado de Gemini API, lee CSVs y MongoDB
├── conductor.html          — frontend del conductor
└── .env                    — API keys (NO subir a GitHub)
```

---

## Guiones de voz

Los textos que dice la voz están en `mock_data.py` dentro de `build_voice_script()`.
El **Rol 4** puede editar esos textos sin tocar nada más.

---

## Notas

- El `.env` **no se sube a GitHub** — está en `.gitignore`
- Si los CSVs no están disponibles, el sistema cae a datos mock automáticamente
- Créditos ElevenLabs: 131,000 disponibles (Plan Creator)