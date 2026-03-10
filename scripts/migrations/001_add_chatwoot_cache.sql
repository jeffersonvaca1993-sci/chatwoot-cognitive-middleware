-- ============================================================================
-- MIGRACIÓN: Agregar campos de caché de Chatwoot
-- Fecha: 2025-11-26
-- Propósito: Optimizar latencia de mensajes cacheando IDs de Chatwoot
-- ============================================================================

-- 1. Agregar columnas de caché (si no existen)
ALTER TABLE clientes_activos 
ADD COLUMN IF NOT EXISTS chatwoot_contact_id INTEGER,
ADD COLUMN IF NOT EXISTS chatwoot_conversation_id INTEGER;

-- 2. Crear índices para optimizar búsquedas
CREATE INDEX IF NOT EXISTS idx_clientes_chatwoot_contact 
ON clientes_activos(chatwoot_contact_id);

CREATE INDEX IF NOT EXISTS idx_clientes_chatwoot_conversation 
ON clientes_activos(chatwoot_conversation_id);

-- 3. Agregar comentarios descriptivos
COMMENT ON COLUMN clientes_activos.chatwoot_contact_id IS 
'ID del contacto en Chatwoot (caché para evitar búsquedas HTTP)';

COMMENT ON COLUMN clientes_activos.chatwoot_conversation_id IS 
'ID de la conversación activa en Chatwoot (caché para envío rápido de mensajes)';

-- 4. Poblar caché con datos existentes (si hay contactos en Chatwoot)
-- NOTA: Esto asume que tienes la tabla 'contacts' de Chatwoot en la misma BD

-- Sincronizar contact_id
UPDATE clientes_activos ca
SET chatwoot_contact_id = ct.id
FROM contacts ct
WHERE ca.credencial_externa = ct.identifier
  AND ca.chatwoot_contact_id IS NULL;

-- Sincronizar conversation_id (solo la más reciente por inbox)
UPDATE clientes_activos ca
SET chatwoot_conversation_id = conv.id
FROM contacts ct
JOIN conversations conv ON ct.id = conv.contact_id
WHERE ca.credencial_externa = ct.identifier
  AND ca.chatwoot_conversation_id IS NULL
  AND conv.inbox_id = 1  -- ⚠️ CAMBIAR POR TU INBOX_ID
  AND conv.id = (
    SELECT MAX(c2.id) 
    FROM conversations c2 
    WHERE c2.contact_id = ct.id 
      AND c2.inbox_id = 1  -- ⚠️ CAMBIAR POR TU INBOX_ID
  );

-- 5. Verificar resultados
SELECT 
    COUNT(*) FILTER (WHERE chatwoot_contact_id IS NOT NULL) as clientes_con_cache_contact,
    COUNT(*) FILTER (WHERE chatwoot_conversation_id IS NOT NULL) as clientes_con_cache_conversation,
    COUNT(*) as total_clientes
FROM clientes_activos;

-- 6. Mostrar clientes sin caché (para debugging)
SELECT 
    id_cliente,
    credencial_externa,
    nombre_alias,
    chatwoot_contact_id,
    chatwoot_conversation_id
FROM clientes_activos
WHERE chatwoot_contact_id IS NULL
   OR chatwoot_conversation_id IS NULL;

-- ============================================================================
-- ROLLBACK (en caso de necesitar revertir)
-- ============================================================================
-- ALTER TABLE clientes_activos DROP COLUMN IF EXISTS chatwoot_contact_id;
-- ALTER TABLE clientes_activos DROP COLUMN IF EXISTS chatwoot_conversation_id;
-- DROP INDEX IF EXISTS idx_clientes_chatwoot_contact;
-- DROP INDEX IF EXISTS idx_clientes_chatwoot_conversation;
