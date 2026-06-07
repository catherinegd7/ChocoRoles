import glob
import pandas as pd
import numpy as np
from pymongo import MongoClient
import certifi 

print("1. Cargando base de datos completa...")
archivos_csv = sorted(glob.glob('backend/Datos_Limpios_ChocoRoles_parte_*.csv'))
df_completo = pd.concat((pd.read_csv(archivo) for archivo in archivos_csv), ignore_index=True)

df_completo.columns = df_completo.columns.str.strip()

df_completo = df_completo.rename(columns={'nombre_sku_solicitado_x': 'nombre_sku_solicitado'})

df_completo['fue_sustituido'] = df_completo['nombre_sku_solicitado_cambio'].notna()


print("Calculando vulnerabilidad de productos...")

prod_stats = df_completo.groupby('nombre_sku_solicitado').agg(
    total_pedidos=('id_pedido', 'count'),
    veces_sustituido=('fue_sustituido', 'sum')
).reset_index()

prod_stats['probabilidad_sustitucion_%'] = (prod_stats['veces_sustituido'] / prod_stats['total_pedidos']) * 100

productos_riesgo = prod_stats[prod_stats['probabilidad_sustitucion_%'] > 5].sort_values(
    by='probabilidad_sustitucion_%', ascending=False)


print("Definiendo diccionario automático de parejas de sustitutos...")

df_sustitutos = df_completo.dropna(subset=['nombre_sku_solicitado_cambio']).copy()
df_sustitutos = df_sustitutos[df_sustitutos['nombre_sku_solicitado'] != df_sustitutos['nombre_sku_solicitado_cambio']]

parejas = df_sustitutos.groupby(['nombre_sku_solicitado', 'nombre_sku_solicitado_cambio']).size().reset_index(name='veces_sustituido')
parejas = parejas.sort_values(by='veces_sustituido', ascending=False)

sustitutos_automaticos = parejas.drop_duplicates(subset=['nombre_sku_solicitado'], keep='first')


print("Calculando score de riesgo de abandono de clientes...")

clientes_stats = df_completo.groupby('customer_id').agg(
    total_compras=('id_pedido', 'nunique'),
    productos_sustituidos=('fue_sustituido', 'sum')
).reset_index()

clientes_stats['porcentaje_afectacion'] = (clientes_stats['productos_sustituidos'] / (clientes_stats['total_compras'])) * 100
clientes_stats['score_riesgo'] = np.clip(clientes_stats['porcentaje_afectacion'], 0, 100)

def etiquetar_riesgo(score):
    if score >= 70:
        return "Alto Riesgo (¡Dar Puntos Urgente!)"
    elif score >= 40:
        return "Riesgo Medio (Monitorear)"
    else:
        return "Cliente Satisfecho"

clientes_stats['estado_satisfaccion'] = clientes_stats['score_riesgo'].apply(etiquetar_riesgo)


print("Estructurando diccionarios para MongoDB...")

coleccion_productos = productos_riesgo.to_dict(orient='records')
coleccion_clientes = clientes_stats.to_dict(orient='records')
coleccion_sustitutos = sustitutos_automaticos.to_dict(orient='records')

if 'fecha' in df_completo.columns:
    df_completo['fecha'] = df_completo['fecha'].astype(str)

print(f"-> Listos para subir {len(coleccion_productos)} productos vulnerables.")
print(f"-> Listos para subir {len(coleccion_clientes)} perfiles de clientes.")
print(f"-> Listos para subir {len(coleccion_sustitutos)} parejas de sustitutos.")


#
print("Conectando a MongoDB Atlas...")

MONGO_URI = "mongodb+srv://agustovalentin07_db_user:elbichosiu@basededatossi.7woegj5.mongodb.net/?appName=BaseDeDatosSi"

try:
    cliente_mongo = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
    db = cliente_mongo['HackathonArca']
    
    col_productos = db['productos_vulnerables']
    col_clientes = db['clientes_riesgo']
    col_sustitutos = db['diccionario_sustitutos']
    col_historial = db['historial_pedidos'] 
    
    print("Limpiando registros antiguos en la nube...")
    col_productos.delete_many({})
    col_clientes.delete_many({})
    col_sustitutos.delete_many({})
    col_historial.delete_many({})
    
    
    print("Subiendo capas de inteligencia...")
    if len(coleccion_productos) > 0: col_productos.insert_many(coleccion_productos)
    if len(coleccion_clientes) > 0: col_clientes.insert_many(coleccion_clientes)
    if len(coleccion_sustitutos) > 0: col_sustitutos.insert_many(coleccion_sustitutos)
        
    #
    print("Iniciando subida de una muestra representativa del historial...")
    
    df_muestra_historial = df_completo.tail(1000000) 
    
    tam_bloque = 25000
    total_filas_muestra = len(df_muestra_historial)
    
    for inicio in range(0, total_filas_muestra, tam_bloque):
        fin = inicio + tam_bloque
        bloque_dict = df_muestra_historial.iloc[inicio:fin].to_dict(orient='records')
        col_historial.insert_many(bloque_dict)
        print(f"📦 Progreso: Enviado bloque {inicio} a {min(fin, total_filas_muestra)} de la muestra...")
        
    print(" ¡SISTEMA INYECTADO! Base de datos ligera y lista para Gemini.")

except Exception as e:
    print(f" Error al conectar o transferir a MongoDB: {e}")