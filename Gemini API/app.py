import datetime
import json
import os
import re
from dotenv import load_dotenv
load_dotenv()
import time
import uuid
import traceback
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from google import genai
from google.genai import types
from data_processor import (
    get_dashboard_data, load_data, get_customer_risk,
    get_mongo_client_profile, get_mongo_clientes_riesgo, list_mongo_collections,
)

app = Flask(__name__)
CORS(app)

API_KEY = os.environ["GEMINI_API_KEY"]
client = genai.Client(api_key=API_KEY)

# Models tried in order when one is unavailable (503 / overloaded)
_MODELS = ["gemini-3.1-flash-lite", "gemini-2.5-flash", "gemini-2.0-flash"]


def gemini_generate(contents, config, retries: int = 2):
    """Call generate_content with automatic model fallback on 503."""
    last_err = None
    for model in _MODELS:
        for attempt in range(retries):
            try:
                return client.models.generate_content(
                    model=model, contents=contents, config=config
                )
            except Exception as e:
                msg = str(e)
                if "503" in msg or "UNAVAILABLE" in msg or "overloaded" in msg.lower():
                    wait = 1.5 * (attempt + 1)
                    time.sleep(wait)
                    last_err = e
                    continue  # retry same model
                raise  # any other error → bubble up immediately
        # exhausted retries on this model → try next
    raise last_err


def gemini_chat_send(chat_session, message, retries: int = 2):
    """Send a chat message with retry on 503."""
    last_err = None
    for attempt in range(retries + 1):
        try:
            return chat_session.send_message(message)
        except Exception as e:
            msg = str(e)
            if "503" in msg or "UNAVAILABLE" in msg or "overloaded" in msg.lower():
                time.sleep(1.5 * (attempt + 1))
                last_err = e
            else:
                raise
    raise last_err

_chat_sessions: dict = {}


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def _build_system_prompt(data: dict) -> str:
    data_str = json.dumps(data, indent=2, ensure_ascii=False, default=str)
    mongo_note = ""
    if data.get("mongo_clientes_riesgo"):
        mongo_note = (
            f"\n\nAdemás tienes acceso a {data.get('mongo_total_clientes', 0)} perfiles de clientes "
            "pre-calculados en MongoDB (campo 'mongo_clientes_riesgo'). "
            "Estos perfiles incluyen score_riesgo, estado_satisfaccion y total_compras calculados por el equipo de Data Science."
        )
    return f"""Eres 'ArcaBot', el asistente de IA integrado en el dashboard de supervisores de almacén de Arca Continental.

Tienes acceso a los siguientes datos reales de la operación (fuente: CSV backend + MongoDB):
{data_str}{mongo_note}

Reglas estrictas:
1. Responde siempre en español, con un tono empático, profesional y directo.
2. Para clientes en nivel Crítico (score ≥ 70), sugiere acciones concretas: bonos, llamada inmediata, prioridad de entrega.
3. Si piden reporte, genera HTML con <h2>, <h3>, <ul>, <li>, <table>. Sin DOCTYPE ni body.
4. Basa SIEMPRE tus respuestas en los datos reales. No inventes números.
5. Junio = época de calor → alta demanda de bebidas.
"""


def _get_filtered_data(params: dict):
    orders, order_details, resultados = load_data()
    country = (params.get("country") or "todos").strip()
    cedis_f = str(params.get("cedis") or "todos").strip()
    bu_f = (params.get("business_unit") or "todos").strip()

    f_orders = orders.copy()
    if country.lower() != "todos":
        f_orders = f_orders[f_orders["pais"].str.lower() == country.lower()]
    if cedis_f.lower() != "todos":
        f_orders = f_orders[f_orders["cedis"].astype(str).str.strip() == cedis_f]
    if bu_f.lower() != "todos":
        f_orders = f_orders[f_orders["business_unit"].str.lower() == bu_f.lower()]

    f_resultados = resultados[resultados["id_pedido"].isin(f_orders["id_pedido"])]
    return f_orders, f_resultados


# ─── DASHBOARD ROUTES ─────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("dashboard.html")


@app.route("/api/stats")
def stats():
    try:
        return jsonify(get_dashboard_data())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/chat", methods=["POST"])
def chat():
    body = request.get_json(force=True)
    message = body.get("message", "").strip()
    session_id = body.get("session_id", "default")
    if not message:
        return jsonify({"error": "Mensaje vacío"}), 400
    try:
        data = get_dashboard_data()
        if session_id not in _chat_sessions:
            _chat_sessions[session_id] = client.chats.create(
                model="gemini-3.1-flash-lite",
                config=types.GenerateContentConfig(
                    system_instruction=_build_system_prompt(data),
                    temperature=0.4,
                ),
            )
        response = gemini_chat_send(_chat_sessions[session_id], message)
        return jsonify({"response": response.text, "ok": True})
    except Exception as e:
        return jsonify({"error": str(e), "ok": False}), 500


@app.route("/api/report", methods=["POST"])
def report():
    body = request.get_json(force=True) or {}
    report_type = body.get("type", "semanal")
    try:
        data = get_dashboard_data()
        data_str = json.dumps(data, indent=2, ensure_ascii=False, default=str)
        config = types.GenerateContentConfig(
            system_instruction="Eres un Analista de Estrategia Operativa de Arca Continental. Genera reportes en HTML limpio sin DOCTYPE ni body.",
            temperature=0.3,
        )
        prompt = f"""Genera un reporte ejecutivo {report_type} basado en estos datos:
{data_str}

Secciones obligatorias:
<h2>1. Resumen Ejecutivo</h2> — tabla con 4 KPIs
<h2>2. Top Sustituciones</h2> — tabla top 5 pares
<h2>3. CEDIS Críticos</h2> — 5 CEDIS con recomendaciones
<h2>4. Plan de Rescate Clientes</h2> — acciones por cliente crítico
<h2>5. Recomendaciones Generales</h2> — 3-5 acciones concretas"""
        response = gemini_generate(contents=prompt, config=config)
        return jsonify({"report": response.text, "ok": True})
    except Exception as e:
        return jsonify({"error": str(e), "ok": False}), 500


@app.route("/api/new-session")
def new_session():
    return jsonify({"session_id": str(uuid.uuid4())})


# ─── REPORT BUILDER ROUTES ────────────────────────────────────────────────────

@app.route("/report-builder")
def report_builder():
    return render_template("report_builder.html")


@app.route("/api/rb/options")
def rb_options():
    """Return all available filter options derived from real data."""
    try:
        orders, _, resultados = load_data()
        countries = sorted(orders["pais"].dropna().unique().tolist())
        merged_c = resultados.merge(orders[["id_pedido", "cedis"]], on="id_pedido", how="left")
        cedis_top = (
            merged_c.groupby("cedis").size()
            .sort_values(ascending=False).head(15)
        )
        cedis_list = [str(c).strip() for c in cedis_top.index if str(c).strip()]
        bus = sorted(orders["business_unit"].dropna().unique().tolist())

        return jsonify({
            "countries": countries,
            "cedis": cedis_list,
            "business_units": bus,
            "analysis_types": [
                {"value": "sustituciones",    "label": "Sustituciones",          "icon": "fa-exchange-alt",   "desc": "Qué productos se sustituyen y con qué frecuencia"},
                {"value": "clientes_riesgo",  "label": "Clientes en Riesgo",     "icon": "fa-user-times",     "desc": "Clientes con mayor probabilidad de abandono"},
                {"value": "cedis",            "label": "CEDIS Performance",       "icon": "fa-warehouse",      "desc": "Centros de distribución con más sustituciones"},
                {"value": "productos",        "label": "Análisis de Productos",   "icon": "fa-boxes",          "desc": "Productos más pedidos y más sustituidos"},
                {"value": "general",          "label": "Reporte General",         "icon": "fa-chart-bar",      "desc": "Visión completa: sustituciones, CEDIS y clientes"},
            ],
            "chart_types": [
                {"value": "bar",            "label": "Barras"},
                {"value": "doughnut",       "label": "Donut"},
                {"value": "table",          "label": "Tabla de datos"},
                {"value": "horizontal_bar", "label": "Barras Horizontales"},
            ],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/rb/chat", methods=["POST"])
def rb_chat():
    """Simple Q&A chatbot with full data context."""
    body = request.get_json(force=True)
    message = body.get("message", "").strip()
    session_id = "rb_" + body.get("session_id", "default")

    try:
        data = get_dashboard_data()
        data_str = json.dumps(data, indent=2, ensure_ascii=False, default=str)

        if session_id not in _chat_sessions:
            system = f"""Eres ArcaBot, asistente de análisis operativo para supervisores de Arca Continental.

Tienes acceso a estos datos reales de la operación:
{data_str}

Responde preguntas concretas sobre:
- Productos más sustituidos y con qué se sustituyen
- Clientes en riesgo de abandono y sus scores
- CEDIS con más sustituciones
- Estadísticas globales de sustituciones

Reglas estrictas:
- Respuestas directas, máximo 4 oraciones.
- Usa siempre los datos reales. Nunca inventes cifras.
- Español, tono profesional y amigable.
- Si no tienes la información solicitada, dilo claramente."""

            _chat_sessions[session_id] = client.chats.create(
                model="gemini-3.1-flash-lite",
                config=types.GenerateContentConfig(
                    system_instruction=system, temperature=0.4
                ),
            )

        response = gemini_chat_send(_chat_sessions[session_id], message)
        return jsonify({"response": response.text.strip(), "ok": True})

    except Exception as e:
        return jsonify({"error": str(e), "ok": False}), 500


@app.route("/api/rb/generate", methods=["POST"])
def rb_generate():
    """Generate a full report with Chart.js data + Gemini narrative."""
    body = request.get_json(force=True)
    params = body.get("params", {})

    try:
        f_orders, f_resultados = _get_filtered_data(params)
        analysis_type = params.get("analysis_type", "general")

        n_pedidos = len(f_orders)
        n_sust = len(f_resultados)
        tasa = round(n_sust / max(n_pedidos, 1) * 100, 1)

        summary_cards = [
            {"label": "Pedidos Analizados",  "value": f"{n_pedidos:,}",  "icon": "fa-shopping-cart", "color": "#60a5fa"},
            {"label": "Sustituciones",        "value": f"{n_sust:,}",     "icon": "fa-exchange-alt",  "color": "#fb923c"},
            {"label": "Tasa de Sustitución",  "value": f"{tasa}%",        "icon": "fa-percent",       "color": "#fbbf24"},
        ]

        charts = []

        # --- Sustituciones / Productos ---
        if analysis_type in ("sustituciones", "general", "productos") and n_sust > 0:
            top_prods = f_resultados["nombre_sku_solicitado"].value_counts().head(10)
            charts.append({
                "id": "chart_top_prods",
                "type": "bar",
                "title": "Top 10 Productos Más Sustituidos",
                "data": {
                    "labels": [p[:38] for p in top_prods.index.tolist()],
                    "datasets": [{"label": "Frecuencia", "data": top_prods.values.tolist(),
                        "backgroundColor": "rgba(239,68,68,0.75)", "borderColor": "#ef4444",
                        "borderWidth": 1, "borderRadius": 5}],
                },
                "options": {"indexAxis": "y"},
            })

            pairs = (
                f_resultados
                .groupby(["nombre_sku_solicitado", "nombre_sku_solicitado_cambio"])
                .size().reset_index(name="freq")
                .sort_values("freq", ascending=False).head(8)
            )
            charts.append({
                "id": "table_pairs",
                "type": "table",
                "title": "Pares de Sustitución Más Frecuentes",
                "headers": ["Producto Solicitado", "→ Sustituido Por", "Veces"],
                "rows": [
                    [r["nombre_sku_solicitado"][:45], r["nombre_sku_solicitado_cambio"][:45], r["freq"]]
                    for _, r in pairs.iterrows()
                ],
            })

        # --- Clientes en riesgo ---
        if analysis_type in ("clientes_riesgo", "general") and n_sust > 0:
            merged = f_resultados.merge(f_orders[["id_pedido", "customer_id"]], on="id_pedido", how="left")
            cust = merged.groupby("customer_id").size()
            criticos = int((cust >= 5).sum())
            altos    = int(((cust >= 3) & (cust < 5)).sum())
            medios   = int(((cust >= 1) & (cust < 3)).sum())

            summary_cards.append({"label": "Clientes Críticos", "value": str(criticos), "icon": "fa-user-times", "color": "#f87171"})
            charts.append({
                "id": "chart_risk",
                "type": "doughnut",
                "title": "Distribución de Riesgo de Clientes",
                "data": {
                    "labels": [f"Crítico — {criticos}", f"Alto — {altos}", f"Medio — {medios}"],
                    "datasets": [{"data": [criticos, altos, medios],
                        "backgroundColor": ["rgba(239,68,68,0.85)", "rgba(251,146,60,0.85)", "rgba(96,165,250,0.85)"],
                        "borderColor": "#111827", "borderWidth": 2}],
                },
            })

        # --- CEDIS ---
        if analysis_type in ("cedis", "general") and n_sust > 0:
            mc = f_resultados.merge(f_orders[["id_pedido", "cedis"]], on="id_pedido", how="left")
            cedis_cnt = mc.groupby("cedis").size().sort_values(ascending=False).head(10)
            if len(cedis_cnt):
                charts.append({
                    "id": "chart_cedis",
                    "type": "bar",
                    "title": "Sustituciones por CEDIS",
                    "data": {
                        "labels": ["CEDIS " + str(c) for c in cedis_cnt.index],
                        "datasets": [{"label": "Sustituciones", "data": cedis_cnt.values.tolist(),
                            "backgroundColor": "rgba(251,146,60,0.75)", "borderColor": "#fb923c",
                            "borderWidth": 1, "borderRadius": 5}],
                    },
                })

        # --- Business unit donut ---
        if analysis_type == "general" and n_sust > 0:
            mb = f_resultados.merge(f_orders[["id_pedido", "business_unit"]], on="id_pedido", how="left")
            bu_cnt = mb.groupby("business_unit").size().sort_values(ascending=False)
            if len(bu_cnt):
                charts.append({
                    "id": "chart_bu",
                    "type": "doughnut",
                    "title": "Sustituciones por Unidad de Negocio",
                    "data": {
                        "labels": bu_cnt.index.tolist(),
                        "datasets": [{"data": bu_cnt.values.tolist(),
                            "backgroundColor": ["rgba(167,139,250,0.85)", "rgba(52,211,153,0.85)", "rgba(251,191,36,0.85)", "rgba(236,72,153,0.85)"],
                            "borderColor": "#111827", "borderWidth": 2}],
                    },
                })

        # --- Gemini narrative ---
        meta = {
            "filtros": params,
            "pedidos_analizados": n_pedidos,
            "sustituciones": n_sust,
            "tasa_sustitucion": tasa,
            "top_5_sustituidos": f_resultados["nombre_sku_solicitado"].value_counts().head(5).to_dict() if n_sust else {},
        }
        nar = gemini_generate(
            contents=f"""Genera un análisis ejecutivo breve (máx 200 palabras) en HTML para este reporte de Arca Continental:

Datos: {json.dumps(meta, ensure_ascii=False, default=str)}
Tipo de análisis: {analysis_type}

Estructura EXACTA (sin DOCTYPE, html, head, body):
<p><strong>Diagnóstico:</strong> [2 oraciones sobre hallazgos clave]</p>
<ul><li>[Insight accionable 1]</li><li>[Insight 2]</li><li>[Insight 3]</li></ul>
<p class="rec"><strong>⚡ Acción prioritaria:</strong> [Una acción concreta e inmediata para hoy]</p>""",
            config=types.GenerateContentConfig(
                system_instruction="Analista de operaciones de Arca Continental. Español. Específico y accionable.",
                temperature=0.3,
            ),
        )

        # Ask Gemini what report to recommend next based on what the user just saw
        recommendation = None
        try:
            rec_resp = gemini_generate(
                contents=f"""El usuario de Arca Continental acaba de ver un reporte de tipo '{analysis_type}' \
con estos resultados clave: {n_pedidos} pedidos, {n_sust} sustituciones, tasa {tasa}%, \
filtros: país={params.get('country','todos')} cedis={params.get('cedis','todos')}.

Elige el siguiente análisis más valioso para complementar lo que ya vio y profundizar la investigación.
Responde ÚNICAMENTE con JSON válido (sin markdown, sin texto extra):
{{"analysis_type":"...","label":"...","reason":"..."}}

Opciones para analysis_type: sustituciones, clientes_riesgo, cedis, productos, general
label: nombre corto amigable (ej: "Clientes en Riesgo")
reason: una sola oración explicando por qué ese análisis aporta valor después de lo que ya vio.""",
                config=types.GenerateContentConfig(temperature=0.3),
            )
            m = re.search(r'\{[^}]+\}', rec_resp.text, re.DOTALL)
            if m:
                recommendation = json.loads(m.group())
        except Exception:
            pass

        return jsonify({
            "ok": True,
            "charts": charts,
            "summary_cards": summary_cards,
            "narrative": nar.text,
            "meta": meta,
            "recommendation": recommendation,
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "trace": traceback.format_exc()}), 500


@app.route("/api/mongo/status")
def mongo_status():
    """Return MongoDB connection status and available collections."""
    try:
        colecciones = list_mongo_collections()
        clientes = get_mongo_clientes_riesgo()
        return jsonify({
            "ok": True,
            "colecciones": colecciones,
            "clientes_riesgo_count": len(clientes),
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/analizar-cliente/<customer_id>")
def analizar_cliente(customer_id):
    """Generate an AI recommendation for a specific client using MongoDB + CSV data."""
    try:
        # Try MongoDB first for pre-computed risk profile
        perfil = get_mongo_client_profile(customer_id)

        if perfil:
            prompt = f"""Eres un asistente de ventas experto de Arca Continental.
Tenemos un cliente con el siguiente perfil de riesgo calculado por nuestro equipo de Data Science:

- ID del Cliente: {perfil.get('customer_id', customer_id)}
- Total de Compras: {perfil.get('total_compras', 'N/D')}
- Productos que le faltaron (Sustituidos): {perfil.get('productos_sustituidos', 'N/D')}
- Score de Riesgo (0 a 100): {perfil.get('score_riesgo', 'N/D')}
- Estado de Satisfacción: {perfil.get('estado_satisfaccion', 'N/D')}

Basado en estos datos, redacta un mensaje corto (máximo 3 líneas) con una recomendación directa
para el vendedor que va a visitar a este cliente hoy.
¿Qué le podemos ofrecer para que no abandone la marca?"""
        else:
            # Fallback: compute from CSV data
            orders, _, resultados = load_data()
            try:
                cid = float(customer_id)
                c_orders = orders[orders["customer_id"] == cid]
                c_sust = resultados[resultados["id_pedido"].isin(c_orders["id_pedido"])]
            except ValueError:
                c_orders = orders[orders["customer_id"].astype(str) == customer_id]
                c_sust = resultados[resultados["id_pedido"].isin(c_orders["id_pedido"])]

            if c_orders.empty:
                return jsonify({"ok": False, "error": "Cliente no encontrado"}), 404

            n_pedidos = len(c_orders)
            n_sust = len(c_sust)
            tasa = round(n_sust / max(n_pedidos, 1) * 100, 1)
            valor = round(c_orders["Total"].sum(), 2) if "Total" in c_orders.columns else "N/D"
            top_sust = c_sust["nombre_sku_solicitado"].value_counts().head(3).to_dict() if n_sust else {}

            prompt = f"""Eres un asistente de ventas experto de Arca Continental.
Tenemos un cliente derivado del análisis de nuestros datos CSV:

- ID del Cliente: {customer_id}
- Total de Pedidos: {n_pedidos}
- Total de Sustituciones Recibidas: {n_sust}
- Tasa de Sustitución: {tasa}%
- Valor Total de Compras: {valor}
- Productos más sustituidos: {top_sust}

Basado en estos datos, redacta un mensaje corto (máximo 3 líneas) con una recomendación directa
para el vendedor que va a visitar a este cliente hoy."""

        config = types.GenerateContentConfig(
            system_instruction="Analista de ventas de Arca Continental. Español. Tono empático y directo.",
            temperature=0.4,
        )
        response = gemini_generate(contents=prompt, config=config)
        return jsonify({"ok": True, "customer_id": customer_id, "recomendacion": response.text, "fuente": "mongodb" if perfil else "csv"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/mongo/clientes-riesgo")
def mongo_clientes_riesgo():
    """Return all MongoDB pre-computed client risk profiles."""
    try:
        clientes = get_mongo_clientes_riesgo()
        return jsonify({"ok": True, "clientes": clientes, "total": len(clientes)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ─── PREDICCIONES IA ──────────────────────────────────────────────────────────

@app.route("/api/predicciones/stock", methods=["POST"])
def prediccion_stock():
    """Predict stock-break risk for most-substituted products."""
    try:
        orders, _, resultados = load_data()
        total_pedidos = len(orders)
        total_sust = len(resultados)

        # Top 10 productos más sustituidos con su probabilidad
        top_prods = resultados["nombre_sku_solicitado"].value_counts().head(10)
        productos_info = []
        for prod, freq in top_prods.items():
            prob_pct = round(freq / max(total_pedidos, 1) * 100, 2)
            # Best substitute found for this product
            sust_row = (
                resultados[resultados["nombre_sku_solicitado"] == prod]
                ["nombre_sku_solicitado_cambio"].value_counts()
            )
            sustituto = sust_row.index[0] if len(sust_row) else "Sin sustituto claro"
            productos_info.append({
                "producto": prod[:50],
                "veces_sustituido": int(freq),
                "probabilidad_fallo_pct": prob_pct,
                "mejor_sustituto": sustituto[:50],
            })

        # Try MongoDB productos_vulnerables for enrichment
        try:
            db = _get_mongo_db_direct()
            if db is not None:
                vuln = list(db["productos_vulnerables"].find({}, {"_id": 0}))
                vuln_map = {v.get("nombre_sku_solicitado", ""): v for v in vuln}
                for p in productos_info:
                    mongo_data = vuln_map.get(p["producto"])
                    if mongo_data:
                        p["probabilidad_fallo_pct"] = mongo_data.get("probabilidad_sustitucion_%", p["probabilidad_fallo_pct"])
        except Exception:
            pass


        mes_actual = datetime.datetime.now().strftime("%B %Y")
        cedis_top = (
            resultados.merge(orders[["id_pedido", "cedis"]], on="id_pedido", how="left")
            .groupby("cedis").size().sort_values(ascending=False).head(3)
        )
        cedis_criticos = [f"CEDIS {c}" for c in cedis_top.index]

        prompt = f"""Analista de suministro Arca Continental. HTML sin DOCTYPE. Sin emojis ni iconos de ningún tipo.

DATOS: {mes_actual} | {total_pedidos:,} pedidos | {total_sust:,} sustituciones | CEDIS criticos: {', '.join(cedis_criticos)}
TOP 10 PRODUCTOS: {json.dumps(productos_info, ensure_ascii=False)}

Genera exactamente este HTML sin emojis y sin texto extra fuera del HTML:
<h3>Quiebre de Stock — {mes_actual}</h3>
<h4>Riesgo esta semana</h4>
<table><thead><tr><th>Producto</th><th>% Fallo</th><th>Sustituto</th><th>Accion</th></tr></thead>
<tbody>[5 filas con datos reales, accion en 5 palabras max]</tbody></table>
<h4>Inventario</h4>
<ul>[3 bullets: verbo + objeto + cantidad/plazo, sin explicaciones]</ul>
<p class="rec"><strong>HOY:</strong> [Una accion urgente, max 15 palabras]</p>"""

        response = gemini_generate(
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction="Analista de cadena de suministro de Arca Continental. Español, profesional y directo. Jamas uses emojis, iconos unicode ni simbolos especiales.",
                temperature=0.3,
            ),
        )
        return jsonify({"ok": True, "prediccion": response.text, "datos_usados": len(productos_info)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/predicciones/siguiente-accion", methods=["POST"])
def prediccion_siguiente_accion():
    """Next best action for the top at-risk clients."""
    try:

        orders, _, resultados = load_data()
        clientes = get_customer_risk(orders, resultados, top_n=5)

        clientes_str = json.dumps(clientes, ensure_ascii=False, indent=2, default=str)

        prompt = f"""Asesor comercial Arca Continental. HTML sin DOCTYPE. Sin emojis. Sin texto fuera del HTML.

CLIENTES EN RIESGO: {clientes_str}

Para cada cliente genera exactamente este bloque, sin emojis ni iconos:
<div class="accion-cliente">
  <div class="accion-header"><span class="badge-riesgo [critico|alto]">[Critico|Alto]</span> <strong>Cliente [ID]</strong> — Score [X]% — [X] sustituciones</div>
  <p class="accion-diagnostico">[Motivo en 10 palabras max: producto fallido, frecuencia]</p>
  <p class="accion-rec"><strong>HOY:</strong> [Accion concreta: verbo + que + a quien, max 15 palabras]</p>
</div>
[Repite para los 5 clientes. Sin h3, sin p inicial, sin texto extra, sin emojis]"""

        response = gemini_generate(
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction="Asesor comercial senior de Arca Continental. Español, accionable, empático. Jamas uses emojis, iconos unicode ni simbolos especiales.",
                temperature=0.4,
            ),
        )
        return jsonify({"ok": True, "prediccion": response.text, "clientes_analizados": len(clientes)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/predicciones/temporada", methods=["POST"])
def prediccion_temporada():
    """Seasonal high-demand prediction based on current month + product data."""
    try:

        orders, _, resultados = load_data()

        now = datetime.datetime.now()
        mes = now.month
        nombre_mes = now.strftime("%B")

        top_prods = resultados["nombre_sku_solicitado"].value_counts().head(15)
        prods_list = [{"producto": p[:50], "sustituciones": int(f)} for p, f in top_prods.items()]

        # Business unit breakdown
        bu_merged = resultados.merge(orders[["id_pedido", "business_unit"]], on="id_pedido", how="left")
        bu_counts = bu_merged.groupby("business_unit").size().sort_values(ascending=False).to_dict()

        # CEDIS breakdown
        cedis_merged = resultados.merge(orders[["id_pedido", "cedis"]], on="id_pedido", how="left")
        cedis_counts = cedis_merged.groupby("cedis").size().sort_values(ascending=False).head(5).to_dict()
        cedis_str = {f"CEDIS {k}": int(v) for k, v in cedis_counts.items()}

        contexto_estacional = {
            12: "diciembre, temporada navideña — alta demanda de bebidas premium, cervezas, sidras",
            1: "enero, inicio de año — demanda estable, menor actividad post-fiestas",
            2: "febrero, San Valentín — oportunidad en jugos y bebidas especiales",
            3: "marzo, inicio primavera — demanda creciente de bebidas refrescantes",
            4: "abril, Semana Santa — picos en agua, jugos, bebidas sin alcohol",
            5: "mayo, calor creciente — alta demanda de agua y bebidas frías",
            6: "junio, inicio de verano — MÁXIMA demanda de bebidas: refrescos, agua, deportivas, sin alcohol",
            7: "julio, verano pleno — demanda muy alta de bebidas frías y de hidratación",
            8: "agosto, fin de verano — demanda sostenida de bebidas, regreso a clases",
            9: "septiembre, Fiestas Patrias México — alta demanda de cervezas y bebidas especiales",
            10: "octubre — demanda en descenso gradual, oportunidad de reposición de inventario",
            11: "noviembre, previo temporada navideña — alerta de preparación de inventario",
        }.get(mes, f"{nombre_mes}, mes estándar")

        prompt = f"""Analista de demanda Arca Continental. HTML sin DOCTYPE. Sin emojis. Solo HTML.

{nombre_mes} — {contexto_estacional}
PRODUCTOS (mas sustituidos): {json.dumps(prods_list, ensure_ascii=False)}
CEDIS TOP 5: {json.dumps(cedis_str, ensure_ascii=False)}

Genera exactamente este HTML sin emojis ni iconos:
<h3>Temporada {nombre_mes}</h3>
<p><strong>Contexto:</strong> [1 oracion clave sobre riesgo de demanda este mes]</p>
<h4>Demanda esperada</h4>
<table><thead><tr><th>Producto</th><th>Riesgo</th><th>+Demanda</th><th>Stock recomendado</th></tr></thead>
<tbody>[6 filas con datos reales y cifras estimadas]</tbody></table>
<h4>Alertas CEDIS</h4>
<ul>[3 bullets: CEDIS + riesgo especifico + accion, max 12 palabras c/u]</ul>
<h4>Cross-selling</h4>
<ul>[2 bullets: producto + perfil de cliente + probabilidad aceptacion]</ul>
<p class="rec"><strong>Esta semana:</strong> [Accion prioritaria, max 15 palabras]</p>"""

        response = gemini_generate(
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction="Analista de demanda de Arca Continental. Español. Predicciones basadas en datos históricos. Jamas uses emojis, iconos unicode ni simbolos especiales.",
                temperature=0.35,
            ),
        )
        return jsonify({"ok": True, "prediccion": response.text, "mes": nombre_mes})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/predicciones/impacto-economico", methods=["POST"])
def prediccion_impacto_economico():
    """Financial loss projection from at-risk clients."""
    try:

        orders, _, resultados = load_data()
        clientes = get_customer_risk(orders, resultados, top_n=50)

        criticos = [c for c in clientes if c["nivel_riesgo"] == "Crítico"]
        altos    = [c for c in clientes if c["nivel_riesgo"] == "Alto"]
        medios   = [c for c in clientes if c["nivel_riesgo"] == "Medio"]

        valor_criticos = sum(c.get("valor_total", 0) or 0 for c in criticos)
        valor_altos    = sum(c.get("valor_total", 0) or 0 for c in altos)
        valor_medios   = sum(c.get("valor_total", 0) or 0 for c in medios)
        valor_total    = valor_criticos + valor_altos + valor_medios

        total_pedidos = len(orders)
        total_sust = len(resultados)
        tasa_global = round(total_sust / max(total_pedidos, 1) * 100, 1)

        top_critico = max(criticos, key=lambda c: c.get("valor_total", 0) or 0) if criticos else None

        resumen = {
            "clientes_criticos": len(criticos),
            "clientes_altos": len(altos),
            "clientes_medios": len(medios),
            "valor_en_riesgo_criticos": round(valor_criticos, 2),
            "valor_en_riesgo_altos": round(valor_altos, 2),
            "valor_en_riesgo_medios": round(valor_medios, 2),
            "valor_total_en_riesgo": round(valor_total, 2),
            "tasa_sustitucion_global": tasa_global,
            "cliente_mayor_valor_en_riesgo": top_critico,
        }

        prompt = f"""Director financiero Arca Continental. HTML sin DOCTYPE. Sin emojis. Solo HTML.

DATOS: {json.dumps(resumen, ensure_ascii=False, default=str)}

Genera exactamente este HTML sin emojis ni iconos:
<h3>Impacto Economico</h3>
<table><thead><tr><th>KPI</th><th>Valor</th><th>Nivel</th></tr></thead>
<tbody>
<tr><td>Clientes Criticos</td><td>[N]</td><td>Alto</td></tr>
<tr><td>Valor en Riesgo</td><td>$[monto MXN]</td><td>Inmediato</td></tr>
<tr><td>Tasa Sustitucion</td><td>[%]</td><td>[nivel segun umbral]</td></tr>
<tr><td>Perdida proyectada/mes</td><td>$[estimado MXN]</td><td>Proyectado</td></tr>
</tbody></table>
<h4>Cliente prioritario</h4>
<p>[ID + valor historico + accion especifica en 1 linea]</p>
<h4>Proyeccion</h4>
<table><thead><tr><th>Escenario</th><th>Clientes perdidos</th><th>Perdida/mes</th><th>Anual</th></tr></thead>
<tbody>[2 filas: sin intervencion vs con plan]</tbody></table>
<h4>Plan de rescate</h4>
<ul>[3 bullets: accion + responsable + plazo, max 12 palabras c/u]</ul>
<p class="rec"><strong>Direccion:</strong> [Una decision ejecutiva, max 15 palabras]</p>"""

        response = gemini_generate(
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction="Director de estrategia financiera de Arca Continental. Español. Tono ejecutivo, cifras concretas en pesos mexicanos. Jamas uses emojis, iconos unicode ni simbolos especiales.",
                temperature=0.3,
            ),
        )
        return jsonify({"ok": True, "prediccion": response.text, "resumen_datos": resumen})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


def _get_mongo_db_direct():
    """Direct MongoDB access for prediction endpoints."""
    try:
        from pymongo import MongoClient
        import certifi
        c = MongoClient(
            "mongodb+srv://agustovalentin07_db_user:elbichosiu@basededatossi.7woegj5.mongodb.net/?appName=BaseDeDatosSi",
            tlsCAFile=certifi.where(), serverSelectionTimeoutMS=3000
        )
        return c["HackathonArca"]
    except Exception:
        return None


if __name__ == "__main__":
    app.run(debug=True, port=5000)
