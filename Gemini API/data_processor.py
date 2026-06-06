import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent  # ChocoRoles root


def _clean_name(val):
    if pd.isna(val):
        return "Desconocido"
    return str(val).strip()


def load_data():
    orders = pd.read_csv(BASE_DIR / "Orders.csv")
    order_details = pd.read_csv(BASE_DIR / "OrderDetails.csv")
    resultados = pd.read_csv(BASE_DIR / "Resultados.csv")

    for df in [orders, order_details, resultados]:
        df.columns = df.columns.str.strip()

    resultados["nombre_sku_solicitado"] = resultados["nombre_sku_solicitado"].apply(_clean_name)
    resultados["nombre_sku_solicitado_cambio"] = resultados["nombre_sku_solicitado_cambio"].apply(_clean_name)

    return orders, order_details, resultados


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
    prods = (
        resultados["nombre_sku_solicitado"]
        .value_counts()
        .head(top_n)
        .reset_index()
    )
    prods.columns = ["producto", "frecuencia"]
    total = prods["frecuencia"].sum()
    prods["pct_total"] = (prods["frecuencia"] / max(total, 1) * 100).round(1)
    prods["producto"] = prods["producto"].str[:40]
    return prods.to_dict("records")


def get_most_used_substitutes(resultados, top_n=10):
    """Products most frequently used as replacements."""
    subs = (
        resultados["nombre_sku_solicitado_cambio"]
        .value_counts()
        .head(top_n)
        .reset_index()
    )
    subs.columns = ["producto_sustituto", "frecuencia"]
    total = subs["frecuencia"].sum()
    subs["pct_total"] = (subs["frecuencia"] / max(total, 1) * 100).round(1)
    # Count how many unique products each substitute replaces
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
    merged = resultados.merge(orders[["id_pedido", "customer_id"]], on="id_pedido", how="left")

    subs_per_customer = merged.groupby("customer_id").size().reset_index(name="sustituciones")
    orders_per_customer = orders.groupby("customer_id").size().reset_index(name="total_pedidos")
    value_per_customer = orders.groupby("customer_id")["Total"].sum().reset_index(name="valor_total")

    risk = (
        subs_per_customer
        .merge(orders_per_customer, on="customer_id", how="left")
        .merge(value_per_customer, on="customer_id", how="left")
    )

    risk["tasa_sustitucion"] = (risk["sustituciones"] / risk["total_pedidos"] * 100).round(1)
    risk["riesgo_score"] = (
        risk["tasa_sustitucion"] * 0.55
        + (risk["sustituciones"].clip(0, 6) / 6 * 45)
    ).clip(0, 100).round(1)

    risk["nivel_riesgo"] = risk["riesgo_score"].apply(
        lambda x: "Crítico" if x >= 70 else ("Alto" if x >= 40 else "Medio")
    )

    risk = risk.sort_values("riesgo_score", ascending=False).head(top_n)
    risk["customer_id"] = risk["customer_id"].apply(lambda x: f"{float(x):.2e}" if pd.notna(x) else "N/A")
    risk["valor_total"] = risk["valor_total"].round(2).fillna(0)

    return risk.to_dict("records")


def get_substitutions_by_businessunit(orders, resultados):
    merged = resultados.merge(orders[["id_pedido", "id_businessunit", "business_unit"]], on="id_pedido", how="left")
    bu = (
        merged.groupby(["business_unit"])
        .size()
        .reset_index(name="total")
        .sort_values("total", ascending=False)
    )
    bu["business_unit"] = bu["business_unit"].fillna("Desconocido").astype(str).str.strip()
    return bu.to_dict("records")


def get_dashboard_data():
    orders, order_details, resultados = load_data()

    return {
        "summary": get_summary(orders, resultados),
        "top_sustituciones": get_top_substitutions(resultados),
        "productos_mas_sustituidos": get_most_substituted_products(resultados),
        "productos_sustitutos": get_most_used_substitutes(resultados),
        "cedis_criticos": get_cedis_stats(orders, resultados),
        "clientes_riesgo": get_customer_risk(orders, resultados),
        "por_business_unit": get_substitutions_by_businessunit(orders, resultados),
    }
