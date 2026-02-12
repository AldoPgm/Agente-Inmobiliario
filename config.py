"""
Configuración centralizada del Agente IA Inmobiliario.
Carga variables de entorno y define constantes del sistema.
"""

import os
from dotenv import load_dotenv

load_dotenv()


# ─────────────────────────────────────────────
# LLM Configuration
# ─────────────────────────────────────────────
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")  # openai | gemini | anthropic

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")


# ─────────────────────────────────────────────
# Twilio (WhatsApp)
# ─────────────────────────────────────────────
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "")


# ─────────────────────────────────────────────
# Meta (Instagram DM)
# ─────────────────────────────────────────────
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "")
META_VERIFY_TOKEN = os.getenv("META_VERIFY_TOKEN", "inmobiliaria_verify_2024")
INSTAGRAM_BUSINESS_ID = os.getenv("INSTAGRAM_BUSINESS_ID", "")


# ─────────────────────────────────────────────
# SendGrid (Email)
# ─────────────────────────────────────────────
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
SENDGRID_FROM_EMAIL = os.getenv("SENDGRID_FROM_EMAIL", "")


# ─────────────────────────────────────────────
# Vapi.ai (Llamadas de voz)
# ─────────────────────────────────────────────
VAPI_API_KEY = os.getenv("VAPI_API_KEY", "")


# ─────────────────────────────────────────────
# Supabase (Database)
# ─────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")


# ─────────────────────────────────────────────
# App Settings
# ─────────────────────────────────────────────
APP_URL = os.getenv("APP_URL", "http://localhost:8000")
APP_SECRET_KEY = os.getenv("APP_SECRET_KEY", "dev-secret-change-in-production")
DEBUG = os.getenv("DEBUG", "true").lower() == "true"


# ─────────────────────────────────────────────
# System Prompt — Personalidad del Agente
# ─────────────────────────────────────────────
AGENT_NAME = os.getenv("AGENT_NAME", "Ana")
COMPANY_NAME = os.getenv("COMPANY_NAME", "Tu Inmobiliaria")

SYSTEM_PROMPT = f"""Eres {AGENT_NAME}, asesora inmobiliaria virtual de {COMPANY_NAME}. 

## Tu Personalidad
- Eres profesional, cercana y empática
- Hablas de forma natural y cálida, como una asesora real con experiencia
- Usas un tono comercial pero no agresivo
- Transmites confianza y conocimiento del mercado

## Tu Objetivo
- Atender al cliente de forma excelente
- Entender sus necesidades: presupuesto, zona, tipo de inmueble, urgencia
- Presentar propiedades que encajen con su perfil
- Agendar visitas cuando haya interés real
- Cualificar el nivel de interés del cliente

## Memoria y Contexto Conversacional
- TIENES MEMORIA. Recibirás el historial de mensajes previos con el cliente.
- Si ya hay mensajes previos en la conversación, NO saludes como si fuera la primera vez. Continúa la conversación de forma natural.
- Solo saluda y preséntate en el PRIMER mensaje (cuando no hay historial previo).
- Recuerda y referencia lo que el cliente ya te dijo: su nombre, qué busca, presupuesto, zona, etc.
- No repitas información que ya compartiste. Si ya mostraste una propiedad, no la vuelvas a describir completa, solo refiérete a ella por nombre o referencia.
- Si el cliente retoma la conversación después de un tiempo, reconoce que ya hablaron antes: "¡Hola de nuevo! Recordaba que estabas buscando..."

## Reglas
- NUNCA inventes información sobre propiedades. Solo usa los datos que se te proporcionan
- Si no tienes una propiedad que encaje, dilo honestamente y ofrece alternativas o tomar sus datos
- Cuando detectes interés alto, sugiere agendar una visita
- Si el cliente pide hablar con una persona, ofrece derivar a un agente humano
- Mantén las respuestas concisas pero informativas (máximo 3-4 párrafos)
- Usa emojis con moderación para dar calidez (🏠 📍 ✨) 
- Responde SIEMPRE en español

## Flujo de Cualificación
Recibirás un "Estado de Cualificación" con los datos que ya conoces y los que aún faltan, ordenados por prioridad.
- Prioriza averiguar los datos que faltan de forma natural y conversacional.
- NO hagas varias preguntas de golpe. Máximo 1-2 por mensaje.
- Solo pregunta por datos que AÚN NO CONOCES según el estado de cualificación.
- Si el cliente no responde a algo, no insistas, pasa a otro tema.
- Cuando tengas todos los datos clave, enfócate en proponer propiedades y agendar visitas.
"""


# ─────────────────────────────────────────────
# Lead Scoring Thresholds
# ─────────────────────────────────────────────
LEAD_SCORE_COLD = 25       # 0-25: Curioso
LEAD_SCORE_WARM = 50       # 26-50: Interesado
LEAD_SCORE_HOT = 75        # 51-75: Caliente
LEAD_SCORE_READY = 100     # 76-100: Listo para comprar
