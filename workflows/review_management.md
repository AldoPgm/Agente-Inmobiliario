---
description: Flujo de gestión de reseñas de Google Business
---

# Workflow: Gestión de Reseñas

## Solicitar Reseñas

1. **Detectar visita completada** → 3 días después de la visita
2. **Enviar solicitud** → WhatsApp + Email con enlace directo a Google
3. **Mensaje cálido** → Personalizado con nombre y propiedad visitada

## Responder Reseñas (Automático)

1. `job_reviews()` se ejecuta 2x/día (10:30, 18:30)
2. Obtiene reseñas sin respuesta de Google Business API
3. Para cada reseña pendiente:
   - **Positiva (4-5★)**: Agradece y menciona que fue un placer
   - **Neutral (3★)**: Agradece feedback, ofrece mejorar
   - **Negativa (1-2★)**: Empatía, disculpas, resolver en privado
4. Genera respuesta con IA (GPT-4o)
5. Publica la respuesta via API

## Métricas de Reputación

- Rating promedio
- Distribución de estrellas (1-5)
- Tasa de respuesta
- Positivas vs negativas

## Configuración

1. Activar Google Business Profile API
2. Obtener `GOOGLE_BUSINESS_ACCOUNT_ID` y `GOOGLE_BUSINESS_LOCATION_ID`
3. Configurar URL de reseña directa para solicitudes
