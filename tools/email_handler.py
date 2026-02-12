"""
Handler de Email.
Integración con SendGrid para enviar y recibir emails.

Docs: https://docs.sendgrid.com/api-reference
Inbound Parse: https://docs.sendgrid.com/for-developers/parsing-email/setting-up-the-inbound-parse-webhook
"""

import httpx
from email.utils import parseaddr
from config import SENDGRID_API_KEY, SENDGRID_FROM_EMAIL, COMPANY_NAME, AGENT_NAME


SENDGRID_API_URL = "https://api.sendgrid.com/v3"


# ─────────────────────────────────────────────
# Enviar emails
# ─────────────────────────────────────────────
async def send_email(
    to_email: str,
    subject: str,
    body_text: str,
    body_html: str = None,
) -> dict:
    """
    Envía un email vía SendGrid.
    
    Args:
        to_email: Email del destinatario
        subject: Asunto del email
        body_text: Cuerpo en texto plano
        body_html: Cuerpo en HTML (opcional, si no se pasa se genera del texto)
    
    Returns:
        Respuesta de SendGrid
    """
    if not body_html:
        body_html = _text_to_html(body_text)
    
    payload = {
        "personalizations": [
            {
                "to": [{"email": to_email}],
                "subject": subject,
            }
        ],
        "from": {
            "email": SENDGRID_FROM_EMAIL,
            "name": f"{AGENT_NAME} — {COMPANY_NAME}",
        },
        "content": [
            {"type": "text/plain", "value": body_text},
            {"type": "text/html", "value": body_html},
        ],
    }
    
    headers = {
        "Authorization": f"Bearer {SENDGRID_API_KEY}",
        "Content-Type": "application/json",
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{SENDGRID_API_URL}/mail/send",
            json=payload,
            headers=headers,
        )
        response.raise_for_status()
        print(f"📧 Email enviado a {to_email}: {subject}")
        return {"status": "sent", "to": to_email}


async def send_property_email(
    to_email: str,
    properties: list[dict],
    lead_name: str = None,
) -> dict:
    """
    Envía un email con propiedades recomendadas.
    Formato HTML profesional con datos de cada propiedad.
    """
    greeting = f"Hola {lead_name}" if lead_name else "Hola"
    subject = f"🏠 Propiedades seleccionadas para ti — {COMPANY_NAME}"
    
    # Generar HTML de propiedades
    props_html = ""
    for prop in properties:
        props_html += f"""
        <div style="border:1px solid #e0e0e0; border-radius:8px; padding:16px; margin:12px 0;">
            <h3 style="color:#2c3e50; margin:0 0 8px;">{prop.get('title', 'Propiedad')}</h3>
            <p style="color:#e74c3c; font-size:20px; font-weight:bold; margin:4px 0;">
                {prop.get('price', 0):,.0f}€ {'/ mes' if prop.get('operation') == 'alquiler' else ''}
            </p>
            <p style="color:#666; margin:4px 0;">
                📍 {prop.get('zone', '')} — {prop.get('sqm', 0)} m²
                {f" | {prop.get('features', {}).get('bedrooms', '?')} hab." if prop.get('features', {}).get('bedrooms') else ""}
                {f" | {prop.get('features', {}).get('bathrooms', '?')} baños" if prop.get('features', {}).get('bathrooms') else ""}
            </p>
            <p style="color:#555; margin:8px 0 0;">{prop.get('description', '')[:200]}</p>
            <p style="margin:8px 0 0;"><strong>Ref:</strong> {prop.get('reference', 'N/A')}</p>
        </div>
        """
    
    body_html = f"""
    <div style="font-family:Arial,sans-serif; max-width:600px; margin:0 auto;">
        <div style="background:#2c3e50; color:white; padding:20px; border-radius:8px 8px 0 0;">
            <h1 style="margin:0; font-size:22px;">🏠 {COMPANY_NAME}</h1>
            <p style="margin:4px 0 0; opacity:0.8;">Tu asesora inmobiliaria, {AGENT_NAME}</p>
        </div>
        <div style="padding:20px; background:#f9f9f9;">
            <p>{greeting},</p>
            <p>He seleccionado estas propiedades que podrían interesarte:</p>
            {props_html}
            <p style="margin-top:20px;">
                ¿Te gustaría agendar una visita o más información sobre alguna?
                Responde a este email o escríbeme por WhatsApp. 😊
            </p>
            <p style="color:#888; font-size:12px; margin-top:30px;">
                — {AGENT_NAME}, {COMPANY_NAME}
            </p>
        </div>
    </div>
    """
    
    body_text = f"{greeting},\n\nHe seleccionado estas propiedades para ti:\n\n"
    for prop in properties:
        body_text += f"- {prop.get('title', 'Propiedad')} — {prop.get('price', 0):,.0f}€\n"
        body_text += f"  {prop.get('zone', '')} | {prop.get('sqm', 0)} m²\n\n"
    body_text += f"Responde a este email para más info.\n— {AGENT_NAME}, {COMPANY_NAME}"
    
    return await send_email(to_email, subject, body_text, body_html)


# ─────────────────────────────────────────────
# Parsear emails entrantes (SendGrid Inbound Parse)
# ─────────────────────────────────────────────
def parse_inbound_email(form_data: dict) -> dict:
    """
    Parsea un email entrante del webhook de SendGrid Inbound Parse.
    
    SendGrid envía el email como form-data con estos campos:
    - from: Remitente
    - to: Destinatario
    - subject: Asunto
    - text: Cuerpo en texto plano
    - html: Cuerpo en HTML
    
    Returns:
        Dict con los campos parseados
    """
    # Extraer email limpio del campo "from"
    raw_from = form_data.get("from", "")
    from_name, from_email = parseaddr(raw_from)
    
    # Extraer texto del cuerpo (preferir text sobre html)
    body = form_data.get("text", "")
    if not body:
        body = form_data.get("html", "")
        body = _strip_html(body)
    
    # Limpiar firmas y texto citado
    body = _clean_email_body(body)
    
    return {
        "from_email": from_email,
        "from_name": from_name,
        "to": form_data.get("to", ""),
        "subject": form_data.get("subject", ""),
        "body": body.strip(),
        "raw_text": form_data.get("text", ""),
        "has_attachments": bool(form_data.get("attachments", "")),
    }


# ─────────────────────────────────────────────
# Utilidades
# ─────────────────────────────────────────────
def _text_to_html(text: str) -> str:
    """Convierte texto plano a HTML básico."""
    lines = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    paragraphs = lines.split("\n\n")
    html_parts = []
    for p in paragraphs:
        p = p.replace("\n", "<br>")
        html_parts.append(f"<p>{p}</p>")
    
    return f"""
    <div style="font-family:Arial,sans-serif; max-width:600px; margin:0 auto; padding:20px;">
        <div style="background:#2c3e50; color:white; padding:16px; border-radius:8px 8px 0 0;">
            <strong>🏠 {COMPANY_NAME}</strong>
        </div>
        <div style="padding:16px; background:#f9f9f9; border-radius:0 0 8px 8px;">
            {"".join(html_parts)}
            <p style="color:#888; font-size:12px; margin-top:20px;">— {AGENT_NAME}, {COMPANY_NAME}</p>
        </div>
    </div>
    """


def _strip_html(html: str) -> str:
    """Elimina tags HTML básicos para obtener texto plano."""
    import re
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"<p[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    return text.strip()


def _clean_email_body(text: str) -> str:
    """
    Limpia el cuerpo del email:
    - Elimina texto citado (líneas que empiezan con >)
    - Corta en líneas como "On ... wrote:" o "El ... escribió:"
    - Elimina firmas comunes
    """
    lines = text.split("\n")
    clean_lines = []
    
    for line in lines:
        stripped = line.strip()
        
        # Cortar en texto citado
        if stripped.startswith(">"):
            break
        
        # Cortar en "On ... wrote:" pattern
        if any(pattern in stripped.lower() for pattern in [
            "on ", "wrote:", "escribió:", "-----original",
            "---------- forwarded", "de:", "enviado:",
        ]):
            break
        
        # Cortar en firmas comunes
        if stripped == "--" or stripped == "---":
            break
        
        clean_lines.append(line)
    
    return "\n".join(clean_lines)
