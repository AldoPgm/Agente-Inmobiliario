"""
Cliente de base de datos Supabase.
Operaciones CRUD para todas las tablas del CRM inmobiliario.
"""

from config import SUPABASE_URL, SUPABASE_KEY
from supabase import create_client, Client

# ─────────────────────────────────────────────
# Conexión
# ─────────────────────────────────────────────
_client: Client | None = None


def get_client() -> Client:
    """Obtiene o crea el cliente de Supabase."""
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise RuntimeError(
                "❌ SUPABASE_URL y SUPABASE_KEY no configurados en .env"
            )
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


# ─────────────────────────────────────────────
# LEADS
# ─────────────────────────────────────────────
async def get_lead_by_phone(phone: str) -> dict | None:
    """Busca un lead por número de teléfono."""
    try:
        result = get_client().table("leads").select("*").eq("phone", phone).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"❌ Error buscando lead por teléfono: {e}")
        return None


async def get_lead_by_id(lead_id: str) -> dict | None:
    """Obtiene un lead por su ID."""
    try:
        result = get_client().table("leads").select("*").eq("id", lead_id).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"❌ Error obteniendo lead: {e}")
        return None


async def create_lead(data: dict) -> dict | None:
    """Crea un nuevo lead."""
    try:
        result = get_client().table("leads").insert(data).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"❌ Error creando lead: {e}")
        return None


async def update_lead(lead_id: str, data: dict) -> dict | None:
    """Actualiza un lead existente."""
    try:
        result = get_client().table("leads").update(data).eq("id", lead_id).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"❌ Error actualizando lead: {e}")
        return None


async def get_all_leads(status: str = None, score_min: int = None) -> list[dict]:
    """Obtiene leads con filtros opcionales."""
    try:
        query = get_client().table("leads").select("*")
        if status:
            query = query.eq("status", status)
        if score_min is not None:
            query = query.gte("score", score_min)
        result = query.order("last_contact", desc=True).execute()
        return result.data or []
    except Exception as e:
        print(f"❌ Error obteniendo leads: {e}")
        return []


# ─────────────────────────────────────────────
# PROPERTIES
# ─────────────────────────────────────────────
async def get_property_by_id(property_id: str) -> dict | None:
    """Obtiene una propiedad por ID."""
    try:
        result = get_client().table("properties").select("*").eq("id", property_id).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"❌ Error obteniendo propiedad: {e}")
        return None


async def search_properties(
    operation: str = None,
    property_type: str = None,
    zone: str = None,
    min_price: float = None,
    max_price: float = None,
    min_sqm: int = None,
    bedrooms: int = None,
    limit: int = 5,
) -> list[dict]:
    """Busca propiedades disponibles con filtros."""
    try:
        query = get_client().table("properties").select("*").eq("status", "disponible")
        
        if operation:
            query = query.eq("operation", operation)
        if property_type:
            query = query.eq("property_type", property_type)
        if zone:
            query = query.ilike("zone", f"%{zone}%")
        if min_price is not None:
            query = query.gte("price", min_price)
        if max_price is not None:
            query = query.lte("price", max_price)
        if min_sqm is not None:
            query = query.gte("sqm", min_sqm)
        
        result = query.limit(limit).execute()
        data = result.data or []
        
        # Filtrar por habitaciones en memoria (jsonb)
        if bedrooms is not None:
            data = [p for p in data if (p.get("features") or {}).get("bedrooms", 0) >= bedrooms]
        
        return data
    except Exception as e:
        print(f"❌ Error buscando propiedades: {e}")
        return []


async def create_property(data: dict) -> dict | None:
    """Crea una nueva propiedad."""
    try:
        result = get_client().table("properties").insert(data).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"❌ Error creando propiedad: {e}")
        return None


async def update_property(property_id: str, data: dict) -> dict | None:
    """Actualiza una propiedad."""
    try:
        result = get_client().table("properties").update(data).eq("id", property_id).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"❌ Error actualizando propiedad: {e}")
        return None


# ─────────────────────────────────────────────
# CONVERSATIONS
# ─────────────────────────────────────────────
async def get_conversation_by_lead(lead_id: str, channel: str) -> dict | None:
    """Obtiene la conversación de un lead en un canal."""
    try:
        result = (
            get_client()
            .table("conversations")
            .select("*")
            .eq("lead_id", lead_id)
            .eq("channel", channel)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"❌ Error obteniendo conversación: {e}")
        return None


async def upsert_conversation(conversation_id: str | None, data: dict) -> dict | None:
    """Crea o actualiza una conversación."""
    try:
        if conversation_id:
            result = (
                get_client()
                .table("conversations")
                .update(data)
                .eq("id", conversation_id)
                .execute()
            )
        else:
            result = get_client().table("conversations").insert(data).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"❌ Error guardando conversación: {e}")
        return None


# ─────────────────────────────────────────────
# APPOINTMENTS
# ─────────────────────────────────────────────
async def create_appointment(data: dict) -> dict | None:
    """Crea una cita/visita."""
    try:
        result = get_client().table("appointments").insert(data).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"❌ Error creando cita: {e}")
        return None


async def get_appointments_by_lead(lead_id: str) -> list[dict]:
    """Obtiene las citas de un lead."""
    try:
        result = (
            get_client()
            .table("appointments")
            .select("*")
            .eq("lead_id", lead_id)
            .order("datetime_", desc=True)
            .execute()
        )
        return result.data or []
    except Exception as e:
        print(f"❌ Error obteniendo citas: {e}")
        return []


async def update_appointment(appointment_id: str, data: dict) -> dict | None:
    """Actualiza una cita."""
    try:
        result = (
            get_client()
            .table("appointments")
            .update(data)
            .eq("id", appointment_id)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"❌ Error actualizando cita: {e}")
        return None


# ─────────────────────────────────────────────
# TASKS
# ─────────────────────────────────────────────
async def create_task(data: dict) -> dict | None:
    """Crea una tarea para el equipo humano."""
    try:
        result = get_client().table("tasks").insert(data).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"❌ Error creando tarea: {e}")
        return None


async def get_pending_tasks(assigned_to: str = None) -> list[dict]:
    """Obtiene tareas pendientes."""
    try:
        query = (
            get_client()
            .table("tasks")
            .select("*")
            .eq("status", "pendiente")
        )
        if assigned_to:
            query = query.eq("assigned_to", assigned_to)
        result = query.order("due_date").execute()
        return result.data or []
    except Exception as e:
        print(f"❌ Error obteniendo tareas: {e}")
        return []


# ─────────────────────────────────────────────
# BÚSQUEDA POR REFERENCIA
# ─────────────────────────────────────────────
async def get_property_by_ref(reference: str) -> dict | None:
    """Obtiene una propiedad por su referencia (ej: REF-001)."""
    try:
        result = (
            get_client()
            .table("properties")
            .select("*")
            .eq("reference", reference)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"❌ Error buscando propiedad por referencia: {e}")
        return None


# ─────────────────────────────────────────────
# NURTURING & REPORTES
# ─────────────────────────────────────────────
async def get_active_leads() -> list[dict]:
    """Obtiene leads activos para nurturing (con actividad reciente o score > 0)."""
    try:
        result = (
            get_client()
            .table("leads")
            .select("*")
            .neq("status", "cerrado")
            .neq("status", "descartado")
            .order("last_contact", desc=True)
            .limit(100)
            .execute()
        )
        return result.data or []
    except Exception as e:
        print(f"❌ Error obteniendo leads activos: {e}")
        return []


async def get_daily_stats() -> dict:
    """Obtiene estadísticas del día para el reporte."""
    from datetime import datetime, timedelta
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    stats = {
        "messages_received": 0,
        "messages_sent": 0,
        "new_leads": 0,
        "hot_leads": 0,
        "visits_scheduled": 0,
        "new_reviews": 0,
    }
    
    try:
        # Leads creados hoy
        leads = (
            get_client()
            .table("leads")
            .select("id", count="exact")
            .gte("created_at", today)
            .execute()
        )
        stats["new_leads"] = leads.count or 0
        
        # Leads calientes
        hot = (
            get_client()
            .table("leads")
            .select("id", count="exact")
            .gte("score", 60)
            .execute()
        )
        stats["hot_leads"] = hot.count or 0
        
        # Citas de hoy
        visits = (
            get_client()
            .table("appointments")
            .select("id", count="exact")
            .gte("created_at", today)
            .execute()
        )
        stats["visits_scheduled"] = visits.count or 0
        
    except Exception as e:
        print(f"⚠️ Error obteniendo estadísticas: {e}")
    
    return stats
