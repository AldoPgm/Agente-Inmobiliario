---
description: Flujo para agendar visitas a inmuebles
---

# Workflow: Agendado de Visitas

## Flujo de Agendado

1. **Detectar intención** → El lead pide agendar visita o muestra interés alto
2. **Identificar propiedad** → ¿Qué propiedad quiere visitar?
3. **Proponer fecha** → El lead sugiere fecha/hora
4. **Consultar disponibilidad** → `get_available_slots(date)`
5. **Mostrar opciones** → `format_available_slots_for_chat()`
6. **Confirmar slot** → El lead elige un horario
7. **Crear evento** → `schedule_visit()` en Google Calendar
8. **Confirmar al lead** → Datos de la visita por el canal activo
9. **Enviar invitación** → Google Calendar envía email automáticamente

## Recordatorios Automáticos

| Momento | Canal | Acción |
|---------|-------|--------|
| 24h antes | Email | Recordar fecha, hora y dirección |
| 2h antes | WhatsApp | Confirmación rápida con dirección |
| 24h después | WhatsApp/Email | Seguimiento post-visita |

## Horarios de Visita

- **Lunes a Viernes:** 10:00–13:00 y 16:00–20:00
- **Sábados:** 10:00–14:00
- **Domingos:** No hay visitas

## Cancelación / Cambio

1. El lead pide cancelar o cambiar
2. `cancel_visit(event_id)` elimina el evento
3. Si quiere cambiar → repetir flujo de agendado
