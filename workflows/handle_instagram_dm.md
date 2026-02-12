---
description: Flujo para manejar mensajes de Instagram DM
---

# Workflow: Gestión de Instagram DM

## Flujo Principal

1. **Webhook recibe evento de Meta** (`POST /api/instagram/webhook`)
2. **Verificar tipo de evento** → Solo procesar `object: "instagram"` + `messaging`
3. **Ignorar ecos** → No procesar mensajes enviados por nosotros
4. **Parsear mensaje** → Extraer `sender_id`, `message_text`, `quick_reply`
5. **Obtener perfil del usuario** → Nombre y foto via Graph API
6. **Identificar lead** → Buscar/crear con `ig:{sender_id}` como identificador
7. **Guardar mensaje** → Al historial de conversación del lead
8. **Buscar propiedades matching** → Si hay preferencias conocidas
9. **Generar respuesta IA** → Con historial + contexto de propiedades
10. **Cualificar lead** → Actualizar score y clasificación
11. **Enviar respuesta** → Dividir si >950 chars (límite Instagram)

## Diferencias con WhatsApp
- Instagram usa **IGSID** en vez de teléfono como identificador
- Límite de **1000 caracteres** por mensaje (se divide automáticamente)
- Soporta **Quick Replies** para opciones rápidas (máx 13)
- Requiere verificación del webhook con **hub.challenge**

## Configuración Meta Developer Portal
1. Crear App en [developers.facebook.com](https://developers.facebook.com)
2. Añadir producto **Instagram Messaging**
3. Configurar webhook: `https://TU-URL/api/instagram/webhook`
4. Token de verificación: usar el valor de `META_VERIFY_TOKEN` en `.env`
5. Suscribirse a: `messages`
