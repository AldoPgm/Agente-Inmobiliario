"""
Modelos de datos Pydantic para la base de datos del CRM inmobiliario.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


# ─────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────
class LeadStatus(str, Enum):
    NUEVO = "nuevo"
    CONTACTADO = "contactado"
    CUALIFICADO = "cualificado"
    VISITA_AGENDADA = "visita_agendada"
    NEGOCIACION = "negociacion"
    CERRADO_GANADO = "cerrado_ganado"
    CERRADO_PERDIDO = "cerrado_perdido"
    INACTIVO = "inactivo"


class LeadScore(str, Enum):
    CURIOSO = "curioso"
    INTERESADO = "interesado"
    CALIENTE = "caliente"
    LISTO = "listo_para_comprar"


class PropertyType(str, Enum):
    PISO = "piso"
    CASA = "casa"
    CHALET = "chalet"
    ATICO = "ático"
    DUPLEX = "dúplex"
    ESTUDIO = "estudio"
    LOCAL = "local"
    OFICINA = "oficina"
    TERRENO = "terreno"
    GARAGE = "garaje"


class PropertyStatus(str, Enum):
    DISPONIBLE = "disponible"
    RESERVADO = "reservado"
    VENDIDO = "vendido"
    ALQUILADO = "alquilado"


class OperationType(str, Enum):
    VENTA = "venta"
    ALQUILER = "alquiler"
    ALQUILER_OPCION_COMPRA = "alquiler_opcion_compra"


class ChannelType(str, Enum):
    WHATSAPP = "whatsapp"
    INSTAGRAM = "instagram"
    EMAIL = "email"
    TELEFONO = "telefono"
    WEB = "web"
    PORTAL = "portal"


class AppointmentStatus(str, Enum):
    PENDIENTE = "pendiente"
    CONFIRMADA = "confirmada"
    CANCELADA = "cancelada"
    COMPLETADA = "completada"
    NO_SHOW = "no_show"


class TaskPriority(str, Enum):
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"
    URGENTE = "urgente"


class TaskStatus(str, Enum):
    PENDIENTE = "pendiente"
    EN_PROGRESO = "en_progreso"
    COMPLETADA = "completada"
    CANCELADA = "cancelada"


# ─────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────
class LeadPreferences(BaseModel):
    """Preferencias extraídas durante la cualificación."""
    operation: Optional[str] = None        # comprar, alquilar
    property_type: Optional[str] = None    # piso, casa, etc.
    zone: Optional[str] = None
    min_budget: Optional[float] = None
    max_budget: Optional[float] = None
    min_sqm: Optional[int] = None
    max_sqm: Optional[int] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    parking: Optional[bool] = None
    urgency: Optional[str] = None          # inmediata, 1-3 meses, sin prisa
    purpose: Optional[str] = None          # primera vivienda, inversión
    notes: Optional[str] = None


class Lead(BaseModel):
    """Modelo de un lead/cliente potencial."""
    id: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    channel: ChannelType = ChannelType.WHATSAPP
    status: LeadStatus = LeadStatus.NUEVO
    score: int = Field(default=0, ge=0, le=100)
    score_label: LeadScore = LeadScore.CURIOSO
    preferences: LeadPreferences = Field(default_factory=LeadPreferences)
    tags: list[str] = Field(default_factory=list)
    assigned_agent: Optional[str] = None
    created_at: Optional[datetime] = None
    last_contact: Optional[datetime] = None
    total_interactions: int = 0


class PropertyFeatures(BaseModel):
    """Características detalladas de un inmueble."""
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    has_parking: bool = False
    has_elevator: bool = False
    has_terrace: bool = False
    has_pool: bool = False
    has_garden: bool = False
    has_storage: bool = False
    has_ac: bool = False
    has_heating: bool = False
    floor: Optional[int] = None
    year_built: Optional[int] = None
    energy_rating: Optional[str] = None
    orientation: Optional[str] = None
    extras: list[str] = Field(default_factory=list)


class Property(BaseModel):
    """Modelo de un inmueble."""
    id: Optional[str] = None
    reference: Optional[str] = None
    title: str = ""
    description: str = ""
    property_type: PropertyType = PropertyType.PISO
    operation: OperationType = OperationType.VENTA
    price: float = 0
    sqm: int = 0
    zone: str = ""
    address: str = ""
    city: str = ""
    features: PropertyFeatures = Field(default_factory=PropertyFeatures)
    community_fee: Optional[float] = None     # Gastos de comunidad
    ibi_tax: Optional[float] = None           # IBI anual
    images: list[str] = Field(default_factory=list)
    status: PropertyStatus = PropertyStatus.DISPONIBLE
    created_at: Optional[datetime] = None


class Message(BaseModel):
    """Un mensaje individual en una conversación."""
    role: str       # "user" o "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    channel: Optional[ChannelType] = None


class Conversation(BaseModel):
    """Historial de conversación con un lead."""
    id: Optional[str] = None
    lead_id: str
    channel: ChannelType
    messages: list[Message] = Field(default_factory=list)
    summary: Optional[str] = None
    updated_at: Optional[datetime] = None


class Appointment(BaseModel):
    """Visita agendada."""
    id: Optional[str] = None
    lead_id: str
    property_id: str
    datetime_: datetime     # Usar datetime_ por conflicto con tipo
    status: AppointmentStatus = AppointmentStatus.PENDIENTE
    agent_name: Optional[str] = None
    calendar_event_id: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None


class Task(BaseModel):
    """Tarea para el equipo humano."""
    id: Optional[str] = None
    lead_id: Optional[str] = None
    type: str               # "llamar", "enviar_info", "seguimiento", etc.
    description: str
    priority: TaskPriority = TaskPriority.MEDIA
    status: TaskStatus = TaskStatus.PENDIENTE
    assigned_to: Optional[str] = None
    due_date: Optional[datetime] = None
    created_at: Optional[datetime] = None


class Review(BaseModel):
    """Reseña de un cliente."""
    id: Optional[str] = None
    lead_id: Optional[str] = None
    platform: str = "google"
    rating: int = Field(ge=1, le=5)
    content: Optional[str] = None
    response: Optional[str] = None
    created_at: Optional[datetime] = None
