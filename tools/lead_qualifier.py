"""
Cualificador inteligente de leads.
Analiza conversaciones para extraer datos y clasificar el potencial del lead.
"""

from models.database_models import Lead, ChannelType
from tools.ai_engine import extract_lead_info
from tools.conversation_manager import (
    get_or_create_conversation,
    get_full_conversation_text,
)
from tools.crm import update_lead_from_extraction


async def qualify_lead(lead: Lead, channel: ChannelType = ChannelType.WHATSAPP) -> Lead:
    """
    Proceso de cualificación completo:
    1. Obtiene la conversación del lead
    2. Extrae información con IA
    3. Actualiza el lead con los datos extraídos
    4. Recalcula score y clasificación
    
    Returns:
        Lead actualizado con score y preferencias
    """
    # Obtener conversación
    conversation = await get_or_create_conversation(lead.id, channel)
    
    if not conversation.messages:
        return lead
    
    # Obtener texto completo de la conversación
    conv_text = get_full_conversation_text(conversation)
    
    # Extraer información con IA
    extracted = await extract_lead_info(conv_text)
    
    if not extracted:
        return lead
    
    # Actualizar lead con info extraída
    lead = await update_lead_from_extraction(lead, extracted)
    
    return lead


def get_qualification_summary(lead: Lead) -> str:
    """
    Genera un resumen de la cualificación del lead.
    Útil para informar al agente humano.
    """
    prefs = lead.preferences
    
    lines = [
        f"📊 **Cualificación de Lead**",
        f"• Nombre: {lead.name or 'No proporcionado'}",
        f"• Score: {lead.score}/100 ({lead.score_label.value})",
        f"• Estado: {lead.status.value}",
        f"• Canal: {lead.channel.value}",
        f"• Interacciones: {lead.total_interactions}",
        "",
        f"🏠 **Preferencias**",
        f"• Operación: {prefs.operation or '❓'}",
        f"• Tipo: {prefs.property_type or '❓'}",
        f"• Zona: {prefs.zone or '❓'}",
        f"• Presupuesto: {_format_budget(prefs.min_budget, prefs.max_budget)}",
        f"• Habitaciones: {prefs.bedrooms or '❓'}",
        f"• Urgencia: {prefs.urgency or '❓'}",
        f"• Finalidad: {prefs.purpose or '❓'}",
    ]
    
    # Indicar qué falta por averiguar
    missing = []
    if not prefs.operation:
        missing.append("operación (comprar/alquilar)")
    if not prefs.zone:
        missing.append("zona")
    if not prefs.max_budget:
        missing.append("presupuesto")
    if not prefs.urgency:
        missing.append("urgencia")
    
    if missing:
        lines.append("")
        lines.append(f"⚠️ **Falta por averiguar**: {', '.join(missing)}")
    
    return "\n".join(lines)


def build_qualification_context(lead) -> str:
    """
    Genera contexto de cualificación para inyectar en el prompt del LLM.
    Le dice al agente exactamente qué datos le faltan y cuáles priorizar.
    """
    prefs = lead.preferences
    
    # Campos conocidos
    known = []
    if prefs.operation:
        known.append(f"- Operación: {prefs.operation}")
    if prefs.property_type:
        known.append(f"- Tipo inmueble: {prefs.property_type}")
    if prefs.zone:
        known.append(f"- Zona: {prefs.zone}")
    if prefs.max_budget or prefs.min_budget:
        known.append(f"- Presupuesto: {_format_budget(prefs.min_budget, prefs.max_budget)}")
    if prefs.bedrooms:
        known.append(f"- Habitaciones: {prefs.bedrooms}")
    if prefs.urgency:
        known.append(f"- Urgencia: {prefs.urgency}")
    if prefs.purpose:
        known.append(f"- Finalidad: {prefs.purpose}")
    if lead.name:
        known.append(f"- Nombre: {lead.name}")
    
    # Campos que faltan con sus puntos
    missing = []
    if not prefs.zone:
        missing.append(("zona o barrio de interés", 15))
    if not prefs.max_budget and not prefs.min_budget:
        missing.append(("presupuesto aproximado", 15))
    if not prefs.operation:
        missing.append(("si quiere comprar o alquilar", 10))
    if not prefs.property_type:
        missing.append(("tipo de inmueble (piso, casa, etc.)", 10))
    if not prefs.urgency:
        missing.append(("urgencia / cuándo lo necesita", 10))
    if not lead.name:
        missing.append(("nombre del cliente", 5))
    if not prefs.bedrooms:
        missing.append(("número de habitaciones", 5))
    if not prefs.purpose:
        missing.append(("finalidad (vivienda habitual, inversión...)", 5))
    
    # Ordenar por puntos (priorizar lo que más aporta)
    missing.sort(key=lambda x: x[1], reverse=True)
    
    # Construir contexto
    lines = [f"\n## Estado de Cualificación"]
    lines.append(f"Score actual: {lead.score}/100 ({lead.score_label.value})")
    
    if known:
        lines.append(f"\nDatos ya conocidos:")
        lines.extend(known)
    
    if missing:
        lines.append(f"\n⚠️ DATOS QUE AÚN NECESITAS AVERIGUAR (ordenados por prioridad):")
        for field, points in missing:
            lines.append(f"- {field} (+{points} puntos)")
        lines.append(f"\nINSTRUCCIÓN: Intenta averiguar los datos que faltan de forma natural durante la conversación.")
        lines.append(f"Prioriza los que están más arriba (valen más puntos). NO preguntes más de 1-2 cosas a la vez.")
        lines.append(f"Si ya preguntaste algo y el cliente no respondió, no insistas. Pasa a otro tema.")
    else:
        lines.append(f"\n✅ ¡Tienes toda la información clave! Este lead está bien cualificado.")
        lines.append(f"Enfócate en cerrar: proponer propiedades concretas y agendar visita.")
    
    return "\n".join(lines)


def _format_budget(min_b: float = None, max_b: float = None) -> str:
    """Formatea el rango de presupuesto."""
    if min_b and max_b:
        return f"{min_b:,.0f}€ - {max_b:,.0f}€"
    elif max_b:
        return f"Hasta {max_b:,.0f}€"
    elif min_b:
        return f"Desde {min_b:,.0f}€"
    return "❓"
