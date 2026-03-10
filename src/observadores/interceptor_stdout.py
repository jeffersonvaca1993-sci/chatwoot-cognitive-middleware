"""
Interceptor de stdout para capturar todos los print() automáticamente.

Este módulo secuestra sys.stdout para redirigir todos los print() 
al sistema de logging, sin necesidad de cambiar el código existente.
"""

import sys
from io import StringIO
from typing import Optional
from datetime import datetime
from pathlib import Path


class StdoutInterceptor:
    """
    Intercepta sys.stdout para capturar todos los print().
    
    Redirige automáticamente a archivos de log manteniendo
    también la salida en consola.
    """
    
    def __init__(self, log_dir: str = "src/observadores/logs/stdout"):
        """
        Inicializa el interceptor.
        
        Args:
            log_dir: Directorio donde guardar los logs
        """
        # Guardar el stdout original
        self.original_stdout = sys.stdout
        
        # Crear directorio de logs
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Nombre del archivo con timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"stdout_{timestamp}.txt"
        
        # Abrir archivo de log
        self.file_handle = open(self.log_file, "w", encoding="utf-8")
        
        # Escribir encabezado
        self._escribir_encabezado()
        
        # Buffer para acumular líneas
        self.buffer = StringIO()
    
    def _escribir_encabezado(self):
        """Escribe el encabezado del archivo de log."""
        self.file_handle.write("=" * 80 + "\n")
        self.file_handle.write("CAPTURA DE STDOUT - ChatGravity MoE\n")
        self.file_handle.write(f"Iniciado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        self.file_handle.write("=" * 80 + "\n\n")
        self.file_handle.flush()
    
    def write(self, text: str):
        """
        Escribe texto (llamado automáticamente por print()).
        
        Args:
            text: Texto a escribir
        """
        # Escribir en consola (stdout original)
        self.original_stdout.write(text)
        self.original_stdout.flush()
        
        # Escribir en archivo con timestamp si es una línea completa
        if text and text != "\n":
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            self.file_handle.write(f"[{timestamp}] {text}")
            self.file_handle.flush()
        elif text == "\n":
            self.file_handle.write(text)
            self.file_handle.flush()
    
    def flush(self):
        """Flush de buffers (requerido por la interfaz de stdout)."""
        self.original_stdout.flush()
        self.file_handle.flush()
    
    def close(self):
        """Cierra el archivo de log y restaura stdout original."""
        if self.file_handle:
            self.file_handle.close()
        sys.stdout = self.original_stdout
    
    def __enter__(self):
        """Context manager: activar interceptor."""
        sys.stdout = self
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager: desactivar interceptor."""
        self.close()


# Instancia global del interceptor
_interceptor_instance: Optional[StdoutInterceptor] = None


def activar_interceptor_stdout():
    """
    Activa el interceptor de stdout globalmente.
    
    Todos los print() se capturarán automáticamente.
    """
    global _interceptor_instance
    if _interceptor_instance is None:
        _interceptor_instance = StdoutInterceptor()
        sys.stdout = _interceptor_instance
        print("✅ Interceptor de stdout activado")


def desactivar_interceptor_stdout():
    """
    Desactiva el interceptor de stdout.
    
    Restaura el stdout original.
    """
    global _interceptor_instance
    if _interceptor_instance is not None:
        _interceptor_instance.close()
        _interceptor_instance = None
        print("✅ Interceptor de stdout desactivado")


def get_interceptor() -> Optional[StdoutInterceptor]:
    """
    Obtiene la instancia del interceptor.
    
    Returns:
        StdoutInterceptor o None si no está activado
    """
    return _interceptor_instance
