#Reporte de Migración Arquitectónica: De Orquestación Externa a Grafo de Estado en Memoria

**Fecha:** 27 de Noviembre de 2025
**Proyecto:** ChatGravity MoE (Mixture of Experts)
**Estado:** Aprobado para Implementación

## 1. Resumen Ejecutivo

Este documento formaliza la decisión estratégica de abandonar la orquestación basada en flujos externos (Kestra/Prefect) en favor de una arquitectura de grafos con estado en memoria (**LangGraph**). El objetivo principal es reducir la latencia de inferencia, garantizar la integridad transaccional en ejecuciones paralelas y unificar el modelo de datos bajo un protocolo simétrico.

## 2. Diagnóstico de la Arquitectura Anterior (Legacy)

La implementación inicial basada en Kestra presentaba limitaciones críticas para un sistema conversacional en tiempo real:

* **Latencia por Protocolo:** Cada transición entre expertos requería una llamada HTTP completa (serialización/deserialización JSON), añadiendo cientos de milisegundos de *overhead* innecesario.
* **Fricción en Ciclos:** La implementación de bucles conversacionales (`while` user is active) en un DAG estático resultaba en patrones de "recursión infinita" o re-ejecuciones de flujo costosas.
* **Estado Fragmentado:** La memoria de la conversación vivía dividida entre el payload de Kestra y bases de datos volátiles, dificultando la coherencia en ramificaciones paralelas.

## 3. Nueva Arquitectura: Grafo Simétrico Stateful (LangGraph)

Se adopta **LangGraph** como motor de ejecución, incrustado directamente en el servicio de Python.

### 3.1. Principios Fundamentales
1.  **Ejecución en Memoria (In-Process):** Los nodos expertos son funciones asíncronas que comparten el mismo espacio de memoria, eliminando la latencia de red entre pasos.
2.  **Simetría de Protocolo:** El grafo es un sistema cerrado donde la entrada y la salida son idénticas (`SenalAgente` $\to$ `SenalAgente`). La API actúa meramente como un adaptador I/O.
3.  **Persistencia Híbrida:**
    * **RAM (Estado Caliente):** Para la ejecución activa del grafo y el paso de archivos pesados entre expertos.
    * **Postgres (Checkpointers):** Para la recuperación ante fallos y persistencia de sesiones.
    * **Redis (Cola de Entrada):** Exclusivamente como buffer de desacoplamiento para mensajes entrantes asíncronos.

## 4. Diseño del Estado: El Patrón "God Object" Protegido

Para resolver los problemas de concurrencia en el patrón *Fan-Out/Fan-In* (Ejecución paralela de expertos), se ha redefinido el objeto `SenalAgente` para actuar simultáneamente como DTO público y Estado privado.

### Estructura de `SenalAgente`
* **Capa Pública (Inmutable):** Identidad del cliente (`PerfilCliente`), Entrada (`Mensaje`), Historial y Directorio de Archivos. Visible para la API.
* **Capa Privada (Infraestructura):**
    * `buffer_ramas`: Lista acumulativa (`operator.add`) para recolectar resultados de expertos paralelos sin condiciones de carrera.
    * `almacen_activos`: Diccionario fusionable (`operator.ior`) que actúa como sistema de archivos en RAM para evitar re-descargas.
    * **Seguridad:** Estos campos están marcados con `exclude=True`, garantizando que nunca se expongan en la respuesta HTTP.

## 5. Beneficios Técnicos

| Dimensión | Arquitectura Anterior (Kestra) | Nueva Arquitectura (LangGraph) |
| :--- | :--- | :--- |
| **Latencia entre Nodos** | Alta (~50-200ms por salto HTTP) | Despreciable (<1ms, paso de referencia en RAM) |
| **Manejo de Archivos** | Ineficiente (Pase por valor o re-descarga) | Óptimo (Referencia en `almacen_activos` compartido) |
| **Concurrencia** | Compleja (Race conditions en escrituras DB) | Gestionada (Reducers deterministas en el Grafo) |
| **Desarrollo** | Disperso (YAML + Código) | Unificado (100% Python, tipado fuerte con Pydantic) |

## 6. Conclusión y Siguientes Pasos

La migración a LangGraph no es solo un cambio de herramienta, es una evolución hacia un sistema operativo de agentes. Al centralizar el estado en `SenalAgente` y proteger la lógica de negocio con `EstrategiaSegura`, hemos creado una base escalable y auditable.

**Acción Inmediata:** Proceder con la refactorización de `src/core/protocolos.py` según la especificación "Espejo de Base de Datos" y la implementación de la fábrica de nodos.


# Reporte de Migración Arquitectónica: De Orquestación Externa a Grafo de Estado en Memoria

**Fecha:** 27 de Noviembre de 2025
**Proyecto:** ChatGravity MoE (Mixture of Experts)
**Estado:** Aprobado para Implementación

## 1\. Resumen Ejecutivo

Este documento formaliza la decisión estratégica de abandonar la orquestación basada en flujos externos (Kestra/Prefect) en favor de una arquitectura de grafos con estado en memoria (**LangGraph**). El objetivo principal es reducir la latencia de inferencia, garantizar la integridad transaccional en ejecuciones paralelas y unificar el modelo de datos bajo un protocolo simétrico.

## 2\. Diagnóstico de la Arquitectura Anterior (Legacy)

La implementación inicial basada en Kestra presentaba limitaciones críticas para un sistema conversacional en tiempo real:

  * **Latencia por Protocolo:** Cada transición entre expertos requería una llamada HTTP completa (serialización/deserialización JSON), añadiendo cientos de milisegundos de *overhead* innecesario.
  * **Fricción en Ciclos:** La implementación de bucles conversacionales (`while` user is active) en un DAG estático resultaba en patrones de "recursión infinita" o re-ejecuciones de flujo costosas.
  * **Estado Fragmentado:** La memoria de la conversación vivía dividida entre el payload de Kestra y bases de datos volátiles, dificultando la coherencia en ramificaciones paralelas.

## 3\. Nueva Arquitectura: Grafo Simétrico Stateful (LangGraph)

Se adopta **LangGraph** como motor de ejecución, incrustado directamente en el servicio de Python.

### 3.1. Principios Fundamentales

1.  **Ejecución en Memoria (In-Process):** Los nodos expertos son funciones asíncronas que comparten el mismo espacio de memoria, eliminando la latencia de red entre pasos.
2.  **Simetría de Protocolo:** El grafo es un sistema cerrado donde la entrada y la salida son idénticas (`SenalAgente` $\to$ `SenalAgente`). La API actúa meramente como un adaptador I/O.
3.  **Persistencia Híbrida:**
      * **RAM (Estado Caliente):** Para la ejecución activa del grafo y el paso de archivos pesados entre expertos.
      * **Postgres (Checkpointers):** Para la recuperación ante fallos y persistencia de sesiones.
      * **Redis (Cola de Entrada):** Exclusivamente como buffer de desacoplamiento para mensajes entrantes asíncronos.

## 4\. Diseño del Estado: El Patrón "God Object" Protegido

Para resolver los problemas de concurrencia en el patrón *Fan-Out/Fan-In* (Ejecución paralela de expertos), se ha redefinido el objeto `SenalAgente` para actuar simultáneamente como DTO público y Estado privado.

### Estructura de `SenalAgente`

  * **Capa Pública (Inmutable):** Identidad del cliente (`PerfilCliente` - Espejo DB), Entrada (`Mensaje`), Historial y Mapa de Archivos. Visible para la API.
  * **Capa Privada (Infraestructura):**
      * `buffer_ramas`: Lista acumulativa (`operator.add`) para recolectar resultados de expertos paralelos sin condiciones de carrera.
      * `almacen_activos`: Diccionario fusionable (`operator.ior`) que actúa como sistema de archivos en RAM para evitar re-descargas.
      * **Seguridad:** Estos campos están marcados con `exclude=True`, garantizando que nunca se expongan en la respuesta HTTP.

## 5\. Beneficios Técnicos

| Dimensión | Arquitectura Anterior (Kestra) | Nueva Arquitectura (LangGraph) |
| :--- | :--- | :--- |
| **Latencia entre Nodos** | Alta (\~50-200ms por salto HTTP) | Despreciable (\<1ms, paso de referencia en RAM) |
| **Manejo de Archivos** | Ineficiente (Pase por valor o re-descarga) | Óptimo (Referencia en `almacen_activos` compartido) |
| **Concurrencia** | Compleja (Race conditions en escrituras DB) | Gestionada (Reducers deterministas en el Grafo) |
| **Desarrollo** | Disperso (YAML + Código) | Unificado (100% Python, tipado fuerte con Pydantic) |

-----

# Especificación del Protocolo Maestro (`SenalAgente`)

**Versión del Protocolo:** 2.0 (Stateful & Database Mirroring)
**Objetivo:** Definir el objeto único de transferencia que alinea la memoria del grafo con la persistencia de la base de datos.

## 1\. Modelos Espejo (Base de Datos $\leftrightarrow$ Memoria)

Estos objetos replican la estructura exacta de las tablas SQL para facilitar la carga y guardado (`Hydration/Persistence`), eliminando la necesidad de traductores complejos.

### 1.1. Identidad (`PerfilCliente`)

*Refleja la tabla `clientes_activos`.*

  * **Campos:** `id_cliente` (PK), `credencial_externa`, `nombre_alias`, `estado_ciclo`, `contexto_vivo` (JSONB dinámico).
  * **Uso:** Inyectado al inicio del flujo por el Orquestador. Permite a los expertos conocer el segmento y datos biográficos del usuario sin consultas SQL adicionales.

### 1.2. Bóveda de Archivos (`ActivoGlobal`)

*Refleja la tabla `activos_globales` + Payload en RAM.*

  * **Campos DB:** `huella_digital_hash` (PK Lógica), `tipo_mime_real`, `nombre_original`, `ruta_almacenamiento`.
  * **Campos Memoria:** `contenido_puro` (Bytes/Texto). Marcado con `exclude=True` para no serializar en logs o API.
  * **Lógica:** Auto-cálculo de Hash SHA-256 al instanciar.

## 2\. La Señal Maestra (`SenalAgente`)

Objeto inmutable (`frozen=True`) que actúa como Estado del Grafo.

### 2.1. Capa Pública (Visible en API/Logs)

Datos transaccionales y de negocio.

```python
class SenalAgente(BaseModel):
    perfil: PerfilCliente          # Quién es
    entrada: Entrada               # Qué dijo ahora
    meta: Metadatos                # Trazabilidad (Tokens, ID)
    historial_chat: List[Mensaje]  # Contexto conversacional
    mapa_archivos: List[str]       # Lista de Hashes (Punteros a archivos activos)
    analisis: Optional[Analisis]   # Conclusión final unificada
```

### 2.2. Capa Privada (Infraestructura del Grafo)

Buffers de gestión de concurrencia y almacenamiento pesado. Invisibles fuera del runtime.

```python
    # Buffer para Fan-Out (Paralelismo)
    # Permite que múltiples expertos escriban resultados simultáneamente.
    buffer_ramas: Annotated[List[AnalisisCognitivo], operator.add] = Field(exclude=True)

    # Almacén de Archivos (RAM Disk)
    # Diccionario {hash: ActivoGlobal} fusionable.
    almacen_activos: Annotated[Dict[str, ActivoGlobal], operator.ior] = Field(exclude=True)
```

## 3\. Ciclo de Vida del Dato

1.  **Hidratación (Entrada):** El Endpoint recibe un mensaje $\to$ Carga `PerfilCliente` de DB $\to$ Crea `SenalAgente` vacía.
2.  **Ejecución (Nodos):**
      * Los expertos leen `perfil` y `entrada`.
      * Si generan archivos, crean `ActivoGlobal` y lo retornan (se fusiona en `almacen_activos`).
      * Si generan ideas, crean `AnalisisCognitivo` y lo retornan (se apila en `buffer_ramas`).
3.  **Unificación (Join):** El nodo Unificador lee `buffer_ramas`, consolida la respuesta y escribe en `analisis` (público).
4.  **Persistencia (Salida):** El orquestador guarda `almacen_activos` nuevos en disco/DB y registra la transacción.
5.  **Respuesta:** La API devuelve el JSON de `SenalAgente` (los campos privados desaparecen automáticamente).

# Estándar de Desarrollo Seguro: Protocolo de Inmutabilidad y Aislamiento para Expertos

**Fecha:** 27 de Noviembre de 2025
**Proyecto:** ChatGravity MoE
**Alcance:** Todos los nuevos Agentes/Expertos

## 1\. Objetivo

Establecer un marco de trabajo que impida condiciones de carrera y corrupción de estado en la ejecución paralela de expertos. Este estándar elimina la responsabilidad del desarrollador de gestionar la infraestructura del grafo, forzando un enfoque en la lógica de negocio pura.

## 2\. Reglas de Oro (Inmutabilidad)

### 2.1. Prohibición de Mutación Directa

El objeto `SenalAgente` es **inmutable** (`frozen=True`). Cualquier intento de modificar sus campos directamente (`senal.entrada = "x"`) provocará una excepción `ValidationError` en tiempo de ejecución.

### 2.2. Auto-Hashing de Archivos

No se permite asignar IDs manuales a los archivos. La clase `ActivoGlobal` (espejo de `BloqueDatosReal`) calculará automáticamente el hash SHA-256 de su contenido al instanciarse. Esto garantiza que el mismo archivo siempre tenga el mismo ID, sin importar qué experto lo genere.

## 3\. Patrón de Implementación: `EstrategiaSegura`

Todo experto debe heredar de `EstrategiaSegura` y está **estrictamente prohibido** que manipule los buffers internos (`buffer_ramas`, `almacen_activos`).

### 3.1. El Contrato de Retorno

El método `_procesar_negocio` solo puede devolver objetos de valor de negocio, nunca la señal completa.

  * **Para Conclusiones:** Devolver `AnalisisCognitivo`.
  * **Para Archivos (Carga Silenciosa):** Devolver `List[ActivoGlobal]`.
  * **Para Archivos + Notificación:** Devolver `List[ProduccionArchivo]`.

### 3.2. Código de Referencia Obligatorio

**Clase Base (`src/expertos/base.py`):**

```python
class EstrategiaSegura(ABC):
    async def ejecutar_simetrico(self, senal: SenalAgente) -> SenalAgente:
        # FONTANERÍA AUTOMÁTICA (NO MODIFICAR)
        # 1. Ejecuta lógica de negocio en sandbox
        resultado = await self._procesar_negocio(senal)
        
        updates = {}
        # 2. Inyección segura en buffers privados
        if isinstance(resultado, AnalisisCognitivo):
            updates["buffer_ramas"] = [resultado]
        elif isinstance(resultado, list):
            # Mapeo automático de archivos al almacén
            if all(isinstance(x, ActivoGlobal) for x in resultado):
                updates["almacen_activos"] = {b.huella_digital_hash: b for b in resultado}
                
        # 3. Retorno de nueva versión inmutable
        return senal.model_copy(update=updates, deep=True)

    @abstractmethod
    async def _procesar_negocio(self, senal: SenalAgente) -> ResultadoNegocio:
        """Espacio de trabajo del desarrollador."""
        pass
```

## 4\. Guía de Auditoría de Código (Checklist)

Antes de aprobar un PR con un nuevo experto, verificar:

1.  [ ] **Herencia:** ¿La clase hereda de `EstrategiaSegura`? (Si hereda de `EstrategiaBase` antigua, rechazar).
2.  [ ] **Inmutabilidad:** ¿El código intenta hacer `senal.campo = valor`? (Debe fallar).
3.  [ ] **Retorno:** ¿Devuelve objetos de dominio (`AnalisisCognitivo`, `ActivoGlobal`) y NO diccionarios sueltos o la señal modificada?
4.  [ ] **Hashing:** ¿Se está inicializando `ActivoGlobal` sin pasar manualmente un hash? (Correcto: dejar que se autocalcule).

## 5\. Excepciones

No existen excepciones para este estándar en el código de producción. Cualquier manipulación directa del estado del grafo debe realizarse únicamente en el **Nodo Unificador** o en el **Orquestador**.


# Guía de Implementación de Nodos: Patrones de Fábrica y Gestión de Concurrencia

**Fecha:** 27 de Noviembre de 2025
**Proyecto:** ChatGravity MoE
**Destinatarios:** Equipo de Desarrollo Backend

## 1\. Objetivo

Estandarizar la creación e integración de nodos expertos dentro del grafo de LangGraph. Esta guía define cómo transformar la lógica de negocio pura (`EstrategiaSegura`) en nodos ejecutables, garantizando la seguridad de tipos y la gestión automática de concurrencia.

## 2\. El Patrón "Fábrica de Nodos"

Para desacoplar la lógica de negocio de la infraestructura del grafo, no escribimos funciones de nodo manualmente. Utilizamos un adaptador genérico que envuelve nuestras estrategias.

### 2.1. El Adaptador Universal (`src/orquestacion/adaptador.py`)

Este componente es el puente entre `EstrategiaSegura` y LangGraph.

  * **Responsabilidad:** Instanciar la estrategia, ejecutarla y traducir su respuesta (Negocio) a actualizaciones de estado (Infraestructura).
  * **Manejo de Estado:** No devuelve la `SenalAgente` completa. Devuelve un diccionario de "Deltas" (cambios) para que el motor de LangGraph aplique los *reducers* (`operator.add` / `operator.ior`).

<!-- end list -->

```python
def crear_nodo_experto(ClaseEstrategia: type[EstrategiaSegura]):
    """
    Genera una función asíncrona compatible con workflow.add_node().
    """
    async def nodo_wrapper(state: SenalAgente):
        # 1. Instanciación Efímera
        estrategia = ClaseEstrategia()
        
        # 2. Ejecución en Sandbox
        # La estrategia devuelve una SenalAgente modificada internamente,
        # pero nosotros extraemos solo lo que debe persistir en los buffers privados.
        resultado_senal = await estrategia.ejecutar_simetrico(state)
        
        # 3. Retorno de Deltas (Para Reducers de LangGraph)
        updates = {}
        
        # A. Si hay análisis, va al buffer de ramas (Lista)
        if resultado_senal.buffer_ramas:
            updates["buffer_ramas"] = resultado_senal.buffer_ramas
            
        # B. Si hay archivos, van al almacén (Diccionario)
        if resultado_senal.almacen_activos:
            updates["almacen_activos"] = resultado_senal.almacen_activos
            
        # C. Si hay cambios públicos (Directorio), se actualizan
        # Nota: Esto solo aplica en secuencias lineales. En paralelo, solo se usan A y B.
        if resultado_senal.directorio != state.directorio:
            updates["directorio"] = resultado_senal.directorio

        return updates

    return nodo_wrapper
```

## 3\. Implementación de una Nueva Estrategia

El desarrollador solo interactúa con `src/expertos/base.py`.

### Pasos para crear un experto:

1.  Heredar de `EstrategiaSegura`.
2.  Implementar `_procesar_negocio(self, senal: SenalAgente)`.
3.  Retornar `AnalisisCognitivo` (pensamiento) o `List[ActivoGlobal]` (archivos).

**Ejemplo:**

```python
class ExpertoFiscal(EstrategiaSegura):
    async def _procesar_negocio(self, senal: SenalAgente) -> AnalisisCognitivo:
        # Lógica pura de negocio
        return AnalisisCognitivo(
            intencion_detectada="EVASION",
            razonamiento="Detectada inconsistencia en montos.",
            accion_sugerida="NOTIFICAR_AUDITORIA"
        )
```

## 4\. Ensamblaje en el Grafo (Wiring)

La conexión en el grafo se realiza utilizando la fábrica.

```python
# src/core/grafo.py
from langgraph.graph import StateGraph
from src.orquestacion.adaptador import crear_nodo_experto

def construir_grafo():
    wf = StateGraph(SenalAgente)
    
    # REGISTRO DE NODOS
    wf.add_node("fiscal", crear_nodo_experto(ExpertoFiscal))
    wf.add_node("legal", crear_nodo_experto(ExpertoLegal))
    wf.add_node("unificar", nodo_unificador) # Nodo especial manual
    
    # CONEXIONES (Fan-Out)
    wf.set_entry_point("router")
    wf.add_conditional_edges("router", lambda x: ["fiscal", "legal"])
    
    # CONEXIONES (Fan-In)
    wf.add_edge("fiscal", "unificar")
    wf.add_edge("legal", "unificar")
    
    return wf.compile()
```

## 5\. Modelo de Concurrencia (Fan-Out/Fan-In)

### 5.1. Escritura Paralela

Cuando `fiscal` y `legal` se ejecutan simultáneamente:

  * Ambos leen la misma versión de `SenalAgente` (copia inmutable).
  * Ambos escriben en `buffer_ramas`.
  * LangGraph serializa las escrituras usando `operator.add`, resultando en una lista: `[AnalisisFiscal, AnalisisLegal]`.

### 5.2. Lectura Unificada

El nodo `unificar` es el único autorizado para vaciar los buffers.

```python
async def nodo_unificador(senal: SenalAgente):
    resultados = senal.buffer_ramas # Lista completa
    analisis_final = fusionar(resultados)
    
    return {
        "analisis": analisis_final, # Escribe en público
        "buffer_ramas": []          # Limpia el buffer privado
    }
```

## 6\. Manejo de Archivos (Ciclo de Vida)

1.  **Creación:** El experto instancia `ActivoGlobal(contenido=bytes)`. El hash se autocalcula.
2.  **Retorno:** El experto retorna `[ActivoGlobal]`.
3.  **Persistencia RAM:** El adaptador inyecta el archivo en `senal.almacen_activos` usando el hash como clave.
4.  **Consumo:** Otros expertos buscan el hash en `senal.mapa_archivos` y recuperan el contenido de `senal.almacen_activos`.