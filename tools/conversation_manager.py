"""
Gestor de conversaciones.
Almacena, recupera y resume el historial de conversaciones por lead.
"""

from datetime import datetime
from models.database_models import Message, Conversation, ChannelType
from tools.database import (
    get_conversation_by_lead,
    upsert_conversation,
)


# ─────────────────────────────────────────────
# Cache en memoria para conversaciones activas
# ─────────────────────────────────────────────
_active_conversations: dict[str, Conversation] = {}

# Máximo de mensajes a mantener en contexto para el LLM
MAX_CONTEXT_MESSAGES = 20


async def get_or_create_conversation(
    lead_id: str,
    channel: ChannelType = ChannelType.WHATSAPP,
) -> Conversation:
    """
    Obtiene la conversación activa de un lead o crea una nueva.
    Primero busca en cache, luego en la base de datos.
    """
    # Buscar en cache
    cache_key = f"{lead_id}_{channel.value}"
    if cache_key in _active_conversations:
        return _active_conversations[cache_key]

    # Buscar en base de datos
    conv = await get_conversation_by_lead(lead_id, channel.value)
    
    if conv:
        conversation = Conversation(
            id=conv["id"],
            lead_id=lead_id,
            channel=channel,
            messages=[Message(**m) for m in (conv.get("messages") or [])],
            summary=conv.get("summary"),
            updated_at=conv.get("updated_at"),
        )
    else:
        conversation = Conversation(
            lead_id=lead_id,
            channel=channel,
            messages=[],
        )
    
    _active_conversations[cache_key] = conversation
    return conversation


async def add_message(
    lead_id: str,
    role: str,
    content: str,
    channel: ChannelType = ChannelType.WHATSAPP,
) -> Conversation:
    """
    Añade un mensaje a la conversación del lead.
    Guarda en cache y persiste en base de datos.
    """
    conversation = await get_or_create_conversation(lead_id, channel)
    
    message = Message(
        role=role,
        content=content,
        timestamp=datetime.now(),
        channel=channel,
    )
    
    conversation.messages.append(message)
    conversation.updated_at = datetime.now()
    
    # Persistir en base de datos
    await _save_conversation(conversation)
    
    return conversation


def get_context_messages(conversation: Conversation) -> list[dict]:
    """
    Obtiene los mensajes recientes formateados para el LLM.
    Limita al máximo de contexto para no exceder el context window.
    """
    recent = conversation.messages[-MAX_CONTEXT_MESSAGES:]
    
    return [
        {"role": msg.role, "content": msg.content}
        for msg in recent
    ]


def get_full_conversation_text(conversation: Conversation) -> str:
    """
    Devuelve toda la conversación como texto plano.
    Útil para el extractor de información de leads.
    """
    lines = []
    for msg in conversation.messages:
        speaker = "CLIENTE" if msg.role == "user" else "AGENTE"
        lines.append(f"{speaker}: {msg.content}")
    return "\n".join(lines)


async def _save_conversation(conversation: Conversation) -> None:
    """Persiste la conversación en Supabase."""
    data = {
        "lead_id": conversation.lead_id,
        "channel": conversation.channel.value,
        "messages": [
            {
                "role": m.role,
                "content": m.content,
                "timestamp": m.timestamp.isoformat(),
                "channel": m.channel.value if m.channel else None,
            }
            for m in conversation.messages
        ],
        "summary": conversation.summary,
        "updated_at": datetime.now().isoformat(),
    }
    
    result = await upsert_conversation(conversation.id, data)
    
    # Actualizar el ID si es nueva
    if result and not conversation.id:
        conversation.id = result.get("id")


async def clear_cache(lead_id: str = None):
    """Limpia el cache de conversaciones."""
    if lead_id:
        keys_to_remove = [k for k in _active_conversations if k.startswith(lead_id)]
        for key in keys_to_remove:
            del _active_conversations[key]
    else:
        _active_conversations.clear()
