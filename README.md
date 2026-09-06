# SWAPP - Order Rescue

**🏆 Hack4Her – 1st Place (Arca Continental Challenge, 2026)**

Winner of a 24-hour national hackathon. An AI-powered platform for supply chain decision optimization, integrating predictive analytics, automated reporting, and real-time notification systems with **Python**, the **Gemini API**, and **MongoDB**.

## What problem does it solve?

At Arca Continental's distribution centers (CEDIS), when a product is out of stock, the customer's order gets substituted without warning — which leads to complaints and the risk of the store dropping the account (churn). Order Rescue flags that risk before it happens: it identifies which products are prone to running out, which customers are at risk of churning, and gives each role (supervisor, driver, customer) a tool to act in time.

## How it works

1. **Data analysis** (`backend/`): cleans and consolidates historical orders, calculates each product's substitution probability and a churn-risk score per customer.
2. **Generative AI with Gemini** (`Gemini API/`): a live-metrics dashboard, the **ArcaBot** chatbot for warehouse supervisors to ask about CEDIS status, an automated report generator, and predictions (stock, seasonality, economic impact, hoarder detection) connected to MongoDB.
3. **Voice notifications** (`elevenlabs/`): turns risk alerts into audio using ElevenLabs TTS and sends them to the driver as a WhatsApp voice note, warning about substitutions or issues before delivery.
4. **Customer app** (`frontend/`): a React interface where the store sees its at-risk products, picks a substitute ("Plan B") with one click, and confirms the order.

## Project structure

```
ChocoRoles/
├── backend/           # Data cleaning and risk scoring (poderMotor.py, limpieza.py, merge.py)
├── Gemini API/         # Flask backend: dashboard, ArcaBot, reports and predictions with Gemini + MongoDB
├── elevenlabs/         # FastAPI backend: voice alerts (ElevenLabs) and WhatsApp delivery to the driver
├── frontend/           # React + Vite app for the customer (orders and substitutions)
└── *.csv               # Order data used for the analysis
```

## Stack

Python (Flask, FastAPI, pandas), Google Gemini API, MongoDB, ElevenLabs TTS, WhatsApp Business API, React + Vite + Tailwind.

## Running it

Each module has its own setup, detailed in its own `readme.md`:

- [`Gemini API/readme.md`](Gemini%20API/readme.md) — dashboard, ArcaBot and reports (`python app.py`, port 8080)
- [`elevenlabs/readme.md`](elevenlabs/readme.md) — voice alerts and WhatsApp (`uvicorn main:app --reload`, port 8000)
- [`frontend/`](frontend/) — customer app (`npm install && npm run dev`)

## Team

Built in 24 hours for the Arca Continental challenge at Hack4Her 2026.
