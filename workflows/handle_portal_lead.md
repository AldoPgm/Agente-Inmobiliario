---
description: Flujo para recibir y procesar leads de portales inmobiliarios
---

# Workflow: Leads de Portales

## Portales Soportados
- Idealista
- Fotocasa
- Habitaclia
- Pisos.com
- Cualquier portal vía parser genérico

## Vías de Entrada

### 1. Webhook directo
```
POST /api/portals/webhook
POST /api/portals/webhook/idealista   (específico)
```

### 2. Email reenviado (via SendGrid)
```
POST /api/portals/email
```
Detecta el portal por el asunto del email y extrae datos con regex.

## Flujo de Procesamiento

1. **Recibir lead** → webhook o email
2. **Parsear datos** → nombre, teléfono, email, mensaje, referencia
3. **Crear/encontrar lead** en CRM
4. **Generar respuesta IA** → con contexto de portal (tono proactivo)
5. **Enviar respuesta** → email y/o WhatsApp
6. **Notificar equipo** → WhatsApp + email al equipo comercial
7. **Cualificar** → actualizar score

## Configuración

1. En cada portal, configurar reenvío de emails a tu dirección SendGrid
2. O configurar webhooks directos si el portal lo soporta
3. Configurar `TEAM_WHATSAPP_NUMBER` y `TEAM_EMAIL` en `.env`
