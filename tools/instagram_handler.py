"""
Handler de Instagram DM.
Integración con Meta Graph API para enviar y recibir mensajes de Instagram Direct.

Docs: https://developers.facebook.com/docs/instagram-messaging
"""

import httpx
from config import META_ACCESS_TOKEN, INSTAGRAM_BUSINESS_ID


GRAPH_API_URL = "https://graph.facebook.com/v21.0"


# ─────────────────────────────────────────────
# Enviar mensajes
# ─────────────────────────────────────────────
async def send_instagram_message(
    recipient_id: str,
    text: str,
) -> dict:
    """
    Envía un mensaje de texto por Instagram DM.
    
    Args:
        recipient_id: IGSID (Instagram-scoped ID) del usuario
        text: Mensaje a enviar
    
    Returns:
        Respuesta de la API de Meta
    """
    url = f"{GRAPH_API_URL}/{INSTAGRAM_BUSINESS_ID}/messages"
    
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text},
    }
    
    headers = {
        "Authorization": f"Bearer {META_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        print(f"📸 Instagram DM enviado a {recipient_id}: {text[:50]}...")
        return result


async def send_instagram_image(
    recipient_id: str,
    image_url: str,
) -> dict:
    """Envía una imagen por Instagram DM."""
    url = f"{GRAPH_API_URL}/{INSTAGRAM_BUSINESS_ID}/messages"
    
    payload = {
        "recipient": {"id": recipient_id},
        "message": {
            "attachment": {
                "type": "image",
                "payload": {"url": image_url},
            }
        },
    }
    
    headers = {
        "Authorization": f"Bearer {META_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()


async def send_instagram_quick_replies(
    recipient_id: str,
    text: str,
    options: list[str],
) -> dict:
    """
    Envía un mensaje con opciones rápidas (quick replies).
    Útil para: tipo de propiedad, operación, zona, etc.
    """
    url = f"{GRAPH_API_URL}/{INSTAGRAM_BUSINESS_ID}/messages"
    
    quick_replies = [
        {"content_type": "text", "title": opt, "payload": opt.upper().replace(" ", "_")}
        for opt in options[:13]  # Instagram soporta máximo 13 quick replies
    ]
    
    payload = {
        "recipient": {"id": recipient_id},
        "message": {
            "text": text,
            "quick_replies": quick_replies,
        },
    }
    
    headers = {
        "Authorization": f"Bearer {META_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()


# ─────────────────────────────────────────────
# Parsear webhook
# ─────────────────────────────────────────────
def parse_instagram_webhook(payload: dict) -> list[dict]:
    """
    Parsea el payload del webhook de Instagram Messaging.
    
    Returns:
        Lista de mensajes entrantes. Cada uno tiene:
        - sender_id: IGSID del remitente
        - message_text: Texto del mensaje
        - message_id: ID del mensaje
        - timestamp: Timestamp del mensaje
        - is_echo: Si es un eco de un mensaje enviado por nosotros
    """
    messages = []
    
    for entry in payload.get("entry", []):
        for messaging_event in entry.get("messaging", []):
            sender_id = messaging_event.get("sender", {}).get("id", "")
            
            # Ignorar ecos (mensajes enviados por nosotros mismos)
            message = messaging_event.get("message", {})
            if message.get("is_echo"):
                continue
            
            # Solo procesar mensajes de texto
            text = message.get("text", "")
            if not text:
                # Podría ser un quick_reply
                quick_reply = message.get("quick_reply", {})
                text = quick_reply.get("payload", "")
            
            if text and sender_id:
                messages.append({
                    "sender_id": sender_id,
                    "message_text": text,
                    "message_id": message.get("mid", ""),
                    "timestamp": messaging_event.get("timestamp", ""),
                    "is_echo": False,
                })
    
    return messages


async def get_instagram_user_profile(user_id: str) -> dict:
    """
    Obtiene el perfil de un usuario de Instagram.
    
    Returns:
        Dict con name y profile_pic (si están disponibles).
    """
    url = f"{GRAPH_API_URL}/{user_id}"
    params = {
        "fields": "name,profile_pic",
        "access_token": META_ACCESS_TOKEN,
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            return {
                "name": data.get("name", ""),
                "profile_pic": data.get("profile_pic", ""),
            }
    except Exception as e:
        print(f"⚠️ No se pudo obtener perfil de Instagram {user_id}: {e}")
        return {"name": "", "profile_pic": ""}
