"""
CRM Inmobiliario.
Gestión de leads, clasificación, historial y tareas para agentes humanos.
"""

from datetime import datetime
from config import LEAD_SCORE_COLD, LEAD_SCORE_WARM, LEAD_SCORE_HOT
from models.database_models import (
    Lead, LeadStatus, LeadScore, LeadPreferences, ChannelType, TaskPriority,
)
from tools.database import (
    get_lead_by_phone,
    create_lead,
    update_lead,
    create_task,
)


async def get_or_create_lead(
    phone: str,
    channel: ChannelType = ChannelType.WHATSAPP,
    name: str = None,
) -> Lead:
    """
    Busca un lead por teléfono o crea uno nuevo.
    Es el punto de entrada para todo nuevo contacto.
    """
    existing = await get_lead_by_phone(phone)
    
    if existing:
        # Actualizar último contacto
        await update_lead(existing["id"], {
            "last_contact": datetime.now().isoformat(),
            "total_interactions": existing.get("total_interactions", 0) + 1,
        })
        
        return Lead(
            id=existing["id"],
            name=existing.get("name"),
            phone=existing["phone"],
            email=existing.get("email"),
            channel=ChannelType(existing.get("channel", channel.value)),
            status=LeadStatus(existing.get("status", "nuevo")),
            score=existing.get("score", 0),
            score_label=LeadScore(existing.get("score_label", "curioso")),
            preferences=LeadPreferences(**(existing.get("preferences") or {})),
            tags=existing.get("tags", []),
            assigned_agent=existing.get("assigned_agent"),
            created_at=existing.get("created_at"),
            last_contact=datetime.now(),
            total_interactions=existing.get("total_interactions", 0) + 1,
        )
    
    # Crear nuevo lead
    lead_data = {
        "phone": phone,
        "name": name,
        "channel": channel.value,
        "status": LeadStatus.NUEVO.value,
        "score": 0,
        "score_label": LeadScore.CURIOSO.value,
        "preferences": {},
        "tags": [],
        "created_at": datetime.now().isoformat(),
        "last_contact": datetime.now().isoformat(),
        "total_interactions": 1,
    }
    
    result = await create_lead(lead_data)
    
    return Lead(
        id=result["id"] if result else None,
        phone=phone,
        name=name,
        channel=channel,
        status=LeadStatus.NUEVO,
        score=0,
        score_label=LeadScore.CURIOSO,
        preferences=LeadPreferences(),
        created_at=datetime.now(),
        last_contact=datetime.now(),
        total_interactions=1,
    )


async def update_lead_from_extraction(lead: Lead, extracted: dict) -> Lead:
    """
    Actualiza un lead con la información extraída por el LLM.
    Solo actualiza campos que no eran conocidos antes.
    """
    prefs = lead.preferences
    updated = False
    
    # Actualizar preferencias si son nuevas
    field_map = {
        "operation": "operation",
        "property_type": "property_type",
        "zone": "zone",
        "min_budget": "min_budget",
        "max_budget": "max_budget",
        "bedrooms": "bedrooms",
        "bathrooms": "bathrooms",
        "min_sqm": "min_sqm",
        "parking": "parking",
        "urgency": "urgency",
        "purpose": "purpose",
    }
    
    for ext_key, pref_key in field_map.items():
        value = extracted.get(ext_key)
        if value is not None and getattr(prefs, pref_key) is None:
            setattr(prefs, pref_key, value)
            updated = True
    
    # Actualizar nombre si no lo teníamos
    extracted_name = extracted.get("name")
    if extracted_name and not lead.name:
        lead.name = extracted_name
        updated = True
    
    # Recalcular score
    lead.preferences = prefs
    lead.score = calculate_lead_score(lead, extracted)
    lead.score_label = get_score_label(lead.score)
    
    # Actualizar status según score
    if lead.score >= LEAD_SCORE_HOT and lead.status == LeadStatus.NUEVO:
        lead.status = LeadStatus.CUALIFICADO
    elif lead.score >= LEAD_SCORE_WARM and lead.status == LeadStatus.NUEVO:
        lead.status = LeadStatus.CONTACTADO
    
    if updated or True:  # Siempre actualizar score
        await update_lead(lead.id, {
            "name": lead.name,
            "preferences": prefs.model_dump(),
            "score": lead.score,
            "score_label": lead.score_label.value,
            "status": lead.status.value,
        })
    
    # Crear tarea si es lead caliente
    if lead.score >= LEAD_SCORE_HOT:
        await _create_hot_lead_task(lead)
    
    # Derivar a humano si lo solicita
    if extracted.get("wants_human_agent"):
        await _create_human_handoff_task(lead)
    
    return lead


def calculate_lead_score(lead: Lead, extracted: dict = None) -> int:
    """
    Calcula el score de un lead (0-100) basado en la info disponible.
    Más info = más score. Info de calidad = más puntos.
    """
    score = 0
    prefs = lead.preferences
    
    # Puntos por información proporcionada
    if prefs.operation:
        score += 10
    if prefs.property_type:
        score += 10
    if prefs.zone:
        score += 15
    if prefs.max_budget or prefs.min_budget:
        score += 15
    if prefs.bedrooms:
        score += 5
    if prefs.urgency:
        score += 10
        if prefs.urgency in ("inmediata", "1-3 meses"):
            score += 10  # Bonus por urgencia
    if prefs.purpose:
        score += 5
    if lead.name:
        score += 5
    
    # Puntos por nivel de interés detectado
    if extracted:
        interest = extracted.get("interest_level", "bajo")
        interest_points = {"bajo": 0, "medio": 5, "alto": 10, "muy alto": 15}
        score += interest_points.get(interest, 0)
        
        if extracted.get("wants_visit"):
            score += 15
    
    # Puntos por interacciones
    if lead.total_interactions >= 3:
        score += 5
    if lead.total_interactions >= 5:
        score += 5
    
    return min(score, 100)


def get_score_label(score: int) -> LeadScore:
    """Clasifica el score numérico en una categoría."""
    if score <= LEAD_SCORE_COLD:
        return LeadScore.CURIOSO
    elif score <= LEAD_SCORE_WARM:
        return LeadScore.INTERESADO
    elif score <= LEAD_SCORE_HOT:
        return LeadScore.CALIENTE
    else:
        return LeadScore.LISTO


async def _create_hot_lead_task(lead: Lead) -> None:
    """Crea una tarea urgente para leads calientes."""
    await create_task({
        "lead_id": lead.id,
        "type": "llamar",
        "description": (
            f"🔥 Lead caliente: {lead.name or lead.phone}. "
            f"Score: {lead.score}/100. "
            f"Busca: {lead.preferences.operation or 'N/A'} "
            f"{lead.preferences.property_type or ''} en {lead.preferences.zone or 'N/A'}. "
            f"Presupuesto: {lead.preferences.max_budget or 'N/A'}€"
        ),
        "priority": TaskPriority.ALTA.value,
        "status": "pendiente",
        "created_at": datetime.now().isoformat(),
    })


async def _create_human_handoff_task(lead: Lead) -> None:
    """Crea tarea cuando el cliente quiere hablar con una persona."""
    await create_task({
        "lead_id": lead.id,
        "type": "contactar",
        "description": (
            f"👤 El cliente {lead.name or lead.phone} ha solicitado hablar con un agente humano. "
            f"Canal: {lead.channel.value}. Contactar lo antes posible."
        ),
        "priority": TaskPriority.URGENTE.value,
        "status": "pendiente",
        "created_at": datetime.now().isoformat(),
    })
