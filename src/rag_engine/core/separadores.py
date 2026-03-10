# src/rag_engine/separadores.py
from typing import List

class SeparadorTexto:
    """
    Divide el texto en fragmentos (chunks) manejables para embeddings.
    """
    def separar(self, texto: str, tamano_chunk: int = 1000) -> List[str]:
        # TODO: Implementar lógica de splitting (ej: RecursiveCharacterTextSplitter)
        return [texto[i:i+tamano_chunk] for i in range(0, len(texto), tamano_chunk)]
