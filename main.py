"""
Agente IA Inmobiliario 24/7
Entry point de la aplicación FastAPI.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config import DEBUG, COMPANY_NAME
from routers import whatsapp, instagram, email, voice, portals
from tools.scheduled_tasks import setup_scheduled_tasks, stop_scheduled_tasks


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Eventos de startup y shutdown."""
    print(f"🏠 Agente IA de {COMPANY_NAME} iniciado")
    print(f"📡 Modo: {'DEBUG' if DEBUG else 'PRODUCCIÓN'}")
    print(f"📱 Canales: WhatsApp, Instagram DM, Email, Voz, Portales")
    
    # Arrancar tareas programadas
    if not DEBUG:
        setup_scheduled_tasks()
    else:
        print("⏰ Tareas programadas desactivadas en modo DEBUG")
    
    yield
    
    # Detener tareas programadas
    stop_scheduled_tasks()
    print("👋 Agente detenido")


app = FastAPI(
    title=f"Agente IA Inmobiliario — {COMPANY_NAME}",
    description="Agente de IA 24/7 para gestión comercial inmobiliaria",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Routers ───
app.include_router(whatsapp.router, prefix="/api/whatsapp", tags=["WhatsApp"])
app.include_router(instagram.router, prefix="/api/instagram", tags=["Instagram"])
app.include_router(email.router, prefix="/api/email", tags=["Email"])
app.include_router(voice.router, prefix="/api/voice", tags=["Voz"])
app.include_router(portals.router, prefix="/api/portals", tags=["Portales"])


# ─── Health Check ───
@app.get("/")
async def root():
    return {
        "status": "online",
        "agent": COMPANY_NAME,
        "message": f"🏠 Agente IA de {COMPANY_NAME} funcionando 24/7",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}
