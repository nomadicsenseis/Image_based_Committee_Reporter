from .base_agent import BaseAgent
from typing import Dict, Any, List, Union
import json
import os
import sys

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.image_utils import encode_image

class TrendlineAnalyzerAgent(BaseAgent):
    """Agente especializado en el análisis de gráficos de tendencias."""
    
    def get_system_prompt(self) -> str:
        return """Eres un/a especialista en el análisis de gráficos de tendencias para aerolíneas. Se te va a proporcionar una imagen de una tabla con los valores de un kpi, para distintas aerolíneas en distintos radios (SMH, LH, etc) en distintas fechas. La tabla puede ser de inbound o de outbound para un dashboard de customer, operations, commercial o disruptions: Tu tarea es:

        FUNDAMENTAL: NO inventes NINGÚN dato, fecha o cifra. Trabaja exclusivamente con la información que puedes ver en la imagen. Si algún dato no es legible o no está disponible, indícalo claramente pero NUNCA lo sustituyas con valores inventados.

        IMPORTANTE:
        - **Enfoque Aerolínea:** Para dashboards de Customer, Operations o Disruptions, enfócate SOLAMENTE en las columnas/aerolíneas de IB (Iberia), ignorando otras (YW, I2, etc.).
        - **Excepción Commercial:** Si el dashboard es 'commercial', ASUME que TODAS las columnas numéricas que ves en la tabla de tendencias corresponden a datos de Iberia (IB).

        1. Identificar el kpi que se está representando en la tabla.
        2. Hacer una valoración de cada una de los radios/categorías de IB en la tabla (o todas las columnas si es commercial), identificando tendencias, picos, caidas, etc POR SEPARADO.
        3. Resumir el análisis en un párrafo.
        4. Calcular y devolver el valor máximo y mínimo observado para cada serie de datos analizada.

        Mantén el análisis enfocado en los datos y evita juicios de valor o recomendaciones subjetivas. Es importante que el análisis sea por separado para cada radio/categoría.
        """

    def analyze_image(self, image_path: Union[str, Dict[str, Any]], trend_thresholds: Dict[str, Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analyze trend graphs and return insights with relevance assessment."""
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
        
        # Prepare the message for the model
        messages = [{
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": """Analiza los gráficos de tendencias y proporciona un análisis detallado. 

IMPORTANTE: 
- NO inventes NINGÚN dato, fecha o cifra. Si algún dato no es legible o no está disponible, indícalo claramente pero NUNCA lo sustituyas con valores inventados.
- IMPORTANTE: Enfócate SOLAMENTE en los radios de IB (Iberia). Debes analizar los datos de IB para cada radio por separado.
- Devuelve SOLO el JSON puro sin bloques de código o comentarios
- Los valores deben ser numéricos cuando sea posible
- Las fechas deben estar en formato YYYY-MM-DD
- Omite recomendaciones o juicios de valor, solo analiza los datos.

El JSON debe seguir esta estructura:
{
  "dashboard_name": <string>,  // Tipo de dashboard
  "direction": <string>,         // inbound o outbound
  "trends": {
    "tabla": [
      {
        "airline_haul": <string>,
        "values": [valor1, valor2, ...],
        "dates": ["YYYY-MM-DD", "YYYY-MM-DD", ...]
      }
    ],
    "overall_analysis": "Análisis general de las tendencias incluyendo picos y caidas, etc para cada radio por separado"
  }
}"""
                },
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": encoded_image
                    }
                }
            ]
        }]
        
        # Add trend thresholds if provided
        if trend_thresholds:
            messages[0]['content'][0]['text'] += f"\n\nUmbrales de tendencias:\n{json.dumps(trend_thresholds, indent=2)}"
        
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
            # --- REMOVE DEBUG TRENDLINE ANALYZER OUTPUT --- 
            # print(f"\n--- DEBUG (TrendlineAnalyzer): Final analysis output --- ")
            # print(json.dumps(analysis, indent=2, ensure_ascii=False))
            # print("--- END DEBUG (TrendlineAnalyzer) ---\n")
            # --- END REMOVE --- 
            return analysis
        except json.JSONDecodeError as e:
            print(f"❌ Error decoding JSON: {e}")
            print(f"Raw response: {response}")
            return {
                "error": "Invalid JSON response",
                "raw_response": response
            } 