"""
Motor de IA Multi-LLM para el Agente Inmobiliario.
Soporta OpenAI (GPT-4o), Google Gemini y Anthropic Claude.
Incluye function calling para que el agente ejecute acciones.
"""

import asyncio
import json
from openai import AsyncOpenAI
from config import (
    LLM_PROVIDER,
    OPENAI_API_KEY, OPENAI_MODEL,
    GEMINI_API_KEY, GEMINI_MODEL,
    ANTHROPIC_API_KEY, ANTHROPIC_MODEL,
    SYSTEM_PROMPT,
)


# ─────────────────────────────────────────────
# Inicialización de clientes
# ─────────────────────────────────────────────
def _get_openai_client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=OPENAI_API_KEY)


def _get_gemini_client() -> AsyncOpenAI:
    """Gemini a través de la API compatible con OpenAI."""
    return AsyncOpenAI(
        api_key=GEMINI_API_KEY,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )


def _get_model() -> str:
    """Devuelve el nombre del modelo según el proveedor configurado."""
    models = {
        "openai": OPENAI_MODEL,
        "gemini": GEMINI_MODEL,
        "anthropic": ANTHROPIC_MODEL,
    }
    return models.get(LLM_PROVIDER, OPENAI_MODEL)


# ─────────────────────────────────────────────
# Definiciones de Tools (Function Calling)
# ─────────────────────────────────────────────
AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_properties",
            "description": "Busca propiedades disponibles que coincidan con los criterios del cliente. Úsalo cuando el cliente describe lo que busca.",
            "parameters": {
                "type": "object",
                "properties": {
                    "zone": {
                        "type": "string",
                        "description": "Zona o barrio donde busca (ej: 'Centro', 'Nervión', 'Triana')",
                    },
                    "property_type": {
                        "type": "string",
                        "enum": ["piso", "casa", "chalet", "ático", "dúplex", "estudio", "local"],
                        "description": "Tipo de inmueble",
                    },
                    "max_price": {
                        "type": "number",
                        "description": "Presupuesto máximo en euros",
                    },
                    "bedrooms": {
                        "type": "integer",
                        "description": "Número mínimo de habitaciones",
                    },
                    "operation": {
                        "type": "string",
                        "enum": ["comprar", "alquilar"],
                        "description": "Tipo de operación",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_property_details",
            "description": "Obtiene los detalles completos de una propiedad específica por su referencia. Úsalo cuando el cliente pide más info sobre un inmueble.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reference": {
                        "type": "string",
                        "description": "Referencia de la propiedad (ej: 'REF-001', 'REF-015')",
                    },
                },
                "required": ["reference"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "schedule_visit",
            "description": "Agenda una visita a una propiedad. Úsalo cuando el cliente quiere ver un inmueble y da una fecha/hora.",
            "parameters": {
                "type": "object",
                "properties": {
                    "property_reference": {
                        "type": "string",
                        "description": "Referencia de la propiedad a visitar",
                    },
                    "preferred_date": {
                        "type": "string",
                        "description": "Fecha preferida en formato YYYY-MM-DD",
                    },
                    "preferred_time": {
                        "type": "string",
                        "description": "Hora preferida en formato HH:MM",
                    },
                    "client_name": {
                        "type": "string",
                        "description": "Nombre del cliente",
                    },
                    "client_phone": {
                        "type": "string",
                        "description": "Teléfono del cliente",
                    },
                },
                "required": ["property_reference", "preferred_date", "preferred_time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_availability",
            "description": "Consulta los horarios disponibles para agendar una visita en una fecha concreta.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Fecha a consultar en formato YYYY-MM-DD",
                    },
                },
                "required": ["date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_mortgage",
            "description": "Calcula la hipoteca aproximada para una propiedad. Úsalo cuando el cliente pregunta por cuotas mensuales o financiación.",
            "parameters": {
                "type": "object",
                "properties": {
                    "price": {
                        "type": "number",
                        "description": "Precio del inmueble en euros",
                    },
                    "down_payment_percent": {
                        "type": "number",
                        "description": "Porcentaje de entrada (por defecto 20)",
                    },
                    "years": {
                        "type": "integer",
                        "description": "Años de la hipoteca (por defecto 30)",
                    },
                    "interest_rate": {
                        "type": "number",
                        "description": "Tipo de interés anual (por defecto 3.5)",
                    },
                },
                "required": ["price"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "transfer_to_human",
            "description": "Transfiere la conversación a un agente humano. Úsalo SOLO cuando: el cliente lo pide explícitamente, quiere negociar/hacer oferta, tiene una queja, o el caso es muy complejo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "enum": ["solicitud_directa", "negociacion", "queja_cliente", "urgente", "otro"],
                        "description": "Motivo de la derivación",
                    },
                    "summary": {
                        "type": "string",
                        "description": "Breve resumen de la conversación para el agente humano",
                    },
                },
                "required": ["reason", "summary"],
            },
        },
    },
]


# ─────────────────────────────────────────────
# Ejecutor de function calls
# ─────────────────────────────────────────────
async def _execute_tool_call(name: str, arguments: dict, lead_context: dict = None) -> str:
    """
    Ejecuta una tool call del LLM y devuelve el resultado como string.
    """
    lead_context = lead_context or {}
    
    if name == "search_properties":
        from tools.property_manager import search_properties_by_criteria, format_property_for_chat
        
        results = await search_properties_by_criteria(
            zone=arguments.get("zone"),
            property_type=arguments.get("property_type"),
            max_price=arguments.get("max_price"),
            bedrooms=arguments.get("bedrooms"),
            operation=arguments.get("operation"),
            limit=5,
        )
        
        if not results:
            return "No se encontraron propiedades con esos criterios. Prueba con criterios diferentes."
        
        output = f"Se encontraron {len(results)} propiedades:\n\n"
        for prop in results:
            output += format_property_for_chat(prop) + "\n"
        return output
    
    elif name == "get_property_details":
        from tools.property_manager import get_property_by_reference, format_property_for_chat
        
        prop = await get_property_by_reference(arguments["reference"])
        if not prop:
            return f"No se encontró la propiedad con referencia {arguments['reference']}."
        return format_property_for_chat(prop)
    
    elif name == "schedule_visit":
        from tools.scheduler import schedule_visit
        from datetime import datetime
        
        date_str = arguments.get("preferred_date", "")
        time_str = arguments.get("preferred_time", "")
        prop_ref = arguments.get("property_reference", "")
        
        try:
            visit_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        except ValueError:
            return f"Formato de fecha/hora no válido. Usa YYYY-MM-DD y HH:MM."
        
        client_name = arguments.get("client_name", lead_context.get("name", ""))
        client_phone = arguments.get("client_phone", lead_context.get("phone", ""))
        client_email = lead_context.get("email", "")
        
        result = await schedule_visit(
            lead_name=client_name,
            lead_phone=client_phone,
            lead_email=client_email,
            property_title=f"Propiedad {prop_ref}",
            property_address="",
            visit_datetime=visit_datetime.isoformat(),
        )
        
        if result and result.get("id"):
            return (
                f"✅ Visita agendada correctamente:\n"
                f"📅 Fecha: {date_str}\n"
                f"🕐 Hora: {time_str}\n"
                f"🏠 Propiedad: {prop_ref}\n"
                f"Se enviarán recordatorios automáticos."
            )
        return "No se pudo agendar la visita. Puede que el horario no esté disponible."
    
    elif name == "check_availability":
        from tools.scheduler import get_available_slots, format_available_slots_for_chat
        
        date_str = arguments.get("date", "")
        
        slots = await get_available_slots(date_str)
        if not slots:
            return f"No hay horarios disponibles el {date_str}. Prueba otro día."
        return format_available_slots_for_chat(date_str, slots)
    
    elif name == "calculate_mortgage":
        from tools.property_manager import calculate_mortgage, format_mortgage_for_chat
        
        result = calculate_mortgage(
            price=arguments["price"],
            down_payment_pct=arguments.get("down_payment_percent", 20),
            years=arguments.get("years", 30),
            interest_rate=arguments.get("interest_rate", 3.5),
        )
        return format_mortgage_for_chat(result)
    
    elif name == "transfer_to_human":
        from tools.human_handoff import handoff_to_human, generate_handoff_response
        
        reason = arguments.get("reason", "solicitud_directa")
        summary = arguments.get("summary", "")
        
        await handoff_to_human(
            lead_name=lead_context.get("name", ""),
            lead_phone=lead_context.get("phone", ""),
            lead_email=lead_context.get("email", ""),
            lead_score=lead_context.get("score", 0),
            channel=lead_context.get("channel", "whatsapp"),
            reason=reason,
            conversation_summary=summary,
        )
        
        return generate_handoff_response(reason)
    
    return f"Función {name} no implementada."


# ─────────────────────────────────────────────
# Motor principal (con function calling)
# ─────────────────────────────────────────────
async def generate_response(
    user_message: str,
    conversation_history: list[dict] = None,
    additional_context: str = "",
    lead_context: dict = None,
    enable_tools: bool = True,
) -> str:
    """
    Genera una respuesta del agente inmobiliario.
    Soporta function calling: el LLM puede ejecutar acciones directamente.
    
    Args:
        user_message: Mensaje del usuario
        conversation_history: Lista de mensajes previos
        additional_context: Contexto adicional (info de propiedades, datos del lead)
        lead_context: Datos del lead actual (name, phone, email, score, channel)
        enable_tools: Si True, habilita function calling
    
    Returns:
        Respuesta generada por el modelo
    """
    # Construir system prompt
    system = SYSTEM_PROMPT
    if additional_context:
        system += f"\n\n## Contexto Adicional\n{additional_context}"

    messages = [{"role": "system", "content": system}]
    
    if conversation_history:
        messages.extend(conversation_history)
    
    messages.append({"role": "user", "content": user_message})

    # Generar respuesta según proveedor
    if LLM_PROVIDER == "anthropic":
        return await _generate_anthropic(messages)
    
    # OpenAI / Gemini → soportan function calling
    client = _get_gemini_client() if LLM_PROVIDER == "gemini" else _get_openai_client()
    
    if enable_tools and LLM_PROVIDER in ("openai", "gemini"):
        return await _generate_with_tools(messages, client, lead_context)
    else:
        return await _generate_openai_compatible(messages, client)


async def _generate_with_tools(
    messages: list[dict],
    client: AsyncOpenAI,
    lead_context: dict = None,
    max_tool_rounds: int = 3,
) -> str:
    """
    Genera respuesta con function calling.
    Permite al LLM llamar herramientas y usar los resultados.
    """
    model = _get_model()
    
    for _round in range(max_tool_rounds):
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                tools=AGENT_TOOLS,
                tool_choice="auto",
                temperature=0.7,
                max_tokens=1024,
            )
        except Exception as e:
            error_str = str(e)
            if "429" in error_str:
                await asyncio.sleep(15)
                continue
            print(f"❌ Error con {LLM_PROVIDER}: {e}")
            return "Lo siento, estoy teniendo dificultades técnicas. ¿Podrías intentar de nuevo? 🙏"
        
        choice = response.choices[0]
        
        # Si el modelo quiere llamar herramientas
        if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
            # Añadir el mensaje del asistente con las tool calls
            messages.append(choice.message.model_dump())
            
            # Ejecutar cada tool call
            for tool_call in choice.message.tool_calls:
                func_name = tool_call.function.name
                try:
                    func_args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    func_args = {}
                
                print(f"🔧 Tool call: {func_name}({func_args})")
                
                result = await _execute_tool_call(func_name, func_args, lead_context)
                
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": str(result),
                })
            
            # Continuar el loop para que el modelo procese los resultados
            continue
        
        # Respuesta final sin tool calls
        return choice.message.content or ""
    
    # Si agotamos los rounds, devolver la última respuesta
    return "Estoy procesando tu solicitud. ¿Puedes darme un momento? 🙏"


async def _generate_openai_compatible(
    messages: list[dict],
    client: AsyncOpenAI,
    max_retries: int = 3,
) -> str:
    """Genera respuesta sin function calling (fallback)."""
    model = _get_model()

    for attempt in range(max_retries):
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7,
                max_tokens=1024,
            )
            return response.choices[0].message.content
        except Exception as e:
            error_str = str(e)
            if "429" in error_str and attempt < max_retries - 1:
                wait = (attempt + 1) * 15
                print(f"⏳ Rate limit. Reintentando en {wait}s...")
                await asyncio.sleep(wait)
                continue
            
            print(f"❌ Error con {LLM_PROVIDER} ({model}): {e}")
            return "Lo siento, estoy teniendo dificultades técnicas. ¿Podrías intentar de nuevo? 🙏"


async def _generate_anthropic(messages: list[dict]) -> str:
    """Genera respuesta usando la API de Anthropic."""
    from anthropic import AsyncAnthropic
    client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    model = _get_model()

    system_msg = ""
    chat_messages = []
    
    for msg in messages:
        if msg["role"] == "system":
            system_msg += msg["content"] + "\n"
        else:
            chat_messages.append(msg)

    try:
        response = await client.messages.create(
            model=model,
            system=system_msg.strip(),
            messages=chat_messages,
            max_tokens=1024,
            temperature=0.7,
        )
        return response.content[0].text
    except Exception as e:
        print(f"❌ Error con Anthropic ({model}): {e}")
        return "Lo siento, estoy teniendo dificultades técnicas. ¿Podrías intentar de nuevo? 🙏"


async def extract_lead_info(conversation_text: str) -> dict:
    """
    Analiza una conversación y extrae información de cualificación del lead.
    Usa el LLM para entender el contexto y extraer datos estructurados.
    
    Returns:
        Dict con campos extraídos: operation, property_type, zone, budget, urgency, etc.
    """
    extraction_prompt = """Analiza la siguiente conversación con un cliente inmobiliario y extrae la información disponible.

Responde SOLO con un JSON válido con estos campos (usa null si no se mencionó):
{
    "operation": "comprar|alquilar|vender|null",
    "property_type": "piso|casa|chalet|ático|dúplex|estudio|local|oficina|terreno|null",
    "zone": "zona mencionada o null",
    "min_budget": número o null,
    "max_budget": número o null,
    "bedrooms": número o null,
    "bathrooms": número o null,
    "min_sqm": número o null,
    "parking": true|false|null,
    "urgency": "inmediata|1-3 meses|3-6 meses|sin prisa|null",
    "purpose": "primera vivienda|inversión|segunda residencia|null",
    "name": "nombre del cliente o null",
    "interest_level": "bajo|medio|alto|muy alto",
    "wants_visit": true|false,
    "wants_human_agent": true|false,
    "notes": "cualquier otra info relevante"
}

CONVERSACIÓN:
"""

    messages = [
        {"role": "system", "content": "Eres un extractor de datos. Responde SOLO con JSON válido, sin markdown ni explicaciones."},
        {"role": "user", "content": extraction_prompt + conversation_text},
    ]

    if LLM_PROVIDER == "gemini":
        response_text = await _generate_openai_compatible(messages, _get_gemini_client())
    elif LLM_PROVIDER == "anthropic":
        response_text = await _generate_anthropic(messages)
    else:
        response_text = await _generate_openai_compatible(messages, _get_openai_client())

    try:
        cleaned = response_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            cleaned = cleaned.rsplit("```", 1)[0]
        return json.loads(cleaned)
    except json.JSONDecodeError:
        print(f"⚠️ No se pudo parsear la respuesta del LLM: {response_text[:200]}")
        return {}
