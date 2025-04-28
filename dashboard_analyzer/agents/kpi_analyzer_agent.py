from .base_agent import BaseAgent
from typing import Dict, Any, List, Union
import json
import os
import sys

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.image_utils import encode_image

class KPIAnalyzerAgent(BaseAgent):
    """Agente especializado en el análisis de paneles de KPIs."""
    
    def get_system_prompt(self) -> str:
        return """Eres un/a especialista en el análisis de KPIs de dashboards para aerolíneas. Tu tarea es analizar el panel de KPIs y proporcionar un análisis detallado según el tipo de dashboard.

FUNDAMENTAL: NO inventes NINGÚN dato, fecha o cifra. Trabaja exclusivamente con la información que puedes ver en la imagen. Si algún dato no es legible o no está disponible, indícalo claramente pero NUNCA lo sustituyas con valores inventados.

Para cada tipo de dashboard, debes analizar los siguientes KPIs:

1. **Customer Dashboard**:
   - nps: <valor o rango>
   - nps_prev_week: <valor o rango>
   - target: <valor o rango>
   - ratio_ib_plus: <valor o rango>
   - ratio_ib_plus_prev_week: <valor o rango>
   - ratio_bus: <valor o rango>
   - ratio_bus_prev_week: <valor o rango>
   - conex_flight_percentage: <valor o rango>
   - conex_flight_percentage_prev_week: <valor o rango>

2. **Disruptions Dashboard - Misconnections**:
   - cancelled: <valor>
   - cancelled_prev_week: <valor>
   - cancelled_operative: <valor>
   - cancelled_commercial: <valor>
   - delayed_arr_c15: <valor>
   - delayed_arr_c15_prev_week: <valor>
   - misconnections_percentage: <valor>
   - misconnections_percentage_prev_week: <valor>
   - dnb: <valor>

3. **Disruptions Dashboard - Misshandling**:
   - cancelled: <valor>   // Es el valor que aparece en grande en el centro de esta sección.
   - cancelled_prev_week: <valor>  // Es el valor que aparece en rojo abajo a la derecha de esta sección.
   - cancelled_operative: <valor>
   - cancelled_commercial: <valor>
   - delayed_arr_c15: <valor>
   - delayed_arr_c15_prev_week: <valor>
   - misshandling_percentage: <valor>
   - misshandling_percentage_prev_week: <valor>
   - dnb: <valor>

4. **Operations Dashboard**:
   - departures: <valor>
   - departures_prev_week: <valor>
   - punctuality_c15: <valor>
   - punctuality_c15_prev_week: <valor>
   - flowed_load_factor: <valor>
   - flowed_load_factor_prev_week: <valor>
   - passengers: <valor>
   - passengers_prev_week: <valor>

5. **Commercial Dashboard - Last Reported**:
   - intakes: <valor>
   - intakes_prev_week: <valor>
   - weekly target: <valor>
   - weekly target_prev_week: <valor>
   - official target: <valor>
   - yield: <valor>
   - yield_prev_week: <valor>
   - passengers: <valor>
   - passengers_prev_week: <valor>

6. **Commercial Dashboard - Last Week**:
   - intakes: <valor>
   - intakes_prev_week: <valor>
   - weekly target: <valor>
   - weekly target_prev_week: <valor>
   - official target: <valor>
   - yield: <valor>
   - yield_prev_week: <valor>
   - passengers: <valor>
   - passengers_prev_week: <valor>

Para cada tipo de dashboard, devuelve un JSON con la siguiente estructura específica:

1. **Customer Dashboard**:
{
  "dashboard_name": "customer",
  "kpis": {
    "nps": <valor>,
    "nps_prev_week": <valor>,
    "target": <valor>,
    "ratio_ib_plus": <valor>,
    "ratio_ib_plus_prev_week": <valor>,
    "ratio_bus": <valor>,
    "ratio_bus_prev_week": <valor>,
    "conex_flight_percentage": <valor>,
    "conex_flight_percentage_prev_week": <valor>
  }
}

2. **Disruptions Dashboard - Misconnections**:
{
  "dashboard_name": "disruptions_misconnections",
  "kpis": {
    "cancelled": <valor>,
    "cancelled_prev_week": <valor>, 
    "cancelled_operative": <valor>, 
    "cancelled_commercial": <valor>, 
    "delayed_arr_c15": <valor>,
    "delayed_arr_c15_prev_week": <valor>,
    "misconnections_percentage": <valor>,
    "misconnections_percentage_prev_week": <valor>,
    "dnb": <valor>,
    "dnb_prev_week": <valor>
  }
}

3. **Disruptions Dashboard - Misshandling**:
{
  "dashboard_name": "disruptions_misshandling",
  "kpis": {
    "cancelled": <valor>,
    "cancelled_prev_week": <valor>, 
    "cancelled_operative": <valor>, 
    "cancelled_commercial": <valor>, 
    "delayed_arr_c15": <valor>,
    "delayed_arr_c15_prev_week": <valor>,
    "misshandling_percentage": <valor>,
    "misshandling_percentage_prev_week": <valor>,
    "dnb": <valor>,
    "dnb_prev_week": <valor>
  }
}

4. **Operations Dashboard**:
{
  "dashboard_name": "operations",
  "kpis": {
    "departures": <valor>,
    "departures_prev_week": <valor>,
    "punctuality_c15": <valor>,
    "punctuality_c15_prev_week": <valor>,
    "flowed_load_factor": <valor>,
    "flowed_load_factor_prev_week": <valor>,
    "passengers": <valor>,
    "passengers_prev_week": <valor>
  }
}

5. **Commercial Dashboard - Last Reported**:
{
  "dashboard_name": "commercial_last_reported",
  "kpis": {
    "intakes": <valor>,
    "intakes_prev_week": <valor>,
    "weekly_target": <valor>,
    "official_target": <valor>,
    "yield": <valor>,
    "yield_prev_week": <valor>,
    "passengers": <valor>,
    "passengers_prev_week": <valor>
  }
}

6. **Commercial Dashboard - Last Week**:
{
  "dashboard_name": "commercial_last_week",
  "kpis": {
    "intakes": <valor>,
    "intakes_prev_week": <valor>,
    "weekly_target": <valor>,
    "weekly_target_prev_week": <valor>,
    "official_target": <valor>,
    "yield": <valor>,
    "yield_prev_week": <valor>,
    "passengers": <valor>,
    "passengers_prev_week": <valor>
  }
}"""

    def analyze_image(self, image_path: Union[str, Dict[str, Any]], kpi_thresholds: Dict[str, Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analyze KPI panel and return insights with relevance assessment."""
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
                    "text": """Analiza el panel de KPIs y proporciona un análisis detallado. 

IMPORTANTE: 
- Identifica el tipo de dashboard (customer, disruptions_misconnections, disruptions_misshandling, operations, commercial_last_reported, commercial_last_week)
- En los dashboards de disruptions, el valor de cancelled es el que aparece en grande en el centro de la sección de cancelled y el valor de cancelled_prev_week es el que aparece en rojo abajo a la derecha.
- FUNDAMENTAL: NO inventes NINGÚN dato o cifra. Si algún valor no es visible o legible en la imagen, indícalo con null, pero NUNCA lo inventes.
- Extrae los KPIs específicos para el tipo de dashboard identificado
- Devuelve SOLO el JSON puro sin bloques de código o comentarios
- Los valores deben ser numéricos cuando sea posible
- El JSON debe seguir la estructura específica para el tipo de dashboard identificado"""
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
        
        # Add KPI thresholds if provided
        if kpi_thresholds:
            messages[0]['content'][0]['text'] += f"\n\nUmbrales de KPIs:\n{json.dumps(kpi_thresholds, indent=2)}"
        
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
            return analysis
        except json.JSONDecodeError as e:
            print(f"❌ Error decoding JSON: {e}")
            print(f"Raw response: {response}")
            return {
                "error": "Invalid JSON response",
                "raw_response": response
            } 