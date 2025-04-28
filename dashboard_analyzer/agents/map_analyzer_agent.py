from .base_agent import BaseAgent
from typing import Dict, Any, List, Union
import json
import os
import sys

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.image_utils import encode_image

class MapAnalyzerAgent(BaseAgent):
    """Agente especializado en el análisis de visualizaciones de mapas."""
    
    def get_system_prompt(self) -> str:
        return """Eres un especialista en el análisis de mapas geográficos y tablas de datos asociadas para aerolíneas, enfocado exclusivamente en Iberia (IB).

Tu **TAREA PRINCIPAL** es analizar la imagen proporcionada (que contiene un mapa y probablemente una tabla de datos) y extraer insights clave sobre la distribución geográfica de un indicador específico (NPS, cancelaciones, puntualidad, etc.) **SOLAMENTE para Iberia (IB)**.

**CONTEXTO OPERATIVO DE IBERIA (para interpretar patrones):**
- Iberia opera principalmente desde su **hub en Madrid, España**.
- Tiene una fuerte presencia en **Europa** y **América** (Norte, Centro y Sur).
- La presencia en **África** es más limitada (principalmente Norte de África, más algunos destinos subsaharianos como Dakar).
- La presencia en **Asia** es muy reducida (ej. Tokio). Ten esto en cuenta al valorar concentraciones o valores "bajos" en estas regiones.

**INSTRUCCIONES DETALLADAS:**

0.  **VALORES NEGATIVOS con - delante:** Al analizar datos numéricos, presta especial atención a los signos negativos. Revisa cada valor individualmente y verifica explícitamente si hay un signo negativo (-) delante del número. No asumas que todos los valores son positivos. Cuando reportes los resultados, confirma visualmente cada signo antes de incluir el valor en tu respuesta.

1.  **Estructura de Datos CRÍTICA (Tabla):** Presta máxima atención a la tabla de datos si está presente.
    *   **Para la mayoría de dashboards (Customer, Operations, Disruptions):** Se organiza en **pares de filas consecutivas** por región: Fila 1 = VALOR NUMÉRICO, Fila 2 = REGIÓN. Asocia valor con la región de la fila siguiente.
    *   **EXCEPCIÓN (si el dashboard es 'commercial'):** La estructura es diferente. Habrá una columna `country_loc` con el país/región. Para cada país, habrá 3 filas: la primera vacía, la segunda con el **valor numérico de Intakes**, y la tercera vacía. Debes asociar el valor de la segunda fila con el país/región de la columna `country_loc`.
    *   **FUNDAMENTAL:** Identifica primero el tipo de dashboard para aplicar la estructura correcta.

2.  **Extracción de Datos (SOLO IB):**
    *   **Si NO es 'commercial':** Examina tabla/mapa e identifica valores/regiones **exclusivamente para Iberia (IB)**, ignorando otras aerolíneas.
    *   **Si SÍ es 'commercial':** Asume que todos los datos numéricos de intakes en la tabla son de Iberia (IB). Extrae el valor de intakes y el país/región asociado según la estructura descrita en el punto 1.

3.  **Identificación de Extremos (Máximos y Mínimos):**
    *   Una vez extraídos los datos de IB, identifica y reporta **EXPRESAMENTE**:
        *   La(s) región(es) con el(los) **valor(es) MÁS ALTO(S)** para IB, indicando claramente el valor y la(s) región(es).
        *   La(s) región(es) con el(los) **valor(es) MÁS BAJO(S)** para IB, indicando claramente el valor y la(s) región(es). Ten en cuenta que puede haber valores negativos, en cuyo caso el mínimo será negativo.
        *   Si hay empates en máximos o mínimos, menciona todas las regiones empatadas.

4.  **Análisis de Patrones y Anomalías (SOLO IB):**
    *   Describe brevemente los **patrones geográficos generales** observados para IB (ej. concentraciones altas/bajas en ciertas zonas), **considerando el contexto operativo** (ej. es normal tener menos actividad/datos en Asia/África).
    *   Señala cualquier **anomalía o situación excepcional** en la distribución geográfica de IB, teniendo en cuenta lo esperado según su red.

5.  **Síntesis del Análisis:**
    *   Consolida tus hallazgos (valores, regiones, extremos, patrones, anomalías) en un análisis técnico y objetivo. Aporta el valor del máximo y la/s región/es asociada/s. Lo mismo para el mínimo.

**REGLAS FUNDAMENTALES:**
*   **NUMEROS NEGATIVOS:** Ten en cuenta que los números negativos son valores negativos con un - delante.
*   **NO INVENTES NADA:** Trabaja *exclusivamente* con la información visible en la imagen. Si un dato no es legible o falta, indícalo claramente.
*   **ENFOQUE IB:** Tu análisis debe centrarse *única y exclusivamente* en los datos de Iberia (IB).
*   **OBJETIVIDAD:** Evita juicios de valor, opiniones o recomendaciones subjetivas. Limítate a describir los datos y patrones observados.
"""

    def analyze_image(self, image_path: Union[str, Dict[str, Any]], map_thresholds: Dict[str, Dict[str, Any]] = None, direccion_esperada: str = None) -> Dict[str, Any]:
        """Analyze map visualizations and return insights with relevance assessment."""
        # Handle different image_path types
        if isinstance(image_path, dict):
            # If we get a dictionary, use the first value (assuming it's a path)
            if image_path:
                for key, value in image_path.items():
                    if value:
                        image_path = value
                        break
                else:
                    return {"error": "No valid image path found in dictionary"}
            else:
                return {"error": "Empty image path dictionary"}
        
        # Now image_path should be a string
        if not isinstance(image_path, str):
            return {"error": f"Expected string image path, got {type(image_path)}"}
            
        # Encode the image
        encoded_image = encode_image(image_path)
        if not encoded_image:
            return {"error": f"Failed to encode image: {image_path}"}
        
        # Prepare the text part of the prompt
        prompt_text = """Analiza el mapa geográfico mostrado y proporciona un análisis detallado. 

IMPORTANTE: 
- Identifica el tipo de dashboard (customer, disruptions_misconnections, disruptions_misshandling, operations, commercial_last_reported, commercial_last_week)
"""
        # Add instruction for direction based on whether it was provided
        if direccion_esperada:
            prompt_text += f"- Este mapa corresponde a la dirección: **{direccion_esperada.upper()}**. Basa tu análisis en esta dirección.\n"
        else:
             prompt_text += "- Identifica si es inbound o outbound\n"
             
        # Add remaining instructions
        prompt_text += """- FUNDAMENTAL: NO inventes NINGÚN dato, región o cifra. Si alguna información no es legible o no está disponible en la imagen, indícalo claramente pero NUNCA la inventes.
- IMPORTANTE: Enfócate SOLAMENTE en los datos relacionados con IB (Iberia). Solo analiza los datos de Iberia, ignorando otras aerolíneas.
- Identifica las regiones presentes en el mapa
- Identifica si hay concentraciones altas o bajas para IB
- Identifica anomalías en IB si las hubiera
- Devuelve SOLO el JSON puro sin bloques de código o comentarios"""

        # Prepare the messages list
        messages = [{
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": prompt_text # Use the constructed prompt text
                },
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg", # Assuming JPEG after potential compression
                        "data": encoded_image
                    }
                }
            ]
        }]
        
        # Add map thresholds if provided
        if map_thresholds:
            # Ensure content list exists and first item is text
            if messages[0]['content'] and messages[0]['content'][0]['type'] == 'text':
                 messages[0]['content'][0]['text'] += f"\n\nUmbrales de mapas:\n{json.dumps(map_thresholds, indent=2)}"
            else: # Fallback if structure is unexpected
                 messages[0]['content'].append({"type": "text", "text": f"\n\nUmbrales de mapas:\n{json.dumps(map_thresholds, indent=2)}"})
        
        # Call the model
        response = self.invoke_model(messages, system_prompt=self.get_system_prompt())
        
        # Parse the response
        try:
            # Clean up the response
            cleaned_response = response
            if "```json" in cleaned_response:
                cleaned_response = cleaned_response.split("```json")[1]
                if "```" in cleaned_response:
                    cleaned_response = cleaned_response.split("```")[0]
            elif "```" in cleaned_response:
                parts = cleaned_response.split("```")
                if len(parts) >= 3:
                    cleaned_response = parts[1]
                    if "\n" in cleaned_response:
                        first_line, rest = cleaned_response.split("\n", 1)
                        if not first_line.strip().startswith("{"):
                            cleaned_response = rest
            
            cleaned_response = cleaned_response.strip()
            
            analysis = json.loads(cleaned_response)
            # --- REMOVE DEBUG MAP ANALYZER OUTPUT --- 
            # print(f"\n--- DEBUG (MapAnalyzer): Final analysis output --- ")
            # print(json.dumps(analysis, indent=2, ensure_ascii=False))
            # print("--- END DEBUG (MapAnalyzer) ---\n")
            # --- END REMOVE --- 
            return analysis
        except json.JSONDecodeError as e:
            print(f"❌ Error decoding JSON: {e}")
            print(f"Raw response: {response}")
            return {
                "error": "Invalid JSON response",
                "raw_response": response
            } 