---
description: Flujo completo cuando llega un mensaje nuevo por cualquier canal
---

# Handle Incoming Message

## Objetivo
Procesar un mensaje entrante y generar una respuesta inteligente del agente inmobiliario.

## Inputs Requeridos
- `message`: Texto del mensaje del cliente
- `phone`: Número de teléfono del cliente
- `channel`: Canal de origen (whatsapp, instagram, email, etc.)
- `profile_name`: Nombre del perfil del cliente (si disponible)

## Flujo

### 1. Identificar Lead
- **Tool**: `tools/crm.py → get_or_create_lead()`
- Buscar si ya existe un lead con ese teléfono
- Si no existe, crear uno nuevo con el canal de origen
- Actualizar `last_contact` y `total_interactions`

### 2. Guardar Mensaje
- **Tool**: `tools/conversation_manager.py → add_message()`
- Añadir el mensaje del usuario al historial de la conversación
- Mantener contexto para el LLM

### 3. Preparar Contexto
- Si el lead ya tiene preferencias (zona, presupuesto, tipo):
  - **Tool**: `tools/property_manager.py → find_matching_properties()`
  - Buscar propiedades que encajen
  - **Tool**: `tools/property_manager.py → build_property_context()`
  - Construir contexto de propiedades para el LLM
- Añadir info del lead al contexto (nombre, score, preferencias conocidas)

### 4. Generar Respuesta
- **Tool**: `tools/ai_engine.py → generate_response()`
- Pasar: mensaje del usuario + historial de conversación + contexto adicional
- El system prompt define la personalidad del agente (ver `config.py`)

### 5. Guardar Respuesta
- **Tool**: `tools/conversation_manager.py → add_message()`
- Guardar la respuesta del agente en el historial

### 6. Cualificar Lead
- Cada 3 interacciones (o en las primeras 2):
  - **Tool**: `tools/lead_qualifier.py → qualify_lead()`
  - Extrae info de la conversación y actualiza score/preferencias
  - Si el lead es "caliente" (score > 75), crea tarea para equipo humano

### 7. Enviar Respuesta
- **Tool**: `tools/whatsapp_handler.py → send_whatsapp_message()` (o handler del canal correspondiente)
- Enviar la respuesta al cliente

## Output
- Mensaje enviado al cliente
- Lead actualizado en CRM
- Historial de conversación guardado

## Edge Cases
- **Mensaje vacío**: Ignorar, no responder
- **Error del LLM**: Enviar mensaje de disculpa genérico
- **Error de Twilio**: Loguear error, reintentar una vez
- **Lead solicita humano**: Crear tarea urgente + informar al equipo
