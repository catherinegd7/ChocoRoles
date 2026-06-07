# mock_data.py — datos desde CSVs via data_processor.py

import sys
import os

# Apunta al folder Gemini API donde está data_processor.py
GEMINI_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Gemini API')
sys.path.insert(0, GEMINI_DIR)

try:
    from data_processor import load_data, get_customer_risk
    PROCESSOR_OK = True
except ImportError as e:
    PROCESSOR_OK = False
    print(f"⚠ No se pudo importar data_processor.py: {e} — usando datos mock")


# ─── FALLBACK MOCK ────────────────────────────────────────────────────────────

MOCK_ALERTS = [
    {
        "id": "alert_001",
        "parada": 1,
        "tipo": "critico",
        "cliente": "Cliente #8429",
        "cedis": "CEDIS Norte",
        "churn_score": 82,
        "sustituciones_mes": 4,
        "producto_original": "Coca-Cola 600ml",
        "producto_sustituto": "Coca-Cola Sin Azúcar 600ml",
        "accion_recomendada": "Hablar personalmente con el cliente y ofrecer puntos de compensación.",
        "puntos_compensacion": 150,
        "estado": "Cliente en Riesgo",
    },
    {
        "id": "alert_002",
        "parada": 2,
        "tipo": "aviso",
        "cliente": "Cliente #3037",
        "cedis": "CEDIS Sur",
        "churn_score": 41,
        "sustituciones_mes": 1,
        "producto_original": "Agua Mineral 600ml ×24",
        "producto_sustituto": None,
        "accion_recomendada": "Informar al cliente sobre el cambio en su pedido.",
        "puntos_compensacion": 50,
        "estado": "Riesgo Moderado",
    },
]

# Cache para no releer los CSVs en cada request
_alerts_cache = None


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def _formato_cliente(customer_id) -> str:
    """'2.05494e+18' → 'Cliente #2054' """
    try:
        id_str = str(customer_id).replace("e+", "").replace(".", "")
        return f"Cliente #{id_str[:4]}"
    except Exception:
        return f"Cliente {customer_id}"


def _get_tipo(score: float) -> str:
    if score >= 70:
        return "critico"
    elif score >= 40:
        return "aviso"
    return "info"


def _get_puntos(tipo: str) -> int:
    return {"critico": 150, "aviso": 50, "info": 0}.get(tipo, 0)


def _get_accion(tipo: str, sustituciones: int, tasa: float) -> str | None:
    if tipo == "critico":
        return (
            f"Cliente con {sustituciones} sustituciones y tasa de afectación del {tasa:.0f}%. "
            f"Hablar personalmente al entregar y ofrecer puntos de compensación."
        )
    elif tipo == "aviso":
        return f"Cliente con {sustituciones} sustituciones. Informar sobre cualquier cambio en el pedido."
    return None


def _csv_row_to_alert(row: dict, index: int) -> dict:
    score = float(row.get("riesgo_score", 0))
    sustituciones = int(row.get("sustituciones", 0))
    tasa = float(row.get("tasa_sustitucion", 0))
    tipo = _get_tipo(score)
    cedis = str(row.get("cedis", "CEDIS")).strip() if "cedis" in row else "CEDIS"

    return {
        "id": f"alert_{index:03d}",
        "parada": index + 1,
        "tipo": tipo,
        "cliente": _formato_cliente(row.get("customer_id", index)),
        "cedis": cedis,
        "churn_score": round(score),
        "sustituciones_mes": sustituciones,
        "producto_original": None,
        "producto_sustituto": None,
        "accion_recomendada": _get_accion(tipo, sustituciones, tasa),
        "puntos_compensacion": _get_puntos(tipo),
        "estado": row.get("nivel_riesgo", "Desconocido"),
        "tasa_sustitucion": tasa,
        "total_pedidos": row.get("total_pedidos", 0),
        "customer_id": row.get("customer_id"),
    }


# ─── API PÚBLICA ──────────────────────────────────────────────────────────────

def get_all_alerts() -> list[dict]:
    global _alerts_cache
    if _alerts_cache is not None:
        return _alerts_cache

    if PROCESSOR_OK:
        try:
            print("📂 Cargando datos desde CSVs...")
            orders, order_details, resultados = load_data()
            riesgo = get_customer_risk(orders, resultados, top_n=20)

            # Solo clientes con riesgo real
            con_riesgo = [r for r in riesgo if float(r.get("riesgo_score", 0)) >= 40]

            if not con_riesgo:
                # Si ninguno supera 40, mostrar top 10 de todos modos
                con_riesgo = riesgo[:10]

            alerts = [_csv_row_to_alert(r, i) for i, r in enumerate(con_riesgo)]
            _alerts_cache = alerts
            print(f"✓ {len(alerts)} alertas cargadas desde CSVs")
            return alerts

        except Exception as e:
            print(f"⚠ Error leyendo CSVs: {e} — usando mock")

    return MOCK_ALERTS


def get_alert_by_id(alert_id: str) -> dict | None:
    for a in get_all_alerts():
        if a["id"] == alert_id:
            return a
    return None

def build_voice_script(alert: dict) -> str:
    parada   = alert["parada"]
    sust     = alert["sustituciones_mes"]
    puntos   = alert["puntos_compensacion"]
    tasa     = alert.get("tasa_sustitucion", 0)
    estado   = alert.get("estado", "")

    if alert["tipo"] == "critico":
        detalle = (
            f"Ha tenido {sust} sustituciones con una tasa de afectación del {tasa:.0f} por ciento. "
            if sust > 0 else
            f"Su nivel de riesgo es crítico. "
        )
        return (
            f"Atención conductor. En la parada {parada} hay una alerta crítica. "
            f"{detalle}"
            f"Por favor, preséntate con amabilidad y menciona que el cliente recibirá "
            f"{puntos} puntos de compensación en su próximo pedido. "
            f"Tu trato en este momento puede marcar la diferencia para retener a este cliente."
        )
    elif alert["tipo"] == "aviso":
        return (
            f"Aviso para la parada {parada}. El cliente puede tener cambios en su pedido. "
            f"Infórmale con anticipación y recuérdale que recibirá "
            f"{puntos} puntos como compensación si hay alguna modificación."
        )
    else:
        return (
            f"Parada {parada}. "
            f"Cliente satisfecho, entrega normal sin cambios. Buen servicio."
        )