import glob
import pandas as pd
from pathlib import Path

try:
    from pymongo import MongoClient
    import certifi
    _MONGO_AVAILABLE = True
except ImportError:
    _MONGO_AVAILABLE = False

BASE_DIR = Path(__file__).parent.parent
BACKEND_DIR = BASE_DIR / "backend"

MONGO_URI = (
    "mongodb+srv://agustovalentin07_db_user:elbichosiu"
    "@basededatossi.7woegj5.mongodb.net/?appName=BaseDeDatosSi"
)
MONGO_DB = "HackathonArca"

_cached_df: pd.DataFrame | None = None
_mongo_client = None


# ─── INTERNAL LOADERS ─────────────────────────────────────────────────────────

def _clean_name(val):
    if pd.isna(val):
        return "Desconocido"
    return str(val).strip()


def _load_backend_csvs() -> pd.DataFrame | None:
    global _cached_df
    if _cached_df is not None:
        return _cached_df
    csv_files = sorted(glob.glob(str(BACKEND_DIR / "Datos_Limpios_ChocoRoles_parte_*.csv")))
    if not csv_files:
        return None
    _cached_df = pd.concat(
        (pd.read_csv(f, encoding="latin-1") for f in csv_files),
        ignore_index=True,
    )
    _cached_df.columns = _cached_df.columns.str.strip()
    return _cached_df


def _get_mongo_db():
    global _mongo_client
    if not _MONGO_AVAILABLE:
        return None
    if _mongo_client is None:
        _mongo_client = MongoClient(MONGO_URI, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=5000)
    return _mongo_client[MONGO_DB]


# ─── PUBLIC DATA LOADERS ──────────────────────────────────────────────────────

def load_data():
    """Return (orders, order_details, resultados) DataFrames.

    Primary source: 8-part backend CSVs.
    Fallback: root Orders.csv / OrderDetails.csv / Resultados.csv.
    """
    df = _load_backend_csvs()

    if df is not None:
        order_cols = [
            "id_pedido", "customer_id", "pais", "business_unit", "cedis",
            "fecha_pedido", "fecha_entrega", "status_final", "total",
        ]
        avail = [c for c in order_cols if c in df.columns]
        orders = df[avail].drop_duplicates(subset=["id_pedido"]).copy()
        orders.rename(columns={"total": "Total"}, inplace=True)

        sust_mask = (
            df["nombre_sku_solicitado_cambio"].notna()
            & (df["nombre_sku_solicitado_cambio"].astype(str).str.strip() != "nan")
        )
        resultados = df.loc[sust_mask, ["id_pedido", "nombre_sku_solicitado_y", "nombre_sku_solicitado_cambio"]].copy()
        resultados.rename(columns={"nombre_sku_solicitado_y": "nombre_sku_solicitado"}, inplace=True)
        resultados["nombre_sku_solicitado"] = resultados["nombre_sku_solicitado"].apply(_clean_name)
        resultados["nombre_sku_solicitado_cambio"] = resultados["nombre_sku_solicitado_cambio"].apply(_clean_name)

        detail_cols = ["id_pedido", "id_linea", "nombre_sku_solicitado_x", "quantity"]
        order_details = df[[c for c in detail_cols if c in df.columns]].copy()

        return orders, order_details, resultados

    # Fallback to root CSVs
    orders = pd.read_csv(BASE_DIR / "Orders.csv")
    order_details = pd.read_csv(BASE_DIR / "OrderDetails.csv")
    resultados = pd.read_csv(BASE_DIR / "Resultados.csv")
    for d in (orders, order_details, resultados):
        d.columns = d.columns.str.strip()
    resultados["nombre_sku_solicitado"] = resultados["nombre_sku_solicitado"].apply(_clean_name)
    resultados["nombre_sku_solicitado_cambio"] = resultados["nombre_sku_solicitado_cambio"].apply(_clean_name)
    return orders, order_details, resultados


def get_mongo_clientes_riesgo() -> list[dict]:
    """Load pre-computed client risk profiles from MongoDB."""
    try:
        db = _get_mongo_db()
        if db is None:
            return []
        docs = list(db["clientes_riesgo"].find({}, {"_id": 0}))
        return docs
    except Exception:
        return []


def get_mongo_client_profile(customer_id) -> dict | None:
    """Fetch a single client risk profile from MongoDB by customer_id."""
    try:
        db = _get_mongo_db()
        if db is None:
            return None
        return db["clientes_riesgo"].find_one({"customer_id": customer_id}, {"_id": 0})
    except Exception:
        return None


def list_mongo_collections() -> list[str]:
    """Return collection names available in the MongoDB database."""
    try:
        db = _get_mongo_db()
        if db is None:
            return []
        return db.list_collection_names()
    except Exception:
        return []


# ─── AGGREGATION FUNCTIONS ────────────────────────────────────────────────────

def get_summary(orders, resultados):
    total_pedidos = len(orders)
    total_sust = len(resultados)
    tasa = round(total_sust / total_pedidos * 100, 1) if total_pedidos else 0

    merged = resultados.merge(orders[["id_pedido", "customer_id"]], on="id_pedido", how="left")
    clientes_subs = merged.groupby("customer_id").size()
    criticos = int((clientes_subs >= 3).sum())

    return {
        "total_pedidos": total_pedidos,
        "total_sustituciones": total_sust,
        "tasa_sustitucion": tasa,
        "clientes_criticos": criticos,
    }


def get_top_substitutions(resultados, top_n=10):
    pairs = (
        resultados.groupby(["nombre_sku_solicitado", "nombre_sku_solicitado_cambio"])
        .size()
        .reset_index(name="frecuencia")
        .sort_values("frecuencia", ascending=False)
        .head(top_n)
    )
    return pairs.to_dict("records")


def get_most_substituted_products(resultados, top_n=10):
    prods = resultados["nombre_sku_solicitado"].value_counts().head(top_n).reset_index()
    prods.columns = ["producto", "frecuencia"]
    total = prods["frecuencia"].sum()
    prods["pct_total"] = (prods["frecuencia"] / max(total, 1) * 100).round(1)
    prods["producto"] = prods["producto"].str[:40]
    return prods.to_dict("records")


def get_most_used_substitutes(resultados, top_n=10):
    subs = resultados["nombre_sku_solicitado_cambio"].value_counts().head(top_n).reset_index()
    subs.columns = ["producto_sustituto", "frecuencia"]
    total = subs["frecuencia"].sum()
    subs["pct_total"] = (subs["frecuencia"] / max(total, 1) * 100).round(1)
    reemplaza = (
        resultados.groupby("nombre_sku_solicitado_cambio")["nombre_sku_solicitado"]
        .nunique()
        .reset_index()
    )
    reemplaza.columns = ["producto_sustituto", "productos_distintos"]
    subs = subs.merge(reemplaza, on="producto_sustituto", how="left")
    subs["producto_sustituto"] = subs["producto_sustituto"].str[:40]
    return subs.to_dict("records")


def get_cedis_stats(orders, resultados, top_n=10):
    merged = resultados.merge(orders[["id_pedido", "cedis"]], on="id_pedido", how="left")
    cedis = (
        merged.dropna(subset=["cedis"])
        .groupby("cedis")
        .size()
        .reset_index(name="total_sustituciones")
        .sort_values("total_sustituciones", ascending=False)
        .head(top_n)
    )
    cedis["cedis"] = cedis["cedis"].astype(str).str.strip()
    return cedis.to_dict("records")


def get_customer_risk(orders, resultados, top_n=20):
    """CSV-derived risk scoring. Merged with MongoDB scores when available."""
    merged = resultados.merge(orders[["id_pedido", "customer_id"]], on="id_pedido", how="left")

    subs_per = merged.groupby("customer_id").size().reset_index(name="sustituciones")
    orders_per = orders.groupby("customer_id").size().reset_index(name="total_pedidos")
    value_per = orders.groupby("customer_id")["Total"].sum().reset_index(name="valor_total")

    risk = subs_per.merge(orders_per, on="customer_id", how="left").merge(value_per, on="customer_id", how="left")
    risk["tasa_sustitucion"] = (risk["sustituciones"] / risk["total_pedidos"] * 100).round(1)
    risk["riesgo_score"] = (
        risk["tasa_sustitucion"] * 0.55 + (risk["sustituciones"].clip(0, 6) / 6 * 45)
    ).clip(0, 100).round(1)
    risk["nivel_riesgo"] = risk["riesgo_score"].apply(
        lambda x: "Crítico" if x >= 70 else ("Alto" if x >= 40 else "Medio")
    )
    risk = risk.sort_values("riesgo_score", ascending=False).head(top_n)
    risk["customer_id"] = risk["customer_id"].apply(lambda x: f"{float(x):.2e}" if pd.notna(x) else "N/A")
    risk["valor_total"] = risk["valor_total"].round(2).fillna(0)

    csv_records = risk.to_dict("records")

    # Enrich with MongoDB pre-computed scores when available
    mongo_risks = get_mongo_clientes_riesgo()
    if mongo_risks:
        mongo_map = {str(r.get("customer_id", "")): r for r in mongo_risks}
        for rec in csv_records:
            mongo_r = mongo_map.get(str(rec["customer_id"]))
            if mongo_r:
                rec["mongo_score_riesgo"] = mongo_r.get("score_riesgo")
                rec["mongo_estado"] = mongo_r.get("estado_satisfaccion")
                rec["mongo_total_compras"] = mongo_r.get("total_compras")

    return csv_records


def get_risk_distribution(orders, resultados):
    """Count ALL customers by risk level for donut chart."""
    merged = resultados.merge(orders[["id_pedido", "customer_id"]], on="id_pedido", how="left")
    subs_per = merged.groupby("customer_id").size().reset_index(name="sustituciones")
    orders_per = orders.groupby("customer_id").size().reset_index(name="total_pedidos")
    risk = subs_per.merge(orders_per, on="customer_id", how="outer").fillna(0)
    risk["tasa_sustitucion"] = (risk["sustituciones"] / risk["total_pedidos"].clip(lower=1) * 100).round(1)
    risk["riesgo_score"] = (
        risk["tasa_sustitucion"] * 0.55 + (risk["sustituciones"].clip(0, 6) / 6 * 45)
    ).clip(0, 100).round(1)
    risk["nivel_riesgo"] = risk["riesgo_score"].apply(
        lambda x: "Crítico" if x >= 70 else ("Alto" if x >= 40 else "Medio")
    )
    total_clientes = int(orders["customer_id"].nunique())
    clientes_con_sust = len(risk)
    sin_riesgo = max(0, total_clientes - clientes_con_sust)
    dist = risk["nivel_riesgo"].value_counts().to_dict()
    return {
        "total": total_clientes,
        "critico": int(dist.get("Crítico", 0)),
        "alto": int(dist.get("Alto", 0)),
        "medio": int(dist.get("Medio", 0)),
        "sin_riesgo": int(sin_riesgo),
    }


def get_substitutions_by_businessunit(orders, resultados):
    merged = resultados.merge(
        orders[["id_pedido", "business_unit"]], on="id_pedido", how="left"
    )
    bu = (
        merged.groupby("business_unit")
        .size()
        .reset_index(name="total")
        .sort_values("total", ascending=False)
    )
    bu["business_unit"] = bu["business_unit"].fillna("Desconocido").astype(str).str.strip()
    return bu.to_dict("records")


def get_dashboard_data():
    orders, order_details, resultados = load_data()

    data = {
        "summary": get_summary(orders, resultados),
        "top_sustituciones": get_top_substitutions(resultados),
        "productos_mas_sustituidos": get_most_substituted_products(resultados),
        "productos_sustitutos": get_most_used_substitutes(resultados),
        "cedis_criticos": get_cedis_stats(orders, resultados),
        "clientes_riesgo": get_customer_risk(orders, resultados),
        "riesgo_distribucion": get_risk_distribution(orders, resultados),
        "por_business_unit": get_substitutions_by_businessunit(orders, resultados),
    }

    # Attach MongoDB risk collection summary if available
    mongo_risks = get_mongo_clientes_riesgo()
    if mongo_risks:
        data["mongo_clientes_riesgo"] = mongo_risks[:50]  # cap for prompt size
        data["mongo_total_clientes"] = len(mongo_risks)

    return data
