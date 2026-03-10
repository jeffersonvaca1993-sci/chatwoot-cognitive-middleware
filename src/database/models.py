# src/database/models.py
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector

# ==============================================================================
# ENUMS
# ==============================================================================

class EstadoCicloCliente(str, Enum):
    prospecto = "prospecto"
    activo = "activo"
    riesgo = "riesgo"
    baja = "baja"

class RolEmpleado(str, Enum):
    soporte_nivel_1 = "soporte_nivel_1"
    ventas = "ventas"
    admin = "admin"
    auditor = "auditor"

class TipoActor(str, Enum):
    ia = "ia"
    empleado = "empleado"
    sistema = "sistema"

class TipoDesenlace(str, Enum):
    respuesta_ia = "respuesta_ia"
    escalada_humano = "escalada_humano"
    intervencion_humana = "intervencion_humana"
    nota_interna = "nota_interna"

# ==============================================================================
# TABLA A: IDENTIDAD DE CLIENTES (EXTERNO)
# ==============================================================================

class ClientesActivos(SQLModel, table=True):
    __tablename__ = "clientes_activos"
    
    id_cliente: Optional[int] = Field(default=None, primary_key=True)
    credencial_externa: str = Field(unique=True, nullable=False)
    fecha_registro: datetime = Field(default_factory=datetime.now)
    nombre_alias: str = Field(default="Cliente")
    contexto_vivo: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSONB))
    estado_ciclo: EstadoCicloCliente = Field(default=EstadoCicloCliente.prospecto)
    ultima_actividad: datetime = Field(default_factory=datetime.now)
    
    # Campos de Autenticación
    email: Optional[str] = Field(default=None, unique=True, nullable=True)
    password_hash: Optional[str] = Field(default=None, nullable=True)
    session_token: Optional[str] = Field(default=None, unique=True, nullable=True)
    
    # Campos de Caché (optimización de llamadas a Chatwoot)
    chatwoot_contact_id: Optional[int] = Field(default=None, nullable=True)
    chatwoot_conversation_id: Optional[int] = Field(default=None, nullable=True)

    # Relaciones
    activos: List["ActivosGlobales"] = Relationship(back_populates="propietario")
    transacciones: List["TransaccionesAgente"] = Relationship(back_populates="cliente")
    punteros: List["PunterosContexto"] = Relationship(back_populates="cliente")

# ==============================================================================
# TABLA B: DIRECTORIO DE EMPLEADOS (INTERNO)
# ==============================================================================

class DirectorioEmpleados(SQLModel, table=True):
    __tablename__ = "directorio_empleados"

    id_empleado: Optional[int] = Field(default=None, primary_key=True)
    id_agente_chatwoot: Optional[str] = Field(unique=True)
    nombre_real: str = Field(nullable=False)
    departamento: str = Field(nullable=False)
    rol_acceso: RolEmpleado = Field(default=RolEmpleado.soporte_nivel_1)
    esta_activo: bool = Field(default=True)

    # Relaciones
    transacciones_respondidas: List["TransaccionesAgente"] = Relationship(back_populates="empleado_responde")

# ==============================================================================
# TABLA C: BÓVEDA DE ACTIVOS (EXPROPIACIÓN)
# ==============================================================================

class ActivosGlobales(SQLModel, table=True):
    __tablename__ = "activos_globales"

    id_activo: Optional[int] = Field(default=None, primary_key=True)
    id_propietario: int = Field(foreign_key="clientes_activos.id_cliente", ondelete="CASCADE")
    huella_digital_hash: str = Field(nullable=False)
    tipo_mime_real: str = Field(nullable=False)
    ruta_almacenamiento: str = Field(nullable=False)
    nombre_original: Optional[str] = None
    tamano_bytes: Optional[int] = None
    creado_en: datetime = Field(default_factory=datetime.now)

    # Relaciones
    propietario: ClientesActivos = Relationship(back_populates="activos")

# ==============================================================================
# TABLA D: MEMORIA TRANSACCIONAL (EL HISTORIAL)
# ==============================================================================

class TransaccionesAgente(SQLModel, table=True):
    __tablename__ = "transacciones_agente"

    id_transaccion: Optional[int] = Field(default=None, primary_key=True) # BigInt en SQL, int en Python suele bastar
    id_cliente: int = Field(foreign_key="clientes_activos.id_cliente")
    fecha_cierre: datetime = Field(default_factory=datetime.now)
    tipo_actor_respuesta: TipoActor = Field(nullable=False)
    id_empleado_responde: Optional[int] = Field(default=None, foreign_key="directorio_empleados.id_empleado")
    tipo_desenlace: TipoDesenlace = Field(nullable=False)
    destino_escalada: Optional[str] = None
    input_usuario: str = Field(nullable=False)
    output_respuesta: Optional[str] = None
    razonamiento_tecnico: Optional[str] = None
    intencion_detectada: Optional[str] = Field(default=None, description="Intención clasificada por el experto (ej: SOLICITUD_VISA)")
    resumen_estado_actual: str = Field(nullable=False)
    ids_activos_involucrados: List[int] = Field(default=[], sa_column=Column(JSONB))
    id_orquestacion_kestra: Optional[str] = Field(default=None, index=True)
    id_mensaje_chatwoot: Optional[int] = Field(default=None, index=True)

    # Relaciones
    cliente: ClientesActivos = Relationship(back_populates="transacciones")
    empleado_responde: Optional[DirectorioEmpleados] = Relationship(back_populates="transacciones_respondidas")

# ==============================================================================
# TABLA E: BASE DE CONOCIMIENTO (LEYES Y NORMAS)
# ==============================================================================

class BaseConocimiento(SQLModel, table=True):
    __tablename__ = "base_conocimiento"

    id_fragmento: Optional[int] = Field(default=None, primary_key=True)
    contenido_textual: str = Field(nullable=False)
    fuente_cita: Optional[str] = None
    categoria: Optional[str] = None
    # Vector de 768 dimensiones (Gemini text-embedding-004 standard)
    vector_embedding: List[float] = Field(sa_column=Column(Vector(768)))
    ultima_actualizacion: datetime = Field(default_factory=datetime.now)

# ==============================================================================
# TABLA F: PUNTEROS DE CONTEXTO (MAPA EXTERNO)
# ==============================================================================

class PunterosContexto(SQLModel, table=True):
    __tablename__ = "punteros_contexto"

    id_puntero: Optional[int] = Field(default=None, primary_key=True)
    id_cliente: int = Field(foreign_key="clientes_activos.id_cliente", ondelete="CASCADE")
    sistema_origen: str = Field(nullable=False)
    id_externo_referencia: str = Field(nullable=False)
    resumen_corto: str = Field(nullable=False)
    uri_carga_datos: str = Field(nullable=False)
    creado_en: datetime = Field(default_factory=datetime.now)

    # Relaciones
    cliente: ClientesActivos = Relationship(back_populates="punteros")
