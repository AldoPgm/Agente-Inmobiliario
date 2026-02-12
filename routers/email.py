"""
Router de Email.
Webhook que recibe emails entrantes (SendGrid Inbound Parse)
y orquesta la respuesta del agente.

Setup: Configurar SendGrid Inbound Parse apuntando a /api/email/webhook
"""

from fastapi import APIRouter, Request
from tools.email_handler import parse_inbound_email, send_email
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


@router.post("/webhook")
async def email_webhook(request: Request):
    """
    Webhook de SendGrid Inbound Parse.
    Recibe emails entrantes y genera respuesta automática.
    
    Flujo (mismo patrón que WhatsApp/Instagram):
    1. Parsear email entrante
    2. Identificar o crear lead por email
    3. Guardar mensaje → contexto → IA → cualificar → responder
    """
    form_data = await request.form()
    incoming = parse_inbound_email(dict(form_data))
    
    from_email = incoming["from_email"]
    from_name = incoming["from_name"]
    subject = incoming["subject"]
    body = incoming["body"]
    
    if not body or not from_email:
        return {"status": "ignored", "reason": "empty body or sender"}
    
    print(f"📧 Email de {from_name} <{from_email}>: {subject}")
    
    # Identificar o crear lead
    lead = await get_or_create_lead(
        phone=from_email,  # Usamos email como identificador
        channel=ChannelType.EMAIL,
        name=from_name or None,
    )
    
    # Si el lead no tiene email guardado, actualizarlo
    if not lead.email:
        lead.email = from_email
    
    # Construir mensaje combinando asunto + cuerpo
    user_message = body
    if subject and not subject.lower().startswith("re:"):
        user_message = f"[Asunto: {subject}]\n{body}"
    
    # Guardar mensaje
    await add_message(
        lead_id=lead.id,
        role="user",
        content=user_message,
        channel=ChannelType.EMAIL,
    )
    
    # Preparar contexto
    additional_context = ""
    
    if lead.preferences.zone or lead.preferences.max_budget or lead.preferences.property_type:
        matching_props = await find_matching_properties(lead, limit=5)
        if matching_props:
            additional_context = build_property_context(matching_props)
    
    additional_context += f"\n\n## Info del Cliente Actual\n"
    additional_context += f"- Nombre: {lead.name or 'No proporcionado'}\n"
    additional_context += f"- Email: {from_email}\n"
    additional_context += f"- Canal: Email\n"
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
    
    # Contexto adicional para email
    additional_context += f"\n## Nota sobre formato\n"
    additional_context += f"- Estás respondiendo un EMAIL, no un chat. Usa un tono un poco más formal.\n"
    additional_context += f"- No uses emojis en exceso en emails.\n"
    additional_context += f"- Estructura bien la respuesta con párrafos.\n"
    
    # Obtener historial y generar respuesta
    conversation = await get_or_create_conversation(lead.id, ChannelType.EMAIL)
    context_messages = get_context_messages(conversation)
    
    if context_messages and context_messages[-1]["role"] == "user":
        context_messages = context_messages[:-1]
    
    agent_response = await generate_response(
        user_message=user_message,
        conversation_history=context_messages,
        additional_context=additional_context,
        lead_context={
            "name": lead.name or "",
            "phone": from_email,
            "email": from_email,
            "score": lead.score,
            "channel": "email",
        },
    )
    
    # Guardar respuesta
    await add_message(
        lead_id=lead.id,
        role="assistant",
        content=agent_response,
        channel=ChannelType.EMAIL,
    )
    
    # Cualificar lead
    if lead.total_interactions % 3 == 0 or lead.total_interactions <= 2:
        await qualify_lead(lead, ChannelType.EMAIL)
    
    # Enviar respuesta por email
    reply_subject = f"Re: {subject}" if subject and not subject.startswith("Re:") else subject
    
    await send_email(
        to_email=from_email,
        subject=reply_subject or f"Respuesta de {lead.name or 'tu asesora'} — Inmobiliaria",
        body_text=agent_response,
    )
    
    print(f"📤 Email respuesta a {from_email}: {agent_response[:80]}...")
    
    return {"status": "ok"}
