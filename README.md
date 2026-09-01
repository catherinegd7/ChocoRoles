# Order Rescue 🥤

**🏆 Hack4Her – 1er Lugar (Arca Continental Challenge, 2026)**

Ganadora del primer lugar en hackathon nacional de 24 horas. Plataforma basada en inteligencia artificial para la optimización de decisiones en cadena de suministro, integrando análisis predictivo, automatización de reportes y sistemas de notificación en tiempo real con **Python**, **Gemini API** y **MongoDB**.

## ¿Qué problema resuelve?

En los CEDIS de Arca Continental, cuando un producto se agota en un pedido, el cliente recibe una sustitución sin previo aviso, lo que genera quejas y riesgo de que la tienda deje de comprar (churn). Order Rescue detecta ese riesgo antes de que ocurra: identifica qué productos son propensos a desabasto, qué clientes están en riesgo de abandono y le da a cada rol (supervisor, conductor, cliente) la herramienta para actuar a tiempo.

## Cómo funciona

1. **Análisis de datos** (`backend/`): limpia y consolida los pedidos históricos, calcula la probabilidad de sustitución por producto y un score de riesgo de abandono por cliente.
2. **IA generativa con Gemini** (`Gemini API/`): dashboard con métricas en vivo, chatbot **ArcaBot** para que el supervisor del almacén pregunte por el estado del CEDIS, un generador de reportes automáticos, y predicciones (stock, temporada, impacto económico, detección de acaparadores) conectadas a MongoDB.
3. **Notificaciones de voz** (`elevenlabs/`): convierte las alertas de riesgo en audios con ElevenLabs TTS y los envía al conductor como nota de voz por WhatsApp, para avisar sustituciones o problemas antes de la entrega.
4. **App del cliente** (`frontend/`): interfaz en React donde la tienda ve sus productos en riesgo, elige un sustituto ("Plan B") con un clic y confirma el pedido.

## Estructura del proyecto

```
ChocoRoles/
├── backend/           # Limpieza de datos y cálculo de riesgo (poderMotor.py, limpieza.py, merge.py)
├── Gemini API/         # Backend Flask: dashboard, ArcaBot, reportes y predicciones con Gemini + MongoDB
├── elevenlabs/         # Backend FastAPI: alertas de voz (ElevenLabs) y envío por WhatsApp al conductor
├── frontend/           # App React + Vite para el cliente (pedidos y sustituciones)
└── *.csv               # Datos de pedidos usados para el análisis
```

## Stack

Python (Flask, FastAPI, pandas), Google Gemini API, MongoDB, ElevenLabs TTS, WhatsApp Business API, React + Vite + Tailwind.

## Cómo correrlo

Cada módulo tiene su propio setup y `readme.md` con el detalle:

- [`Gemini API/readme.md`](Gemini%20API/readme.md) — dashboard, ArcaBot y reportes (`python app.py`, puerto 8080)
- [`elevenlabs/readme.md`](elevenlabs/readme.md) — alertas de voz y WhatsApp (`uvicorn main:app --reload`, puerto 8000)
- [`frontend/`](frontend/) — app del cliente (`npm install && npm run dev`)

## Equipo

Proyecto desarrollado en 24 horas para el reto de Arca Continental en Hack4Her 2026.
