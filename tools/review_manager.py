"""
Gestor de Reseñas (Google Business Profile).
Solicita, monitorea y responde reseñas automáticamente.

Docs: https://developers.google.com/my-business/reference/rest
"""

import os
import httpx
from datetime import datetime
from tools.ai_engine import generate_response
from tools.whatsapp_handler import send_whatsapp_message
from tools.email_handler import send_email
from config import AGENT_NAME, COMPANY_NAME


# ─────────────────────────────────────────────
# Configuración
# ─────────────────────────────────────────────
GOOGLE_BUSINESS_ACCOUNT_ID = os.getenv("GOOGLE_BUSINESS_ACCOUNT_ID", "")
GOOGLE_BUSINESS_LOCATION_ID = os.getenv("GOOGLE_BUSINESS_LOCATION_ID", "")
GOOGLE_BUSINESS_API_URL = "https://mybusiness.googleapis.com/v4"

# Umbral de tiempo tras visita para solicitar reseña
REVIEW_REQUEST_DELAY_DAYS = 3


# ─────────────────────────────────────────────
# Solicitar reseñas
# ─────────────────────────────────────────────
async def request_review(
    phone: str = None,
    email: str = None,
    name: str = "",
    property_title: str = "",
    review_url: str = "",
):
    """
    Solicita una reseña al cliente después de una visita exitosa.
    Se envía por WhatsApp y/o email según los datos disponibles.
    
    Args:
        phone: Teléfono del cliente
        email: Email del cliente
        name: Nombre del cliente
        property_title: Propiedad que visitó
        review_url: URL directa para dejar reseña en Google
    """
    greeting = f"¡Hola {name}!" if name else "¡Hola!"
    
    # Mensaje WhatsApp
    if phone and not phone.startswith("ig:"):
        whatsapp_msg = (
            f"{greeting} 😊\n\n"
            f"Espero que la experiencia con {COMPANY_NAME} haya sido positiva. "
            f"Tu opinión es muy importante para nosotros.\n\n"
            f"¿Podrías dejarnos una reseña rápida? Solo toma 1 minuto ⭐\n\n"
        )
        if review_url:
            whatsapp_msg += f"👉 {review_url}\n\n"
        whatsapp_msg += f"¡Muchas gracias!\n— {AGENT_NAME}, {COMPANY_NAME}"
        
        try:
            await send_whatsapp_message(to=f"whatsapp:{phone}", body=whatsapp_msg)
            print(f"✅ Solicitud de reseña WhatsApp → {phone}")
        except Exception as e:
            print(f"⚠️ Error solicitando reseña por WhatsApp: {e}")
    
    # Mensaje Email
    if email:
        email_body = (
            f"{greeting}\n\n"
            f"Esperamos que tu experiencia buscando propiedad con {COMPANY_NAME} "
            f"haya sido satisfactoria.\n\n"
            f"Nos encantaría conocer tu opinión. ¿Podrías dedicarnos un minuto "
            f"para dejar una reseña?\n\n"
        )
        if review_url:
            email_body += f"Enlace directo: {review_url}\n\n"
        email_body += (
            f"Tu feedback nos ayuda a seguir mejorando.\n\n"
            f"Un saludo,\n"
            f"{AGENT_NAME}\n"
            f"{COMPANY_NAME}"
        )
        
        try:
            await send_email(
                to_email=email,
                subject=f"⭐ ¿Nos dejas tu opinión? — {COMPANY_NAME}",
                body_text=email_body,
            )
            print(f"✅ Solicitud de reseña Email → {email}")
        except Exception as e:
            print(f"⚠️ Error solicitando reseña por email: {e}")


# ─────────────────────────────────────────────
# Leer reseñas de Google Business
# ─────────────────────────────────────────────
async def get_reviews(access_token: str, limit: int = 50) -> list[dict]:
    """
    Obtiene las reseñas de Google Business Profile.
    
    Returns:
        Lista de reseñas con: reviewer, rating, comment, date, reply
    """
    if not GOOGLE_BUSINESS_ACCOUNT_ID or not GOOGLE_BUSINESS_LOCATION_ID:
        print("⚠️ Google Business no configurado")
        return []
    
    url = (
        f"{GOOGLE_BUSINESS_API_URL}/accounts/{GOOGLE_BUSINESS_ACCOUNT_ID}"
        f"/locations/{GOOGLE_BUSINESS_LOCATION_ID}/reviews"
    )
    
    headers = {
        "Authorization": f"Bearer {access_token}",
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=headers,
                params={"pageSize": limit},
            )
            response.raise_for_status()
            data = response.json()
            
            reviews = []
            for review in data.get("reviews", []):
                reviews.append({
                    "id": review.get("reviewId", ""),
                    "reviewer": review.get("reviewer", {}).get("displayName", ""),
                    "rating": review.get("starRating", ""),
                    "comment": review.get("comment", ""),
                    "date": review.get("createTime", ""),
                    "has_reply": bool(review.get("reviewReply")),
                    "reply": review.get("reviewReply", {}).get("comment", ""),
                })
            
            return reviews
    except Exception as e:
        print(f"⚠️ Error obteniendo reseñas: {e}")
        return []


async def get_pending_reviews(access_token: str) -> list[dict]:
    """Obtiene reseñas que aún no tienen respuesta."""
    all_reviews = await get_reviews(access_token)
    return [r for r in all_reviews if not r["has_reply"]]


# ─────────────────────────────────────────────
# Responder reseñas automáticamente
# ─────────────────────────────────────────────
async def generate_review_reply(
    reviewer_name: str,
    rating: str,
    comment: str,
) -> str:
    """
    Genera una respuesta personalizada para una reseña usando IA.
    
    Args:
        reviewer_name: Nombre de quien reseñó
        rating: Puntuación (ONE_STAR a FIVE_STAR)
        comment: Texto de la reseña
    
    Returns:
        Texto de respuesta generada por IA
    """
    rating_map = {
        "ONE_STAR": 1, "TWO_STARS": 2, "THREE_STARS": 3,
        "FOUR_STARS": 4, "FIVE_STARS": 5,
    }
    stars = rating_map.get(rating, 0)
    
    prompt = (
        f"Genera una respuesta profesional y cálida para esta reseña de Google "
        f"de {COMPANY_NAME}:\n\n"
        f"Nombre: {reviewer_name}\n"
        f"Puntuación: {stars}/5 estrellas\n"
        f"Comentario: {comment or '(sin comentario)'}\n\n"
        f"Reglas:\n"
        f"- Si es positiva (4-5★): agradece y menciona que fue un placer ayudarle\n"
        f"- Si es neutral (3★): agradece el feedback y ofrece mejorar\n"
        f"- Si es negativa (1-2★): sé empático, pide disculpas y ofrece resolver en privado\n"
        f"- Firma como el equipo de {COMPANY_NAME}\n"
        f"- Máximo 150 palabras\n"
        f"- No uses emojis excesivos, máximo 1-2\n"
        f"- Tono profesional pero cercano"
    )
    
    reply = await generate_response(
        user_message=prompt,
        additional_context="Estás respondiendo una reseña de Google Business.",
    )
    
    return reply


async def post_review_reply(
    access_token: str,
    review_id: str,
    reply_text: str,
) -> bool:
    """Publica una respuesta a una reseña en Google Business."""
    if not GOOGLE_BUSINESS_ACCOUNT_ID or not GOOGLE_BUSINESS_LOCATION_ID:
        return False
    
    url = (
        f"{GOOGLE_BUSINESS_API_URL}/accounts/{GOOGLE_BUSINESS_ACCOUNT_ID}"
        f"/locations/{GOOGLE_BUSINESS_LOCATION_ID}/reviews/{review_id}/reply"
    )
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.put(
                url,
                headers=headers,
                json={"comment": reply_text},
            )
            response.raise_for_status()
            print(f"✅ Respuesta publicada en reseña {review_id}")
            return True
    except Exception as e:
        print(f"❌ Error publicando respuesta: {e}")
        return False


async def auto_reply_pending_reviews(access_token: str) -> dict:
    """
    Responde automáticamente todas las reseñas pendientes.
    Genera respuestas con IA y las publica.
    """
    pending = await get_pending_reviews(access_token)
    results = {"replied": 0, "errors": 0}
    
    for review in pending:
        try:
            reply = await generate_review_reply(
                reviewer_name=review["reviewer"],
                rating=review["rating"],
                comment=review["comment"],
            )
            
            success = await post_review_reply(access_token, review["id"], reply)
            
            if success:
                results["replied"] += 1
            else:
                results["errors"] += 1
                
        except Exception as e:
            print(f"⚠️ Error respondiendo reseña {review['id']}: {e}")
            results["errors"] += 1
    
    print(f"📊 Reseñas: {results['replied']} respondidas, {results['errors']} errores")
    return results


# ─────────────────────────────────────────────
# Análisis de reputación
# ─────────────────────────────────────────────
def analyze_reviews(reviews: list[dict]) -> dict:
    """
    Analiza las reseñas para generar métricas de reputación.
    
    Returns:
        Dict con métricas: average_rating, total, distribution, sentiment
    """
    if not reviews:
        return {"average_rating": 0, "total": 0, "distribution": {}}
    
    rating_map = {
        "ONE_STAR": 1, "TWO_STARS": 2, "THREE_STARS": 3,
        "FOUR_STARS": 4, "FIVE_STARS": 5,
    }
    
    ratings = [rating_map.get(r["rating"], 0) for r in reviews]
    distribution = {i: ratings.count(i) for i in range(1, 6)}
    
    return {
        "average_rating": round(sum(ratings) / len(ratings), 1),
        "total": len(reviews),
        "distribution": distribution,
        "positive": sum(1 for r in ratings if r >= 4),
        "neutral": sum(1 for r in ratings if r == 3),
        "negative": sum(1 for r in ratings if r <= 2),
        "reply_rate": sum(1 for r in reviews if r["has_reply"]) / len(reviews) * 100,
    }
