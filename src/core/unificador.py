# src/core/unificador.py
from typing import List
import copy
from src.core.protocolos import SenalAgente, ItemContexto

class UnificadorEstructural:
    """
    Encargado de realizar el 'Fan-In' (Convergencia) de múltiples ramas de ejecución.
    No concatena texto ciegamente. Preserva la estructura completa de cada agente
    insertándola en la memoria de la señal resultante.
    """

    @staticmethod
    def unificar(senales: List[SenalAgente]) -> SenalAgente:
        if not senales:
            raise ValueError("Se requiere al menos una señal para unificar.")

        # 1. Usamos la primera señal como base para heredar el contexto global (User Input, Trace ID)
        # Es importante hacer deepcopy para no mutar la entrada si se reutilizara.
        maestra = senales[0].copy(deep=True)

        # 2. Limpiamos el análisis previo, ya que esta nueva señal representa
        # un estado "pre-síntesis" donde el nuevo experto aún no ha opinado.
        maestra.analisis = None
        
        # Opcional: Podríamos limpiar el contexto anterior si quisiéramos una señal "pura"
        # con solo los resultados nuevos, pero generalmente queremos preservar la historia.
        # maestra.contexto = [] 

        # 3. Acumuladores
        total_tokens = 0
        nuevos_items_contexto = []

        # 4. Iteramos sobre TODAS las señales (incluida la 0, porque queremos su resultado también)
        for i, senal in enumerate(senales):
            # A. Suma de Costos (Tokens)
            total_tokens += senal.meta.tokens_acumulados

            # B. Inserción Estructural (El núcleo del patrón)
            # Enpaquetamos la señal entera dentro de un ItemContexto.
            # Esto permite al siguiente LLM "ver" todo lo que pensó el experto anterior.
            item_memoria = ItemContexto(
                tipo="memoria_agente_previo",
                contenido=senal # Aquí guardamos el objeto Pydantic completo
            )
            nuevos_items_contexto.append(item_memoria)

        # 5. Actualizamos la Maestra
        maestra.meta.tokens_acumulados = total_tokens
        
        # Agregamos los resultados de los expertos al final del contexto existente
        maestra.contexto.extend(nuevos_items_contexto)
        
        # Marcamos el paso para trazabilidad
        maestra.meta.modelo_ultimo_paso = "system:unificador_estructural"

        return maestra
