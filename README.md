# 🏠 Agente Inmobiliario IA

> Un asistente virtual autónomo que atiende leads 24/7 por **WhatsApp, Instagram, Email y Voz**, cualifica clientes, busca propiedades y agenda visitas automáticamente.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)
![OpenAI](https://img.shields.io/badge/AI-GPT--4o-orange.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## 🌟 Características Principales

- **Multi-Canal**: Atiende de form unificada en WhatsApp (Twilio), Instagram (Meta), Email (SendGrid) y Teléfono (Vapi.ai).
- **Cualificación Inteligente**: Detecta intención de compra/alquiler, presupuesto, zona y urgencia mediante conversación natural.
- **Lead Scoring en Tiempo Real**: Asigna puntuación (0-100) según la calidad del lead y prioriza los más calientes.
- **Búsqueda de Propiedades**: Conecta con tu base de datos para recomendar inmuebles que encajan con el cliente.
- **Agendado Automático**: Sincronización bidireccional con Google Calendar para concertar citas sin intervención humana.
- **Human Handoff**: Deriva al equipo comercial cuando detecta negociaciones, quejas o clientes VIP.

## 🚀 Demo Interactiva

Prueba una simulación de conversación real aquí:  
👉 **[Ver Demo en Vivo](https://aldopgm.github.io/Agente-Inmobiliario/demo.html)**

## 🛠️ Tecnologías

- **Backend**: FastAPI (Python)
- **IA**: OpenAI GPT-4o / Google Gemini 2.0 (configurable)
- **Base de Datos**: Supabase (PostgreSQL)
- **Integraciones**:
  - Twilio (WhatsApp)
  - SendGrid (Email)
  - Meta Graph API (Instagram)
  - Vapi.ai (Voz)
  - Google Calendar API

## 📦 Instalación

1. **Clonar el repositorio**
   ```bash
   git clone https://github.com/AldoPgm/Agente-Inmobiliario.git
   cd Agente-Inmobiliario
   ```

2. **Crear entorno virtual e instalar dependencias**
   ```bash
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configurar variables de entorno**
   - Copia el archivo de ejemplo:
     ```bash
     cp .env.example .env
     ```
   - Edita `.env` con tus API keys reales (OpenAI, Twilio, Supabase, etc.).

4. **Inicializar Base de Datos**
   - Ejecuta el script SQL en tu proyecto de Supabase:
     ```bash
     # Copia el contenido de setup_database.sql y ejecútalo en el SQL Editor de Supabase
     ```

5. **Ejecutar servidor**
   ```bash
   uvicorn main:app --reload
   ```

## 🌐 Despliegue

Este proyecto incluye un `Procfile` listo para desplegar en **Railway** o **Render**.

1. Sube tu código a GitHub.
2. Conecta tu repo en Railway.
3. Configura las variables de entorno en el dashboard.
4. ¡Listo! Tu agente estará activo en `https://tu-proyecto.up.railway.app`.

## 📂 Estructura del Proyecto

```
.
├── main.py                 # Punto de entrada (Servidor FastAPI)
├── config.py               # Configuración y System Prompts
├── tools/                  # Lógica de negocio y herramientas IA
│   ├── ai_engine.py        # Motor de IA (GPT-4o / Gemini)
│   ├── crm.py              # Gestión de leads y scoring
│   ├── scheduler.py        # Integración Google Calendar
│   ├── property_manager.py # Búsqueda de inmuebles
│   └── ...
├── routers/                # Webhooks de cada canal
│   ├── whatsapp.py
│   ├── instagram.py
│   ├── email.py
│   └── voice.py
└── models/                 # Modelos de datos Pydantic
```

## 📄 Licencia

Distribuido bajo la licencia MIT. Ver `LICENSE` para más información.

---
Hecho con ❤️ por [AldoPgm](https://github.com/AldoPgm)
