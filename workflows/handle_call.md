---
description: Flujo para manejar llamadas telefónicas con Vapi.ai
---

# Workflow: Gestión de Llamadas

## Llamadas Entrantes

1. **Vapi.ai recibe la llamada** → El asistente de voz atiende
2. **Saludo automático** → "¡Hola! Soy Ana de Tu Inmobiliaria..."
3. **Conversación IA** → Mismo prompt que chat, adaptado a voz
4. **Transcripción en tiempo real** → Vapi transcribe con Deepgram
5. **Al colgar** → Webhook `end-of-call-report` con transcripción

## Llamadas Salientes

Útil para:
- Follow-up a leads calientes
- Recordatorios de visita
- Reactivación de leads fríos

```python
await make_outbound_call(
    phone_number="+34612345678",
    context="Lead caliente, interesado en REF-001, presupuesto 200K"
)
```

## Post-Llamada (Automático)

1. **Guardar transcripción** → En historial del lead
2. **Cualificar lead** → Actualizar score basado en la llamada
3. **Crear tareas** → Si se detectó interés alto o solicitud de visita

## Configuración Vapi.ai

1. Crear cuenta en [vapi.ai](https://vapi.ai)
2. Obtener API key → `VAPI_API_KEY` en `.env`
3. Configurar webhook: `https://TU-URL/api/voice/webhook`
4. El asistente se crea automáticamente al iniciar

## Adaptaciones de Voz vs Chat
- Frases más cortas y claras
- No hacer listas largas → ofrecer enviar por WhatsApp
- Confirmar datos repitiendo
- Máximo 10 minutos por llamada
