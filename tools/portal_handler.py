"""
Handler de Portales Inmobiliarios.
Recibe leads desde Idealista, Fotocasa, Habitaclia y otros portales
via webhook o email parsing.
"""

from datetime import datetime
from typing import Optional


# ─────────────────────────────────────────────
# Parsers por portal
# ─────────────────────────────────────────────
def parse_idealista_lead(payload: dict) -> dict:
    """
    Parsea un lead de Idealista.
    Idealista puede enviar leads via email o API webhook.
    """
    return {
        "source": "idealista",
        "name": payload.get("name", payload.get("nombre", "")),
        "phone": payload.get("phone", payload.get("telefono", "")),
        "email": payload.get("email", ""),
        "message": payload.get("message", payload.get("mensaje", "")),
        "property_reference": payload.get("property_ref", payload.get("referencia", "")),
        "property_url": payload.get("property_url", payload.get("url_inmueble", "")),
        "timestamp": payload.get("timestamp", datetime.now().isoformat()),
    }


def parse_fotocasa_lead(payload: dict) -> dict:
    """Parsea un lead de Fotocasa."""
    return {
        "source": "fotocasa",
        "name": payload.get("contactName", payload.get("nombre", "")),
        "phone": payload.get("contactPhone", payload.get("telefono", "")),
        "email": payload.get("contactEmail", payload.get("email", "")),
        "message": payload.get("contactMessage", payload.get("mensaje", "")),
        "property_reference": payload.get("propertyReference", ""),
        "property_url": payload.get("propertyUrl", ""),
        "timestamp": payload.get("date", datetime.now().isoformat()),
    }


def parse_habitaclia_lead(payload: dict) -> dict:
    """Parsea un lead de Habitaclia."""
    return {
        "source": "habitaclia",
        "name": payload.get("nombre", payload.get("name", "")),
        "phone": payload.get("telefono", payload.get("phone", "")),
        "email": payload.get("email", ""),
        "message": payload.get("comentario", payload.get("message", "")),
        "property_reference": payload.get("referencia", ""),
        "property_url": payload.get("url", ""),
        "timestamp": datetime.now().isoformat(),
    }


def parse_generic_portal_lead(payload: dict) -> dict:
    """
    Parser genérico para portales que no tienen formato específico.
    Intenta mapear campos comunes.
    """
    # Buscar nombre en campos habituales
    name = (
        payload.get("name", "")
        or payload.get("nombre", "")
        or payload.get("contactName", "")
        or payload.get("lead_name", "")
    )
    
    phone = (
        payload.get("phone", "")
        or payload.get("telefono", "")
        or payload.get("contactPhone", "")
        or payload.get("mobile", "")
    )
    
    email = (
        payload.get("email", "")
        or payload.get("contactEmail", "")
        or payload.get("mail", "")
    )
    
    message = (
        payload.get("message", "")
        or payload.get("mensaje", "")
        or payload.get("comments", "")
        or payload.get("body", "")
    )
    
    return {
        "source": payload.get("source", payload.get("portal", "desconocido")),
        "name": name,
        "phone": phone,
        "email": email,
        "message": message,
        "property_reference": payload.get("property_ref", payload.get("referencia", "")),
        "property_url": payload.get("property_url", payload.get("url", "")),
        "timestamp": datetime.now().isoformat(),
    }


# ─────────────────────────────────────────────
# Parser de emails de portales
# ─────────────────────────────────────────────
def parse_portal_email(subject: str, body: str) -> Optional[dict]:
    """
    Parsea un email de notificación de portal inmobiliario.
    Detecta el portal por el asunto y extrae los datos.
    """
    subject_lower = subject.lower()
    
    # Detectar portal por asunto
    if "idealista" in subject_lower:
        return _extract_from_email_body(body, "idealista")
    elif "fotocasa" in subject_lower:
        return _extract_from_email_body(body, "fotocasa")
    elif "habitaclia" in subject_lower:
        return _extract_from_email_body(body, "habitaclia")
    elif "pisos.com" in subject_lower:
        return _extract_from_email_body(body, "pisos.com")
    elif any(kw in subject_lower for kw in ["contacto", "lead", "inmueble", "consulta"]):
        return _extract_from_email_body(body, "portal_generico")
    
    return None


def _extract_from_email_body(body: str, source: str) -> dict:
    """Extrae datos de contacto del cuerpo de un email de portal."""
    import re
    
    # Buscar email
    email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.]+', body)
    email = email_match.group(0) if email_match else ""
    
    # Buscar teléfono español
    phone_match = re.search(r'(?:\+34|0034)?[\s.-]?[6789]\d{2}[\s.-]?\d{3}[\s.-]?\d{3}', body)
    phone = re.sub(r'[\s.-]', '', phone_match.group(0)) if phone_match else ""
    
    # Buscar nombre (patrones comunes en emails de portales)
    name = ""
    for pattern in [
        r'(?:Nombre|Name|Cliente):\s*(.+)',
        r'(?:De|From):\s*([A-ZÁÉÍÓÚ][a-záéíóú]+ [A-ZÁÉÍÓÚ][a-záéíóú]+)',
    ]:
        name_match = re.search(pattern, body, re.IGNORECASE)
        if name_match:
            name = name_match.group(1).strip()
            break
    
    # Buscar referencia de propiedad
    ref_match = re.search(r'(?:Ref|Referencia|REF)[.:\s-]*([A-Z0-9-]+)', body, re.IGNORECASE)
    reference = ref_match.group(1) if ref_match else ""
    
    # Extraer mensaje/comentario
    message = ""
    for pattern in [
        r'(?:Mensaje|Comentario|Message):\s*(.+?)(?:\n\n|\Z)',
        r'(?:Consulta|Interesado en):\s*(.+?)(?:\n\n|\Z)',
    ]:
        msg_match = re.search(pattern, body, re.IGNORECASE | re.DOTALL)
        if msg_match:
            message = msg_match.group(1).strip()
            break
    
    if not message:
        # Usar las primeras líneas no vacías como mensaje
        lines = [l.strip() for l in body.split("\n") if l.strip() and not l.strip().startswith(("--", "___"))]
        message = " ".join(lines[:3])
    
    return {
        "source": source,
        "name": name,
        "phone": phone,
        "email": email,
        "message": message,
        "property_reference": reference,
        "property_url": "",
        "timestamp": datetime.now().isoformat(),
    }


# ─────────────────────────────────────────────
# Router principal
# ─────────────────────────────────────────────
PORTAL_PARSERS = {
    "idealista": parse_idealista_lead,
    "fotocasa": parse_fotocasa_lead,
    "habitaclia": parse_habitaclia_lead,
}


def parse_portal_lead(payload: dict) -> dict:
    """
    Detecta el portal y parsea el lead automáticamente.
    Si no reconoce el portal, usa el parser genérico.
    """
    source = (
        payload.get("source", "")
        or payload.get("portal", "")
        or payload.get("origin", "")
    ).lower()
    
    parser = PORTAL_PARSERS.get(source, parse_generic_portal_lead)
    return parser(payload)
