import pandas as pd
import numpy as np
import os

# 1. CARGAR LOS DATOS
print("Cargando archivos CSV...")
order_details = pd.read_csv('OrderDetails.csv')
orders = pd.read_csv('Orders.csv')
results = pd.read_csv('Resultados.csv')

# 2. ESTANDARIZAR NOMBRES DE COLUMNAS
print("Estandarizando columnas...")
for df in [order_details, orders, results]:
    df.columns = df.columns.str.lower().str.strip()

# 3. LIMPIEZA DE TEXTOS Y ESPACIOS
print("Limpiando espacios en textos...")
columnas_texto_od = ['nombre_sku_solicitado', 'status']
for col in columnas_texto_od:
    if col in order_details.columns:
        order_details[col] = order_details[col].astype(str).str.strip()

columnas_texto_res = ['nombre_sku_solicitado', 'nombre_sku_solicitado_cambio']
for col in columnas_texto_res:
    if col in results.columns:
        results[col] = results[col].astype(str).str.strip()

# 4. CORRECCIÓN DE FALSOS NULOS
print("Corrigiendo valores nulos...")
orders = orders.replace('NULL', np.nan)
orders = orders.replace('IA  ', np.nan) 

order_details = order_details.dropna(subset=['id_pedido']).drop_duplicates()
orders = orders.dropna(subset=['id_pedido']).drop_duplicates()
results = results.dropna(subset=['id_pedido', 'id_linea']).drop_duplicates()

# 5. UNIR LAS TABLAS (MERGE)
print("Uniendo las tablas...")
# Primer cruce
df_completo = pd.merge(orders, order_details, on='id_pedido', how='inner')

columnas_comunes = ['id_pedido', 'id_linea'] 
df_final = pd.merge(df_completo, results, on=columnas_comunes, how='left')

# 6. ORDENAR LOS DATOS
print("Ordenando los datos...")
df_final = df_final.sort_values(by=['id_pedido', 'id_linea'], ascending=[True, True])
print(f"¡Éxito! Total de filas listas para analizar: {df_final.shape[0]}")

# 7. DIVIDIR EN 8 PARTES Y GUARDAR
print("Dividiendo archivo en 8 partes...")
numero_de_partes = 8

# Aseguramos que la carpeta backend exista
os.makedirs('backend', exist_ok=True)

# Calculamos cuántas filas debe tener cada pedazo matemáticamente
tamaño_pedazo = len(df_final) // numero_de_partes + 1

for i in range(numero_de_partes):
    # Cortamos el DataFrame original usando .iloc (rebanado nativo de pandas)
    inicio = i * tamaño_pedazo
    fin = inicio + tamaño_pedazo
    pedazo = df_final.iloc[inicio:fin]
    
    # Genera nombres: Datos_Limpios_ChocoRoles_parte_1.csv hasta la 8
    nombre_archivo = f'backend/Datos_Limpios_ChocoRoles_parte_{i+1}.csv'
    
    # Guardamos el pedazo (solo si no se nos fue en blanco en la última vuelta)
    if not pedazo.empty:
        pedazo.to_csv(nombre_archivo, index=False)
        print(f"✔️ Guardado {nombre_archivo} con {len(pedazo)} filas.")

print("¡Proceso terminado con éxito!")