# 🔄 Migraciones de Base de Datos

Este directorio contiene scripts de migración SQL para actualizar el schema de la base de datos en ambientes de desarrollo y producción.

## 📋 Convenciones

### Nomenclatura de Archivos
```
NNN_descripcion_corta.sql
```

- `NNN`: Número secuencial de 3 dígitos (001, 002, etc.)
- `descripcion_corta`: Descripción en snake_case
- Ejemplo: `001_add_chatwoot_cache.sql`

### Estructura de Migración

Cada archivo debe contener:

1. **Header**: Comentario con fecha, propósito y descripción
2. **Cambios**: Sentencias SQL idempotentes (usar `IF NOT EXISTS`)
3. **Verificación**: Queries para validar la migración
4. **Rollback**: Comentado al final para revertir si es necesario

## 🚀 Cómo Ejecutar Migraciones

### Desarrollo (Local)

```bash
# Ejecutar una migración específica
docker exec -i moe_postgres psql -U postgres -d chatwoot_production < scripts/migrations/001_add_chatwoot_cache.sql

# Ver resultado
docker exec moe_postgres psql -U postgres -d chatwoot_production -c "\d clientes_activos"
```

### Producción

⚠️ **IMPORTANTE**: Siempre hacer backup antes de migrar en producción

```bash
# 1. Backup de la base de datos
docker exec moe_postgres pg_dump -U postgres chatwoot_production > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. Ejecutar migración
docker exec -i moe_postgres psql -U postgres -d chatwoot_production < scripts/migrations/001_add_chatwoot_cache.sql

# 3. Verificar
docker exec moe_postgres psql -U postgres -d chatwoot_production -c "SELECT COUNT(*) FROM clientes_activos WHERE chatwoot_contact_id IS NOT NULL;"
```

## 📝 Registro de Migraciones

| # | Archivo | Fecha | Descripción | Estado |
|---|---------|-------|-------------|--------|
| 001 | `001_add_chatwoot_cache.sql` | 2025-11-26 | Agregar campos de caché de IDs de Chatwoot | ✅ Listo |

## 🔍 Verificar Estado de la BD

```bash
# Ver todas las columnas de clientes_activos
docker exec moe_postgres psql -U postgres -d chatwoot_production -c "\d clientes_activos"

# Ver índices
docker exec moe_postgres psql -U postgres -d chatwoot_production -c "\di"

# Ver datos de ejemplo
docker exec moe_postgres psql -U postgres -d chatwoot_production -c "SELECT id_cliente, credencial_externa, chatwoot_contact_id, chatwoot_conversation_id FROM clientes_activos LIMIT 5;"
```

## ⚠️ Troubleshooting

### Error: "column already exists"

Si ya ejecutaste la migración parcialmente:

```sql
-- Verificar qué columnas existen
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'clientes_activos';
```

Las migraciones usan `IF NOT EXISTS` para ser idempotentes.

### Rollback de Migración

Cada migración tiene un bloque comentado al final con las sentencias de rollback:

```sql
-- ROLLBACK
-- ALTER TABLE clientes_activos DROP COLUMN IF EXISTS chatwoot_contact_id;
```

Descomenta y ejecuta solo si es necesario revertir.

## 🎯 Próximas Migraciones Planeadas

- [ ] `002_add_intencion_detectada.sql`: Agregar campo a transacciones_agente
- [ ] `003_populate_transacciones.sql`: Migrar mensajes históricos de Chatwoot
- [ ] `004_add_embedding_dimension.sql`: Cambiar dimensión de embeddings si es necesario

---

**Mantenido por:** Equipo de Desarrollo  
**Última actualización:** 2025-11-26
