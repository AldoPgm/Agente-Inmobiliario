"""
Test local del Agente IA Inmobiliario.
Permite conversar con el agente desde la terminal sin necesidad de Twilio ni WhatsApp.

Uso:
    python tools/test_local.py

Requiere:
    - GEMINI_API_KEY (o OPENAI_API_KEY) configurada en .env
    - SUPABASE_URL y SUPABASE_KEY en .env (opcional, funciona sin DB)
"""

import asyncio
import sys
import os

# Añadir el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import AGENT_NAME, COMPANY_NAME, LLM_PROVIDER
from tools.ai_engine import generate_response


# ─────────────────────────────────────────────
# Modo Simple (sin base de datos)
# Solo conversa con el LLM usando el system prompt
# ─────────────────────────────────────────────

# Historial de la conversación local
conversation_history: list[dict] = []


async def chat(user_message: str) -> str:
    """Envía un mensaje al agente y devuelve la respuesta."""
    
    # Añadir mensaje del usuario al historial
    conversation_history.append({"role": "user", "content": user_message})
    
    # Generar respuesta (pasa el historial sin el último mensaje)
    response = await generate_response(
        user_message=user_message,
        conversation_history=conversation_history[:-1],
        additional_context=SAMPLE_PROPERTIES_CONTEXT,
    )
    
    # Guardar respuesta del agente
    conversation_history.append({"role": "assistant", "content": response})
    
    return response


# Contexto de ejemplo con propiedades (para test sin DB)
SAMPLE_PROPERTIES_CONTEXT = """
## Propiedades Disponibles

- **Piso luminoso en el centro** (Ref: REF-001)
  Tipo: piso | Operación: venta
  Precio: 185,000€ | 85 m²
  Zona: Centro | Dirección: Calle Mayor 15, 3ºB, Madrid
  Habitaciones: 3 | Baños: 1
  Comunidad: 120€/mes | IBI: 650€/año
  Extras: Ascensor, A/C, Calefacción
  Descripción: Precioso piso reformado con mucha luz natural. Cocina americana equipada, suelos de parquet.

- **Ático con terraza panorámica** (Ref: REF-002)
  Tipo: ático | Operación: venta
  Precio: 320,000€ | 110 m²
  Zona: Salamanca | Dirección: Paseo de las Acacias 8, Madrid
  Habitaciones: 2 | Baños: 2
  Comunidad: 200€/mes | IBI: 1,100€/año
  Extras: Terraza 40m², Parking, Ascensor, A/C
  Descripción: Espectacular ático con terraza de 40m² y vistas despejadas. Acabados de alta calidad.

- **Estudio moderno junto al metro** (Ref: REF-003)
  Tipo: estudio | Operación: venta
  Precio: 95,000€ | 38 m²
  Zona: Lavapiés | Dirección: Calle Embajadores 22, 1ºA, Madrid
  Habitaciones: 0 | Baños: 1
  Comunidad: 45€/mes | IBI: 280€/año
  Descripción: Estudio completamente reformado, ideal para inversión o primera vivienda.

- **Casa con jardín en urbanización** (Ref: REF-004)
  Tipo: casa | Operación: venta
  Precio: 410,000€ | 180 m²
  Zona: Las Rozas | Dirección: Urbanización Los Pinos 14, Las Rozas
  Habitaciones: 4 | Baños: 3
  Comunidad: 180€/mes | IBI: 900€/año
  Extras: Parking, Jardín, Piscina comunitaria, Trastero
  Descripción: Magnífica casa adosada en urbanización privada. Garaje para 2 coches, chimenea.

- **Piso en alquiler zona universitaria** (Ref: REF-005)
  Tipo: piso | Operación: alquiler
  Precio: 950€/mes | 75 m²
  Zona: Moncloa | Dirección: Avenida Complutense 30, 4ºC, Madrid
  Habitaciones: 3 | Baños: 1
  Comunidad: 80€/mes (incluida) | IBI: 400€/año (incluido)
  Descripción: Piso amueblado y equipado, listo para entrar. Ideal para estudiantes o jóvenes profesionales.
"""


async def main():
    """Loop principal del test local."""
    
    print("=" * 60)
    print(f"  🏠 Test Local — Agente {AGENT_NAME} de {COMPANY_NAME}")
    print(f"  🤖 Motor IA: {LLM_PROVIDER.upper()}")
    print(f"  📝 Escribe 'salir' para terminar")
    print(f"  📝 Escribe 'reset' para reiniciar conversación")
    print("=" * 60)
    print()
    
    # Verificar que haya API key
    if LLM_PROVIDER == "gemini":
        from config import GEMINI_API_KEY
        if not GEMINI_API_KEY:
            print("❌ GEMINI_API_KEY no configurada en .env")
            print("   Obtén una gratis en: https://aistudio.google.com/apikey")
            return
    elif LLM_PROVIDER == "openai":
        from config import OPENAI_API_KEY
        if not OPENAI_API_KEY:
            print("❌ OPENAI_API_KEY no configurada en .env")
            return
    
    print(f"💬 {AGENT_NAME}: ¡Hola! Soy {AGENT_NAME}, asesora inmobiliaria de {COMPANY_NAME}.")
    print(f"   ¿En qué puedo ayudarte hoy? 🏡")
    print()
    
    while True:
        try:
            user_input = input("👤 Tú: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 ¡Hasta luego!")
            break
        
        if not user_input:
            continue
        
        if user_input.lower() == "salir":
            print("👋 ¡Hasta luego!")
            break
        
        if user_input.lower() == "reset":
            conversation_history.clear()
            print("🔄 Conversación reiniciada\n")
            continue
        
        print(f"\n💬 {AGENT_NAME}: ", end="", flush=True)
        
        try:
            response = await chat(user_input)
            print(response)
        except Exception as e:
            print(f"\n❌ Error: {e}")
        
        print()


if __name__ == "__main__":
    asyncio.run(main())
