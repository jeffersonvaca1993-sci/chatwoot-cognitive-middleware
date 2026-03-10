"""
Observador de llamadas a LLMs para desarrollo.
Reemplazará a Langfuse cuando esté disponible en producción.

Registra TODAS las llamadas a LLMs con detalles completos.
Formato legible para humanos.
Un archivo por ejecución (cada vez que se levanta Docker).
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import json


class ObservadorLLM:
    """
    Observador de llamadas a LLMs que guarda en archivos .txt planos.
    
    Interfaz compatible con Langfuse para migración futura.
    Registra todas las llamadas con detalles completos.
    """
    
    def __init__(self):
        # Crear carpeta de logs si no existe
        self.logs_dir = Path("src/observadores/logs/llm")
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Nombre del archivo con fecha y hora
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.logs_dir / f"llm_trace_{timestamp}.txt"
        
        # Contador de llamadas
        self.call_count = 0
        
        # Escribir encabezado
        self._escribir_encabezado()
    
    def _escribir_encabezado(self):
        """Escribe el encabezado del archivo de log."""
        with open(self.log_file, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write(f"OBSERVADOR DE LLAMADAS A LLMs - ChatGravity MoE\n")
            f.write(f"Iniciado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
    
    def registrar_llamada(
        self,
        modelo: str,
        prompt: str,
        respuesta: str,
        tokens_prompt: int,
        tokens_respuesta: int,
        tokens_totales: int,
        latencia_ms: float,
        costo_estimado: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ):
        """
        Registra una llamada a un LLM.
        
        Args:
            modelo: Nombre del modelo (ej: "gpt-4", "claude-3-opus")
            prompt: Prompt enviado al LLM
            respuesta: Respuesta recibida del LLM
            tokens_prompt: Tokens del prompt
            tokens_respuesta: Tokens de la respuesta
            tokens_totales: Total de tokens
            latencia_ms: Latencia en milisegundos
            costo_estimado: Costo estimado en USD (opcional)
            metadata: Metadata adicional (opcional)
            error: Mensaje de error si la llamada falló (opcional)
        """
        self.call_count += 1
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            # Encabezado de la llamada
            f.write("=" * 80 + "\n")
            f.write(f"LLAMADA #{self.call_count}\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write("=" * 80 + "\n\n")
            
            # Información del modelo
            f.write("📊 MODELO\n")
            f.write(f"  Nombre: {modelo}\n")
            f.write(f"  Latencia: {latencia_ms:.2f} ms\n")
            if costo_estimado is not None:
                f.write(f"  Costo estimado: ${costo_estimado:.6f} USD\n")
            f.write("\n")
            
            # Tokens
            f.write("🔢 TOKENS\n")
            f.write(f"  Prompt: {tokens_prompt:,}\n")
            f.write(f"  Respuesta: {tokens_respuesta:,}\n")
            f.write(f"  Total: {tokens_totales:,}\n")
            f.write("\n")
            
            # Metadata adicional
            if metadata:
                f.write("📋 METADATA\n")
                for key, value in metadata.items():
                    f.write(f"  {key}: {value}\n")
                f.write("\n")
            
            # Prompt
            f.write("📝 PROMPT\n")
            f.write("-" * 80 + "\n")
            f.write(prompt)
            f.write("\n" + "-" * 80 + "\n\n")
            
            # Respuesta o Error
            if error:
                f.write("❌ ERROR\n")
                f.write("-" * 80 + "\n")
                f.write(error)
                f.write("\n" + "-" * 80 + "\n\n")
            else:
                f.write("✅ RESPUESTA\n")
                f.write("-" * 80 + "\n")
                f.write(respuesta)
                f.write("\n" + "-" * 80 + "\n\n")
            
            f.write("\n\n")
    
    def registrar_trace(
        self,
        trace_id: str,
        nombre: str,
        input_data: Any,
        output_data: Any,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Registra una traza completa (compatible con Langfuse).
        
        Args:
            trace_id: ID único de la traza
            nombre: Nombre de la traza
            input_data: Datos de entrada
            output_data: Datos de salida
            metadata: Metadata adicional (opcional)
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write(f"🔍 TRAZA: {nombre}\n")
            f.write(f"ID: {trace_id}\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write("=" * 80 + "\n\n")
            
            if metadata:
                f.write("📋 METADATA\n")
                for key, value in metadata.items():
                    f.write(f"  {key}: {value}\n")
                f.write("\n")
            
            f.write("📥 INPUT\n")
            f.write("-" * 80 + "\n")
            f.write(str(input_data))
            f.write("\n" + "-" * 80 + "\n\n")
            
            f.write("📤 OUTPUT\n")
            f.write("-" * 80 + "\n")
            f.write(str(output_data))
            f.write("\n" + "-" * 80 + "\n\n")
            
            f.write("\n\n")
    
    def get_estadisticas(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de las llamadas registradas.
        
        Returns:
            Dict con estadísticas
        """
        return {
            "total_llamadas": self.call_count,
            "archivo_log": str(self.log_file)
        }


# Instancia global del observador
_observador_instance: Optional[ObservadorLLM] = None


def get_observador_llm() -> ObservadorLLM:
    """
    Obtiene la instancia global del observador de LLMs.
    
    Returns:
        ObservadorLLM: Instancia del observador
    """
    global _observador_instance
    if _observador_instance is None:
        _observador_instance = ObservadorLLM()
    return _observador_instance
