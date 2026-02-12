"""
Handler de WhatsApp via Twilio.
Recibe y envía mensajes a través de la API de Twilio.
"""

from twilio.rest import Client
from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER


# ─────────────────────────────────────────────
# Cliente Twilio
# ─────────────────────────────────────────────
_twilio_client: Client | None = None


def get_twilio_client() -> Client:
    """Obtiene o crea el cliente de Twilio."""
    global _twilio_client
    if _twilio_client is None:
        if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
            raise RuntimeError("❌ TWILIO_ACCOUNT_SID y TWILIO_AUTH_TOKEN no configurados en .env")
        _twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    return _twilio_client


async def send_whatsapp_message(to: str, body: str, media_url: str = None) -> dict:
    """
    Envía un mensaje de WhatsApp.
    
    Args:
        to: Número del destinatario (formato: whatsapp:+34XXXXXXXXX)
        body: Texto del mensaje
        media_url: URL de imagen/documento (opcional)
    
    Returns:
        Dict con info del mensaje enviado
    """
    try:
        client = get_twilio_client()
        
        # Asegurar formato WhatsApp
        if not to.startswith("whatsapp:"):
            to = f"whatsapp:{to}"
        
        from_number = TWILIO_WHATSAPP_NUMBER
        if not from_number.startswith("whatsapp:"):
            from_number = f"whatsapp:{from_number}"
        
        kwargs = {
            "body": body,
            "from_": from_number,
            "to": to,
        }
        
        if media_url:
            kwargs["media_url"] = [media_url]
        
        message = client.messages.create(**kwargs)
        
        print(f"📤 WhatsApp enviado a {to}: {body[:50]}...")
        
        return {
            "sid": message.sid,
            "status": message.status,
            "to": to,
            "body": body[:100],
        }
    
    except Exception as e:
        print(f"❌ Error enviando WhatsApp a {to}: {e}")
        return {"error": str(e)}


def parse_incoming_webhook(form_data: dict) -> dict:
    """
    Parsea los datos del webhook de Twilio.
    
    Args:
        form_data: Datos del formulario recibido en el webhook
    
    Returns:
        Dict con los campos relevantes del mensaje
    """
    return {
        "from": form_data.get("From", ""),
        "to": form_data.get("To", ""),
        "body": form_data.get("Body", "").strip(),
        "message_sid": form_data.get("MessageSid", ""),
        "num_media": int(form_data.get("NumMedia", 0)),
        "media_urls": [
            form_data.get(f"MediaUrl{i}")
            for i in range(int(form_data.get("NumMedia", 0)))
        ],
        "profile_name": form_data.get("ProfileName", ""),
        "phone": form_data.get("From", "").replace("whatsapp:", ""),
    }


def get_phone_number(whatsapp_id: str) -> str:
    """Extrae el número de teléfono del formato WhatsApp de Twilio."""
    return whatsapp_id.replace("whatsapp:", "")
