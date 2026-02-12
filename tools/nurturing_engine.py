"""
Motor de Nurturing (seguimiento automático).
Gestiona follow-ups inteligentes para mantener engagement con leads:
- Reactivación de leads fríos
- Follow-up post-visita
- Envío de nuevas propiedades matching
- Secuencias de nutrición por etapa del funnel
"""

from datetime import datetime, timedelta
from typing import Optional

from tools.whatsapp_handler import send_whatsapp_message
from tools.email_handler import send_email, send_property_email
from tools.property_manager import find_matching_properties, format_property_for_chat
from tools.ai_engine import generate_response
from config import AGENT_NAME, COMPANY_NAME


# ─────────────────────────────────────────────
# Reglas de Nurturing
# ─────────────────────────────────────────────
NURTURING_RULES = {
    "post_first_contact": {
        "delay_hours": 24,
        "condition": "total_interactions <= 2 and score < 30",
        "channel": "whatsapp",
        "description": "Primer seguimiento tras contacto inicial",
    },
    "post_visit": {
        "delay_hours": 24,
        "condition": "status == 'visita_completada'",
        "channel": "both",
        "description": "Seguimiento después de una visita",
    },
    "warm_lead_nudge": {
        "delay_hours": 72,
        "condition": "score >= 30 and score < 60 and days_since_contact >= 3",
        "channel": "whatsapp",
        "description": "Empujar lead tibio con propiedades nuevas",
    },
    "cold_lead_reactivation": {
        "delay_hours": 168,  # 7 días
        "condition": "score < 30 and days_since_contact >= 7",
        "channel": "email",
        "description": "Reactivar lead frío con contenido de valor",
    },
    "hot_lead_urgency": {
        "delay_hours": 48,
        "condition": "score >= 60 and days_since_contact >= 2",
        "channel": "whatsapp",
        "description": "Lead caliente sin actividad — crear urgencia",
    },
    "new_properties_matching": {
        "delay_hours": 0,  # Se ejecuta al añadir propiedades
        "condition": "has_preferences and new_properties_available",
        "channel": "email",
        "description": "Nuevas propiedades que coinciden con criterios",
    },
}


# ─────────────────────────────────────────────
# Motor principal
# ─────────────────────────────────────────────
async def process_nurturing(leads: list[dict]) -> dict:
    """
    Procesa la lista de leads y ejecuta acciones de nurturing.
    Diseñado para ejecutarse periódicamente via APScheduler.
    
    Args:
        leads: Lista de leads con sus datos y historial
    
    Returns:
        Resumen de acciones ejecutadas
    """
    actions_taken = {
        "messages_sent": 0,
        "emails_sent": 0,
        "leads_processed": 0,
        "errors": 0,
    }
    
    now = datetime.now()
    
    for lead in leads:
        try:
            last_contact = lead.get("last_contact")
            if isinstance(last_contact, str):
                last_contact = datetime.fromisoformat(last_contact)
            
            days_since = (now - last_contact).days if last_contact else 999
            score = lead.get("score", 0)
            interactions = lead.get("total_interactions", 0)
            
            # Evaluar cada regla
            action = _evaluate_nurturing_rules(lead, days_since, score, interactions)
            
            if action:
                await _execute_nurturing_action(lead, action)
                actions_taken["leads_processed"] += 1
                
                if action["channel"] in ("whatsapp", "both"):
                    actions_taken["messages_sent"] += 1
                if action["channel"] in ("email", "both"):
                    actions_taken["emails_sent"] += 1
                    
        except Exception as e:
            print(f"⚠️ Error nurturing lead {lead.get('id', '?')}: {e}")
            actions_taken["errors"] += 1
    
    return actions_taken


def _evaluate_nurturing_rules(
    lead: dict,
    days_since_contact: int,
    score: int,
    interactions: int,
) -> Optional[dict]:
    """Evalúa las reglas y devuelve la acción a ejecutar (si aplica)."""
    
    # Lead caliente sin actividad → urgencia
    if score >= 60 and days_since_contact >= 2:
        return {
            "type": "hot_lead_urgency",
            "channel": "whatsapp",
            "template": "hot_lead",
        }
    
    # Lead tibio → propiedades relevantes
    if 30 <= score < 60 and days_since_contact >= 3:
        return {
            "type": "warm_lead_nudge",
            "channel": "whatsapp",
            "template": "warm_nudge",
        }
    
    # Post primer contacto
    if interactions <= 2 and score < 30 and 1 <= days_since_contact <= 2:
        return {
            "type": "post_first_contact",
            "channel": "whatsapp",
            "template": "first_followup",
        }
    
    # Lead frío → reactivación
    if score < 30 and days_since_contact >= 7:
        return {
            "type": "cold_lead_reactivation",
            "channel": "email",
            "template": "reactivation",
        }
    
    return None


async def _execute_nurturing_action(lead: dict, action: dict):
    """Ejecuta una acción de nurturing."""
    phone = lead.get("phone", "")
    email = lead.get("email", "")
    name = lead.get("name", "")
    template = action.get("template", "")
    
    message = _generate_nurturing_message(template, lead)
    
    # Enviar por WhatsApp
    if action["channel"] in ("whatsapp", "both") and phone and not phone.startswith("ig:"):
        try:
            await send_whatsapp_message(
                to=f"whatsapp:{phone}",
                body=message,
            )
            print(f"✅ Nurturing WhatsApp → {phone} ({action['type']})")
        except Exception as e:
            print(f"⚠️ Error nurturing WhatsApp {phone}: {e}")
    
    # Enviar por Email
    if action["channel"] in ("email", "both") and email:
        subject_map = {
            "first_followup": f"¿Encontraste lo que buscabas? — {COMPANY_NAME}",
            "warm_nudge": f"🏠 Nuevas opciones para ti — {COMPANY_NAME}",
            "hot_lead": f"¡No te pierdas esta oportunidad! — {COMPANY_NAME}",
            "reactivation": f"Te echamos de menos — {COMPANY_NAME}",
        }
        
        try:
            await send_email(
                to_email=email,
                subject=subject_map.get(template, f"Novedades — {COMPANY_NAME}"),
                body_text=message,
            )
            print(f"✅ Nurturing Email → {email} ({action['type']})")
        except Exception as e:
            print(f"⚠️ Error nurturing Email {email}: {e}")


def _generate_nurturing_message(template: str, lead: dict) -> str:
    """Genera el mensaje de nurturing según la plantilla."""
    name = lead.get("name", "")
    greeting = f"¡Hola {name}!" if name else "¡Hola!"
    prefs = lead.get("preferences", {})
    
    zone = prefs.get("zone", "")
    prop_type = prefs.get("property_type", "")
    budget = prefs.get("max_budget", "")
    
    if template == "first_followup":
        return (
            f"{greeting} 😊\n\n"
            f"Soy {AGENT_NAME} de {COMPANY_NAME}. "
            f"Ayer estuvimos hablando y quería saber si encontraste lo que buscabas "
            f"o si puedo ayudarte con algo más.\n\n"
            f"{'Recuerdo que buscabas ' + (prop_type or 'algo') + (' en ' + zone if zone else '') + '. ' if zone or prop_type else ''}"
            f"Tengo algunas opciones que podrían interesarte. ¿Seguimos? 🏠"
        )
    
    elif template == "warm_nudge":
        return (
            f"{greeting}\n\n"
            f"🏠 Han llegado nuevas propiedades que coinciden con lo que buscas"
            f"{' en ' + zone if zone else ''}"
            f"{' (' + prop_type + ')' if prop_type else ''}.\n\n"
            f"¿Te gustaría que te envíe los detalles? Solo responde \"sí\" "
            f"y te mando toda la info. 😊\n\n"
            f"— {AGENT_NAME}, {COMPANY_NAME}"
        )
    
    elif template == "hot_lead":
        return (
            f"{greeting}\n\n"
            f"¡Quería avisarte! Hay mucho interés en las propiedades que viste"
            f"{' en ' + zone if zone else ''}. "
            f"Si quieres que te reserve una visita antes de que se vayan, "
            f"¡dime y lo agendamos! 🔥\n\n"
            f"— {AGENT_NAME}, {COMPANY_NAME}"
        )
    
    elif template == "reactivation":
        return (
            f"{greeting}\n\n"
            f"Hace tiempo que no hablamos y quería escribirte. "
            f"{'¿Sigues buscando ' + (prop_type or 'propiedad') + (' en ' + zone if zone else '') + '? ' if zone or prop_type else '¿Sigues buscando propiedad? '}\n\n"
            f"Tenemos novedades interesantes en nuestro catálogo. "
            f"Si quieres, puedo enviarte las últimas opciones.\n\n"
            f"¡Estamos aquí para ayudarte!\n\n"
            f"Un saludo,\n"
            f"{AGENT_NAME}\n"
            f"{COMPANY_NAME}"
        )
    
    return f"{greeting}\n\n¿Puedo ayudarte con algo? — {AGENT_NAME}, {COMPANY_NAME}"


# ─────────────────────────────────────────────
# Notificación de nuevas propiedades
# ─────────────────────────────────────────────
async def notify_new_property_to_matching_leads(
    property_data: dict,
    matching_leads: list[dict],
):
    """
    Notifica a leads cuyos criterios coinciden con una nueva propiedad.
    Se ejecuta cuando se añade una propiedad al catálogo.
    """
    for lead in matching_leads:
        email = lead.get("email", "")
        phone = lead.get("phone", "")
        name = lead.get("name", "")
        
        if email:
            await send_property_email(
                to_email=email,
                properties=[property_data],
                lead_name=name,
            )
        elif phone and not phone.startswith("ig:"):
            prop_text = (
                f"🏠 ¡{name or 'Hola'}! Nueva propiedad que encaja con tu búsqueda:\n\n"
                f"*{property_data.get('title', '')}*\n"
                f"💰 {property_data.get('price', 0):,.0f}€\n"
                f"📍 {property_data.get('zone', '')}\n"
                f"📐 {property_data.get('sqm', 0)} m²\n\n"
                f"¿Quieres más detalles o agendar una visita?"
            )
            await send_whatsapp_message(to=f"whatsapp:{phone}", body=prop_text)
