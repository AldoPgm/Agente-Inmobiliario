"""
Tareas programadas con APScheduler.
Ejecuta jobs periódicos: nurturing, recordatorios, reseñas, reportes.
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime


# ─────────────────────────────────────────────
# Scheduler global
# ─────────────────────────────────────────────
scheduler = AsyncIOScheduler(timezone="Europe/Madrid")


# ─────────────────────────────────────────────
# Job: Nurturing de leads
# ─────────────────────────────────────────────
async def job_nurturing():
    """
    Ejecuta el motor de nurturing.
    Evalúa todos los leads activos y envía follow-ups.
    Frecuencia: cada 4 horas (9:00, 13:00, 17:00)
    """
    from tools.nurturing_engine import process_nurturing
    from tools.database import get_active_leads
    
    print(f"🔄 [{datetime.now().strftime('%H:%M')}] Ejecutando nurturing...")
    
    try:
        leads = await get_active_leads()
        results = await process_nurturing(leads)
        print(
            f"✅ Nurturing: {results['leads_processed']} leads procesados, "
            f"{results['messages_sent']} WhatsApp, {results['emails_sent']} emails"
        )
    except Exception as e:
        print(f"❌ Error en nurturing: {e}")


# ─────────────────────────────────────────────
# Job: Recordatorios de visitas
# ─────────────────────────────────────────────
async def job_reminders():
    """
    Envía recordatorios de visitas próximas.
    Frecuencia: cada hora
    """
    from tools.reminder_service import send_visit_reminders
    
    print(f"🔔 [{datetime.now().strftime('%H:%M')}] Verificando recordatorios...")
    
    try:
        await send_visit_reminders()
    except Exception as e:
        print(f"❌ Error en recordatorios: {e}")


# ─────────────────────────────────────────────
# Job: Responder reseñas
# ─────────────────────────────────────────────
async def job_reviews():
    """
    Revisa y responde reseñas pendientes de Google.
    Frecuencia: 2 veces al día (10:00 y 18:00)
    """
    from tools.review_manager import auto_reply_pending_reviews
    from tools.scheduler import _load_google_token
    
    print(f"⭐ [{datetime.now().strftime('%H:%M')}] Revisando reseñas...")
    
    try:
        token = _load_google_token()
        if token:
            results = await auto_reply_pending_reviews(token)
            print(f"✅ Reseñas: {results['replied']} respondidas")
        else:
            print("⚠️ Sin token de Google, saltando reseñas")
    except Exception as e:
        print(f"❌ Error en reseñas: {e}")


# ─────────────────────────────────────────────
# Job: Reporte diario
# ─────────────────────────────────────────────
async def job_daily_report():
    """
    Genera un reporte diario de actividad.
    Frecuencia: 1 vez al día (21:00)
    """
    from tools.database import get_daily_stats
    
    print(f"📊 [{datetime.now().strftime('%H:%M')}] Generando reporte diario...")
    
    try:
        stats = await get_daily_stats()
        
        report = (
            f"📊 REPORTE DIARIO — {datetime.now().strftime('%d/%m/%Y')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📥 Mensajes recibidos: {stats.get('messages_received', 0)}\n"
            f"📤 Mensajes enviados: {stats.get('messages_sent', 0)}\n"
            f"👥 Leads nuevos: {stats.get('new_leads', 0)}\n"
            f"🔥 Leads calientes: {stats.get('hot_leads', 0)}\n"
            f"📅 Visitas agendadas: {stats.get('visits_scheduled', 0)}\n"
            f"⭐ Reseñas nuevas: {stats.get('new_reviews', 0)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )
        
        print(report)
        # Aquí se podría enviar el reporte por email al dueño de la inmobiliaria
        
    except Exception as e:
        print(f"❌ Error generando reporte: {e}")


# ─────────────────────────────────────────────
# Configurar y arrancar scheduler
# ─────────────────────────────────────────────
def setup_scheduled_tasks():
    """Configura todos los jobs programados y arranca el scheduler."""
    
    # Nurturing: 3 veces al día (9:00, 13:00, 17:00)
    scheduler.add_job(
        job_nurturing,
        CronTrigger(hour="9,13,17", minute=0),
        id="nurturing",
        name="Nurturing de leads",
        replace_existing=True,
    )
    
    # Recordatorios: cada hora (de 8:00 a 21:00)
    scheduler.add_job(
        job_reminders,
        CronTrigger(hour="8-21", minute=0),
        id="reminders",
        name="Recordatorios de visitas",
        replace_existing=True,
    )
    
    # Reseñas: 2 veces al día (10:00 y 18:00)
    scheduler.add_job(
        job_reviews,
        CronTrigger(hour="10,18", minute=30),
        id="reviews",
        name="Responder reseñas",
        replace_existing=True,
    )
    
    # Reporte diario: 21:00
    scheduler.add_job(
        job_daily_report,
        CronTrigger(hour=21, minute=0),
        id="daily_report",
        name="Reporte diario",
        replace_existing=True,
    )
    
    scheduler.start()
    
    print("⏰ Tareas programadas configuradas:")
    print("  • Nurturing: 9:00, 13:00, 17:00")
    print("  • Recordatorios: cada hora (8h-21h)")
    print("  • Reseñas: 10:30, 18:30")
    print("  • Reporte diario: 21:00")


def stop_scheduled_tasks():
    """Detiene el scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        print("⏰ Tareas programadas detenidas")
