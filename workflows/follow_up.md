---
description: Reglas de seguimiento y nurturing automático de leads
---

# Workflow: Seguimiento y Nurturing

## Reglas de Follow-Up

| Regla | Condición | Delay | Canal | Acción |
|-------|-----------|-------|-------|--------|
| Post primer contacto | ≤2 interacciones, score <30 | 24h | WhatsApp | Recordar interés, ofrecer opciones |
| Lead tibio | Score 30-60, 3+ días sin contacto | 72h | WhatsApp | Enviar propiedades nuevas |
| Lead caliente | Score 60+, 2+ días sin contacto | 48h | WhatsApp | Crear urgencia |
| Lead frío | Score <30, 7+ días sin contacto | 7 días | Email | Reactivación con contenido de valor |
| Nuevas propiedades | Lead con preferencias + nueva propiedad matching | Inmediato | Email | Notificar propiedad |

## Schedule (APScheduler)

- **Nurturing**: 9:00, 13:00, 17:00 (3x/día)
- **Recordatorios visitas**: cada hora (8h-21h)
- **Reseñas Google**: 10:30, 18:30 (2x/día)
- **Reporte diario**: 21:00

## Flujo de Ejecución

1. `job_nurturing()` se ejecuta según schedule
2. Obtiene todos los leads activos de Supabase
3. Para cada lead, evalúa las reglas de nurturing
4. Si una regla aplica → genera mensaje personalizado
5. Envía por el canal correspondiente (WhatsApp/Email)
6. Registra la acción en el historial del lead
