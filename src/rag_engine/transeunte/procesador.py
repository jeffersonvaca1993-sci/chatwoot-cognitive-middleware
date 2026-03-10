# src/rag_engine/transeunte/procesador.py
import os
from typing import List
from src.rag_engine.core.base import ProcesadorDocumento

class ProcesadorReglamentoTranseunte(ProcesadorDocumento):
    """
    Lógica específica para 'reglamento.txt' ubicado en este mismo directorio.
    """
    
    def __init__(self):
        # Calculamos la ruta absoluta del archivo de texto basado en la ubicación de este script
        base_dir = os.path.dirname(os.path.abspath(__file__))
        ruta_archivo = os.path.join(base_dir, "reglamento.txt")
        
        super().__init__(
            ruta_archivo=ruta_archivo,
            categoria="transeunte",
            fuente="Reglamento Transeúnte 2025"
        )

    def cargar(self) -> str:
        if not os.path.exists(self.ruta_archivo):
            print(f"Error: No se encuentra {self.ruta_archivo}")
            return ""
        with open(self.ruta_archivo, "r", encoding="utf-8") as f:
            return f.read()

    def separar(self, contenido: str) -> List[str]:
        """
        Estrategia de separación personalizada.
        """
        bloques_crudos = contenido.split('\n\n')
        fragmentos_limpios = []
        
        buffer_actual = ""
        
        for bloque in bloques_crudos:
            bloque = bloque.strip()
            if not bloque:
                continue
            
            if len(bloque) < 50 and not bloque.startswith("*") and not bloque.startswith("**"):
                buffer_actual = bloque
            else:
                if buffer_actual:
                    fragmento_final = f"{buffer_actual}\n{bloque}"
                    buffer_actual = ""
                else:
                    fragmento_final = bloque
                
                fragmentos_limpios.append(fragmento_final)
        
        if buffer_actual:
            fragmentos_limpios.append(buffer_actual)
            
        return fragmentos_limpios
