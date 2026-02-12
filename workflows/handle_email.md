---
description: Flujo para manejar emails entrantes y salientes
---

# Workflow: Gestión de Email

## Flujo de Email Entrante

1. **Webhook recibe email** (`POST /api/email/webhook`) via SendGrid Inbound Parse
2. **Parsear email** → Extraer remitente, asunto, cuerpo
3. **Limpiar cuerpo** → Eliminar firmas, texto citado, HTML
4. **Identificar lead** → Buscar/crear por dirección de email
5. **Construir mensaje** → Combinar asunto + cuerpo si es email nuevo
6. **Guardar mensaje** → Al historial de conversación del lead
7. **Adaptar contexto** → Agregar nota de formato email (más formal, menos emojis)
8. **Generar respuesta IA** → Con historial + propiedades + tono email
9. **Cualificar lead** → Actualizar score y clasificación
10. **Enviar respuesta** → Email con diseño HTML profesional via SendGrid

## Email Proactivo (Propiedades)
- `send_property_email()` envía propiedades recomendadas con HTML profesional
- Incluye: foto, precio, zona, características y CTA
- Útil para: seguimiento, nurturing, nuevas propiedades matching

## Diferencias con WhatsApp/Instagram
- Tono **más formal** y profesional
- Sin límite de longitud significativo
- Emails incluyen **diseño HTML** con branding
- Se respeta `Re:` en el asunto para hilos
- Se limpia texto citado y firmas automáticamente

## Configuración SendGrid Inbound Parse
1. Crear cuenta en [sendgrid.com](https://sendgrid.com)
2. Configurar **Inbound Parse**: Settings → Inbound Parse → Add Host & URL
3. Dominio: tu dominio de email
4. URL: `https://TU-URL/api/email/webhook`
5. Crear API Key y ponerla en `.env` como `SENDGRID_API_KEY`
