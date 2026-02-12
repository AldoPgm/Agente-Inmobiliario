"""
Gestor de Propiedades.
Búsqueda, formato comercial y cálculo de hipoteca.
"""

from models.database_models import Lead, Property
from tools.database import search_properties, get_property_by_id


async def find_matching_properties(lead: Lead, limit: int = 3) -> list[dict]:
    """
    Busca propiedades que encajen con las preferencias del lead.
    
    Returns:
        Lista de propiedades coincidentes
    """
    prefs = lead.preferences
    
    results = await search_properties(
        operation=prefs.operation,
        property_type=prefs.property_type,
        zone=prefs.zone,
        min_price=prefs.min_budget,
        max_price=prefs.max_budget,
        min_sqm=prefs.min_sqm,
        bedrooms=prefs.bedrooms,
        limit=limit,
    )
    
    return results


async def search_properties_by_criteria(
    zone: str = None,
    property_type: str = None,
    max_price: float = None,
    bedrooms: int = None,
    operation: str = None,
    limit: int = 5,
) -> list[dict]:
    """
    Busca propiedades con filtros explícitos.
    Usado por function calling del LLM.
    """
    results = await search_properties(
        operation=operation,
        property_type=property_type,
        zone=zone,
        max_price=max_price,
        bedrooms=bedrooms,
        limit=limit,
    )
    return results


async def get_property_by_reference(reference: str) -> dict | None:
    """
    Obtiene una propiedad por su referencia (ej: REF-001).
    """
    from tools.database import get_property_by_ref
    return await get_property_by_ref(reference)


def format_property_for_chat(prop: dict) -> str:
    """
    Formatea una propiedad para enviar por chat (WhatsApp, Instagram, etc.)
    Presenta la información de forma atractiva y comercial.
    """
    features = prop.get("features") or {}
    
    # Título y tipo
    title = prop.get("title", "Propiedad")
    prop_type = prop.get("property_type", "")
    operation = prop.get("operation", "venta")
    
    # Precio
    price = prop.get("price", 0)
    if operation == "alquiler":
        price_text = f"💰 {price:,.0f}€/mes"
    else:
        price_text = f"💰 {price:,.0f}€"
    
    # Características principales
    details = []
    sqm = prop.get("sqm", 0)
    if sqm:
        details.append(f"📐 {sqm} m²")
    
    bedrooms = features.get("bedrooms")
    if bedrooms:
        details.append(f"🛏️ {bedrooms} hab.")
    
    bathrooms = features.get("bathrooms")
    if bathrooms:
        details.append(f"🚿 {bathrooms} baños")
    
    zone = prop.get("zone", "")
    if zone:
        details.append(f"📍 {zone}")
    
    details_text = " · ".join(details)
    
    # Extras
    extras = []
    if features.get("has_parking"):
        extras.append("🅿️ Parking")
    if features.get("has_terrace"):
        extras.append("🌿 Terraza")
    if features.get("has_elevator"):
        extras.append("🛗 Ascensor")
    if features.get("has_pool"):
        extras.append("🏊 Piscina")
    if features.get("has_ac"):
        extras.append("❄️ A/C")
    
    extras_text = " · ".join(extras) if extras else ""
    
    # Gastos
    gastos = []
    community_fee = prop.get("community_fee")
    if community_fee:
        gastos.append(f"Comunidad: {community_fee:,.0f}€/mes")
    
    ibi = prop.get("ibi_tax")
    if ibi:
        gastos.append(f"IBI: {ibi:,.0f}€/año")
    
    gastos_text = " · ".join(gastos) if gastos else ""
    
    # Construir mensaje
    lines = [
        f"🏠 *{title}*",
        f"{price_text}",
        f"{details_text}",
    ]
    
    if extras_text:
        lines.append(f"✨ {extras_text}")
    
    if gastos_text:
        lines.append(f"📋 {gastos_text}")
    
    # Descripción corta
    desc = prop.get("description", "")
    if desc:
        # Truncar a 150 caracteres
        short_desc = desc[:150] + "..." if len(desc) > 150 else desc
        lines.append(f"\n{short_desc}")
    
    # Referencia
    ref = prop.get("reference")
    if ref:
        lines.append(f"\n_Ref: {ref}_")
    
    return "\n".join(lines)


def format_properties_list(properties: list[dict]) -> str:
    """Formatea una lista de propiedades para enviar por chat."""
    if not properties:
        return (
            "No he encontrado propiedades que encajen exactamente con lo que buscas en este momento. "
            "Pero puedo tomar nota de tus preferencias y avisarte en cuanto tengamos algo nuevo. "
            "¿Te parece bien? 😊"
        )
    
    header = f"He encontrado {len(properties)} propiedad(es) que podrían interesarte:\n"
    
    formatted = [header]
    for i, prop in enumerate(properties, 1):
        formatted.append(f"━━━ Opción {i} ━━━")
        formatted.append(format_property_for_chat(prop))
    
    formatted.append("\n¿Te gustaría más información sobre alguna de estas propiedades? ¿O quieres que agendemos una visita? 🏡")
    
    return "\n\n".join(formatted)


def calculate_mortgage(
    price: float,
    down_payment_pct: float = 20,
    interest_rate: float = 3.5,
    years: int = 30,
) -> dict:
    """
    Calcula una hipoteca aproximada.
    
    Args:
        price: Precio del inmueble
        down_payment_pct: Porcentaje de entrada (default 20%)
        interest_rate: Tipo de interés anual (default 3.5%)
        years: Años de la hipoteca (default 30)
    
    Returns:
        Dict con detalles de la hipoteca
    """
    down_payment = price * (down_payment_pct / 100)
    loan_amount = price - down_payment
    
    # Calcular cuota mensual (fórmula francesa)
    monthly_rate = (interest_rate / 100) / 12
    n_payments = years * 12
    
    if monthly_rate > 0:
        monthly_payment = loan_amount * (
            monthly_rate * (1 + monthly_rate) ** n_payments
        ) / ((1 + monthly_rate) ** n_payments - 1)
    else:
        monthly_payment = loan_amount / n_payments
    
    total_paid = monthly_payment * n_payments
    total_interest = total_paid - loan_amount
    
    return {
        "price": price,
        "down_payment": down_payment,
        "down_payment_pct": down_payment_pct,
        "loan_amount": loan_amount,
        "interest_rate": interest_rate,
        "years": years,
        "monthly_payment": round(monthly_payment, 2),
        "total_paid": round(total_paid, 2),
        "total_interest": round(total_interest, 2),
    }


def format_mortgage_for_chat(mortgage: dict) -> str:
    """Formatea un cálculo de hipoteca para enviar por chat."""
    return (
        f"💰 *Simulación de Hipoteca*\n\n"
        f"🏷️ Precio: {mortgage['price']:,.0f}€\n"
        f"💵 Entrada ({mortgage['down_payment_pct']:.0f}%): {mortgage['down_payment']:,.0f}€\n"
        f"🏦 Importe financiado: {mortgage['loan_amount']:,.0f}€\n"
        f"📊 Tipo de interés: {mortgage['interest_rate']}% fijo\n"
        f"📅 Plazo: {mortgage['years']} años\n\n"
        f"📌 *Cuota mensual: {mortgage['monthly_payment']:,.0f}€/mes*\n\n"
        f"_⚠️ Esta es una estimación orientativa. "
        f"El tipo de interés y las condiciones reales dependerán de tu banco y perfil financiero._"
    )


def build_property_context(properties: list[dict]) -> str:
    """
    Construye contexto de propiedades para inyectar en el system prompt del LLM.
    Así el agente puede responder preguntas específicas sobre propiedades.
    """
    if not properties:
        return "No hay propiedades disponibles que coincidan con los criterios."
    
    context_parts = ["## Propiedades Disponibles\n"]
    
    for prop in properties:
        features = prop.get("features") or {}
        context_parts.append(
            f"- **{prop.get('title', 'Sin título')}** (Ref: {prop.get('reference', 'N/A')})\n"
            f"  Tipo: {prop.get('property_type', 'N/A')} | Operación: {prop.get('operation', 'N/A')}\n"
            f"  Precio: {prop.get('price', 0):,.0f}€ | {prop.get('sqm', 0)} m²\n"
            f"  Zona: {prop.get('zone', 'N/A')} | Dirección: {prop.get('address', 'N/A')}\n"
            f"  Habitaciones: {features.get('bedrooms', 'N/A')} | Baños: {features.get('bathrooms', 'N/A')}\n"
            f"  Comunidad: {prop.get('community_fee', 'N/A')}€/mes | IBI: {prop.get('ibi_tax', 'N/A')}€/año\n"
            f"  Descripción: {prop.get('description', 'Sin descripción')}\n"
        )
    
    return "\n".join(context_parts)
