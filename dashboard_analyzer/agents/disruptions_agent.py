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

class DisruptionsAgent(BaseAgent):
    """Agente especializado en el análisis de dashboards de 'Disruptions' para aerolíneas."""
    
    def __init__(self):
        super().__init__()
        self.kpi_analyzer = KPIAnalyzerAgent()
        self.trendline_analyzer = TrendlineAnalyzerAgent()
        self.map_analyzer = MapAnalyzerAgent()
        
        # Definir los umbrales para los KPIs según la tabla proporcionada
        self.kpi_thresholds = {
            "cancelled": {
                "min": 0,
                "max": 15,  # valores absolutos
                "change_threshold": 0.10,  # 10% vs PW
                "change_type": "percentage"
            },
            "delayed_arr_c15": {
                "min": 200,
                "max": 400,  # valores absolutos
                "change_threshold": 0.10,  # 10% vs PW
                "change_type": "percentage"
            },
            "misconnections_percentage": {
                "min": 0.75,  # 0,75%
                "max": 1.0,   # 1%
                "change_threshold": 0.05,  # 5% vs PW
                "change_type": "percentage"
            },
            "misshandling_permille": {
                "min": 12.0,  # 12‰
                "max": 18.0,  # 18‰
                "change_type": "percentage",
                "change_threshold": 0.05  # 5% vs PW
            },
            "dng": {
                "min": 0.3,  # 0,3‰
                "max": 1.0,  # 1‰
                "change_threshold": 0.05,  # 5% vs PW
                "change_type": "percentage"
            },
            "dnb": {
                "min": 0.5,  # 0,5‰
                "max": 1.0,  # 1‰
                "change_threshold": 0.05,  # 5% vs PW
                "change_type": "percentage"
            }
        }
    
    def get_system_prompt(self) -> str:
        return """Eres un/a especialista en la revisión del panel de "Disruptions" para aerolíneas. Tu tarea es coordinar el análisis de diferentes aspectos del dashboard de disruptions, utilizando agentes especializados para cada componente."""
    
    def analyze_image(self, image_paths: Dict[str, str]) -> Dict[str, Any]:
        """Analyze disruptions dashboard images using specialized agents."""
        # Obtener las imágenes para cada tipo de análisis
        kpi_missconexions = image_paths.get("panel_kpis_missconexions")
        kpi_misshandling = image_paths.get("panel_kpis_misshandling")
        
        # Imágenes de tendencias (inbound/outbound)
        trend_images = {
            "inbound_cancelled_evolution": image_paths.get("inbound_cancelled_evolution"),
            "outbound_cancelled_evolution": image_paths.get("outbound_cancelled_evolution")
        }
        
        # Imágenes de mapas (inbound/outbound)
        map_images = {
            "inbound_cancelled_byregion": image_paths.get("inbound_cancelled_byregion"),
            "outbound_cancelled_byregion": image_paths.get("outbound_cancelled_byregion")
        }
        
        # Registrar qué imágenes están disponibles
        print("\n📊 Disruptions Images Status:")
        print(f"KPI Missconexions: {'✅ Found' if kpi_missconexions else '❌ Missing'}")
        print(f"KPI Misshandling: {'✅ Found' if kpi_misshandling else '❌ Missing'}")
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
            "kpi_data": {
                "missconexions": {},
                "misshandling": {}
            },
            "trend_data": {},
            "map_data": {}
        }
        
        # Implementar paralelización para análisis de KPIs, Trends y Maps
        from concurrent.futures import ThreadPoolExecutor
        import time
        
        # Función para ejecutar análisis de KPIs
        def analyze_kpis():
            kpi_results = {
                "missconexions": None,
                "misshandling": None
            }
            
            if kpi_missconexions:
                start_time = time.time()
                print(f"Analyzing KPI Missconexions: {os.path.basename(kpi_missconexions)}")
                missconexions_analysis = self.kpi_analyzer.analyze_image(kpi_missconexions)
                elapsed_time = time.time() - start_time
                print(f"✅ KPI Missconexions analysis completed in {elapsed_time:.2f} seconds")
                if missconexions_analysis is not None and "error" not in missconexions_analysis:
                    kpi_results["missconexions"] = missconexions_analysis
            
            if kpi_misshandling:
                start_time = time.time()
                print(f"Analyzing KPI Misshandling: {os.path.basename(kpi_misshandling)}")
                misshandling_analysis = self.kpi_analyzer.analyze_image(kpi_misshandling)
                elapsed_time = time.time() - start_time
                print(f"✅ KPI Misshandling analysis completed in {elapsed_time:.2f} seconds")
                if misshandling_analysis is not None and "error" not in misshandling_analysis:
                    kpi_results["misshandling"] = misshandling_analysis
                    
            return kpi_results
            
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
                kpi_results = kpi_future.result()
                raw_data["kpi_data"] = kpi_results
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
            "kpi_thresholds": self.kpi_thresholds
        }
        
        # --- REMOVE DEBUG DISRUPTIONS TREND INPUT --- 
        # print(f"\n--- DEBUG (DisruptionsAgent): Trend data received --- ")
        # print(json.dumps(raw_data.get("trend_data", {}), indent=2, ensure_ascii=False))
        # print("--- END DEBUG (DisruptionsAgent Trend Input) --- \n")
        # --- END REMOVE --- 

        # --- REMOVE DEBUG DISRUPTIONS MAP INPUT --- 
        # print(f"\n--- DEBUG (DisruptionsAgent): Map data received --- ")
        # print(json.dumps(raw_data.get("map_data", {}), indent=2, ensure_ascii=False))
        # print("--- END DEBUG (DisruptionsAgent) --- \n")
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
        
        # Get the system prompt
        system_prompt = """Eres un/a especialista en la revisión y análisis del panel de "Disruptions" para aerolíneas. 
Tu tarea es analizar los datos proporcionados, verificar si los valores exceden los umbrales definidos, y generar un análisis 
estructurado en formato JSON siguiendo exactamente el esquema proporcionado.

Identifica los KPIs que están fuera de rango o que tienen cambios significativos comparados con valores previos.
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

                # --- REMOVE DEBUG DISRUPTIONS TREND OUTPUT --- 
                # print(f"\n--- DEBUG (DisruptionsAgent): Trend analysis in LLM result --- ")
                # print(json.dumps(llm_result.get("trend_analysis", {}), indent=2, ensure_ascii=False))
                # print("--- END DEBUG (DisruptionsAgent Trend Output) ---\n")
                # --- END REMOVE --- 
                
                # --- REMOVE DEBUG DISRUPTIONS MAP OUTPUT --- 
                # print(f"\n--- DEBUG (DisruptionsAgent): Map analysis in LLM result --- ")
                # print(json.dumps(llm_result.get("map_analysis", {}), indent=2, ensure_ascii=False))
                # print("--- END DEBUG (DisruptionsAgent) ---\n")
                # --- END REMOVE --- 

                # --- START RECONSTRUCTION --- 
                final_result = {
                    "trend_analysis": llm_result.get("trend_analysis", {}),
                    "map_analysis": llm_result.get("map_analysis", {}),
                    "overall_analysis": llm_result.get("overall_analysis", "")
                }
                reconstructed_kpi_analysis = {}
                original_kpi_analysis = llm_result.get("kpi_analysis", {})

                kpi_definitions = {
                    "cancelled_vs_cancelled_prev_week": ("cancelled_value", "prev_week_cancelled_value", ["cancelled_prev_week"]),
                    "delayed_arr_c15_vs_delayed_arr_c15_prev_week": ("delayed_arr_c15_value", "prev_week_delayed_arr_c15_value", ["delayed_arr_c15_prev_week"]),
                    "misconnections_percentage_vs_misconnections_percentage_prev_week": ("misconnections_percentage_value", "prev_week_misconnections_percentage_value", ["misconnections_percentage_prev_week"]),
                    "misshandling_permille_vs_misshandling_permille_prev_week": ("misshandling_permille_value", "prev_week_misshandling_permille_value", ["misshandling_permille_prev_week"])
                }
                
                processed_original_keys = set()

                # Process defined comparison KPIs first
                for target_key, (val_key, prev_val_key, alt_keys) in kpi_definitions.items():
                    found_data = None
                    if target_key in original_kpi_analysis:
                        found_data = original_kpi_analysis.get(target_key)
                        processed_original_keys.add(target_key)
                    else:
                        for alt_key in alt_keys:
                            if alt_key in original_kpi_analysis:
                                found_data = original_kpi_analysis.get(alt_key)
                                processed_original_keys.add(alt_key)
                                break
                    
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
                        new_data = {k: v for k, v in new_data.items() if v is not None}
                    elif found_data is not None: 
                         new_data = found_data
                         
                    reconstructed_kpi_analysis[target_key] = new_data

                # Add remaining simple KPIs
                for original_key, kpi_data in original_kpi_analysis.items():
                    if original_key not in processed_original_keys and original_key not in [alt for _, _, alt_list in kpi_definitions.values() for alt in alt_list]:
                         if isinstance(kpi_data, dict):
                             reconstructed_kpi_analysis[original_key] = {
                                 "value": kpi_data.get("value"),
                                 "analysis": kpi_data.get("analysis", "")
                             }
                             reconstructed_kpi_analysis[original_key] = {k:v for k,v in reconstructed_kpi_analysis[original_key].items() if v is not None}
                         else: 
                             reconstructed_kpi_analysis[original_key] = {"value": kpi_data, "analysis": ""}
                         
                final_result["kpi_analysis"] = reconstructed_kpi_analysis
                # --- END RECONSTRUCTION --- 
                                
                # --- REMOVE DEBUG DISRUPTIONS FINAL OUTPUT --- 
                # print(f"\n--- DEBUG (DisruptionsAgent): Final combined analysis output --- ")
                # print(json.dumps(final_result, indent=2, ensure_ascii=False))
                # print("--- END DEBUG (DisruptionsAgent Final Output) ---\n")
                # --- END REMOVE --- 
                
                return final_result
            
            except json.JSONDecodeError:
                # Ensure json is available for error handling if needed (though less likely now)
                import json
                print("Error: Could not parse JSON from model response.")
                print(f"Response: {response}")
                return self._create_empty_structure()
            except Exception as parse_err: # Catch other potential parsing/reconstruction errors
                 import json # Ensure json is available
                 print(f"Error during disruptions analysis post-processing: {parse_err}")
                 # Ensure this return is aligned with the except block
                 return self._create_empty_structure()
                
        except Exception as e:
            # Ensure json is available for error handling
            import json
            print(f"Error calling model in DisruptionsAgent: {e}")
            return self._create_empty_structure()
    
    def _create_analysis_prompt(self, raw_data: Dict[str, Any], thresholds: Dict[str, Any]) -> str:
        """Create a prompt for the model to generate a structured analysis."""
        prompt = """Analiza los siguientes datos del dashboard de Disruptions y proporciona un análisis estructurado.

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
        2. **Tendencias:** Describe patrones clave y **OBLIGATORIAMENTE incluye los valores `cancelaciones_maximas` y `cancelaciones_minimas`** para cada segmento (in/out) si los datos de entrada (`trend_data`) los contienen.
        3. **Mapas:** Describe patrones clave y **OBLIGATORIAMENTE incluye `region_max_cancelaciones`, `valor_maximo`, `region_min_cancelaciones`, `valor_minimo`** para cada segmento (in/out) si los datos de entrada (`map_data`) los contienen.
        4. **Overall:** Resume hallazgos clave, incluyendo los **máximos y mínimos de cancelaciones MÁS SIGNIFICATIVOS** de tendencias y mapas.
        5. Genera un análisis estructurado siguiendo **ESTRICTAMENTE** el formato JSON de salida especificado.

        **Formato JSON de Salida Requerido (¡SEGUIR ESTRICTAMENTE! INCLUIR *TODOS* LOS CAMPOS):**
        ```json
        {{
          "kpi_analysis": {{
            "cancelled": {{ "value": number, "analysis": "string" }},
            "cancelled_vs_cancelled_prev_week": {{ "cancelled_value": number, "prev_week_cancelled_value": number, "difference": number, "percentage_change": number | null, "is_relevant": boolean, "analysis": "string" }},
            "cancelled_operative": {{ "value": number, "analysis": "string" }},
            "cancelled_commercial": {{ "value": number, "analysis": "string" }},
            "delayed_arr_c15": {{ "value": number, "analysis": "string" }},
            "delayed_arr_c15_vs_delayed_arr_c15_prev_week": {{ "delayed_arr_c15_value": number, "prev_week_delayed_arr_c15_value": number, "difference": number, "percentage_change": number | null, "is_relevant": boolean, "analysis": "string" }},
            "misconnections_percentage": {{ "value": number, "analysis": "string" }},
            "misconnections_percentage_vs_misconnections_percentage_prev_week": {{ "misconnections_percentage_value": number, "prev_week_misconnections_percentage_value": number, "difference": number, "percentage_change": number | null, "is_relevant": boolean, "analysis": "string" }},
            "misshandling_permille": {{ "value": number, "analysis": "string" }},
            "misshandling_permille_vs_misshandling_permille_prev_week": {{ "misshandling_permille_value": number, "prev_week_misshandling_permille_value": number, "difference": number, "percentage_change": number | null, "is_relevant": boolean, "analysis": "string" }},
            "dnb": {{ "value": number, "analysis": "string" }},
            "dng": {{ "value": number, "analysis": "string" }}
          }},
          "trend_analysis": {{
            "inbound": {{
              "cancelled_evolution": {{ "overall_analysis": "string", "cancelaciones_maximas": number | null, "cancelaciones_minimas": number | null }}
            }},
            "outbound": {{
              "cancelled_evolution": {{ "overall_analysis": "string", "cancelaciones_maximas": number | null, "cancelaciones_minimas": number | null }}
            }}
          }},
          "map_analysis": {{
            "inbound": {{ "analysis": "string", "region_max_cancelaciones": string | null, "valor_maximo": number | null, "region_min_cancelaciones": string | null, "valor_minimo": number | null }},
            "outbound": {{ "analysis": "string", "region_max_cancelaciones": string | null, "valor_maximo": number | null, "region_min_cancelaciones": string | null, "valor_minimo": number | null }}
          }},
          "overall_analysis": "string (incluyendo resumen de max/min cancelaciones)"
        }}
        ```

        **Reglas CRÍTICAS:**
        - **INCLUYE TODOS LOS CAMPOS** del formato JSON, especialmente los de max/min cancelaciones y regiones donde se especifica. Si los datos de entrada no los proporcionan, usa `null` como valor, pero la clave DEBE estar presente.
        - Menciona KPIs solo si son relevantes.
        - Usa diferencia absoluta, no porcentual, para KPIs comparativos.
        - Enfócate solo en IB para cancelaciones.
        - No inventes datos.
        - **RESPONDE ÚNICAMENTE CON EL JSON.**
"""
        return prompt

    def _create_empty_structure(self) -> Dict[str, Any]:
        """Create an empty structure following the expected format."""
        return {
            "kpi_analysis": {
                "cancelled": {},
                "cancelled_vs_cancelled_prev_week": {},
                "cancelled_operative": {},
                "cancelled_commercial": {},
                "delayed_arr_c15": {},
                "delayed_arr_c15_vs_delayed_arr_c15_prev_week": {},
                "misconnections_percentage": {},
                "misconnections_percentage_vs_misconnections_percentage_prev_week": {},
                "misshandling_permille": {},
                "misshandling_permille_vs_misshandling_permille_prev_week": {},
                "dnb": {},
                "dng": {}
            },
            "trend_analysis": {
                "inbound": {
                    "cancelled_evolution": {}
                },
                "outbound": {
                    "cancelled_evolution": {}
                }
            },
            "map_analysis": {
                "inbound": {},
                "outbound": {}
            },
            "overall_analysis": "No se pudo generar un análisis debido a un error."
        }