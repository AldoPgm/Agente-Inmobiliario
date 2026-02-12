"""
Derivación a agente humano (Human Handoff).
Notifica al equipo cuando un lead necesita atención humana:
- Lead caliente que quiere cerrar
- Cliente solicita hablar con persona
- Lead de portal nuevo (alta prioridad)
- Situaciones que el agente IA no puede resolver
"""

from datetime import datetime
from tools.whatsapp_handler import send_whatsapp_message
from tools.email_handler import send_email
from config import AGENT_NAME, COMPANY_NAME
import os


# ─────────────────────────────────────────────
# Configuración de notificaciones al equipo
# ─────────────────────────────────────────────
TEAM_WHATSAPP = os.getenv("TEAM_WHATSAPP_NUMBER", "")  # Número del responsable
TEAM_EMAIL = os.getenv("TEAM_EMAIL", "")  # Email del equipo comercial
TEAM_EMAILS_CC = os.getenv("TEAM_EMAILS_CC", "").split(",")  # Emails adicionales


# ─────────────────────────────────────────────
# Detección de intención de derivación
# ─────────────────────────────────────────────
HANDOFF_KEYWORDS = [
    "hablar con persona", "hablar con alguien", "hablar con humano",
    "agente real", "persona real", "no un robot", "no un bot",
    "quiero llamar", "llámame", "contacto directo",
    "hablar con un asesor", "asesor humano", "comercial",
    "me urge", "urgente", "cerrar operación", "firmar",
    "oferta", "negociar", "contraoferta",
    "problema", "queja", "reclamación", "insatisfecho",
]


def detect_handoff_intent(message: str) -> bool:
    """
    Detecta si el cliente quiere hablar con un humano.
    
    Returns:
        True si se detecta intención de derivación
    """
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in HANDOFF_KEYWORDS)


def get_handoff_reason(message: str) -> str:
    """Determina la razón de la derivación."""
    msg = message.lower()
    
    if any(kw in msg for kw in ["queja", "reclamación", "problema", "insatisfecho"]):
        return "queja_cliente"
    elif any(kw in msg for kw in ["oferta", "negociar", "contraoferta", "firmar", "cerrar"]):
        return "negociacion"
    elif any(kw in msg for kw in ["urgente", "me urge"]):
        return "urgente"
    elif any(kw in msg for kw in ["persona", "humano", "asesor", "comercial", "robot", "bot"]):
        return "solicitud_directa"
    else:
        return "otro"


# ─────────────────────────────────────────────
# Notificaciones al equipo
# ─────────────────────────────────────────────
async def handoff_to_human(
    lead_name: str,
    lead_phone: str,
    lead_email: str = "",
    lead_score: int = 0,
    channel: str = "whatsapp",
    reason: str = "solicitud_directa",
    conversation_summary: str = "",
    last_message: str = "",
) -> bool:
    """
    Deriva un lead al equipo humano.
    Envía notificación por WhatsApp y email al responsable comercial.
    
    Returns:
        True si se notificó correctamente
    """
    reason_labels = {
        "queja_cliente": "⚠️ QUEJA DE CLIENTE",
        "negociacion": "💰 NEGOCIACIÓN / OFERTA",
        "urgente": "🔴 URGENTE",
        "solicitud_directa": "👤 SOLICITA HABLAR CON PERSONA",
        "lead_caliente": "🔥 LEAD CALIENTE",
        "portal_nuevo": "🏘️ LEAD DE PORTAL",
        "otro": "📋 REQUIERE ATENCIÓN",
    }
    
    reason_label = reason_labels.get(reason, "📋 REQUIERE ATENCIÓN")
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    notified = False
    
    # 1. Notificar por WhatsApp al responsable
    if TEAM_WHATSAPP:
        whatsapp_msg = (
            f"{reason_label}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 *{lead_name or 'Sin nombre'}*\n"
            f"📱 {lead_phone}\n"
            f"{'📧 ' + lead_email if lead_email else ''}\n"
            f"📊 Score: {lead_score}/100\n"
            f"📱 Canal: {channel}\n"
            f"🕐 {now}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
        )
        
        if last_message:
            whatsapp_msg += f"💬 Último mensaje:\n\"{last_message[:200]}\"\n\n"
        
        if conversation_summary:
            whatsapp_msg += f"📝 Resumen:\n{conversation_summary[:300]}\n"
        
        try:
            await send_whatsapp_message(
                to=f"whatsapp:{TEAM_WHATSAPP}",
                body=whatsapp_msg,
            )
            notified = True
            print(f"📲 Handoff WhatsApp → equipo: {lead_name}")
        except Exception as e:
            print(f"⚠️ Error notificando por WhatsApp: {e}")
    
    # 2. Notificar por Email
    if TEAM_EMAIL:
        subject = f"{reason_label} — {lead_name or lead_phone} — {COMPANY_NAME}"
        
        email_body = (
            f"DERIVACIÓN DE LEAD\n"
            f"{'=' * 40}\n\n"
            f"Motivo: {reason_label}\n"
            f"Fecha/Hora: {now}\n\n"
            f"DATOS DEL CLIENTE\n"
            f"{'-' * 40}\n"
            f"Nombre: {lead_name or 'No proporcionado'}\n"
            f"Teléfono: {lead_phone}\n"
            f"Email: {lead_email or 'No proporcionado'}\n"
            f"Score: {lead_score}/100\n"
            f"Canal original: {channel}\n\n"
        )
        
        if last_message:
            email_body += f"ÚLTIMO MENSAJE DEL CLIENTE\n{'-' * 40}\n\"{last_message}\"\n\n"
        
        if conversation_summary:
            email_body += f"RESUMEN DE CONVERSACIÓN\n{'-' * 40}\n{conversation_summary}\n\n"
        
        email_body += (
            f"ACCIÓN REQUERIDA\n{'-' * 40}\n"
            f"Contactar al cliente lo antes posible.\n\n"
            f"— {AGENT_NAME} (Agente IA), {COMPANY_NAME}"
        )
        
        try:
            await send_email(
                to_email=TEAM_EMAIL,
                subject=subject,
                body_text=email_body,
            )
            notified = True
            print(f"📧 Handoff Email → equipo: {lead_name}")
        except Exception as e:
            print(f"⚠️ Error notificando por email: {e}")
    
    if not TEAM_WHATSAPP and not TEAM_EMAIL:
        print(f"⚠️ Sin TEAM_WHATSAPP_NUMBER ni TEAM_EMAIL configurados. No se pudo derivar.")
    
    return notified


async def notify_team_new_portal_lead(
    lead_name: str,
    lead_phone: str,
    lead_email: str,
    source: str,
    message: str,
    property_ref: str = "",
):
    """Notifica al equipo de un nuevo lead de portal inmobiliario."""
    return await handoff_to_human(
        lead_name=lead_name,
        lead_phone=lead_phone,
        lead_email=lead_email,
        channel=f"portal ({source})",
        reason="portal_nuevo",
        last_message=message,
        conversation_summary=f"Lead recibido de {source}. "
            + (f"Interesado en propiedad {property_ref}. " if property_ref else "")
            + (f"Mensaje: {message}" if message else "Sin mensaje."),
    )


async def notify_team_hot_lead(
    lead_name: str,
    lead_phone: str,
    lead_email: str = "",
    lead_score: int = 0,
    channel: str = "whatsapp",
    conversation_summary: str = "",
):
    """Notifica al equipo de un lead caliente que necesita seguimiento humano."""
    return await handoff_to_human(
        lead_name=lead_name,
        lead_phone=lead_phone,
        lead_email=lead_email,
        lead_score=lead_score,
        channel=channel,
        reason="lead_caliente",
        conversation_summary=conversation_summary,
    )


def generate_handoff_response(reason: str) -> str:
    """
    Genera el mensaje que el agente envía al cliente al derivarlo.
    Lo usa el router cuando detecta intención de hablar con humano.
    """
    if reason == "queja_cliente":
        return (
            f"Lamento mucho que hayas tenido una mala experiencia. "
            f"He contactado a nuestro equipo y un responsable se pondrá en contacto contigo "
            f"en los próximos minutos para resolverlo personalmente. 🤝"
        )
    elif reason == "negociacion":
        return (
            f"¡Genial que quieras avanzar! He avisado a nuestro equipo comercial. "
            f"Un asesor especializado te contactará en breve para ayudarte con la negociación. "
            f"¿Hay algún horario que prefieras para la llamada? 📞"
        )
    elif reason == "urgente":
        return (
            f"Entiendo la urgencia. He marcado tu caso como prioritario. "
            f"Un miembro de nuestro equipo te contactará lo antes posible. "
            f"Si prefieres, también puedes llamarnos directamente. 📞"
        )
    else:
        return (
            f"Por supuesto, te pongo en contacto con uno de nuestros asesores. "
            f"He compartido tu conversación con el equipo para que puedan ayudarte "
            f"sin que tengas que repetir nada. Te contactarán en breve. 🤝"
        )
