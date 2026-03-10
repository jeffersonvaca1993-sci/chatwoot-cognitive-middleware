-- scripts/update_schema_auth.sql

-- Agregar columnas para autenticación en clientes_activos
ALTER TABLE clientes_activos 
ADD COLUMN IF NOT EXISTS email TEXT UNIQUE,
ADD COLUMN IF NOT EXISTS password_hash TEXT;

-- Comentario para documentación
COMMENT ON COLUMN clientes_activos.email IS 'Email para login (opcional, puede ser NULL para invitados)';
COMMENT ON COLUMN clientes_activos.password_hash IS 'Hash bcrypt de la contraseña';
