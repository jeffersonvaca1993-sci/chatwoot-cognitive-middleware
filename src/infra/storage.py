# src/infra/storage.py
import os
from typing import Protocol

class StorageService(Protocol):
    def guardar(self, nombre_archivo: str, contenido: bytes) -> str:
        ...

class LocalStorageService:
    def __init__(self, base_path: str = "storage_data"):
        self.base_path = base_path
        os.makedirs(self.base_path, exist_ok=True)

    def guardar(self, nombre_archivo: str, contenido: bytes) -> str:
        """Guarda bytes en disco y retorna la ruta absoluta."""
        ruta_completa = os.path.join(self.base_path, nombre_archivo)
        with open(ruta_completa, "wb") as f:
            f.write(contenido)
        return os.path.abspath(ruta_completa)
