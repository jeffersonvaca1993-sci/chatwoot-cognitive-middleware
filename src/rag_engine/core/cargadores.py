# src/rag_engine/cargadores.py

class CargadorDocumentos:
    """
    Responsable de convertir archivos binarios (PDF, DOCX) a texto plano.
    """
    def cargar(self, ruta_archivo: str) -> str:
        # TODO: Implementar lógica de carga (ej: PyPDF2, Textract)
        raise NotImplementedError("Método de carga no implementado")
