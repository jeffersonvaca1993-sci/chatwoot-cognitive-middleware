# src/rag_engine/core/base.py
from abc import ABC, abstractmethod
from typing import List
from src.rag_engine.core.vectorizador_gemini import VectorizadorGemini
from src.rag_engine.core.indexador import Indexador

class ProcesadorDocumento(ABC):
    """
    Plantilla para procesar diferentes tipos de documentos (PDF, TXT, Markdown, etc.)
    y diferentes lógicas de separación (por párrafos, por artículos, etc.).
    """
    
    def __init__(self, ruta_archivo: str, categoria: str, fuente: str):
        self.ruta_archivo = ruta_archivo
        self.categoria = categoria
        self.fuente = fuente
        self.vectorizador = VectorizadorGemini()
        self.indexador = Indexador()

    @abstractmethod
    def cargar(self) -> str:
        """Lee el archivo y devuelve el contenido crudo."""
        pass

    @abstractmethod
    def separar(self, contenido: str) -> List[str]:
        """Divide el contenido en fragmentos lógicos."""
        pass

    async def procesar(self):
        """
        MÉTODO PLANTILLA (Template Method).
        Orquesta el flujo: Cargar -> Separar -> Vectorizar -> Indexar.
        """
        print(f"📄 Procesando: {self.ruta_archivo}")
        
        # 1. Cargar
        contenido = self.cargar()
        if not contenido:
            print("   ⚠️ Archivo vacío o no encontrado.")
            return

        # 2. Separar
        fragmentos = self.separar(contenido)
        print(f"   🧩 Se generaron {len(fragmentos)} fragmentos.")

        # 3. Vectorizar e Indexar (Loop)
        for i, frag in enumerate(fragmentos):
            try:
                # Vectorizar
                vector = await self.vectorizador.generar_embedding(frag)
                
                # Indexar
                self.indexador.indexar_fragmento(
                    texto=frag,
                    vector=vector,
                    fuente=self.fuente,
                    categoria=self.categoria
                )
                if len(fragmentos) < 20 or i % 5 == 0:
                    print(f"      ✅ Indexado fragmento {i+1}/{len(fragmentos)}")
            except Exception as e:
                print(f"      ❌ Error en fragmento {i+1}: {e}")
        
        print(f"✨ Procesamiento completado para {self.fuente}")
