"""
Servicio de recordatorios automáticos.
Envía recordatorios por WhatsApp y Email antes de las visitas.
Usa APScheduler para programar los envíos.
"""

import asyncio
from datetime import datetime, timedelta
from tools.scheduler import get_upcoming_visits
from tools.whatsapp_handler import send_whatsapp_message
from tools.email_handler import send_email
from config import AGENT_NAME, COMPANY_NAME


# ─────────────────────────────────────────────
# Recordatorios de visitas
# ─────────────────────────────────────────────
async def send_visit_reminders():
    """
    Envía recordatorios de visitas próximas.
    Debe ejecutarse periódicamente (ej: cada hora via APScheduler).
    
    Envía recordatorio:
    - 24h antes: por email
    - 2h antes: por WhatsApp
    """
    visits = await get_upcoming_visits(days=2)
    now = datetime.now()
    
    for visit in visits:
        start_str = visit.get("start", "")
        if not start_str:
            continue
        
        visit_time = datetime.fromisoformat(start_str.replace("Z", "+00:00")).replace(tzinfo=None)
        time_until = visit_time - now
        
        # Extraer datos del lead de la descripción
        description = visit.get("description", "")
        lead_info = _parse_visit_description(description)
        
        property_title = visit.get("summary", "").replace("🏠 Visita: ", "")
        location = visit.get("location", "")
        
        # Recordatorio 24h antes (por email)
        if timedelta(hours=23) <= time_until <= timedelta(hours=25):
            if lead_info.get("email"):
                await _send_email_reminder(
                    email=lead_info["email"],
                    name=lead_info.get("name", ""),
                    property_title=property_title,
                    address=location,
                    visit_time=visit_time,
                )
        
        # Recordatorio 2h antes (por WhatsApp)
        if timedelta(hours=1, minutes=50) <= time_until <= timedelta(hours=2, minutes=10):
            if lead_info.get("phone"):
                await _send_whatsapp_reminder(
                    phone=lead_info["phone"],
                    name=lead_info.get("name", ""),
                    property_title=property_title,
                    address=location,
                    visit_time=visit_time,
                )


async def _send_whatsapp_reminder(
    phone: str,
    name: str,
    property_title: str,
    address: str,
    visit_time: datetime,
):
    """Envía recordatorio de visita por WhatsApp."""
    day_name = _day_name_es(visit_time)
    
    message = (
        f"📅 ¡Hola{' ' + name if name else ''}! Te recuerdo que tienes una visita:\n\n"
        f"🏠 *{property_title}*\n"
        f"📍 {address}\n"
        f"🕐 {day_name} {visit_time.strftime('%d/%m/%Y')} a las {visit_time.strftime('%H:%M')}\n\n"
        f"¿Todo sigue en pie? Confirma con un 👍 o avísame si necesitas cambiar algo.\n\n"
        f"— {AGENT_NAME}, {COMPANY_NAME}"
    )
    
    try:
        await send_whatsapp_message(to=f"whatsapp:{phone}", body=message)
        print(f"✅ Recordatorio WhatsApp enviado a {phone}")
    except Exception as e:
        print(f"⚠️ Error enviando recordatorio WhatsApp a {phone}: {e}")


async def _send_email_reminder(
    email: str,
    name: str,
    property_title: str,
    address: str,
    visit_time: datetime,
):
    """Envía recordatorio de visita por email."""
    day_name = _day_name_es(visit_time)
    
    subject = f"📅 Recordatorio: Visita a {property_title} mañana"
    
    body = (
        f"Hola {name or ''},\n\n"
        f"Te recordamos tu visita programada para mañana:\n\n"
        f"Propiedad: {property_title}\n"
        f"Dirección: {address}\n"
        f"Fecha: {day_name} {visit_time.strftime('%d/%m/%Y')}\n"
        f"Hora: {visit_time.strftime('%H:%M')}\n\n"
        f"Si necesitas cancelar o cambiar la hora, simplemente responde a este email.\n\n"
        f"Un saludo,\n"
        f"{AGENT_NAME}\n"
        f"{COMPANY_NAME}"
    )
    
    try:
        await send_email(to_email=email, subject=subject, body_text=body)
        print(f"✅ Recordatorio email enviado a {email}")
    except Exception as e:
        print(f"⚠️ Error enviando recordatorio email a {email}: {e}")


# ─────────────────────────────────────────────
# Post-visita
# ─────────────────────────────────────────────
async def send_post_visit_followup(
    phone: str = None,
    email: str = None,
    name: str = "",
    property_title: str = "",
):
    """
    Envía mensaje de seguimiento después de una visita.
    Se ejecuta 24h después de la visita.
    """
    message = (
        f"¡Hola{' ' + name if name else ''}! 😊\n\n"
        f"Espero que la visita a *{property_title}* haya sido de tu agrado. "
        f"¿Qué te pareció? ¿Tienes alguna pregunta o te gustaría ver otras opciones?\n\n"
        f"Estoy aquí para ayudarte con lo que necesites.\n\n"
        f"— {AGENT_NAME}, {COMPANY_NAME}"
    )
    
    if phone:
        try:
            await send_whatsapp_message(to=f"whatsapp:{phone}", body=message)
        except Exception:
            pass
    
    if email:
        try:
            await send_email(
                to_email=email,
                subject=f"¿Qué te pareció {property_title}? — {COMPANY_NAME}",
                body_text=message.replace("*", ""),
            )
        except Exception:
            pass


# ─────────────────────────────────────────────
# Utilidades
# ─────────────────────────────────────────────
def _parse_visit_description(description: str) -> dict:
    """Extrae datos del lead de la descripción del evento."""
    info = {"name": "", "phone": "", "email": ""}
    
    for line in description.split("\n"):
        line = line.strip()
        if "Cliente:" in line:
            info["name"] = line.split("Cliente:")[-1].strip().strip("*")
        elif "Teléfono:" in line:
            info["phone"] = line.split("Teléfono:")[-1].strip().strip("*")
        elif "Email:" in line:
            info["email"] = line.split("Email:")[-1].strip().strip("*")
    
    return info


def _day_name_es(dt: datetime) -> str:
    """Nombre del día en español."""
    days = {
        0: "lunes", 1: "martes", 2: "miércoles", 3: "jueves",
        4: "viernes", 5: "sábado", 6: "domingo",
    }
    return days.get(dt.weekday(), "")
