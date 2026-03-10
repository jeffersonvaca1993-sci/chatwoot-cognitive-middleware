-- scripts/init_db.sql

-- 1. ACTIVACIÓN DE EXTENSIONES
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. ENUMS (TIPOS DE DATOS PERSONALIZADOS)
DO $$ BEGIN
    CREATE TYPE estado_ciclo_cliente AS ENUM ('prospecto', 'activo', 'riesgo', 'baja');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE rol_empleado AS ENUM ('soporte_nivel_1', 'ventas', 'admin', 'auditor');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE tipo_actor AS ENUM ('ia', 'empleado', 'sistema');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE tipo_desenlace AS ENUM ('respuesta_ia', 'escalada_humano', 'intervencion_humana', 'nota_interna');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- ========================================================
-- TABLA A: IDENTIDAD DE CLIENTES (EXTERNO)
-- ========================================================
CREATE TABLE IF NOT EXISTS clientes_activos (
    id_cliente SERIAL PRIMARY KEY,
    credencial_externa TEXT UNIQUE NOT NULL,
    fecha_registro TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    nombre_alias TEXT DEFAULT 'Cliente',
    contexto_vivo JSONB DEFAULT '{}'::jsonb,
    estado_ciclo estado_ciclo_cliente DEFAULT 'prospecto',
    ultima_actividad TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Campos de Autenticación (para login/registro)
    email TEXT UNIQUE,
    password_hash TEXT,
    session_token TEXT UNIQUE,
    avatar_url TEXT,
    
    -- Campos de Caché (para optimizar llamadas a Chatwoot)
    chatwoot_contact_id INTEGER,
    chatwoot_conversation_id INTEGER,
    chatwoot_pubsub_token TEXT
);

-- Índices para optimizar búsquedas
CREATE INDEX IF NOT EXISTS idx_clientes_email ON clientes_activos(email);
CREATE INDEX IF NOT EXISTS idx_clientes_session_token ON clientes_activos(session_token);
CREATE INDEX IF NOT EXISTS idx_clientes_chatwoot_contact ON clientes_activos(chatwoot_contact_id);

COMMENT ON TABLE clientes_activos IS 'Directorio maestro de usuarios externos (compradores).';
COMMENT ON COLUMN clientes_activos.credencial_externa IS 'Identificador único del cliente en sistemas externos (ej. guest_ABC123).';
COMMENT ON COLUMN clientes_activos.email IS 'Email del cliente (NULL para invitados, requerido para usuarios registrados).';
COMMENT ON COLUMN clientes_activos.password_hash IS 'Hash bcrypt de la contraseña (NULL para invitados).';
COMMENT ON COLUMN clientes_activos.session_token IS 'Token de sesión activo para autenticación stateless.';
COMMENT ON COLUMN clientes_activos.chatwoot_contact_id IS 'ID del contacto en Chatwoot (caché para evitar búsquedas).';
COMMENT ON COLUMN clientes_activos.chatwoot_conversation_id IS 'ID de la conversación activa en Chatwoot (caché).';

-- ========================================================
-- TABLA B: DIRECTORIO DE EMPLEADOS (INTERNO)
-- ========================================================
CREATE TABLE IF NOT EXISTS directorio_empleados (
    id_empleado SERIAL PRIMARY KEY,
    id_agente_chatwoot TEXT UNIQUE,
    nombre_real TEXT NOT NULL,
    departamento TEXT NOT NULL,
    rol_acceso rol_empleado DEFAULT 'soporte_nivel_1',
    esta_activo BOOLEAN DEFAULT TRUE
);
COMMENT ON TABLE directorio_empleados IS 'Nómina interna para gestión de permisos y escalamientos.';

-- ========================================================
-- TABLA C: BÓVEDA DE ACTIVOS (EXPROPIACIÓN)
-- ========================================================
CREATE TABLE IF NOT EXISTS activos_globales (
    id_activo SERIAL PRIMARY KEY,
    id_propietario INT REFERENCES clientes_activos(id_cliente) ON DELETE CASCADE,
    huella_digital_hash TEXT NOT NULL,
    tipo_mime_real TEXT NOT NULL,
    ruta_almacenamiento TEXT NOT NULL,
    nombre_original TEXT,
    tamano_bytes BIGINT,
    creado_en TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_activos_propietario ON activos_globales(id_propietario);
COMMENT ON TABLE activos_globales IS 'Inventario físico de archivos expropiados y verificados.';

-- ========================================================
-- TABLA D: MEMORIA TRANSACCIONAL (EL HISTORIAL)
-- ========================================================
CREATE TABLE IF NOT EXISTS transacciones_agente (
    id_transaccion BIGSERIAL PRIMARY KEY,
    id_cliente INT REFERENCES clientes_activos(id_cliente) NOT NULL,
    fecha_cierre TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    tipo_actor_respuesta tipo_actor NOT NULL,
    id_empleado_responde INT REFERENCES directorio_empleados(id_empleado),
    tipo_desenlace tipo_desenlace NOT NULL,
    destino_escalada TEXT,
    input_usuario TEXT NOT NULL,
    output_respuesta TEXT,
    razonamiento_tecnico TEXT,
    resumen_estado_actual TEXT NOT NULL,
    ids_activos_involucrados JSONB DEFAULT '[]'::jsonb,
    id_orquestacion_kestra TEXT,
    id_mensaje_chatwoot INT
);
CREATE INDEX IF NOT EXISTS idx_transacciones_cliente ON transacciones_agente(id_cliente);
CREATE INDEX IF NOT EXISTS idx_kestra_ref ON transacciones_agente(id_orquestacion_kestra);
CREATE INDEX IF NOT EXISTS idx_chatwoot_ref ON transacciones_agente(id_mensaje_chatwoot);
COMMENT ON TABLE transacciones_agente IS 'Bitácora de unidades de trabajo completadas. Reemplaza el chat log.';

-- ========================================================
-- TABLA E: BASE DE CONOCIMIENTO (LEYES Y NORMAS)
-- ========================================================
CREATE TABLE IF NOT EXISTS base_conocimiento (
    id_fragmento SERIAL PRIMARY KEY,
    contenido_textual TEXT NOT NULL,
    fuente_cita TEXT,
    categoria TEXT,
    vector_embedding vector(1536),
    ultima_actualizacion TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_vector_conocimiento ON base_conocimiento USING hnsw (vector_embedding vector_cosine_ops);
COMMENT ON TABLE base_conocimiento IS 'Biblioteca estática para RAG (Grounding).';

-- ========================================================
-- TABLA F: PUNTEROS DE CONTEXTO (MAPA EXTERNO)
-- ========================================================
CREATE TABLE IF NOT EXISTS punteros_contexto (
    id_puntero SERIAL PRIMARY KEY,
    id_cliente INT REFERENCES clientes_activos(id_cliente) ON DELETE CASCADE,
    sistema_origen TEXT NOT NULL,
    id_externo_referencia TEXT NOT NULL,
    resumen_corto TEXT NOT NULL,
    uri_carga_datos TEXT NOT NULL,
    creado_en TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_punteros_cliente ON punteros_contexto(id_cliente);
COMMENT ON TABLE punteros_contexto IS 'Índice de información externa para carga perezosa.';
