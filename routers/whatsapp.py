"""
Router de WhatsApp.
Endpoint principal que recibe mensajes de WhatsApp via Twilio
y orquesta la respuesta del agente.
"""

from fastapi import APIRouter, Request, Response
from tools.whatsapp_handler import parse_incoming_webhook, send_whatsapp_message
from tools.crm import get_or_create_lead
from tools.conversation_manager import (
    add_message,
    get_or_create_conversation,
    get_context_messages,
    get_full_conversation_text,
)
from tools.ai_engine import generate_response, extract_lead_info
from tools.lead_qualifier import qualify_lead, build_qualification_context
from tools.property_manager import (
    find_matching_properties,
    format_properties_list,
    build_property_context,
    calculate_mortgage,
    format_mortgage_for_chat,
)
from models.database_models import ChannelType


router = APIRouter()


@router.post("/webhook")
async def whatsapp_webhook(request: Request):
    """
    Webhook principal de WhatsApp (Twilio).
    
    Flujo completo:
    1. Parsear mensaje entrante
    2. Identificar o crear lead
    3. Guardar mensaje en historial
    4. Buscar propiedades relevantes (contexto)
    5. Generar respuesta con IA
    6. Cualificar lead
    7. Guardar respuesta y enviar
    """
    # 1. Parsear el mensaje entrante
    form_data = await request.form()
    incoming = parse_incoming_webhook(dict(form_data))
    
    user_message = incoming["body"]
    phone = incoming["phone"]
    profile_name = incoming["profile_name"]
    
    if not user_message:
        return Response(content="", media_type="text/xml")
    
    print(f"📥 WhatsApp de {profile_name} ({phone}): {user_message}")
    
    # 2. Identificar o crear lead
    lead = await get_or_create_lead(
        phone=phone,
        channel=ChannelType.WHATSAPP,
        name=profile_name or None,
    )
    
    # 3. Guardar mensaje del usuario en historial
    await add_message(
        lead_id=lead.id,
        role="user",
        content=user_message,
        channel=ChannelType.WHATSAPP,
    )
    
    # 4. Preparar contexto (propiedades relevantes)
    additional_context = ""
    
    # Si ya tenemos preferencias, buscar propiedades matching
    if lead.preferences.zone or lead.preferences.max_budget or lead.preferences.property_type:
        matching_props = await find_matching_properties(lead, limit=5)
        if matching_props:
            additional_context = build_property_context(matching_props)
    
    # Añadir info del lead al contexto
    additional_context += f"\n\n## Info del Cliente Actual\n"
    additional_context += f"- Nombre: {lead.name or 'No proporcionado'}\n"
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
    
    # Inyectar estado de cualificación (datos que faltan + prioridad)
    additional_context += build_qualification_context(lead)
    
    # 5. Obtener historial y generar respuesta
    conversation = await get_or_create_conversation(lead.id, ChannelType.WHATSAPP)
    context_messages = get_context_messages(conversation)
    
    # Quitar el último mensaje (ya lo pasamos como user_message)
    if context_messages and context_messages[-1]["role"] == "user":
        context_messages = context_messages[:-1]
    
    agent_response = await generate_response(
        user_message=user_message,
        conversation_history=context_messages,
        additional_context=additional_context,
        lead_context={
            "name": lead.name or "",
            "phone": phone,
            "email": lead.email or "",
            "score": lead.score,
            "channel": "whatsapp",
        },
    )
    
    # 6. Guardar respuesta del agente
    await add_message(
        lead_id=lead.id,
        role="assistant",
        content=agent_response,
        channel=ChannelType.WHATSAPP,
    )
    
    # 7. Cualificar lead (cada 3 interacciones para no sobrecargar)
    if lead.total_interactions % 3 == 0 or lead.total_interactions <= 2:
        await qualify_lead(lead, ChannelType.WHATSAPP)
    
    # 8. Enviar respuesta por WhatsApp
    await send_whatsapp_message(
        to=incoming["from"],
        body=agent_response,
    )
    
    print(f"📤 Respuesta a {phone}: {agent_response[:80]}...")
    
    # Twilio espera una respuesta TwiML vacía
    return Response(
        content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
        media_type="text/xml",
    )


@router.get("/webhook")
async def whatsapp_webhook_verify(request: Request):
    """
    Verificación del webhook (Twilio no lo necesita normalmente,
    pero lo dejamos por compatibilidad).
    """
    return {"status": "WhatsApp webhook active"}
