-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- Schema de Supabase para el CRM Inmobiliario
-- Ejecutar en Supabase SQL Editor
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

-- Extensión UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─── LEADS ───
CREATE TABLE IF NOT EXISTS leads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT,
    phone TEXT UNIQUE,
    email TEXT,
    channel TEXT DEFAULT 'whatsapp',
    status TEXT DEFAULT 'nuevo',
    score INTEGER DEFAULT 0,
    score_label TEXT DEFAULT 'curioso',
    preferences JSONB DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    assigned_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_contact TIMESTAMPTZ DEFAULT NOW(),
    total_interactions INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_leads_phone ON leads(phone);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_score ON leads(score);

-- ─── PROPERTIES ───
CREATE TABLE IF NOT EXISTS properties (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reference TEXT UNIQUE,
    title TEXT NOT NULL,
    description TEXT,
    property_type TEXT DEFAULT 'piso',
    operation TEXT DEFAULT 'venta',
    price DECIMAL(12,2) DEFAULT 0,
    sqm INTEGER DEFAULT 0,
    zone TEXT,
    address TEXT,
    city TEXT,
    features JSONB DEFAULT '{}',
    community_fee DECIMAL(8,2),
    ibi_tax DECIMAL(8,2),
    images TEXT[] DEFAULT '{}',
    status TEXT DEFAULT 'disponible',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_properties_status ON properties(status);
CREATE INDEX IF NOT EXISTS idx_properties_zone ON properties(zone);
CREATE INDEX IF NOT EXISTS idx_properties_price ON properties(price);
CREATE INDEX IF NOT EXISTS idx_properties_operation ON properties(operation);

-- ─── CONVERSATIONS ───
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id UUID REFERENCES leads(id) ON DELETE CASCADE,
    channel TEXT DEFAULT 'whatsapp',
    messages JSONB DEFAULT '[]',
    summary TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversations_lead ON conversations(lead_id);

-- ─── APPOINTMENTS ───
CREATE TABLE IF NOT EXISTS appointments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id UUID REFERENCES leads(id) ON DELETE CASCADE,
    property_id UUID REFERENCES properties(id),
    datetime_ TIMESTAMPTZ NOT NULL,
    status TEXT DEFAULT 'pendiente',
    agent_name TEXT,
    calendar_event_id TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_appointments_lead ON appointments(lead_id);
CREATE INDEX IF NOT EXISTS idx_appointments_date ON appointments(datetime_);

-- ─── TASKS ───
CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id UUID REFERENCES leads(id) ON DELETE SET NULL,
    type TEXT NOT NULL,
    description TEXT NOT NULL,
    priority TEXT DEFAULT 'media',
    status TEXT DEFAULT 'pendiente',
    assigned_to TEXT,
    due_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority);

-- ─── REVIEWS ───
CREATE TABLE IF NOT EXISTS reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id UUID REFERENCES leads(id) ON DELETE SET NULL,
    platform TEXT DEFAULT 'google',
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    content TEXT,
    response TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- Datos de ejemplo: Propiedades
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

INSERT INTO properties (reference, title, description, property_type, operation, price, sqm, zone, address, city, features, community_fee, ibi_tax, status)
VALUES
    ('REF-001', 'Piso luminoso en el centro', 'Precioso piso reformado con mucha luz natural. Cocina americana equipada, suelos de parquet, ventanas con doble acristalamiento. Ubicado en una zona tranquila pero céntrica, cerca de transporte público y comercios.', 'piso', 'venta', 185000, 85, 'Centro', 'Calle Mayor 15, 3ºB', 'Madrid', '{"bedrooms": 3, "bathrooms": 1, "has_elevator": true, "has_ac": true, "has_heating": true, "floor": 3, "year_built": 2005, "energy_rating": "C", "orientation": "sur"}', 120, 650, 'disponible'),
    
    ('REF-002', 'Ático con terraza panorámica', 'Espectacular ático con terraza de 40m² y vistas despejadas. Salón amplio con acceso directo a terraza, suite principal con baño en suite. Acabados de alta calidad.', 'ático', 'venta', 320000, 110, 'Salamanca', 'Paseo de las Acacias 8', 'Madrid', '{"bedrooms": 2, "bathrooms": 2, "has_terrace": true, "has_elevator": true, "has_ac": true, "has_heating": true, "has_parking": true, "floor": 6, "year_built": 2018, "energy_rating": "B", "orientation": "sur-oeste"}', 200, 1100, 'disponible'),
    
    ('REF-003', 'Estudio moderno junto al metro', 'Estudio completamente reformado, ideal para inversión o primera vivienda. Zona de cocina independiente con electrodomésticos nuevos. Baño completo con plato de ducha. A 2 minutos del metro.', 'estudio', 'venta', 95000, 38, 'Lavapiés', 'Calle Embajadores 22, 1ºA', 'Madrid', '{"bedrooms": 0, "bathrooms": 1, "has_elevator": false, "has_ac": true, "floor": 1, "year_built": 1975, "energy_rating": "D"}', 45, 280, 'disponible'),
    
    ('REF-004', 'Casa con jardín en urbanización', 'Magnífica casa adosada en urbanización privada con piscina comunitaria. Jardín privado, garaje para 2 coches. 3 plantas, amplio salón con chimenea. Zona residencial muy tranquila.', 'casa', 'venta', 410000, 180, 'Las Rozas', 'Urbanización Los Pinos, 14', 'Las Rozas', '{"bedrooms": 4, "bathrooms": 3, "has_parking": true, "has_garden": true, "has_pool": true, "has_storage": true, "has_ac": true, "has_heating": true, "year_built": 2010, "energy_rating": "B"}', 180, 900, 'disponible'),
    
    ('REF-005', 'Piso en alquiler zona universitaria', 'Piso amueblado y equipado, listo para entrar. 3 habitaciones exteriores, salón amplio, cocina con lavaplatos y horno. Calefacción central incluida. Ideal para estudiantes o jóvenes profesionales.', 'piso', 'alquiler', 950, 75, 'Moncloa', 'Avenida Complutense 30, 4ºC', 'Madrid', '{"bedrooms": 3, "bathrooms": 1, "has_elevator": true, "has_heating": true, "floor": 4, "year_built": 1990, "energy_rating": "D"}', 80, 400, 'disponible');
