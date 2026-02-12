"""
Router de Portales Inmobiliarios.
Recibe leads de Idealista, Fotocasa, Habitaclia y otros portales.
Soporta tanto webhooks directos como emails reenviados.
"""

from fastapi import APIRouter, Request
from tools.portal_handler import parse_portal_lead, parse_portal_email
from tools.crm import get_or_create_lead
from tools.conversation_manager import add_message, get_or_create_conversation, get_context_messages
from tools.ai_engine import generate_response
from tools.lead_qualifier import qualify_lead, build_qualification_context
from tools.property_manager import find_matching_properties, build_property_context
from tools.human_handoff import notify_team_new_portal_lead
from tools.email_handler import send_email, parse_inbound_email
from tools.whatsapp_handler import send_whatsapp_message
from models.database_models import ChannelType
from config import AGENT_NAME, COMPANY_NAME


router = APIRouter()


@router.post("/webhook")
async def portal_webhook(request: Request):
    """
    Webhook genérico para portales inmobiliarios.
    Acepta JSON con datos del lead. Detecta el portal automáticamente.
    
    Ejemplo:
    POST /api/portals/webhook
    {
        "source": "idealista",
        "name": "Juan García",
        "phone": "+34612345678",
        "email": "juan@email.com",
        "message": "Me interesa el piso de la zona centro",
        "property_ref": "REF-001"
    }
    """
    payload = await request.json()
    lead_data = parse_portal_lead(payload)
    
    return await _process_portal_lead(lead_data)


@router.post("/webhook/{portal_name}")
async def portal_webhook_specific(request: Request, portal_name: str):
    """
    Webhook específico por portal.
    Ej: /api/portals/webhook/idealista
    """
    payload = await request.json()
    payload["source"] = portal_name
    lead_data = parse_portal_lead(payload)
    
    return await _process_portal_lead(lead_data)


@router.post("/email")
async def portal_email_webhook(request: Request):
    """
    Recibe emails de portales (reenviados via SendGrid Inbound Parse).
    Detecta el portal por el asunto y extrae datos del lead.
    """
    form_data = await request.form()
    parsed_email = parse_inbound_email(dict(form_data))
    
    subject = parsed_email.get("subject", "")
    body = parsed_email.get("body", "")
    
    lead_data = parse_portal_email(subject, body)
    
    if not lead_data:
        return {"status": "ignored", "reason": "No se pudo parsear como lead de portal"}
    
    return await _process_portal_lead(lead_data)


async def _process_portal_lead(lead_data: dict) -> dict:
    """
    Procesa un lead de portal:
    1. Crear/encontrar lead en CRM
    2. Guardar el mensaje/consulta
    3. Responder automáticamente por email/WhatsApp
    4. Notificar al equipo humano
    5. Cualificar
    """
    source = lead_data.get("source", "portal")
    name = lead_data.get("name", "")
    phone = lead_data.get("phone", "")
    email = lead_data.get("email", "")
    message = lead_data.get("message", "")
    prop_ref = lead_data.get("property_reference", "")
    
    # Necesitamos al menos un medio de contacto
    contact_id = phone or email
    if not contact_id:
        return {"status": "error", "reason": "Sin teléfono ni email"}
    
    print(f"🏘️ Lead de {source}: {name} ({contact_id})")
    
    # 1. Crear/encontrar lead
    lead = await get_or_create_lead(
        phone=contact_id,
        channel=ChannelType.PORTAL,
        name=name or None,
    )
    
    if email and not lead.email:
        lead.email = email
    
    # 2. Guardar el mensaje como contexto
    user_message = f"[Lead de {source}]"
    if prop_ref:
        user_message += f" Interesado en propiedad {prop_ref}."
    if message:
        user_message += f" {message}"
    
    await add_message(
        lead_id=lead.id,
        role="user",
        content=user_message,
        channel=ChannelType.PORTAL,
    )
    
    # 3. Preparar contexto y generar respuesta
    additional_context = f"\n## Origen del Lead\n"
    additional_context += f"- Portal: {source}\n"
    additional_context += f"- Referencia propiedad: {prop_ref or 'No especificada'}\n"
    additional_context += f"- Mensaje original: {message}\n"
    additional_context += f"\n## Instrucción especial\n"
    additional_context += (
        f"- Este lead llegó de un portal inmobiliario ({source}). "
        f"Respóndele presentándote y mostrando interés en ayudarle. "
        f"Si mencionó una propiedad, dale info y ofrece agendar visita. "
        f"Sé proactivo: el lead ya mostró interés, aprovéchalo.\n"
    )
    
    if lead.preferences.zone or lead.preferences.max_budget:
        matching_props = await find_matching_properties(lead, limit=5)
        if matching_props:
            additional_context += build_property_context(matching_props)
    
    # Inyectar estado de cualificación
    additional_context += build_qualification_context(lead)
    
    conversation = await get_or_create_conversation(lead.id, ChannelType.PORTAL)
    context_messages = get_context_messages(conversation)
    if context_messages and context_messages[-1]["role"] == "user":
        context_messages = context_messages[:-1]
    
    agent_response = await generate_response(
        user_message=user_message,
        conversation_history=context_messages,
        additional_context=additional_context,
        lead_context={
            "name": name or "",
            "phone": phone or "",
            "email": email or "",
            "score": lead.score,
            "channel": f"portal ({source})",
        },
    )
    
    await add_message(
        lead_id=lead.id,
        role="assistant",
        content=agent_response,
        channel=ChannelType.PORTAL,
    )
    
    # 4. Enviar respuesta al lead
    response_sent = False
    
    if email:
        try:
            await send_email(
                to_email=email,
                subject=f"Re: Tu consulta en {source} — {COMPANY_NAME}",
                body_text=agent_response,
            )
            response_sent = True
        except Exception as e:
            print(f"⚠️ Error enviando email a lead de portal: {e}")
    
    if phone and not phone.startswith("ig:") and phone != email:
        try:
            await send_whatsapp_message(
                to=f"whatsapp:{phone}",
                body=agent_response,
            )
            response_sent = True
        except Exception as e:
            print(f"⚠️ Error enviando WhatsApp a lead de portal: {e}")
    
    # 5. Cualificar
    await qualify_lead(lead, ChannelType.PORTAL)
    
    # 6. Notificar al equipo humano
    await notify_team_new_portal_lead(
        lead_name=name,
        lead_phone=phone,
        lead_email=email,
        source=source,
        message=message,
        property_ref=prop_ref,
    )
    
    print(f"✅ Lead de {source} procesado: {name} (respuesta enviada: {response_sent})")
    
    return {
        "status": "ok",
        "lead_id": lead.id,
        "source": source,
        "response_sent": response_sent,
    }
