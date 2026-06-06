import json
import os
from google import genai
from google.genai import types

# 1. Configuración del Cliente
API_KEY = os.environ["GEMINI_API_KEY"]
client = genai.Client(api_key=API_KEY)

# 2. DATOS SIMULADOS (MOCK) - Esto es lo que te entregará tu compañero de Datos
# Diseñado en base a las columnas de Arca Continental (CEDIS, Clientes, SKUs)
datos_logistica_mock = {
    "fecha_reporte": "2026-06-06",
    "cedis_afectado": "3012 (México)",
    "periodo": "Semanal (Últimos 7 días)",
    "productos_alta_demanda_temporada": [
        {"sku": "COCA-600", "nombre": "Coca-Cola Original 600ml", "incremento_demanda": "+35%", "motivo": "Ola de calor regional"},
        {"sku": "JOY-PNC", "nombre": "Joya Ponche 600ml", "incremento_demanda": "+20%", "motivo": "Fin de semana largo"}
    ],
    "top_sustituciones_frecuentes": [
        {"sku_solicitado": "JOY-PNC", "nombre_solicitado": "Joya Ponche 600ml", "sku_sustituto": "JOY-DRZ", "nombre_sustituto": "Joya Durazno 600ml", "frecuencia_semanal": 142},
        {"sku_solicitado": "TONI-FRU", "nombre_solicitado": "Leche Saborizada Toni Frutilla 200ml", "sku_sustituto": "TONI-CHO", "nombre_sustituto": "Leche Saborizada Toni Chocolate 200ml", "frecuencia_semanal": 89}
    ],
    "clientes_riesgo_abandono_alto": [
        {
            "customer_id": "8.42921E+18", 
            "nombre_tienda": "Abarrotes La Bendición", 
            "sustituciones_recientes": 4, 
            "caida_volumen_compra": "-25%",
            "satisfaccion_score": "Crítico (2/10)"
        },
        {
            "customer_id": "3.03732E+18", 
            "nombre_tienda": "MiniSuper Don Chuy", 
            "sustituciones_recientes": 3, 
            "caida_volumen_compra": "-18%",
            "satisfaccion_score": "Bajo (4/10)"
        }
    ]
}

# 3. Instrucciones del Sistema para Gemini
# Le enseñamos a Gemini a estructurar el reporte con etiquetas HTML limpias para que el Rol 3 (Frontend) lo pinte directo en pantalla
configuracion_reporte = types.GenerateContentConfig(
    system_instruction="""
    Eres un Analista de Estrategia Operativa de Arca Continental experto en retención de clientes.
    Tu tarea es transformar datos JSON crudos de logística en un Reporte Ejecutivo de Alertas y Predicciones altamente humano y empático.
    
    Reglas de formato estrictas para tu respuesta:
    1. Usa encabezados HTML claros (<h2>, <h3>) para separar las secciones.
    2. Usa listas (<ul>, <li>) o tablas HTML (<table>, <tr>, <td>) simples para los datos.
    3. No uses lenguaje robótico. Concéntrate en la perspectiva humana: el impacto en el tendero y sugerencias comerciales concretas.
    4. Incluye SIEMPRE recomendaciones de compensación (ej. bonos de puntos, llamadas de disculpa) para los clientes en riesgo crítico de abandono.
    """,
    temperature=0.3 # Temperatura baja para que sea preciso con los datos y no invente números
)

# 4. Función Principal para Generar el Reporte
def generar_reporte_ejecutivo(datos):
    # Convertimos el diccionario de Python a un texto JSON limpio para que Gemini lo entienda perfectamente
    datos_json_texto = json.dumps(datos, indent=2, ensure_ascii=False)
    
    prompt = f"""
    Genera el reporte ejecutivo semanal basándote exclusivamente en estos datos actuales del almacén:
    {datos_json_texto}
    
    Por favor, estructura el reporte con las siguientes 3 secciones obligatorias:
    1. Resumen de Temporada (Productos que vuelan y por qué).
    2. Diagnóstico de Sustituciones Frecuentes en Bodega.
    3. Plan de Rescate para Clientes en Alerta de Abandono Crítico (Sugerencias muy empáticas de qué hacer con ellos para no perderlos).
    """
    
    print("🤖 Generando reporte con Gemini API...")
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=configuracion_reporte
    )
    
    return response.text

# 5. Ejecución de prueba
if __name__ == "__main__":
    reporte_final_html = generar_reporte_ejecutivo(datos_logistica_mock)
    
    print("\n================ RESULTADO DEL REPORTE (HTML PARA EL FRONTEND) ================\n")
    print(reporte_final_html)
    
    # OPCIONAL: Guardamos el resultado en un archivo .html de prueba para que lo veas en el navegador
    with open("reporte_visual.html", "w", encoding="utf-8") as f:
        f.write(reporte_final_html)
    print("\n✓ ¡Archivo 'reporte_visual.html' creado! Ábrelo para ver cómo quedó la estructura.")