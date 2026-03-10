"""
Módulo de logging simple para desarrollo.
Reemplazará a Langfuse cuando esté disponible en producción.

SOLO registra errores y advertencias.
Formato legible para humanos.
Un archivo por ejecución (cada vez que se levanta Docker).
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any


class Logger:
    """
    Logger simple que guarda en archivos .txt planos.
    
    Interfaz compatible con Langfuse para migración futura.
    Solo registra errores y advertencias.
    """
    
    def __init__(self):
        # Crear carpeta de logs si no existe
        self.logs_dir = Path("src/observadores/logs/eventos")
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Nombre del archivo con fecha y hora
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.logs_dir / f"log_{timestamp}.txt"
        
        # Escribir encabezado
        self._escribir_encabezado()
    
    def _escribir_encabezado(self):
        """Escribe el encabezado del archivo de log."""
        with open(self.log_file, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write(f"LOG DE EVENTOS - ChatGravity MoE\n")
            f.write(f"Iniciado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Nivel: ERRORES Y ADVERTENCIAS\n")
            f.write("=" * 80 + "\n\n")
    
    def _escribir(self, nivel: str, mensaje: str, contexto: Optional[Dict[str, Any]] = None):
        """Escribe una entrada en el log."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {nivel}\n")
            f.write(f"{mensaje}\n")
            
            if contexto:
                f.write("Contexto:\n")
                for key, value in contexto.items():
                    f.write(f"  - {key}: {value}\n")
            
            f.write("-" * 80 + "\n\n")
    
    def error(self, mensaje: str, contexto: Optional[Dict[str, Any]] = None):
        """
        Registra un error.
        
        Args:
            mensaje: Descripción del error
            contexto: Información adicional (opcional)
        """
        self._escribir("❌ ERROR", mensaje, contexto)
    
    def warning(self, mensaje: str, contexto: Optional[Dict[str, Any]] = None):
        """
        Registra una advertencia.
        
        Args:
            mensaje: Descripción de la advertencia
            contexto: Información adicional (opcional)
        """
        self._escribir("⚠️ ADVERTENCIA", mensaje, contexto)
    
    def info(self, mensaje: str, contexto: Optional[Dict[str, Any]] = None):
        """
        Registra información (NO SE USA en desarrollo, solo para compatibilidad).
        
        En desarrollo solo registramos errores y advertencias.
        Este método existe para compatibilidad futura con Langfuse.
        """
        pass  # No hacer nada en desarrollo
    
    def debug(self, mensaje: str, contexto: Optional[Dict[str, Any]] = None):
        """
        Registra debug (NO SE USA en desarrollo, solo para compatibilidad).
        
        En desarrollo solo registramos errores y advertencias.
        Este método existe para compatibilidad futura con Langfuse.
        """
        pass  # No hacer nada en desarrollo


# Instancia global del logger
_logger_instance: Optional[Logger] = None


def get_logger() -> Logger:
    """
    Obtiene la instancia global del logger.
    
    Returns:
        Logger: Instancia del logger
    """
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = Logger()
    return _logger_instance
