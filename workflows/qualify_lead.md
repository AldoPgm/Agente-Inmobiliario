---
description: Proceso de cualificación inteligente de leads inmobiliarios
---

# Qualify Lead

## Objetivo
Analizar la conversación con un cliente para extraer datos clave y clasificar su nivel de interés.

## Inputs Requeridos
- `lead_id`: ID del lead a cualificar
- `channel`: Canal de la conversación

## Flujo

### 1. Obtener Conversación
- **Tool**: `tools/conversation_manager.py → get_or_create_conversation()`
- Cargar historial completo de la conversación

### 2. Extraer Información con IA
- **Tool**: `tools/ai_engine.py → extract_lead_info()`
- El LLM analiza la conversación y devuelve un JSON con:
  - `operation`: comprar/alquilar/vender
  - `property_type`: piso, casa, etc.
  - `zone`: zona de interés
  - `min_budget` / `max_budget`: rango de presupuesto
  - `bedrooms`: habitaciones deseadas
  - `urgency`: inmediata, 1-3 meses, sin prisa
  - `purpose`: primera vivienda, inversión
  - `interest_level`: bajo, medio, alto, muy alto
  - `wants_visit`: si quiere agendar visita
  - `wants_human_agent`: si pide hablar con persona

### 3. Actualizar Lead
- **Tool**: `tools/crm.py → update_lead_from_extraction()`
- Actualizar preferencias (solo campos nuevos, no sobreescribir)
- Recalcular score

### 4. Calcular Score (0-100)

| Dato proporcionado | Puntos |
|---|---|
| Operación (comprar/alquilar) | +10 |
| Tipo de inmueble | +10 |
| Zona | +15 |
| Presupuesto | +15 |
| Habitaciones | +5 |
| Urgencia | +10 |
| Urgencia inmediata/1-3 meses | +10 bonus |
| Finalidad | +5 |
| Nombre | +5 |
| Interés alto/muy alto | +10/+15 |
| Quiere visita | +15 |
| 3+ interacciones | +5 |
| 5+ interacciones | +5 |

### 5. Clasificar

| Score | Clasificación | Acción |
|---|---|---|
| 0-25 | 🔵 Curioso | Seguir conversación |
| 26-50 | 🟡 Interesado | Enviar propiedades |
| 51-75 | 🟠 Caliente | Crear tarea para agente |
| 76-100 | 🔴 Listo para comprar | Tarea urgente + llamar |

### 6. Acciones Automáticas
- **Score ≥ 75**: Crear tarea "llamar" con prioridad ALTA
- **Pide humano**: Crear tarea "contactar" con prioridad URGENTE
- **Quiere visita**: Preparar para agendado (Fase 3)

## Output
- Lead actualizado con score, clasificación y preferencias
- Tareas creadas si aplica

## Notas
- No hacer todas las preguntas de golpe; integrarlas naturalmente
- El score se recalcula cada vez, no acumula
- Priorizar calidad de datos sobre cantidad
