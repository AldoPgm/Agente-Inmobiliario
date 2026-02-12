"""
Router de Instagram DM.
Webhook que recibe mensajes de Instagram y orquesta la respuesta del agente.

Setup: Configurar webhook en Meta Developer Portal apuntando a /api/instagram/webhook
"""

from fastapi import APIRouter, Request, Response
from config import META_VERIFY_TOKEN
from tools.instagram_handler import (
    parse_instagram_webhook,
    send_instagram_message,
    get_instagram_user_profile,
)
from tools.crm import get_or_create_lead
from tools.conversation_manager import (
    add_message,
    get_or_create_conversation,
    get_context_messages,
)
from tools.ai_engine import generate_response
from tools.lead_qualifier import qualify_lead, build_qualification_context
from tools.property_manager import find_matching_properties, build_property_context
from models.database_models import ChannelType


router = APIRouter()


@router.get("/webhook")
async def instagram_verify(request: Request):
    """
    Verificación del webhook de Meta.
    Meta envía un GET con hub.challenge que debemos devolver.
    """
    params = request.query_params
    mode = params.get("hub.mode", "")
    token = params.get("hub.verify_token", "")
    challenge = params.get("hub.challenge", "")
    
    if mode == "subscribe" and token == META_VERIFY_TOKEN:
        print("✅ Webhook de Instagram verificado")
        return Response(content=challenge, media_type="text/plain")
    
    return Response(content="Forbidden", status_code=403)


@router.post("/webhook")
async def instagram_webhook(request: Request):
    """
    Webhook principal de Instagram DM.
    
    Flujo (mismo patrón que WhatsApp):
    1. Parsear mensajes entrantes
    2. Para cada mensaje: identificar lead → contexto → IA → cualificar → responder
    """
    payload = await request.json()
    
    # Verificar que es un evento de messaging
    obj = payload.get("object", "")
    if obj != "instagram":
        return {"status": "ignored"}
    
    # Parsear mensajes
    incoming_messages = parse_instagram_webhook(payload)
    
    for msg in incoming_messages:
        sender_id = msg["sender_id"]
        user_message = msg["message_text"]
        
        if not user_message:
            continue
        
        print(f"📸 Instagram DM de {sender_id}: {user_message}")
        
        # Obtener perfil del usuario
        profile = await get_instagram_user_profile(sender_id)
        
        # Identificar o crear lead (Instagram usa IGSID en vez de teléfono)
        lead = await get_or_create_lead(
            phone=f"ig:{sender_id}",  # Prefijo para diferenciar de teléfonos
            channel=ChannelType.INSTAGRAM,
            name=profile.get("name") or None,
        )
        
        # Guardar mensaje del usuario
        await add_message(
            lead_id=lead.id,
            role="user",
            content=user_message,
            channel=ChannelType.INSTAGRAM,
        )
        
        # Preparar contexto
        additional_context = ""
        
        if lead.preferences.zone or lead.preferences.max_budget or lead.preferences.property_type:
            matching_props = await find_matching_properties(lead, limit=5)
            if matching_props:
                additional_context = build_property_context(matching_props)
        
        additional_context += f"\n\n## Info del Cliente Actual\n"
        additional_context += f"- Nombre: {lead.name or 'No proporcionado'}\n"
        additional_context += f"- Canal: Instagram DM\n"
        additional_context += f"- Score: {lead.score}/100 ({lead.score_label.value})\n"
        additional_context += f"- Interacciones: {lead.total_interactions}\n"
        
        if lead.preferences.operation:
            additional_context += f"- Busca: {lead.preferences.operation}\n"
        if lead.preferences.property_type:
            additional_context += f"- Tipo: {lead.preferences.property_type}\n"
        if lead.preferences.zone:
            additional_context += f"- Zona: {lead.preferences.zone}\n"
        if lead.preferences.max_budget:
            additional_context += f"- Presupuesto max: {lead.preferences.max_budget}€\n"
        
        # Inyectar estado de cualificación
        additional_context += build_qualification_context(lead)
        
        # Obtener historial y generar respuesta
        conversation = await get_or_create_conversation(lead.id, ChannelType.INSTAGRAM)
        context_messages = get_context_messages(conversation)
        
        if context_messages and context_messages[-1]["role"] == "user":
            context_messages = context_messages[:-1]
        
        agent_response = await generate_response(
            user_message=user_message,
            conversation_history=context_messages,
            additional_context=additional_context,
            lead_context={
                "name": lead.name or "",
                "phone": f"ig:{sender_id}",
                "email": lead.email or "",
                "score": lead.score,
                "channel": "instagram",
            },
        )
        
        # Guardar respuesta
        await add_message(
            lead_id=lead.id,
            role="assistant",
            content=agent_response,
            channel=ChannelType.INSTAGRAM,
        )
        
        # Cualificar lead
        if lead.total_interactions % 3 == 0 or lead.total_interactions <= 2:
            await qualify_lead(lead, ChannelType.INSTAGRAM)
        
        # Enviar respuesta por Instagram DM
        # Instagram tiene límite de 1000 chars por mensaje, dividir si es necesario
        if len(agent_response) > 950:
            chunks = _split_message(agent_response, max_len=950)
            for chunk in chunks:
                await send_instagram_message(sender_id, chunk)
        else:
            await send_instagram_message(sender_id, agent_response)
        
        print(f"📤 Respuesta Instagram a {sender_id}: {agent_response[:80]}...")
    
    return {"status": "ok"}


def _split_message(text: str, max_len: int = 950) -> list[str]:
    """Divide un mensaje largo en chunks respetando saltos de línea."""
    if len(text) <= max_len:
        return [text]
    
    chunks = []
    current = ""
    
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > max_len:
            if current:
                chunks.append(current.strip())
            current = line
        else:
            current += "\n" + line if current else line
    
    if current:
        chunks.append(current.strip())
    
    return chunks
