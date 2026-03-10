# src/clientes_llm/gemini.py
import os
import google.generativeai as genai
from google.generativeai.types import GenerationConfig, HarmCategory, HarmBlockThreshold
from .base import ClienteLLMBase
from src.core.protocolos import PayloadTecnicoLLM, ResultadoTecnicoLLM, MensajeNativo

class ClienteGemini(ClienteLLMBase):
    
    def _cargar_api_key(self) -> str:
        key = os.getenv("GEMINI_API_KEY")
        if not key:
            # Fallback para desarrollo local si no está en env pero sí en config
            from src.config import settings
            if settings.GEMINI_API_KEY:
                return settings.GEMINI_API_KEY
            raise ValueError("Falta la variable de entorno GEMINI_API_KEY")
        return key

    def _inicializar_sdk(self):
        genai.configure(api_key=self.api_key)

    def _mapear_roles(self, mensajes: list[MensajeNativo]) -> tuple:
        """
        TRADUCTOR DE ROLES:
        Nuestro sistema usa: 'system', 'user', 'assistant'
        Gemini usa: 'user', 'model' (y el system prompt va aparte o al inicio)
        """
        historial_gemini = []
        system_instruction = None

        for msg in mensajes:
            if msg.rol == "system":
                # Gemini 1.5 soporta system_instruction nativo, lo extraemos
                system_instruction = msg.contenido
            elif msg.rol == "user":
                historial_gemini.append({"role": "user", "parts": [msg.contenido]})
            elif msg.rol == "assistant":
                historial_gemini.append({"role": "model", "parts": [msg.contenido]})
        
        return system_instruction, historial_gemini

    async def invocar_privado(self, payload: PayloadTecnicoLLM) -> ResultadoTecnicoLLM:
        try:
            # 1. TRADUCCIÓN (Input -> Formato Google)
            sys_prompt, historial = self._mapear_roles(payload.mensajes_stack)
            
            # Instanciamos el modelo específico solicitado en el payload
            # Mapeamos alias internos a nombres reales de Google si hace falta
            modelo_real = "gemini-1.5-flash" if "FLASH" in payload.alias_modelo_objetivo else "gemini-1.5-pro"
            
            model = genai.GenerativeModel(
                model_name=modelo_real,
                system_instruction=sys_prompt
            )

            # Configuración de generación (Temperatura, Tokens, JSON)
            gen_config = GenerationConfig(
                temperature=payload.parametros_api.get("temperature", 0.7),
                max_output_tokens=payload.parametros_api.get("max_tokens", 1024),
                response_mime_type="application/json" if payload.parametros_api.get("json_mode") else "text/plain"
            )

            # Seguridad: Lo ponemos permisivo por defecto para no bloquear respuestas válidas
            safety = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            }

            # 2. EJECUCIÓN (Llamada Async)
            # Nota: Usamos generate_content_async para no bloquear el worker de FastAPI
            response = await model.generate_content_async(
                contents=historial,
                generation_config=gen_config,
                safety_settings=safety
            )

            # 3. TRADUCCIÓN INVERSA (Formato Google -> Output)
            # Extraemos texto y conteo de tokens
            texto_final = response.text
            usage = response.usage_metadata
            
            return ResultadoTecnicoLLM(
                texto_generado=texto_final,
                tokens_input=usage.prompt_token_count,
                tokens_output=usage.candidates_token_count,
                data_raw=response.to_dict() # Guardamos el raw por si acaso (debugging)
            )

        except Exception as e:
            # Manejo de errores robusto: Devolvemos un resultado de error técnico
            # para que la Estrategia decida qué hacer (reintentar o fallar)
            print(f"Error Crítico Gemini: {str(e)}")
            return ResultadoTecnicoLLM(
                texto_generado=f"ERROR_PROVEEDOR: {str(e)}",
                tokens_input=0,
                tokens_output=0
            )
