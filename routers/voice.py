"""
Router de Voz (Vapi.ai).
Webhook que recibe eventos de llamadas: inicio, fin, transcripciones y function calls.
"""

from fastapi import APIRouter, Request
from tools.voice_handler import parse_vapi_webhook
from tools.crm import get_or_create_lead
from tools.conversation_manager import add_message
from tools.lead_qualifier import qualify_lead
from models.database_models import ChannelType


router = APIRouter()


@router.post("/webhook")
async def voice_webhook(request: Request):
    """
    Webhook de Vapi.ai.
    Recibe eventos de llamadas y procesa transcripciones.
    
    Eventos principales:
    - end-of-call-report: Llamada terminada, incluye transcripción completa
    - function-call: El asistente quiere ejecutar una acción
    - status-update: Actualización de estado de la llamada
    """
    payload = await request.json()
    event = parse_vapi_webhook(payload)
    
    event_type = event["event_type"]
    print(f"📞 Evento Vapi: {event_type}")
    
    # ── Llamada terminada → guardar transcripción y cualificar ──
    if event_type == "end-of-call-report":
        phone = event.get("phone_number", "")
        transcript = event.get("transcript", "")
        summary = event.get("summary", "")
        duration = event.get("duration_seconds", 0)
        
        if phone and transcript:
            # Crear/encontrar lead
            lead = await get_or_create_lead(
                phone=phone,
                channel=ChannelType.TELEFONO,
            )
            
            # Guardar la conversación completa como un mensaje
            call_content = (
                f"[LLAMADA TELEFÓNICA — Duración: {duration // 60}m {duration % 60}s]\n\n"
                f"Transcripción:\n{transcript}\n\n"
                f"Resumen: {summary}"
            )
            
            await add_message(
                lead_id=lead.id,
                role="user",
                content=call_content,
                channel=ChannelType.TELEFONO,
            )
            
            # Cualificar lead basado en la llamada
            await qualify_lead(lead, ChannelType.TELEFONO)
            
            print(f"📝 Llamada con {phone} guardada ({duration}s)")
        
        return {"status": "ok", "action": "call_recorded"}
    
    # ── Function call → ejecutar acción ──
    elif event_type == "function-call":
        func = event.get("function_call", {})
        func_name = func.get("name", "")
        func_params = func.get("parameters", {})
        
        print(f"🔧 Function call: {func_name}({func_params})")
        
        # Aquí se pueden manejar function calls del asistente
        # Ej: agendar visita, buscar propiedad, etc.
        result = await _handle_function_call(func_name, func_params)
        
        return {"result": result}
    
    # ── Status update → log ──
    elif event_type == "status-update":
        status = event.get("status", "")
        print(f"📞 Estado de llamada: {status}")
        return {"status": "ok"}
    
    return {"status": "ignored"}


async def _handle_function_call(name: str, params: dict) -> str:
    """
    Maneja function calls del asistente de voz.
    El asistente puede pedir ejecutar acciones durante la llamada.
    """
    if name == "schedule_visit":
        # Importar aquí para evitar imports circulares
        from tools.scheduler import schedule_visit
        result = await schedule_visit(**params)
        return f"Visita agendada correctamente" if "id" in result else f"Error al agendar"
    
    elif name == "search_properties":
        from tools.property_manager import search_properties_by_criteria
        # Buscar propiedades matching
        return "Búsqueda realizada"
    
    elif name == "transfer_to_human":
        return "Transferencia a agente humano solicitada"
    
    return f"Función {name} no reconocida"


@router.get("/status")
async def voice_status():
    """Estado del servicio de voz."""
    return {"status": "active", "provider": "vapi.ai"}
