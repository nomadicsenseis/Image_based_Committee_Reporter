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

class OperationsAgent(BaseAgent):
    """Agente especializado en el análisis de dashboards de 'Operations' para aerolíneas."""
    
    def __init__(self):
        super().__init__()
        self.kpi_analyzer = KPIAnalyzerAgent()
        self.trendline_analyzer = TrendlineAnalyzerAgent()
        self.map_analyzer = MapAnalyzerAgent()
        
        # Definir los umbrales para los KPIs según la tabla proporcionada
        self.kpi_thresholds = {
            "departures": {
                "min": 1500,
                "max": 2000,
                "change_threshold": 0.05,  # 5% vs PW
                "change_type": "percentage"
            },
            "punctuality_c15": {
                "min": 0.87,  # 87%
                "max": 0.90,  # 90%
                "change_threshold": 0.05,  # 5% vs PW
                "change_type": "percentage"
            },
            "load_factor": {
                "min": 0.80,  # 80%
                "max": 0.90,  # 90%
                "change_threshold": 0.05,  # 5% vs PW
                "change_type": "percentage"
            },
            "passengers": {
                "min": 300000,
                "max": 400000,
                "change_threshold": 0.05,  # 5% vs PW
                "change_type": "percentage"
            }
        }
        
        self.trend_thresholds = {
            "departures": {
                "change_threshold": 200,  # vuelos
                "trend_threshold": 3    # número de puntos consecutivos
            },
            "punctuality_c15": {
                "change_threshold": 0.05,  # porcentaje
                "trend_threshold": 3    # número de puntos consecutivos
            },
            "load_factor": {
                "change_threshold": 0.05,  # porcentaje
                "trend_threshold": 3    # número de puntos consecutivos
            },
            "passengers": {
                "change_threshold": 20000,  # pax
                "trend_threshold": 3    # número de puntos consecutivos
            }
        }
        
        self.map_thresholds = {
            "departures": {
                "high_threshold": 1800,   # vuelos
                "low_threshold": 1200,    # vuelos
                "anomaly_threshold": 300  # desviación estándar
            },
            "punctuality_c15": {
                "high_threshold": 0.90,   # porcentaje
                "low_threshold": 0.85,    # porcentaje
                "anomaly_threshold": 0.10  # desviación estándar
            }
        }
    
    def get_system_prompt(self) -> str:
        return """Eres un/a especialista en la revisión del panel de "Operations" para aerolíneas. Tu tarea es coordinar el análisis de diferentes aspectos del dashboard de operations, utilizando agentes especializados para cada componente."""
    
    def analyze_image(self, image_paths: Dict[str, str]) -> Dict[str, Any]:
        """Analyze operations dashboard images using specialized agents."""
        # Obtener las imágenes para cada tipo de análisis
        kpi_image = image_paths.get("panel_kpis_operations")
        
        # Imágenes de tendencias (inbound/outbound) - Use CORRECT keys in dictionary definition
        trend_images = {
            "inbound_PuncDep15_evolution": image_paths.get("inbound_PuncDep15_evolution"), # Corrected Dict Key
            "outbound_PuncDep15_evolution": image_paths.get("outbound_PuncDep15_evolution") # Corrected Dict Key
        }
        
        # Imágenes de mapas (inbound/outbound) - Use CORRECT keys in dictionary definition
        map_images = {
            "inbound_PuncDep15_byregion": image_paths.get("inbound_PuncDep15_byregion"), # Corrected Dict Key
            "outbound_PuncDep15_byregion": image_paths.get("outbound_PuncDep15_byregion") # Corrected Dict Key
        }
        
        # Registrar qué imágenes están disponibles
        print("\n📊 Operations Images Status:")
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
                        direccion_esperada=direccion_esperada 
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
        
        # --- REMOVE DEBUG OPERATIONS TREND INPUT --- 
        # print(f"\n--- DEBUG (OperationsAgent): Trend data received --- ")
        # print(json.dumps(raw_data.get("trend_data", {}), indent=2, ensure_ascii=False))
        # print("--- END DEBUG (OperationsAgent Trend Input) --- \n")
        # --- END REMOVE --- 
        
        # --- REMOVE DEBUG OPERATIONS MAP INPUT --- 
        # print(f"\n--- DEBUG (OperationsAgent): Map data received --- ")
        # print(json.dumps(raw_data.get("map_data", {}), indent=2, ensure_ascii=False))
        # print("--- END DEBUG (OperationsAgent) --- \n")
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
        
        system_prompt = """Eres un/a especialista en la revisión y análisis del panel de "Operations" para aerolíneas. 
Tu tarea es analizar los datos proporcionados, verificar si los valores exceden los umbrales definidos, y generar un análisis 
estructurado en formato JSON siguiendo exactamente el esquema proporcionado.

Identifica los KPIs que están fuera de rango o que tienen cambios significativos comparados con valores previos.
Para cada valor relevante, proporciona un análisis claro y accionable sobre las operaciones.
Mantén estrictamente la estructura JSON proporcionada en el prompt."""

        try:
            # Ensure json is available within the outer try for invoke_model
            import json
            response = self.invoke_model(messages, system_prompt)
            try:
                # Ensure json is available for parsing logic
                import json
                # Find JSON content in the response
                import re
                json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    json_str = response
                
                # Parse the JSON
                llm_result = json.loads(json_str) # Store parsed result separately
                
                if not isinstance(llm_result, dict):
                    print("Error: Model did not return a valid JSON object.")
                    return self._create_empty_structure()

                # --- START RECONSTRUCTION --- 
                final_result = {
                    # Copy other top-level keys directly
                    "trend_analysis": llm_result.get("trend_analysis", {}),
                    "map_analysis": llm_result.get("map_analysis", {}),
                    "overall_analysis": llm_result.get("overall_analysis", "")
                }
                reconstructed_kpi_analysis = {}
                original_kpi_analysis = llm_result.get("kpi_analysis", {})

                kpi_definitions = {
                    "departures_vs_departures_prev_week": ("departures_value", "prev_week_departures_value", ["departures_prev_week"]),
                    "punctuality_c15_vs_punctuality_c15_prev_week": ("punctuality_c15_value", "prev_week_punctuality_c15_value", ["punctuality_c15_prev_week"]),
                    "flowed_load_factor_vs_flowed_load_factor_prev_week": ("flowed_load_factor_value", "prev_week_flowed_load_factor_value", ["flowed_load_factor_prev_week"]),
                    "passengers_vs_passengers_prev_week": ("passengers_value", "prev_week_passengers_value", ["passengers_prev_week"])
                }
                
                processed_original_keys = set()

                # Process defined comparison KPIs first
                for target_key, (val_key, prev_val_key, alt_keys) in kpi_definitions.items():
                    found_data = None
                    # Check if target key exists
                    if target_key in original_kpi_analysis:
                        found_data = original_kpi_analysis.get(target_key)
                        processed_original_keys.add(target_key)
                    else:
                        # Check alternative keys
                        for alt_key in alt_keys:
                            if alt_key in original_kpi_analysis:
                                found_data = original_kpi_analysis.get(alt_key)
                                processed_original_keys.add(alt_key)
                                break
                    
                    # Reconstruct the internal structure
                    new_data = {}
                    if isinstance(found_data, dict):
                        new_data = {
                            val_key: found_data.get(val_key, found_data.get("value")), 
                            prev_val_key: found_data.get(prev_val_key, found_data.get("previous_value")),
                            "difference": found_data.get("difference"),
                            "percentage_change": found_data.get("percentage_change"),
                            "is_relevant": found_data.get("is_relevant", False),
                            "analysis": found_data.get("analysis", "")
                        }
                        new_data = {k: v for k, v in new_data.items() if v is not None} # Clean None
                    elif found_data is not None: # Handle cases where data might not be a dict
                         new_data = found_data # Keep original data if not a dict
                    
                    # Assign reconstructed data to the target key even if empty
                    reconstructed_kpi_analysis[target_key] = new_data

                # Add remaining simple KPIs
                for original_key, kpi_data in original_kpi_analysis.items():
                    if original_key not in processed_original_keys and original_key not in [alt for _, _, alt_list in kpi_definitions.values() for alt in alt_list]:
                         # Ensure simple KPIs also have the standard {value:..., analysis:...} structure if possible
                         if isinstance(kpi_data, dict):
                             reconstructed_kpi_analysis[original_key] = {
                                 "value": kpi_data.get("value"),
                                 "analysis": kpi_data.get("analysis", "")
                             }
                             reconstructed_kpi_analysis[original_key] = {k:v for k,v in reconstructed_kpi_analysis[original_key].items() if v is not None}
                         else: # If not a dict, store the value directly under 'value'
                             reconstructed_kpi_analysis[original_key] = {"value": kpi_data, "analysis": ""}
                         

                final_result["kpi_analysis"] = reconstructed_kpi_analysis
                # --- END RECONSTRUCTION ---
                                
                # --- REMOVE DEBUG OPERATIONS MAP OUTPUT --- 
                # print(f"\n--- DEBUG (OperationsAgent): Map analysis in LLM result --- ")
                # print(json.dumps(llm_result.get("map_analysis", {}), indent=2, ensure_ascii=False))
                # print("--- END DEBUG (OperationsAgent) ---\n")
                # --- END REMOVE --- 

                # --- REMOVE DEBUG OPERATIONS TREND OUTPUT --- 
                # print(f"\n--- DEBUG (OperationsAgent): Trend analysis in LLM result --- ")
                # print(json.dumps(llm_result.get("trend_analysis", {}), indent=2, ensure_ascii=False))
                # print("--- END DEBUG (OperationsAgent Trend Output) ---\n")
                # --- END REMOVE --- 

                return final_result # Return the fully reconstructed result
                
            except json.JSONDecodeError:
                # Ensure json is available for error handling
                import json
                print("Error: Could not parse JSON from model response.")
                print(f"Response: {response}")
                return self._create_empty_structure()
            except Exception as parse_err: # Catch other potential parsing/reconstruction errors
                 import json # Ensure json is available
                 print(f"Error during operations analysis post-processing: {parse_err}")
                 return self._create_empty_structure()
                
        except Exception as e:
            # Ensure json is available for error handling
            import json
            print(f"Error calling model in OperationsAgent: {e}")
            return self._create_empty_structure()
    
    def _create_analysis_prompt(self, raw_data: Dict[str, Any], thresholds: Dict[str, Any]) -> str:
        """Create a prompt for the model to generate a structured analysis."""
        prompt = f"""Analiza los siguientes datos del dashboard de Operations y proporciona un análisis estructurado.

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
        2. **Tendencias:** Describe patrones clave y **OBLIGATORIAMENTE incluye los valores `valor_maximo` y `valor_minimo`** para cada segmento (in/out) si los datos de entrada (`trend_data`) los contienen.
        3. **Mapas:** Describe patrones clave y **OBLIGATORIAMENTE incluye `region_maxima`, `valor_maximo`, `region_minima`, `valor_minimo`** para cada segmento (in/out) si los datos de entrada (`map_data`) los contienen.
        4. **Overall:** Resume hallazgos clave, incluyendo los **máximos y mínimos MÁS SIGNIFICATIVOS** de tendencias y mapas.
        5. Genera un análisis estructurado siguiendo **ESTRICTAMENTE** el formato JSON de salida especificado.

        **Formato JSON de Salida Requerido (¡SEGUIR ESTRICTAMENTE! INCLUIR *TODOS* LOS CAMPOS):**
        ```json
        {{
          "kpi_analysis": {{
            "departures": {{ "value": number, "analysis": "string" }},
            "departures_vs_departures_prev_week": {{ "departures_value": number, "prev_week_departures_value": number, "difference": number, "percentage_change": number | null, "is_relevant": boolean, "analysis": "string" }},
            "punctuality_c15": {{ "value": number, "analysis": "string" }},
            "punctuality_c15_vs_punctuality_c15_prev_week": {{ "punctuality_c15_value": number, "prev_week_punctuality_c15_value": number, "difference": number, "percentage_change": number | null, "is_relevant": boolean, "analysis": "string" }},
            "flowed_load_factor": {{ "value": number, "analysis": "string" }},
            "flowed_load_factor_vs_flowed_load_factor_prev_week": {{ "flowed_load_factor_value": number, "prev_week_flowed_load_factor_value": number, "difference": number, "percentage_change": number | null, "is_relevant": boolean, "analysis": "string" }},
            "passengers": {{ "value": number, "analysis": "string" }},
            "passengers_vs_passengers_prev_week": {{ "passengers_value": number, "prev_week_passengers_value": number, "difference": number, "percentage_change": number | null, "is_relevant": boolean, "analysis": "string" }}
          }},
          "trend_analysis": {{
            "inbound": {{
              "PunDepC15_evolution": {{ "overall_analysis": "string", "valor_maximo": number | null, "valor_minimo": number | null }}
            }},
            "outbound": {{
              "PunDepC15_evolution": {{ "overall_analysis": "string", "valor_maximo": number | null, "valor_minimo": number | null }}
            }}
          }},
          "map_analysis": {{
            "inbound": {{ "analysis": "string", "region_maxima": string | null, "valor_maximo": number | null, "region_minima": string | null, "valor_minimo": number | null }},
            "outbound": {{ "analysis": "string", "region_maxima": string | null, "valor_maximo": number | null, "region_minima": string | null, "valor_minimo": number | null }}
          }},
          "overall_analysis": "string (incluyendo resumen de max/min)"
        }}
        ```

        **Reglas CRÍTICAS:**
        - **INCLUYE TODOS LOS CAMPOS** del formato JSON, especialmente `valor_maximo`, `valor_minimo`, `region_maxima`, `region_minima` donde se especifica. Si los datos de entrada no los proporcionan para un segmento, puedes usar `null` como valor, pero la clave DEBE estar presente.
        - Menciona KPIs solo si son relevantes.
        - Usa diferencia absoluta, no porcentual, para KPIs comparativos.
        - Enfócate solo en IB.
        - No hables de factor de carga, habla de load_factor.
        - No inventes datos.
        - **RESPONDE ÚNICAMENTE CON EL JSON.**
        """
        return prompt

    def _create_empty_structure(self) -> Dict[str, Any]:
        """Create an empty structure following the expected format."""
        return {
            "kpi_analysis": {
                "departures": {},
                "departures_vs_departures_prev_week": {},
                "punctuality_c15": {},
                "punctuality_c15_vs_punctuality_c15_prev_week": {},
                "flowed_load_factor": {},
                "flowed_load_factor_vs_flowed_load_factor_prev_week": {},
                "passengers": {},
                "passengers_vs_passengers_prev_week": {}
            },
            "trend_analysis": {
                "inbound": {
                    "PunDepC15_evolution": {}
                },
                "outbound": {
                    "PunDepC15_evolution": {}
                }
            },
            "map_analysis": {
                "inbound": {},
                "outbound": {}
            },
            "overall_analysis": "No se pudo generar un análisis debido a un error."
        }