"""
Handler de llamadas de voz con Vapi.ai
Integración para llamadas entrantes y salientes con IA conversacional.

Docs: https://docs.vapi.ai
"""

import httpx
from config import VAPI_API_KEY, AGENT_NAME, COMPANY_NAME, SYSTEM_PROMPT


VAPI_API_URL = "https://api.vapi.ai"


# ─────────────────────────────────────────────
# Configuración del asistente de voz
# ─────────────────────────────────────────────
VOICE_SYSTEM_PROMPT = SYSTEM_PROMPT + """

## Instrucciones adicionales para llamadas de voz
- Habla de forma clara y pausada, como en una llamada telefónica real.
- Usa frases cortas. No hagas listas largas por teléfono.
- Si el cliente pregunta por una propiedad, describe máximo 2-3 características clave.
- Para detalles extensos, ofrece enviar la info por WhatsApp o email.
- Si necesitas deletrear algo (dirección, nombre), hazlo claramente.
- Confirma datos importantes repitiéndolos: "Entonces, buscas un piso de 3 habitaciones en el centro, ¿correcto?"
"""

VOICE_ASSISTANT_CONFIG = {
    "name": f"{AGENT_NAME} — {COMPANY_NAME}",
    "model": {
        "provider": "openai",
        "model": "gpt-4o",
        "systemPrompt": VOICE_SYSTEM_PROMPT,
        "temperature": 0.7,
    },
    "voice": {
        "provider": "11labs",
        "voiceId": "EXAVITQu4vr4xnSDxMaL",  # "Sarah" — voz femenina profesional
    },
    "transcriber": {
        "provider": "deepgram",
        "model": "nova-2",
        "language": "es",
    },
    "firstMessage": f"¡Hola! Soy {AGENT_NAME} de {COMPANY_NAME}. ¿En qué puedo ayudarte hoy?",
    "endCallMessage": f"Muchas gracias por tu llamada. Si necesitas algo más, no dudes en contactarnos. ¡Hasta pronto!",
    "silenceTimeoutSeconds": 30,
    "maxDurationSeconds": 600,  # 10 minutos máximo
    "backgroundSound": "office",
}


# ─────────────────────────────────────────────
# Gestión de asistentes
# ─────────────────────────────────────────────
async def create_vapi_assistant() -> dict:
    """
    Crea o actualiza el asistente de voz en Vapi.
    Solo necesita ejecutarse una vez al configurar.
    
    Returns:
        Dict con el ID del asistente creado
    """
    headers = {
        "Authorization": f"Bearer {VAPI_API_KEY}",
        "Content-Type": "application/json",
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{VAPI_API_URL}/assistant",
            json=VOICE_ASSISTANT_CONFIG,
            headers=headers,
        )
        response.raise_for_status()
        result = response.json()
        print(f"✅ Asistente de voz creado: {result.get('id', 'N/A')}")
        return result


async def get_vapi_assistants() -> list[dict]:
    """Lista todos los asistentes configurados en Vapi."""
    headers = {"Authorization": f"Bearer {VAPI_API_KEY}"}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{VAPI_API_URL}/assistant", headers=headers)
        response.raise_for_status()
        return response.json()


# ─────────────────────────────────────────────
# Llamadas salientes
# ─────────────────────────────────────────────
async def make_outbound_call(
    phone_number: str,
    assistant_id: str = None,
    context: str = "",
) -> dict:
    """
    Realiza una llamada saliente con el agente IA.
    
    Args:
        phone_number: Número a llamar (formato E.164: +34612345678)
        assistant_id: ID del asistente Vapi (usa el default si no se especifica)
        context: Contexto adicional para la llamada (info del lead, motivo, etc.)
    
    Returns:
        Dict con el ID de la llamada
    """
    headers = {
        "Authorization": f"Bearer {VAPI_API_KEY}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "phoneNumberId": phone_number,
        "customer": {"number": phone_number},
    }
    
    if assistant_id:
        payload["assistantId"] = assistant_id
    else:
        # Usar config inline si no hay assistant_id
        config = VOICE_ASSISTANT_CONFIG.copy()
        if context:
            config["model"]["systemPrompt"] += f"\n\n## Contexto de esta llamada\n{context}"
        payload["assistant"] = config
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{VAPI_API_URL}/call/phone",
            json=payload,
            headers=headers,
        )
        response.raise_for_status()
        result = response.json()
        print(f"📞 Llamada saliente a {phone_number}: {result.get('id', 'N/A')}")
        return result


# ─────────────────────────────────────────────
# Parsear webhook de Vapi
# ─────────────────────────────────────────────
def parse_vapi_webhook(payload: dict) -> dict:
    """
    Parsea el payload del webhook de Vapi.
    
    Eventos relevantes:
    - call.started: Llamada iniciada
    - call.ended: Llamada terminada (incluye transcripción)
    - call.analysis: Análisis post-llamada
    - function-call: El asistente quiere ejecutar una función
    
    Returns:
        Dict parseado con tipo de evento y datos
    """
    event_type = payload.get("message", {}).get("type", "")
    
    result = {
        "event_type": event_type,
        "call_id": payload.get("message", {}).get("call", {}).get("id", ""),
        "phone_number": "",
        "transcript": "",
        "summary": "",
        "duration_seconds": 0,
        "ended_reason": "",
        "function_call": None,
    }
    
    call_data = payload.get("message", {}).get("call", {})
    
    if event_type == "end-of-call-report":
        result["transcript"] = payload.get("message", {}).get("transcript", "")
        result["summary"] = payload.get("message", {}).get("summary", "")
        result["duration_seconds"] = call_data.get("duration", 0)
        result["ended_reason"] = payload.get("message", {}).get("endedReason", "")
        
        # Extraer número del cliente
        customer = call_data.get("customer", {})
        result["phone_number"] = customer.get("number", "")
    
    elif event_type == "function-call":
        result["function_call"] = {
            "name": payload.get("message", {}).get("functionCall", {}).get("name", ""),
            "parameters": payload.get("message", {}).get("functionCall", {}).get("parameters", {}),
        }
    
    elif event_type == "status-update":
        result["status"] = payload.get("message", {}).get("status", "")
    
    return result


async def get_call_details(call_id: str) -> dict:
    """Obtiene detalles de una llamada por su ID."""
    headers = {"Authorization": f"Bearer {VAPI_API_KEY}"}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{VAPI_API_URL}/call/{call_id}", headers=headers)
        response.raise_for_status()
        return response.json()
