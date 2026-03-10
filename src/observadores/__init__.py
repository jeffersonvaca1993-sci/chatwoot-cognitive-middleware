"""
Módulo de observabilidad para desarrollo.

Proporciona logging y observación de LLMs con archivos .txt planos.
Interfaz compatible con Langfuse para migración futura.
"""

from .logger import Logger, get_logger
from .observador_llm import ObservadorLLM, get_observador_llm
from .interceptor_stdout import (
    StdoutInterceptor,
    activar_interceptor_stdout,
    desactivar_interceptor_stdout,
    get_interceptor
)

__all__ = [
    "Logger",
    "get_logger",
    "ObservadorLLM",
    "get_observador_llm",
    "StdoutInterceptor",
    "activar_interceptor_stdout",
    "desactivar_interceptor_stdout",
    "get_interceptor",
]
