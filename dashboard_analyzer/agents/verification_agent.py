from .base_agent import BaseAgent
from typing import Dict, Any
import json
import os
import sys

# Add the parent directory to the path if needed, assuming structure like other agents
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class VerificationAgent(BaseAgent):
    """
    Agent specialized in verifying if the output of the SynthesisAgent
    complies with the specified rules, using an LLM for assessment.
    """

    def __init__(self):
        super().__init__()
        # You might use a different model for verification if needed, 
        # but let's use the same one for now.
        # self.verification_model_id = os.getenv('VERIFICATION_MODEL_ARN', self.model_id) 

    def get_system_prompt(self) -> str:
        """Returns a placeholder system prompt (not used for core logic)."""
        # The core verification logic is built within the verify method itself.
        return "Verification Agent System Prompt Placeholder - Logic is in verify method."

    def analyze_image(self, image_path: Any) -> Dict[str, Any]:
        """Placeholder for analyze_image (not applicable for this agent)."""
        # This agent does not analyze images directly.
        print("⚠️ VerificationAgent.analyze_image called, but it does not process images.")
        return {"status": "not_applicable", "message": "VerificationAgent does not analyze images."}

    def verify(self, synthesis_output: Dict) -> Dict:
        """
        Verifica la salida de síntesis contra las reglas usando un LLM.

        Args:
            synthesis_output: El diccionario JSON generado por SynthesisAgent.

        Returns:
            Diccionario con estado: {"status": "favorable" | "desfavorable", "reason": "..."}
        """
        print("\n🔎 Iniciando proceso de verificación...")

        # --- REGLAS ACTUALIZADAS Y DETALLADAS PARA EL VERIFICADOR --- 
        synthesis_rules_for_verification = """
        **REGLAS ESTRICTAS A VERIFICAR EN EL JSON PROPORCIONADO:**

        **1. Lenguaje y Terminología:**
           - ¿Usa exclusivamente "target" (no "objetivo")?
           - ¿Usa exclusivamente "load_factor" (no "factor de carga")?
           - ¿Usa exclusivamente "inbound" / "outbound" (no "entrada" / "salida")?
           - ¿Usa exclusivamente "puntualidad en entradas/salidas" (no "puntualidad C15")?
           - ¿Usa exclusivamente "misshandling" / "missconnections" (sin traducir)?

        **2. Manejo de Datos y Fidelidad:**
           - **Comparaciones (`..._vs_..._prev_week`):** ¿Solo se mencionan KPIs comparativos si su `is_relevant` era `true` (basado en el texto generado, ya que no ves la entrada)? ¿Se evita mencionar explícitamente la diferencia porcentual?
           - **Inbound/Outbound en Tendencias/Mapas:** ¿Se especifica *siempre* "inbound" u "outbound" al describir tendencias o mapas?
           - **Datos Faltantes:** Si el texto menciona datos faltantes, ¿es breve y relevante al análisis?

        **3. Consideraciones Específicas por Área (Contenido de los 4 mini-informes):**
           - **Selección Inbound/Outbound (Tendencias/Mapas):** Si se describe una tendencia o mapa para un área, ¿se especifica claramente si se refiere a inbound, outbound o ambos? (La regla subyacente es elegir el segmento con valores más extremos/bajos).
           - **Customer:** (Verificación difícil) ¿El texto evita mencionar el decalaje NPS de 4 días?
           - **Disruptions:** ¿El análisis de cancelaciones se centra solo en IB? ¿Se valora la relevancia de disrupciones en contexto operativo (posible comentario sobre divergencia)?
           - **Commercial:** ¿Se mencionan intakes recientes (implícito)? ¿Se evita detalle exacto en diferencia vs target (redondeo implícito)? ¿Se combina vista general y evolución? ¿Se considera estacionalidad/ratio business/leisure si es relevante? ¿Se menciona crecimiento espectacular (+10M vs target) si ocurrió?

        **4. Qué Evitar (Ausencia de contenido prohibido):**
           - **Redundancia:** ¿Hay frases o ideas repetidas innecesariamente?
           - **Correlación Ops/Disruptions/NPS Obvia:** ¿Evita mencionar esta correlación básica *a menos que* proporcione detalles específicos (fechas, valores, etc.) como se indica en el punto 5?
           - **Obviedad General:** ¿Evita comentarios triviales como "KPIs malos necesitan seguimiento"?
           - **Mención Explícita Decalaje NPS:** ¿Contiene la frase "4 días" o similar al hablar del NPS? (NO DEBE)
           - **Mención Explícita Umbrales:** ¿Menciona valores numéricos de umbrales o rangos de referencia? (NO DEBE)

        **5. Análisis Cruzado (`overall_interpretation`):**
           - **Conexión entre Áreas:** ¿El párrafo conecta claramente puntos clave de diferentes áreas (Commercial, Customer, Ops, Disruptions)?
           - **Verificación Decalaje NPS:** ¿Las conexiones Ops/Disruptions -> NPS parecen temporalmente consistentes (considerando 4 días implícitamente)? Si se menciona una conexión específica, ¿incluye detalles (días, valores, etc.)? ¿Evita mencionar "4 días"?
           - **Verificación Inbound/Outbound:** Si compara datos entre áreas (ej. Ops y Customer), ¿mantiene la perspectiva (inbound con inbound, outbound con outbound)? **¡VERIFICAR ESTO CUIDADOSAMENTE!**
           - **Comentario Divergencias (Opcional):** Si aplica (ver regla), ¿describe la divergencia Ops/Disruptions/NPS como inesperada?
           - **Evita Obviedades:** ¿El análisis cruzado aporta valor más allá de la correlación básica?

        **6. Formato y Estructura:**
           - **JSON Válido:** ¿La respuesta completa es SÓLO un objeto JSON válido?
           - **Estructura Exacta:** ¿La estructura es estrictamente `{"weekly_report": {"commercial": ..., "customer": ..., "operations": ..., "disruptions": ..., "overall_interpretation": ...}}`?
           - **Longitud:** ¿Cada uno de los 4 informes de área tiene aprox. 2-3 frases? ¿`overall_interpretation` tiene aprox. 3-5 frases?
        """
        # -------------------------------------------------------------

        verification_task = (
            "Eres un verificador experto y muy estricto. Tu única tarea es comprobar si el JSON proporcionado (`synthesis_output`) "
            "cumple ESTRICTAMENTE TODAS las reglas especificadas en `REGLAS A VERIFICAR`. NO intentes corregir el JSON, solo verifica."
            "Tu respuesta DEBE ser OBLIGATORIAMENTE un único objeto JSON con dos claves:"
            "1. `status`: Debe ser la cadena 'favorable' si CUMPLE TODAS las reglas, o 'desfavorable' si falla en CUALQUIER regla."
            "2. `reason`: Si el status es 'desfavorable', esta clave debe contener una cadena explicando BREVEMENTE cuál es la regla MÁS IMPORTANTE que se ha incumplido. Si el status es 'favorable', esta clave debe contener una cadena vacía ''."
            "NO incluyas NADA MÁS en tu respuesta fuera de este objeto JSON."
        )

        synthesis_output_str = json.dumps(synthesis_output, indent=2, ensure_ascii=False)

        # Prompt para el LLM Verificador (usa reglas actualizadas y copiadas)
        verification_prompt = f"""{verification_task}\n\n{synthesis_rules_for_verification}\n\n**JSON a Verificar (`synthesis_output`):**\n\n```json\n{synthesis_output_str}\n```\n\n**Tu Respuesta (SOLO el JSON de verificación):**"""

        # --- DEBUGGING: Print the full prompt sent to the verifier --- 
        print("\n--- DEBUG (Verifier): Prompt Enviado al LLM --- ")
        # Print first N chars for brevity in logs if needed
        # print(verification_prompt[:1500] + ("..." if len(verification_prompt)>1500 else ""))
        print(verification_prompt) # Print full prompt for now
        print("--- FIN DEBUG (Verifier): Prompt Enviado --- \n")
        # --- END DEBUGGING ---

        messages = [{
            "role": "user",
            "content": [{"type": "text", "text": verification_prompt}]
        }]

        try:
            response = self.invoke_model(messages=messages)
            print(f"DEBUG (Verificador): Respuesta LLM cruda: {response}")

            try:
                # Basic cleanup attempt (remove potential markdown)
                cleaned_response = response.strip()
                if cleaned_response.startswith("```json"):
                    cleaned_response = cleaned_response[7:]
                if cleaned_response.endswith("```"):
                    cleaned_response = cleaned_response[:-3]
                cleaned_response = cleaned_response.strip()

                verification_result = json.loads(cleaned_response)
                
                # Validate structure
                if isinstance(verification_result, dict) and \
                   'status' in verification_result and \
                   'reason' in verification_result and \
                   verification_result['status'] in ['favorable', 'desfavorable']:
                    
                    print(f"✅ Resultado Verificación: {verification_result}")
                    return verification_result
                else:
                    print("❌ Estructura respuesta LLM Verificador inválida.")
                    return {"status": "desfavorable", "reason": "El agente verificador no produjo un JSON de estado válido."}

            except json.JSONDecodeError as e:
                print(f"❌ Error decodificando JSON de verificación: {e}")
                print(f"Respuesta cruda: {response}")
                return {"status": "desfavorable", "reason": "La respuesta del agente verificador no era JSON válido."}

        except Exception as e:
            print(f"❌ Error llamando al modelo de verificación: {e}")
            return {"status": "desfavorable", "reason": f"Error durante llamada API de verificación: {e}"} 