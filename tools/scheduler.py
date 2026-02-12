"""
Agendador de visitas con Google Calendar.
Gestiona la creación, modificación y consulta de citas para visitas a inmuebles.

Docs: https://developers.google.com/calendar/api
"""

import os
import json
from datetime import datetime, timedelta
from typing import Optional

import httpx
from config import APP_URL, AGENT_NAME, COMPANY_NAME


# ─────────────────────────────────────────────
# Configuración
# ─────────────────────────────────────────────
GOOGLE_CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "primary")
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
GOOGLE_TOKEN_PATH = os.getenv("GOOGLE_TOKEN_PATH", "token.json")

CALENDAR_API_URL = "https://www.googleapis.com/calendar/v3"

# Horarios de visita permitidos
VISIT_HOURS = {
    "morning": {"start": "10:00", "end": "13:00"},
    "afternoon": {"start": "16:00", "end": "20:00"},
    "saturday": {"start": "10:00", "end": "14:00"},
}

# Duración por defecto de una visita (minutos)
DEFAULT_VISIT_DURATION = 45


# ─────────────────────────────────────────────
# Autenticación Google
# ─────────────────────────────────────────────
_access_token: Optional[str] = None


def _load_google_token() -> str:
    """Carga el token de acceso de Google desde token.json."""
    global _access_token
    
    if _access_token:
        return _access_token
    
    if os.path.exists(GOOGLE_TOKEN_PATH):
        with open(GOOGLE_TOKEN_PATH, "r") as f:
            token_data = json.load(f)
            _access_token = token_data.get("access_token", "")
            return _access_token
    
    print("⚠️ No se encontró token.json. Ejecuta la autenticación de Google Calendar primero.")
    return ""


def _get_headers() -> dict:
    """Headers con autenticación para Google Calendar API."""
    token = _load_google_token()
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


# ─────────────────────────────────────────────
# Consultar disponibilidad
# ─────────────────────────────────────────────
async def get_available_slots(
    date: str,
    duration_minutes: int = DEFAULT_VISIT_DURATION,
) -> list[dict]:
    """
    Obtiene horarios disponibles para un día dado.
    
    Args:
        date: Fecha en formato YYYY-MM-DD
        duration_minutes: Duración de la visita en minutos
    
    Returns:
        Lista de slots disponibles: [{"start": "10:00", "end": "10:45"}, ...]
    """
    # Determinar horarios según día
    dt = datetime.strptime(date, "%Y-%m-%d")
    day_name = dt.strftime("%A").lower()
    
    if day_name == "sunday":
        return []  # No hay visitas los domingos
    
    if day_name == "saturday":
        hours = VISIT_HOURS["saturday"]
    else:
        # Lunes a viernes: mañana y tarde
        hours = None  # Usamos ambos rangos
    
    # Obtener eventos existentes del día
    existing_events = await _get_events_for_date(date)
    
    # Generar slots disponibles
    available = []
    
    time_ranges = []
    if day_name == "saturday":
        time_ranges.append(VISIT_HOURS["saturday"])
    else:
        time_ranges.append(VISIT_HOURS["morning"])
        time_ranges.append(VISIT_HOURS["afternoon"])
    
    for time_range in time_ranges:
        start_h, start_m = map(int, time_range["start"].split(":"))
        end_h, end_m = map(int, time_range["end"].split(":"))
        
        current = dt.replace(hour=start_h, minute=start_m)
        end_time = dt.replace(hour=end_h, minute=end_m)
        
        while current + timedelta(minutes=duration_minutes) <= end_time:
            slot_end = current + timedelta(minutes=duration_minutes)
            
            # Verificar que no se solape con eventos existentes
            is_available = True
            for event in existing_events:
                event_start = datetime.fromisoformat(event["start"].replace("Z", "+00:00")).replace(tzinfo=None)
                event_end = datetime.fromisoformat(event["end"].replace("Z", "+00:00")).replace(tzinfo=None)
                
                if current < event_end and slot_end > event_start:
                    is_available = False
                    break
            
            if is_available:
                available.append({
                    "start": current.strftime("%H:%M"),
                    "end": slot_end.strftime("%H:%M"),
                    "datetime_start": current.isoformat(),
                    "datetime_end": slot_end.isoformat(),
                })
            
            current += timedelta(minutes=30)  # Slots cada 30 min
    
    return available


async def _get_events_for_date(date: str) -> list[dict]:
    """Obtiene todos los eventos de un día del calendario."""
    dt = datetime.strptime(date, "%Y-%m-%d")
    time_min = dt.isoformat() + "Z"
    time_max = (dt + timedelta(days=1)).isoformat() + "Z"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{CALENDAR_API_URL}/calendars/{GOOGLE_CALENDAR_ID}/events",
                headers=_get_headers(),
                params={
                    "timeMin": time_min,
                    "timeMax": time_max,
                    "singleEvents": "true",
                    "orderBy": "startTime",
                },
            )
            response.raise_for_status()
            events = response.json().get("items", [])
            
            return [
                {
                    "id": e.get("id"),
                    "summary": e.get("summary", ""),
                    "start": e.get("start", {}).get("dateTime", ""),
                    "end": e.get("end", {}).get("dateTime", ""),
                }
                for e in events
            ]
    except Exception as e:
        print(f"⚠️ Error al consultar Google Calendar: {e}")
        return []


# ─────────────────────────────────────────────
# Crear visitas
# ─────────────────────────────────────────────
async def schedule_visit(
    lead_name: str,
    lead_phone: str,
    lead_email: str,
    property_title: str,
    property_address: str,
    visit_datetime: str,
    duration_minutes: int = DEFAULT_VISIT_DURATION,
    agent_name: str = None,
    notes: str = "",
) -> dict:
    """
    Agenda una visita en Google Calendar.
    
    Args:
        lead_name: Nombre del cliente
        lead_phone: Teléfono del cliente
        lead_email: Email del cliente (para invitación)
        property_title: Nombre/título de la propiedad
        property_address: Dirección de la propiedad
        visit_datetime: Fecha y hora en formato ISO (2024-01-15T10:00:00)
        duration_minutes: Duración en minutos
        agent_name: Nombre del agente que acompaña
        notes: Notas adicionales
    
    Returns:
        Dict con el evento creado (id, htmlLink, etc.)
    """
    start = datetime.fromisoformat(visit_datetime)
    end = start + timedelta(minutes=duration_minutes)
    
    event = {
        "summary": f"🏠 Visita: {property_title}",
        "description": (
            f"**Visita inmobiliaria**\n\n"
            f"📋 **Propiedad:** {property_title}\n"
            f"📍 **Dirección:** {property_address}\n"
            f"👤 **Cliente:** {lead_name}\n"
            f"📱 **Teléfono:** {lead_phone}\n"
            f"{'📧 **Email:** ' + lead_email if lead_email else ''}\n"
            f"{'🏢 **Agente:** ' + (agent_name or AGENT_NAME)}\n"
            f"{'📝 **Notas:** ' + notes if notes else ''}\n\n"
            f"— {COMPANY_NAME}"
        ),
        "location": property_address,
        "start": {
            "dateTime": start.isoformat(),
            "timeZone": "Europe/Madrid",
        },
        "end": {
            "dateTime": end.isoformat(),
            "timeZone": "Europe/Madrid",
        },
        "attendees": [],
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "popup", "minutes": 60},   # 1 hora antes
                {"method": "popup", "minutes": 15},   # 15 min antes
            ],
        },
        "colorId": "6",  # Naranja — visitas
    }
    
    # Añadir email del cliente como asistente si disponible
    if lead_email:
        event["attendees"].append({"email": lead_email})
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{CALENDAR_API_URL}/calendars/{GOOGLE_CALENDAR_ID}/events",
                headers=_get_headers(),
                json=event,
                params={"sendUpdates": "all"},  # Envía invitación por email
            )
            response.raise_for_status()
            result = response.json()
            
            print(f"📅 Visita agendada: {property_title} — {start.strftime('%d/%m/%Y %H:%M')}")
            return {
                "id": result.get("id"),
                "html_link": result.get("htmlLink"),
                "start": start.isoformat(),
                "end": end.isoformat(),
                "summary": result.get("summary"),
            }
    except Exception as e:
        print(f"❌ Error al agendar visita: {e}")
        return {"error": str(e)}


async def cancel_visit(event_id: str) -> bool:
    """Cancela una visita del calendario."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{CALENDAR_API_URL}/calendars/{GOOGLE_CALENDAR_ID}/events/{event_id}",
                headers=_get_headers(),
            )
            response.raise_for_status()
            print(f"🗑️ Visita cancelada: {event_id}")
            return True
    except Exception as e:
        print(f"❌ Error al cancelar visita: {e}")
        return False


async def get_upcoming_visits(days: int = 7) -> list[dict]:
    """Obtiene las visitas de los próximos N días."""
    now = datetime.now()
    time_max = now + timedelta(days=days)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{CALENDAR_API_URL}/calendars/{GOOGLE_CALENDAR_ID}/events",
                headers=_get_headers(),
                params={
                    "timeMin": now.isoformat() + "Z",
                    "timeMax": time_max.isoformat() + "Z",
                    "singleEvents": "true",
                    "orderBy": "startTime",
                    "q": "Visita",  # Solo eventos de visita
                },
            )
            response.raise_for_status()
            events = response.json().get("items", [])
            
            return [
                {
                    "id": e.get("id"),
                    "summary": e.get("summary", ""),
                    "start": e.get("start", {}).get("dateTime", ""),
                    "end": e.get("end", {}).get("dateTime", ""),
                    "location": e.get("location", ""),
                    "description": e.get("description", ""),
                }
                for e in events
            ]
    except Exception as e:
        print(f"⚠️ Error al obtener visitas: {e}")
        return []


# ─────────────────────────────────────────────
# Utilidades para el agente
# ─────────────────────────────────────────────
def format_available_slots_for_chat(date: str, slots: list[dict]) -> str:
    """Formatea los horarios disponibles para mostrar en chat."""
    if not slots:
        return f"Lo siento, no hay horarios disponibles para el {date}. ¿Quieres probar otro día?"
    
    dt = datetime.strptime(date, "%Y-%m-%d")
    day_name = _day_name_es(dt)
    
    text = f"📅 **Horarios disponibles para {day_name} {dt.strftime('%d/%m/%Y')}:**\n\n"
    
    for slot in slots:
        text += f"• {slot['start']} — {slot['end']}\n"
    
    text += f"\n¿Cuál te viene mejor? 🏠"
    return text


def _day_name_es(dt: datetime) -> str:
    """Nombre del día en español."""
    days = {
        0: "lunes", 1: "martes", 2: "miércoles", 3: "jueves",
        4: "viernes", 5: "sábado", 6: "domingo",
    }
    return days.get(dt.weekday(), "")
