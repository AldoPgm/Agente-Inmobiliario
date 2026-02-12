---
description: Cómo responder consultas sobre propiedades inmobiliarias
---

# Property Inquiry

## Objetivo
Responder consultas de clientes sobre propiedades de forma profesional y comercial, utilizando datos reales de la base de datos.

## Inputs Requeridos
- `lead_id`: ID del lead que consulta
- `query`: Pregunta o criterios del cliente

## Flujo

### 1. Identificar Intención
El cliente puede preguntar sobre:
- **Búsqueda general**: "Busco un piso en el centro por 200k"
- **Propiedad específica**: "La referencia ABC123"
- **Detalles**: "¿Tiene parking?" "¿Cuántos metros?"
- **Precio/financiación**: "¿Se puede negociar?" "¿Cuánto sería la hipoteca?"
- **Zona**: "¿Cómo es el barrio?" "¿Hay colegios cerca?"

### 2. Buscar Propiedades
- **Tool**: `tools/property_manager.py → find_matching_properties()`
- Usar las preferencias del lead como filtros
- Buscar máximo 5 propiedades

### 3. Formatear para Chat
- **Tool**: `tools/property_manager.py → format_properties_list()`
- Incluir: precio, metros, zona, habitaciones, extras
- Formato atractivo con emojis
- Máximo 3 propiedades por mensaje para no saturar

### 4. Cálculo de Hipoteca (si aplica)
- **Tool**: `tools/property_manager.py → calculate_mortgage()`
- Parámetros por defecto: 20% entrada, 3.5% interés, 30 años
- **Tool**: `tools/property_manager.py → format_mortgage_for_chat()`
- Siempre aclarar que es estimación orientativa

### 5. Inyectar Contexto en IA
- **Tool**: `tools/property_manager.py → build_property_context()`
- Añadir datos de propiedades al contexto del LLM
- Así el agente puede responder preguntas específicas sin inventar datos

## Reglas

### SIEMPRE
- ✅ Usar datos reales de la base de datos
- ✅ Ser honesto si no hay propiedades que encajen
- ✅ Ofrecer alternativas o tomar datos para avisar
- ✅ Incluir disclaimer en cálculos de hipoteca
- ✅ Sugerir visita cuando haya interés alto

### NUNCA
- ❌ Inventar datos de propiedades
- ❌ Dar información de precio incorrecta
- ❌ Prometer disponibilidad sin verificar
- ❌ Omitir gastos (comunidad, IBI) si se tienen

## Output
- Mensaje formateado con propiedades relevantes
- Contexto actualizado para futuras preguntas

## Edge Cases
- **Sin propiedades**: Ofrecer tomar datos y avisar cuando haya algo nuevo
- **Propiedad vendida/reservada**: Informar y ofrecer alternativas similares
- **Precio fuera de rango**: Sugerir ajustar criterios o zonas alternativas
