import json
import os
from google import genai
from google.genai import types

# 1. Configuración del Cliente de Google
API_KEY = os.environ["GEMINI_API_KEY"]
client = genai.Client(api_key=API_KEY)

# 2. Base de Datos Local (La misma información que compartes con tu equipo)
datos_cedis_actuales = {
    "cedis": "3012 (México)",
    "periodo": "Semanal - Junio 2026",
    "productos_alta_demanda": [
        {"nombre": "Coca-Cola Original 600ml", "riesgo_desabasto": "Alto (+35% demanda por calor)"},
        {"nombre": "Joya Ponche 600ml", "riesgo_desabasto": "Medio (+20% demanda)"}
    ],
    "clientes_criticos_riesgo": [
        {"id": "8.42921E+18", "tienda": "Abarrotes La Bendición", "quejas_sustitucion": 4, "riesgo_abandono": "90%"},
        {"id": "3.03732E+18", "tienda": "MiniSuper Don Chuy", "quejas_sustitucion": 3, "riesgo_abandono": "75%"}
    ]
}

# 3. Instrucciones de Personalidad para el Chatbot
instrucciones_chatbot = f"""
Eres 'ArcaBot', la inteligencia de soporte en tiempo real para supervisores de Arca Continental en el almacén.
Tienes acceso directo a los siguientes datos operativos en tiempo real del CEDIS:
{json.dumps(datos_cedis_actuales, indent=2, ensure_ascii=False)}

Tu misión:
1. Responder las dudas del trabajador con un tono muy humano, empático y profesional.
2. Si te pide el "reporte", genera una estructura clara en texto o formato HTML (usando <h2>, <ul>, etc.) resumiendo los datos.
3. Si pregunta por un cliente específico o qué hacer con las quejas, dale sugerencias comerciales empáticas como bonos de puntos o llamadas inmediatas de servicio.
4. Mantén las respuestas accionables y al grano. El trabajador está operando un almacén real.
"""

# 4. Inicializar el modo CHAT (Guarda el historial de la conversación automáticamente)
print("🤖 Inicializando ArcaBot para Almacenes...")
chat = client.chats.create(
    model="gemini-2.5-flash",
    config=types.GenerateContentConfig(
        system_instruction=instrucciones_chatbot,
        temperature=0.4
    )
)

# 5. Bucle de ejecución para simular la interfaz de chat en vivo
print("\n======================================================================")
print("¡Bienvenido al canal de ArcaBot! (Escribe 'salir' para terminar el chat)")
print("======================================================================\n")

while True:
    # Captura la entrada del usuario en la consola
    mensaje_usuario = input("👤 Supervisor: ")
    
    # Condición de salida
    if mensaje_usuario.lower() in ['salir', 'exit', 'quit']:
        print("🤖 ArcaBot: Entendido. ¡Que tengas un excelente turno en el almacén!")
        break
    
    if not mensaje_usuario.strip():
        continue
        
    # El método chat.send_message envía el texto y mantiene el historial vivo internamente
    response = chat.send_message(mensaje_usuario)
    
    print(f"\n🤖 ArcaBot:\n{response.text}\n")
    print("-" * 70)