from .base_agent import BaseAgent
from .kpi_analyzer_agent import KPIAnalyzerAgent
from .trendline_analyzer_agent import TrendlineAnalyzerAgent
from .map_analyzer_agent import MapAnalyzerAgent
from typing import Dict, Any, List, Union
import json
import os
import sys

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.image_utils import encode_image

class CustomerAgent(BaseAgent):
    """Agente especializado en el análisis de dashboards de 'Customer' para aerolíneas."""
    
    def __init__(self):
        super().__init__()
        self.kpi_analyzer = KPIAnalyzerAgent()
        self.trendline_analyzer = TrendlineAnalyzerAgent()
        self.map_analyzer = MapAnalyzerAgent()
        
        # Definir los umbrales para los KPIs según la tabla proporcionada
        self.kpi_thresholds = {
            "nps": {
                "min": 25,
                "max": 40,
                "change_threshold": 5,  # 5 puntos vs target
                "change_type": "absolute"  # Para NPS usamos diferencia absoluta
            },
            "ratio_pax_ib_plus": {
                "min": 0.25,  # 25%
                "max": 0.30,  # 30%
                "change_threshold": 0.10,  # 10% vs PW
                "change_type": "percentage"
            },
            "leisure_business": {
                "min": 0.18,  # 18%
                "max": 0.25,  # 25%
                "change_threshold": 0.05,  # 5% vs PW
                "change_type": "percentage"
            },
            "conex_flight": {
                "min": 0.12,  # 12%
                "max": 0.18,  # 18%
                "change_threshold": 0.05,  # 5% vs PW
                "change_type": "percentage"
            }
        }
        
        self.trend_thresholds = {
            "nps": {
                "change_threshold": 5,  # puntos
                "trend_threshold": 3    # número de puntos consecutivos
            },
            "ratio_pax_ib_plus": {
                "change_threshold": 10,  # porcentaje
                "trend_threshold": 3    # número de puntos consecutivos
            },
            "leisure_business": {
                "change_threshold": 5,  # porcentaje
                "trend_threshold": 3    # número de puntos consecutivos
            }
        }
        
        self.map_thresholds = {
            "nps": {
                "high_threshold": 35,   # puntos
                "low_threshold": 20,    # puntos
                "anomaly_threshold": 15  # desviación estándar
            }
        }
    
    def get_system_prompt(self) -> str:
        return """Eres un/a especialista en la revisión del panel de "Customer" para aerolíneas. Tu tarea es coordinar el análisis de diferentes aspectos del dashboard de customer, utilizando agentes especializados para cada componente."""
    
    def analyze_image(self, image_paths: Dict[str, str]) -> Dict[str, Any]:
        """Analyze customer dashboard images using specialized agents."""
        # Obtener las imágenes para cada tipo de análisis
        kpi_image = image_paths.get("panel_kpis_customer")
        
        # Imágenes de tendencias (inbound/outbound)
        trend_images = {
            "inbound_nps_evolution": image_paths.get("inbound_NPS_evolution"),
            "outbound_nps_evolution": image_paths.get("outbound_NPS_evolution")
        }
        
        # Imágenes de mapas (inbound/outbound)
        map_images = {
            "inbound_nps_byregion": image_paths.get("inbound_NPS_byregion"),
            "outbound_nps_byregion": image_paths.get("outbound_NPS_byregion")
        }
        
        # Registrar qué imágenes están disponibles
        print("\n📊 Customer Images Status:")
        print(f"KPI Image: {'✅ Found' if kpi_image else '❌ Missing'}")
        print("Trend Images:")
        for trend_type, img_path in trend_images.items():
            status = "✅ Found" if img_path else "❌ Missing"
            print(f"  - {trend_type}: {status}")
        print("Map Images:")
        for map_type, img_path in map_images.items():
            status = "✅ Found" if img_path else "❌ Missing"
            print(f"  - {map_type}: {status}")
        
        # Collect raw outputs from specialized agents
        raw_data = {
            "kpi_data": {},
            "trend_data": {},
            "map_data": {}
        }
        
        # Implementar paralelización para análisis de KPIs, Trends y Maps
        from concurrent.futures import ThreadPoolExecutor
        import time
        
        # Función para ejecutar análisis de KPIs
        def analyze_kpis():
            if kpi_image:
                start_time = time.time()
                print(f"Analyzing KPI image: {os.path.basename(kpi_image)}")
                kpi_analysis = self.kpi_analyzer.analyze_image(kpi_image)
                elapsed_time = time.time() - start_time
                print(f"✅ KPI analysis completed in {elapsed_time:.2f} seconds")
                return kpi_analysis
            return None
            
        # Función para ejecutar análisis de Trends
        def analyze_trends():
            trend_results = {}
            for trend_type, img_path in trend_images.items():
                if img_path:
                    start_time = time.time()
                    print(f"Analyzing trend image {trend_type}: {os.path.basename(img_path)}")
                    trend_analysis = self.trendline_analyzer.analyze_image(img_path)
                    elapsed_time = time.time() - start_time
                    print(f"✅ Trend analysis for {trend_type} completed in {elapsed_time:.2f} seconds")
                    if trend_analysis is not None and "error" not in trend_analysis:
                        trend_results[trend_type] = trend_analysis
            return trend_results
            
        # Función para ejecutar análisis de Maps
        def analyze_maps():
            map_results = {}
            for map_type, img_path in map_images.items():
                if img_path:
                    # Extract direction from map_type key
                    direccion_esperada = None
                    if "inbound" in map_type.lower():
                        direccion_esperada = "inbound"
                    elif "outbound" in map_type.lower():
                        direccion_esperada = "outbound"
                        
                    start_time = time.time()
                    print(f"Analyzing map image {map_type}: {os.path.basename(img_path)}")
                    # Pass the expected direction to the analyzer
                    map_analysis = self.map_analyzer.analyze_image(
                        image_path=img_path,
                        direccion_esperada=direccion_esperada,
                        map_thresholds=self.map_thresholds # Pass thresholds if needed
                    )
                    elapsed_time = time.time() - start_time
                    print(f"✅ Map analysis for {map_type} completed in {elapsed_time:.2f} seconds")
                    if map_analysis is not None and "error" not in map_analysis:
                        map_results[map_type] = map_analysis
            return map_results
        
        # Ejecutar los análisis en paralelo
        with ThreadPoolExecutor(max_workers=3) as executor:
            # Iniciar todos los análisis
            kpi_future = executor.submit(analyze_kpis)
            trend_future = executor.submit(analyze_trends)
            map_future = executor.submit(analyze_maps)
            
            # Recoger resultados
            try:
                kpi_analysis = kpi_future.result()
                if kpi_analysis is not None and "error" not in kpi_analysis:
                    raw_data["kpi_data"] = kpi_analysis
            except Exception as e:
                print(f"❌ Error in KPI analysis: {str(e)}")
                
            try:
                raw_data["trend_data"] = trend_future.result()
            except Exception as e:
                print(f"❌ Error in Trend analysis: {str(e)}")
                
            try:
                raw_data["map_data"] = map_future.result()
            except Exception as e:
                print(f"❌ Error in Map analysis: {str(e)}")
        
        # Generate full analysis from raw data
        analysis = self.generate_analysis(raw_data)
        
        return analysis

    def generate_analysis(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a structured analysis using the LLM based on raw data from sub-agents."""
        # Ensure json is available for potential use in prompt creation or error handling
        import json 
        # Get the defined thresholds for the model
        thresholds_info = {
            "kpi_thresholds": self.kpi_thresholds,
            "trend_thresholds": self.trend_thresholds,
            "map_thresholds": self.map_thresholds
        }
        
        # --- REMOVE DEBUG CUSTOMER TREND INPUT --- 
        # print(f"\n--- DEBUG (CustomerAgent): Trend data received --- ")
        # print(json.dumps(raw_data.get("trend_data", {}), indent=2, ensure_ascii=False))
        # print("--- END DEBUG (CustomerAgent Trend Input) --- \n")
        # --- END REMOVE --- 

        # --- REMOVE DEBUG CUSTOMER MAP INPUT --- 
        # print(f"\n--- DEBUG (CustomerAgent): Map data received --- ")
        # print(json.dumps(raw_data.get("map_data", {}), indent=2, ensure_ascii=False))
        # print("--- END DEBUG (CustomerAgent) --- \n")
        # --- END REMOVE --- 

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": self._create_analysis_prompt(raw_data, thresholds_info)
                    }
                ]
            }
        ]
        
        system_prompt = """Eres un/a especialista en la revisión y análisis del panel de "Customer" para aerolíneas. 
Tu tarea es analizar los datos proporcionados, verificar si los valores exceden los umbrales definidos, y generar un análisis 
estructurado en formato JSON siguiendo exactamente el esquema proporcionado.

Identifica los KPIs que están fuera de rango o que tienen cambios significativos comparados con valores previos o target.
Para cada valor relevante, proporciona un análisis claro y accionable.
Mantén estrictamente la estructura JSON proporcionada en el prompt."""

        try:
            # Ensure json is available within the outer try for invoke_model
            import json 
            response = self.invoke_model(messages, system_prompt)
            try:
                # Ensure json is available for parsing logic
                import json 
                # Find JSON content in the response
                import re # json already imported above
                # Try to find JSON between markdown code blocks
                json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    # If not found in code blocks, use the entire response
                    json_str = response
                
                # Parse the JSON
                result = json.loads(json_str)
                
                # --- REMOVE DEBUG CUSTOMER TREND OUTPUT --- 
                # print(f"\n--- DEBUG (CustomerAgent): Trend analysis in LLM result --- ")
                # print(json.dumps(result.get("trend_analysis", {}), indent=2, ensure_ascii=False))
                # print("--- END DEBUG (CustomerAgent Trend Output) ---\n")
                # --- END REMOVE --- 

                # --- REMOVE DEBUG CUSTOMER MAP OUTPUT --- 
                # print(f"\n--- DEBUG (CustomerAgent): Map analysis in LLM result --- ")
                # print(json.dumps(result.get("map_analysis", {}), indent=2, ensure_ascii=False))
                # print("--- END DEBUG (CustomerAgent) ---\n")
                # --- END REMOVE --- 

                # Ensure we have the right structure
                if not isinstance(result, dict):
                    print("Error: Model did not return a valid JSON object.")
                    # Return a basic structure
                    return self._create_empty_structure()
                
                return result
                
            except json.JSONDecodeError:
                # Ensure json is available for error handling
                import json 
                print("Error: Could not parse JSON from model response.")
                print(f"Response: {response}")
                return self._create_empty_structure()
            except Exception as parse_err: # Catch other potential parsing errors
                 import json # Ensure json is available
                 print(f"Error during customer analysis post-processing: {parse_err}")
                 return self._create_empty_structure()
                
        except Exception as e:
            # Ensure json is available for error handling
            import json 
            print(f"Error calling model in CustomerAgent: {e}")
            return self._create_empty_structure()
    
    def _create_analysis_prompt(self, raw_data: Dict[str, Any], thresholds: Dict[str, Any]) -> str:
        """Create a prompt for the model to generate a structured analysis."""
        prompt = f"""Analiza los siguientes datos del dashboard de Customer y proporciona un análisis estructurado.

        **ANÁLISIS DETALLADOS DE ENTRADA:**
        ### Datos de KPIs
        {json.dumps(raw_data.get("kpi_data", {}), indent=2)}
        
        ### Datos de Tendencias
        {json.dumps(raw_data.get("trend_data", {}), indent=2)}
        
        ### Datos de Mapas
        {json.dumps(raw_data.get("map_data", {}), indent=2)}
        
        ### Umbrales definidos para evaluar los datos:
        {json.dumps(thresholds, indent=2)}
        
        **TAREA:**
        1. Evalúa todos los KPIs relevantes contra umbrales.
        2. **Tendencias:** Describe patrones clave y **OBLIGATORIAMENTE incluye los valores `nps_maximo` y `nps_minimo`** para cada segmento (in/out) si los datos de entrada (`trend_data`) los contienen.
        3. **Mapas:** Describe patrones clave y **OBLIGATORIAMENTE incluye `region_maxima_nps`, `nps_maximo`, `region_minima_nps`, `nps_minimo`** para cada segmento (in/out) si los datos de entrada (`map_data`) los contienen.
        4. **Overall:** Resume hallazgos clave, incluyendo los **máximos y mínimos de NPS MÁS SIGNIFICATIVOS** de tendencias y mapas.
        5. Genera un análisis estructurado siguiendo **ESTRICTAMENTE** el formato JSON de salida especificado.

        **Formato JSON de Salida Requerido (¡SEGUIR ESTRICTAMENTE! INCLUIR *TODOS* LOS CAMPOS):**
        ```json
        {{
          "kpi_analysis": {{
            "nps": {{ "value": number, "analysis": "string" }},  
            "nps_vs_nps_prev_week": {{ "nps_value": number, "prev_week_nps_value": number, "difference": number, "percentage_change": number | null, "is_relevant": boolean, "analysis": "string" }},
            "nps_vs_target": {{ "nps_value": number, "target": number, "difference": number, "percentage_change": number | null, "is_relevant": boolean, "analysis": "string" }},
            "ratio_ib_plus": {{ "value": number, "analysis": "string" }},
            "ratio_ib_plus_prev_week": {{ "ratio_ib_plus_value": number, "prev_week_ratio_ib_plus_value": number, "difference": number, "percentage_change": number | null, "is_relevant": boolean, "analysis": "string" }},
            "ratio_bus_leisure": {{ "value": number, "analysis": "string" }},
            "ratio_bus_leisure_prev_week": {{ "ratio_bus_leisure_value": number, "prev_week_ratio_bus_leisure_value": number, "difference": number, "percentage_change": number | null, "is_relevant": boolean, "analysis": "string" }},
            "conex_flight_percentage": {{ "value": number, "analysis": "string" }},
            "conex_flight_percentage_prev_week": {{ "conex_flight_percentage_value": number, "prev_week_conex_flight_percentage_value": number, "difference": number, "percentage_change": number | null, "is_relevant": boolean, "analysis": "string" }}
          }},
          "trend_analysis": {{
            "inbound": {{
              "NPS_evolution": {{ "overall_analysis": "string", "nps_maximo": number | null, "nps_minimo": number | null }}
            }},
            "outbound": {{
              "NPS_evolution": {{ "overall_analysis": "string", "nps_maximo": number | null, "nps_minimo": number | null }}
            }}
          }},
          "map_analysis": {{
            "inbound": {{ "analysis": "string", "region_maxima_nps": string | null, "nps_maximo": number | null, "region_minima_nps": string | null, "nps_minimo": number | null }},
            "outbound": {{ "analysis": "string", "region_maxima_nps": string | null, "nps_maximo": number | null, "region_minima_nps": string | null, "nps_minimo": number | null }}
          }},
          "overall_analysis": "string (incluyendo resumen de max/min NPS)"
        }}
        ```

        **Reglas CRÍTICAS:**
        - **INCLUYE TODOS LOS CAMPOS** del formato JSON, especialmente los de max/min NPS y regiones donde se especifica. Si los datos de entrada no los proporcionan, usa `null` como valor, pero la clave DEBE estar presente.
        - Menciona KPIs solo si son relevantes.
        - Usa diferencia absoluta para NPS vs Target, no % diff para vs PW.
        - No inventes datos.
        - **RESPONDE ÚNICAMENTE CON EL JSON.**
        """
        return prompt

    def _create_empty_structure(self) -> Dict[str, Any]:
        """Create an empty structure following the expected format."""
        return {
            "kpi_analysis": {
                "nps": {},  
                "nps_vs_nps_prev_week": {}, 
                "nps_vs_target": {}, 
                "ratio_ib_plus": {},
                "ratio_ib_plus_prev_week": {},
                "ratio_bus_leisure": {},
                "ratio_bus_leisure_prev_week": {},
                "conex_flight_percentage": {},
                "conex_flight_percentage_prev_week": {}
            },
            "trend_analysis": {
                "inbound": {
                    "NPS_evolution": {}
                },
                "outbound": {
                    "NPS_evolution": {}
                }
            },
            "map_analysis": {
                "inbound": {},
                "outbound": {}
            },
            "overall_analysis": "No se pudo generar un análisis debido a un error."
        }