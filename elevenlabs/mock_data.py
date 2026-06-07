# mock_data.py — datos desde CSVs via data_processor.py

import sys
import os

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
        "estado": "Crítico",
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
        "estado": "Alto",
    },
]

_alerts_cache = None


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def _get_tipo(nivel: str) -> str:
    nivel = str(nivel).lower()
    if "crítico" in nivel or "critico" in nivel:
        return "critico"
    elif "alto" in nivel:
        return "aviso"
    return "info"


def _get_puntos(tipo: str) -> int:
    return {"critico": 150, "aviso": 50, "info": 0}.get(tipo, 0)


def _get_accion(tipo: str, sustituciones: int, tasa: float) -> str | None:
    if tipo == "critico":
        return (
            f"Cliente con {sustituciones} sustituciones y tasa de afectación del {tasa:.0f}%. "
            "Hablar personalmente al entregar y ofrecer puntos de compensación."
        )
    elif tipo == "aviso":
        return f"Cliente con {sustituciones} sustituciones. Informar sobre cualquier cambio en el pedido."
    return None


def _csv_row_to_alert(row: dict, index: int) -> dict:
    score       = float(row.get("riesgo_score", row.get("tasa_sustitucion", 0)))
    sustituciones = int(row.get("sustituciones", 0))
    tasa        = float(row.get("tasa_sustitucion", 0))
    nivel       = str(row.get("nivel_riesgo", "Medio"))
    tipo        = _get_tipo(nivel)

    return {
        "id": f"alert_{index:03d}",
        "parada": index + 1,
        "tipo": tipo,
        "cliente": f"Parada {index + 1}",   # Sin nombre real en los datos
        "cedis": str(row.get("cedis", "CEDIS")).strip(),
        "churn_score": round(score),
        "sustituciones_mes": sustituciones,
        "producto_original": None,
        "producto_sustituto": None,
        "accion_recomendada": _get_accion(tipo, sustituciones, tasa),
        "puntos_compensacion": _get_puntos(tipo),
        "estado": nivel,
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
            # IMPORTANTE: el nuevo data_processor.py requiere order_details
            orders, order_details, resultados = load_data()
            riesgo = get_customer_risk(orders, order_details, resultados, top_n=20)

            if not riesgo:
                print("⚠ No se encontraron clientes con riesgo — usando mock")
                return MOCK_ALERTS

            alerts = [_csv_row_to_alert(r, i) for i, r in enumerate(riesgo)]
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
    """
    Guión de voz empático para ElevenLabs.
    El Rol 4 puede editar estos textos directamente aquí.
    """
    parada = alert["parada"]
    sust   = alert["sustituciones_mes"]
    puntos = alert["puntos_compensacion"]
    tasa   = alert.get("tasa_sustitucion", 0)
    estado = alert.get("estado", "")

    if alert["tipo"] == "critico":
        detalle = (
            f"Ha tenido {sust} sustituciones. "
            if sust > 0 else
            "Su nivel de riesgo es crítico. "
        )
        return (
            f"Atención conductor. En la parada {parada} hay una alerta crítica. "
            f"{detalle}"
            f"Por favor, preséntate con amabilidad y menciona que el cliente recibirá "
            f"{puntos} puntos de compensación en su próximo pedido. "
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
            "Cliente satisfecho, entrega normal sin cambios. Buen servicio."
        )
    
def build_apartar_script(alert: dict) -> str:
    parada = alert["parada"]
    return (
        f"Producto apartado para la parada {parada}. "
    )