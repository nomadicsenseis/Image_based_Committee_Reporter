from .base_agent import BaseAgent
from .kpi_analyzer_agent import KPIAnalyzerAgent
from .trendline_analyzer_agent import TrendlineAnalyzerAgent
from .map_analyzer_agent import MapAnalyzerAgent
from typing import Dict, Any, List, Union
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
import time
import re
import copy

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.image_utils import encode_image

class CommercialAgent(BaseAgent):
    """Agente especializado en el análisis de dashboards de 'Commercial' para aerolíneas."""
    
    def __init__(self):
        super().__init__()
        self.kpi_analyzer = KPIAnalyzerAgent()
        self.trendline_analyzer = TrendlineAnalyzerAgent()
        self.map_analyzer = MapAnalyzerAgent()
        
        # Definir los umbrales para los KPIs
        self.kpi_thresholds = {
            "intakes": {
                "min": 100000,    # Mínimo del rango
                "max": 140000,    # Máximo del rango
                "change_threshold": 10000000,  # 10M vs target
                "change_type": "absolute"
            },
            "yield": {
                "min": 200,    # Mínimo del rango
                "max": 300,    # Máximo del rango
                "change_threshold": 0.05,  # 5% vs PW
                "change_type": "percentage"
            },
            "passengers": {
                "min": 400000,    # Mínimo del rango
                "max": 650000,    # Máximo del rango
                "change_threshold": 0.10,  # 10% vs PW
                "change_type": "percentage"
            }
        }
    
    def get_system_prompt(self) -> str:
        return """Eres un/a especialista en la revisión del panel de "Commercial" para aerolíneas. Tu tarea es coordinar el análisis de diferentes aspectos del dashboard de commercial, utilizando agentes especializados para cada componente.

FUNDAMENTAL: NO inventes NINGÚN dato, fecha o cifra. Trabaja exclusivamente con la información proporcionada en los datos extraídos. Si algún dato no está disponible, indícalo claramente pero NUNCA lo sustituyas con valores inventados."""
    
    def analyze_image(self, image_paths: Union[str, List[str], Dict[str, Any]], system_prompt: Dict[str, Any] = None) -> Dict[str, Any]:
        """Analyze commercial dashboard images using specialized agents."""
        print("Analyzing commercial images...")
        
        # Handle different input types
        if isinstance(image_paths, str):
            image_paths = [image_paths]
        elif isinstance(image_paths, dict):
            # If we receive a nested structure, use it directly
            if "panel_kpis" in image_paths and "trends" in image_paths and "maps" in image_paths:
                kpi_images = image_paths["panel_kpis"]
                trend_images = image_paths["trends"]
                map_images = image_paths["maps"]
            else:
                # Extract images using direct dictionary lookup
                kpi_images = {
                    'last_reported': image_paths.get('panel_kpis_commercial_last_reported'),
                    'last_week': image_paths.get('panel_kpis_commercial_last_week')
                }
                
                trend_images = {
                    'last_reported': {
                        'weekly': image_paths.get('evolution_intakes_weekly_by_flight_month_last_reported'),
                        'sales_date_region': image_paths.get('evolution_intakes_by_salesdateregion_last_reported'),
                        'sales_date_haul': image_paths.get('evolution_intakes_by_salesdatehaul_last_reported')
                    },
                    'last_week': {
                        'weekly': image_paths.get('evolution_intakes_weekly_by_flight_month_last_week'),
                        'sales_date_region': image_paths.get('evolution_intakes_by_salesdateregion_last_week'),
                        'sales_date_haul': image_paths.get('evolution_intakes_by_salesdatehaul_last_week')
                    }
                }
                
                map_images = {
                    'last_reported': image_paths.get('intakes_by_region_last_reported'),
                    'last_week': image_paths.get('intakes_by_region_last_week')
                }
        
        # Imprimir archivos encontrados y faltantes
        print("\n📊 Commercial Images Status:")
        print("KPI Images:")
        for period, img_path in kpi_images.items():
            status = "✅ Found" if img_path else "❌ Missing"
            print(f"  - panel_kpis_commercial_{period}: {status}")
            
        print("Trend Images:")
        for period, period_trends in trend_images.items():
            print(f"  {period}:")
            for trend_type, img_path in period_trends.items():
                img_name = f"evolution_intakes_{'weekly_by_flight_month' if trend_type == 'weekly' else f'by_{trend_type}'}"
                status = "✅ Found" if img_path else "❌ Missing"
                print(f"    - {img_name}_{period}: {status}")
                
        print("Map Images:")
        for period, img_path in map_images.items():
            status = "✅ Found" if img_path else "❌ Missing"
            print(f"  - intakes_by_region_{period}: {status}")
        
        # Procesar datos en paralelo - ejecutar el análisis de last_reported y last_week simultáneamente
        # Solo después de que ambos análisis estén completos, ejecutar la combinación/comparación
        
        # Preparar las imágenes para cada período
        last_reported_images = {
            "kpi_images": {k: v for k, v in kpi_images.items() if k == "last_reported"},
            "trend_images": {k: v for k, v in trend_images.items() if k == "last_reported"},
            "map_images": {k: v for k, v in map_images.items() if k == "last_reported"}
        }
        
        last_week_images = {
            "kpi_images": {k: v for k, v in kpi_images.items() if k == "last_week"},
            "trend_images": {k: v for k, v in trend_images.items() if k == "last_week"},
            "map_images": {k: v for k, v in map_images.items() if k == "last_week"}
        }
        
        # Ejecutar análisis en paralelo para ambos períodos
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Iniciar ambos análisis en paralelo
            future_last_reported = executor.submit(self._analyze_period, "last_reported", last_reported_images)
            future_last_week = executor.submit(self._analyze_period, "last_week", last_week_images)
            
            # Esperar a que ambos análisis completen
            print("Waiting for both period analyses to complete...")
            last_reported_analysis = future_last_reported.result()
            last_week_analysis = future_last_week.result()
        
        # Una vez que ambos análisis están completos, combinarlos y generar la comparación
        print("Both analyses complete. Combining results...")
        combined_analysis = self._combine_period_analyses(last_reported_analysis, last_week_analysis)
        
        return combined_analysis
    
    def _analyze_period(self, period: str, period_images: Dict[str, Any]) -> Dict[str, Any]:
        """Analiza un único período (last_reported o last_week)"""
        print(f"Processing {period} period...")
        
        # Extract images for this period
        kpi_images = period_images.get("kpi_images", {})
        trend_images = period_images.get("trend_images", {})
        map_images = period_images.get("map_images", {})
        
        # Print debug info
        print(f"KPI images for {period}: {list(kpi_images.keys())}")
        
        # Verificar si hay imágenes faltantes y registrarlas
        missing_files = []
        if not any(kpi_images.values()):
            missing_files.append(f"panel_kpis_commercial_{period}.png")
        
        for trend_type, trend_path in trend_images.get(period, {}).items():
            if not trend_path:
                if trend_type == 'weekly':
                    missing_files.append(f"evolution_intakes_weekly_by_flight_month_{period}.png")
                elif trend_type == 'sales_date_region':
                    missing_files.append(f"evolution_intakes_by_salesdateregion_{period}.png")
                elif trend_type == 'sales_date_haul':
                    missing_files.append(f"evolution_intakes_by_salesdatehaul_{period}.png")
        
        if not any(map_images.values()):
            missing_files.append(f"intakes_by_region_{period}.png")
            
        # Si faltan demasiados archivos, devolver estructura con datos faltantes
        if len(missing_files) > 2:  # Si faltan más de 2 archivos importantes
            print(f"⚠️ Too many missing files for {period} period: {', '.join(missing_files)}")
            result = self._create_empty_period_structure(period)
            result["missing_data"] = f"Faltan archivos importantes para el análisis de {period}: {', '.join(missing_files)}"
            return result
        
        # Collect raw outputs from specialized agents
        raw_data = {
            "kpi_data": {},
            "trend_data": {},
            "map_data": {}
        }
        
        # Paralelizar análisis de KPIs, Trends y Maps dentro de un período
        with ThreadPoolExecutor(max_workers=3) as executor:
            # Función para ejecutar análisis de KPIs
            def analyze_kpis():
                kpi_results = {}
                for p, img_path in kpi_images.items():
                    if img_path:
                        print(f"Analyzing KPI image for {p}: {os.path.basename(img_path)}")
                        import time
                        start_time = time.time()
                        kpi_analysis = self.kpi_analyzer.analyze_image(img_path)
                        elapsed_time = time.time() - start_time
                        print(f"✅ KPI analysis for {p} completed in {elapsed_time:.2f} seconds")
                        print(f"KPI Analysis result type: {type(kpi_analysis)}")
                        
                        # Convertir valores no serializables si es necesario
                        if kpi_analysis and isinstance(kpi_analysis, dict) and "kpis" in kpi_analysis:
                            kpis = kpi_analysis["kpis"]
                            serializable_kpis = {}
                            for kpi_key, kpi_value in kpis.items():
                                if hasattr(kpi_value, 'item'):  # numpy types tienen .item()
                                    serializable_kpis[kpi_key] = kpi_value.item()
                                else:
                                    serializable_kpis[kpi_key] = kpi_value
                            
                            # Crear una estructura directamente utilizable por el modelo
                            processed_kpis = {
                                "dashboard_name": kpi_analysis.get("dashboard_name", ""),
                                "raw_kpis": serializable_kpis,  # Mantener los KPIs originales
                                # Transformarlos al formato esperado para facilitar el trabajo del modelo
                                "kpis_formatted": {
                                    "intakes": {"value": serializable_kpis.get("intakes")},
                                    "intakes_prev_week": {
                                        "value": serializable_kpis.get("intakes"), 
                                        "previous_value": serializable_kpis.get("intakes_prev_week"),
                                        "difference": serializable_kpis.get("intakes") - serializable_kpis.get("intakes_prev_week") if serializable_kpis.get("intakes") is not None and serializable_kpis.get("intakes_prev_week") is not None else None,
                                        "percentage_change": (serializable_kpis.get("intakes") / serializable_kpis.get("intakes_prev_week") - 1) * 100 if serializable_kpis.get("intakes") is not None and serializable_kpis.get("intakes_prev_week") is not None and serializable_kpis.get("intakes_prev_week") != 0 else None
                                    },
                                    "weekly_target": {"value": serializable_kpis.get("weekly_target")},
                                    "official_target": {"value": serializable_kpis.get("official_target")},
                                    "yield": {"value": serializable_kpis.get("yield")},
                                    "yield_prev_week": {
                                        "value": serializable_kpis.get("yield"),
                                        "previous_value": serializable_kpis.get("yield_prev_week"),
                                        "difference": serializable_kpis.get("yield") - serializable_kpis.get("yield_prev_week") if serializable_kpis.get("yield") is not None and serializable_kpis.get("yield_prev_week") is not None else None,
                                        "percentage_change": (serializable_kpis.get("yield") / serializable_kpis.get("yield_prev_week") - 1) * 100 if serializable_kpis.get("yield") is not None and serializable_kpis.get("yield_prev_week") is not None and serializable_kpis.get("yield_prev_week") != 0 else None
                                    },
                                    "passengers": {"value": serializable_kpis.get("passengers")},
                                    "passengers_prev_week": {
                                        "value": serializable_kpis.get("passengers"),
                                        "previous_value": serializable_kpis.get("passengers_prev_week"),
                                        "difference": serializable_kpis.get("passengers") - serializable_kpis.get("passengers_prev_week") if serializable_kpis.get("passengers") is not None and serializable_kpis.get("passengers_prev_week") is not None else None,
                                        "percentage_change": (serializable_kpis.get("passengers") / serializable_kpis.get("passengers_prev_week") - 1) * 100 if serializable_kpis.get("passengers") is not None and serializable_kpis.get("passengers_prev_week") is not None and serializable_kpis.get("passengers_prev_week") != 0 else None
                                    }
                                }
                            }
                            
                            # Imprimir análisis serializable
                            print(f"KPI Analysis content processed: {str(processed_kpis)}")
                            
                            # Guardar tanto los KPIs originales como los procesados
                            kpi_results[p] = processed_kpis
                            print(f"Added KPI data for {p}")
                        else:
                            print("KPI Analysis is None, not a dict, or doesn't contain 'kpis'")
                            # Note: The logic for this 'if' block might need review as it's nested
                            # inside the 'else' of the previous 'if kpi_analysis...'
                            # It might belong outside the `if img_path:` block entirely.
                            if kpi_analysis is not None and "error" not in kpi_analysis:
                                kpi_results[p] = kpi_analysis
                                print(f"Added raw KPI data for {p}")
                            else:
                                print(f"⚠️ KPI analysis error or None for {p}")
                return kpi_results
                
            # Función para ejecutar análisis de Trends
            def analyze_trends():
                import json
                trend_results = {}
                # --- DEBUG COMMERCIAL TREND ANALYZER INPUT (Per Period) ---
                print(f"\n--- DEBUG (CommercialAgent-{period}): Trend images for trend_analyzer --- ")
                print(json.dumps(trend_images, indent=2, ensure_ascii=False))
                print("--- END DEBUG --- \n")
                # --- END DEBUG --- 
                for p, trend_dict in trend_images.items(): # p is last_reported or last_week
                    trend_results[p] = {}
                    if isinstance(trend_dict, dict):
                        for trend_type, img_path in trend_dict.items(): # trend_type is weekly, sales_date_region etc.
                            if img_path:
                                import time
                                start_time = time.time()
                                print(f"Analyzing trend image for {p}/{trend_type}: {os.path.basename(img_path)}")
                                trend_analysis = self.trendline_analyzer.analyze_image(img_path)
                                elapsed_time = time.time() - start_time
                                print(f"✅ Trend analysis for {p}/{trend_type} completed in {elapsed_time:.2f} seconds")
                                # --- DEBUG COMMERCIAL TREND ANALYZER OUTPUT (Per Period/Type) ---
                                print(f"\n--- DEBUG (CommercialAgent-{period}): Trend analysis RECEIVED from trend_analyzer for {p}/{trend_type} --- ")
                                print(json.dumps(trend_analysis, indent=2, ensure_ascii=False))
                                print("--- END DEBUG --- \n")
                                # --- END DEBUG --- 
                                
                                # Correctly indented if/else for trend_analysis result
                                if trend_analysis is not None and "error" not in trend_analysis:
                                    trend_results[p][trend_type] = trend_analysis
                                else:
                                    print(f"⚠️ Trend analysis error or None for {p}/{trend_type}")
                                    error_msg = trend_analysis.get("error", "Unknown") if isinstance(trend_analysis, dict) else "Formato inválido"
                                    trend_results[p][trend_type] = {"overall_analysis": f"Error o sin datos para tendencia {trend_type}", "error": error_msg}
                            else: # Corresponds to if img_path:
                                trend_results[p][trend_type] = {"overall_analysis": f"Imagen de tendencia faltante para {trend_type}"}
                    else: # Corresponds to if isinstance(trend_dict, dict):
                        print(f"⚠️ Trend images for period {p} is not a dict: {trend_dict}")
                        trend_results[p] = {"error": "Trend image data structure incorrect"}       
                return trend_results
                
            # Función para ejecutar análisis de Maps
            def analyze_maps():
                import json
                map_results = {}
                # --- DEBUG COMMERCIAL MAP ANALYZER INPUT (Per Period) ---
                print(f"\n--- DEBUG (CommercialAgent-{period}): Map images for map_analyzer --- ")
                print(json.dumps(map_images, indent=2, ensure_ascii=False))
                print("--- END DEBUG --- \n")
                # --- END DEBUG --- 
                for p, img_path in map_images.items():
                    if img_path:
                        # Infer direction from filename (assuming standard naming)
                        direccion_esperada = None 
                        if isinstance(img_path, str):
                             filename_lower = os.path.basename(img_path).lower()
                             if "inbound" in filename_lower:
                                 direccion_esperada = "inbound"
                             elif "outbound" in filename_lower:
                                 direccion_esperada = "outbound"
                             # Add more checks if filename structure varies
                             
                        import time
                        start_time = time.time()
                        print(f"Analyzing map image for {p}: {os.path.basename(img_path)}")
                        # Pass the inferred direction
                        map_analysis = self.map_analyzer.analyze_image(
                             image_path=img_path,
                             direccion_esperada=direccion_esperada
                        )
                        elapsed_time = time.time() - start_time
                        print(f"✅ Map analysis for {p} completed in {elapsed_time:.2f} seconds")
                        # --- DEBUG COMMERCIAL MAP ANALYZER OUTPUT (Per Period) ---
                        print(f"\n--- DEBUG (CommercialAgent-{period}): Map analysis RECEIVED from map_analyzer for {p} --- ")
                        print(json.dumps(map_analysis, indent=2, ensure_ascii=False))
                        print("--- END DEBUG --- \n")
                        # --- END DEBUG --- 
                        if map_analysis is not None and "error" not in map_analysis:
                            map_results[p] = map_analysis
                        else:
                             print(f"⚠️ Map analysis error or None for {p}")
                             map_results[p] = {"analysis": f"Error o sin datos para mapa {p}", "error": map_analysis.get("error", "Unknown") if isinstance(map_analysis, dict) else "Formato inválido"}
                    else:
                         map_results[p] = {"analysis": f"Imagen de mapa faltante para {p}"}
                return map_results
            
            # Iniciar todos los análisis en paralelo dentro del período
            kpi_future = executor.submit(analyze_kpis)
            trend_future = executor.submit(analyze_trends)
            map_future = executor.submit(analyze_maps)
            
            # Recoger resultados
            try:
                import json
                kpi_analysis_result = kpi_future.result()
                raw_data["kpi_data"] = kpi_analysis_result
            except Exception as e:
                 import json
                 print(f"❌ Error in KPI analysis for {period}: {str(e)}")
                 raw_data["kpi_data"] = {period: {"error": f"Error grave al recoger análisis de KPIs: {str(e)}"}}
            
            try:
                 import json
                 trend_data_result = trend_future.result()
                 # --- DEBUG COMMERCIAL TREND DATA BEFORE LLM (Per Period) ---
                 print(f"\n--- DEBUG (CommercialAgent-{period}): Trend data BEFORE sending to LLM --- ")
                 print(json.dumps(trend_data_result, indent=2, ensure_ascii=False))
                 print("--- END DEBUG --- \n")
                 # --- END DEBUG --- 
                 raw_data["trend_data"] = trend_data_result
            except Exception as e:
                 import json
                 print(f"❌ Error in Trend analysis for {period}: {str(e)}")
                 raw_data["trend_data"] = {period: {"error": f"Error grave al recoger análisis de tendencias: {str(e)}"}}
            
            try: # Collect map results
                import json
                map_data_result = map_future.result()
                # --- DEBUG COMMERCIAL MAP DATA BEFORE LLM (Per Period) ---
                print(f"\n--- DEBUG (CommercialAgent-{period}): Map data BEFORE sending to LLM --- ")
                print(json.dumps(map_data_result, indent=2, ensure_ascii=False))
                print("--- END DEBUG --- \n")
                # --- END DEBUG --- 
                raw_data["map_data"] = map_data_result
            except Exception as e:
                import json
                print(f"❌ Error in Map analysis for {period}: {str(e)}")
                # Create a serializable error structure
                error_detail = {"error": f"Error grave al recoger análisis de mapas: {str(e)}"}
                raw_data["map_data"] = {period: error_detail} # Use period as key matching expected structure
        
        # Print raw KPI data for debugging
        try:
            # Intenta imprimir string directamente sin json.dumps
            print(f"Raw KPI data after analysis: {str(raw_data['kpi_data'])}")
        except Exception as e:
            print(f"Error printing raw KPI data: {str(e)}")
        
        # Registrar archivos faltantes para el informe
        if missing_files:
            raw_data["missing_files"] = missing_files
            
        # Generate structured analysis for this period only
        thresholds_info = {
            "kpi_thresholds": self.kpi_thresholds
        }
        
        # Create period-specific prompt
        prompt = self._create_period_analysis_prompt(period, raw_data, thresholds_info)
        
        # Create a messages array for the model
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ]
        
        # Get the system prompt
        system_prompt = f"""Eres un/a especialista en el análisis de dashboards comerciales para aerolíneas, enfocado específicamente en el período '{period}'. 
Tu tarea es analizar los datos proporcionados, verificar si los valores exceden los umbrales definidos, y generar un análisis 
estructurado en formato JSON siguiendo exactamente el esquema proporcionado.

FUNDAMENTAL: NO inventes NINGÚN dato, fecha o cifra. Trabaja exclusivamente con la información proporcionada en los datos extraídos.
Si algún dato no está disponible, indícalo claramente pero NUNCA lo sustituyas con valores inventados.

IMPORTANTE: Debes usar EXACTAMENTE los valores numéricos de KPIs proporcionados. NO omitas ningún KPI si tienes su valor.

Identifica los KPIs que están fuera de rango o que tienen cambios significativos comparados con valores previos.
Para cada valor relevante, proporciona un análisis claro y accionable sobre el rendimiento comercial.
Mantén estrictamente la estructura JSON proporcionada en el prompt."""

        # Initialize placeholders for LLM output parts
        llm_kpi_analysis = {}
        llm_trend_analysis = {}
        llm_map_analysis = {}
        llm_period_overall_analysis = ""

        try:
            # --- Call LLM to get textual analysis --- 
            response = self.invoke_model(messages, system_prompt)
            try:
                # --- Inner try for JSON processing ---
                import json
                import re 
                # Clean up the JSON text - remove markdown code blocks if present
                cleaned_response = response.strip()
                json_str = cleaned_response # Initialize json_str earlier
                if cleaned_response.startswith("```json"):
                    # Try to extract content between the first set of backticks
                    match = re.search(r"```json\s*([\s\S]*?)\s*```", cleaned_response, re.DOTALL)
                    if match:
                        json_str = match.group(1).strip()
                    else: # Fallback if markdown detected but not parsed
                         print(f"⚠️ Could not extract JSON from detected markdown block for {period}. Trying direct parse.")
                elif cleaned_response.startswith("```"):
                     match = re.search(r"```\s*([\s\S]*?)\s*```", cleaned_response, re.DOTALL)
                     if match:
                          json_str = match.group(1).strip()
                          # Remove potential language identifier line
                          if "\n" in json_str:
                               first_line, rest = json_str.split("\n", 1)
                               if not first_line.strip().startswith("{"):
                                    json_str = rest.strip()
                          print(f"⚠️ Extracted content from generic markdown block for {period}.")
                else:
                          print(f"⚠️ Could not extract JSON from generic markdown block for {period}. Trying direct parse.")
                
                # Parse the JSON
                llm_result = json.loads(json_str)
                
                if isinstance(llm_result, dict):
                    # Extract textual parts from LLM response
                    llm_kpi_analysis = llm_result.get("kpi_analysis", {}).get(period, {}) 
                    llm_trend_analysis = llm_result.get("trend_analysis", {}).get(period, {})
                    llm_map_analysis = llm_result.get("map_analysis", {}).get(period, {})
                    llm_period_overall_analysis = llm_result.get("period_overall_analysis", "")
                    print(f"✅ LLM analysis sections extracted for {period}.")
                else:
                    print(f"❌ LLM result is not a dictionary for {period}.")
                    llm_period_overall_analysis = f"Error: LLM response structure invalid for {period}."
                    # Force return here if structure is wrong, no point combining
                    return self._create_empty_period_structure(period)
                
            # Catch specific JSON parsing errors
            except json.JSONDecodeError as json_e:
                 import json 
                 print(f"❌ Error decoding JSON for {period}: {json_e}")
                 # Try to log the problematic string if json_str was defined
                 try: 
                      print(f"Raw response excerpt causing JSON error: {json_str[:500]}...")
                 except NameError:
                      print(f"Raw response excerpt causing JSON error: {response[:500]}...") # Fallback to raw response
                 llm_period_overall_analysis = f"Error processing LLM response for {period}: Invalid JSON."
                 return self._create_empty_period_structure(period) 
            
            # Catch other potential errors during parsing/extraction
            except Exception as parse_err: 
                 import json 
                 # Print specific error here
                 print(f"❌ Error during commercial analysis post-processing for {period}: {parse_err}")
                 llm_period_overall_analysis = f"Error processing LLM response for {period}: {parse_err}"
                 return self._create_empty_period_structure(period)
                
        # Outer except for invoke_model call failure
        except Exception as e:
            import json 
            print(f"Error calling model for {period}: {e}")
            return self._create_empty_period_structure(period)
    
        # --- Programmatic Extraction and Combination --- 
        final_period_result = self._create_empty_period_structure(period) # Start empty

        # 1. Keep KPI analysis from LLM
        final_period_result["kpi_analysis"][period] = llm_kpi_analysis

        # 2. Process Trend Data (Intakes)
        raw_period_trend_data = raw_data.get("trend_data", {}).get(period, {})
        final_trend_analysis_period = {}
        for trend_key in raw_period_trend_data: # e.g., evolution_intakes_weekly...
            raw_trend = raw_period_trend_data.get(trend_key, {})
            llm_trend = llm_trend_analysis.get(trend_key, {})
            
            # Initialize max/min
            intake_max = None
            intake_min = None
            
            # Attempt to calculate max/min programmatically from raw table data
            try:
                if isinstance(raw_trend, dict) and 'trends' in raw_trend and isinstance(raw_trend['trends'], dict):
                     trends_table = raw_trend['trends'].get('tabla', [])
                     all_values = []
                     for entry in trends_table:
                          # Look for 'IB' in the airline haul key and extract values
                          if isinstance(entry, dict) and 'airline_haul' in entry and 'IB' in entry['airline_haul'].upper() and 'values' in entry:
                               values = [v for v in entry['values'] if isinstance(v, (int, float))] # Filter non-numeric
                               if values:
                                    all_values.extend(values)
                     
                     if all_values:
                          intake_max = max(all_values)
                          intake_min = min(all_values)
            except Exception as calc_e:
                 print(f"⚠️ Error calculating trend max/min for {period}/{trend_key}: {calc_e}")

            final_trend_analysis_period[trend_key] = {
                # Use LLM text, fallback to raw text if LLM's is missing/empty
                "overall_analysis": llm_trend.get("overall_analysis") or raw_trend.get("overall_analysis", "Análisis no disponible"),
                "intake_maximo": intake_max, # Use calculated value
                "intake_minimo": intake_min  # Use calculated value
            }
            # Clean None values AFTER calculation attempt
            final_trend_analysis_period[trend_key] = {k: v for k, v in final_trend_analysis_period[trend_key].items() if v is not None}
            
        final_period_result["trend_analysis"][period] = final_trend_analysis_period

        # 3. Process Map Data (Intakes)
        raw_period_map_data = raw_data.get("map_data", {}).get(period, {})
        llm_map = llm_map_analysis # Already scoped to the period
        
        # Extract max/min programmatically, checking for different key names used by MapAnalyzer
        max_region = None
        max_valor = None
        min_region = None
        min_valor = None
        
        # Check structures like {"ib_max": {"value": V, "regions": [R1, R2]}}
        ib_max_data = raw_period_map_data.get("analysis", {}).get("ib_max") if isinstance(raw_period_map_data.get("analysis"), dict) else raw_period_map_data.get("ib_max")
        ib_min_data = raw_period_map_data.get("analysis", {}).get("ib_min") if isinstance(raw_period_map_data.get("analysis"), dict) else raw_period_map_data.get("ib_min")
        
        if isinstance(ib_max_data, dict):
            max_valor = ib_max_data.get("value")
            max_region = ", ".join(ib_max_data.get("regions", []))
        if isinstance(ib_min_data, dict):
            min_valor = ib_min_data.get("value")
            min_region = ", ".join(ib_min_data.get("regions", []))

        # Fallback checks for other possible key names (just in case)
        if max_valor is None and "valor_maximo" in raw_period_map_data:
             max_valor = raw_period_map_data.get("valor_maximo")
             max_region = raw_period_map_data.get("region_max_intakes") # Or region_maxima?
        if min_valor is None and "valor_minimo" in raw_period_map_data:
             min_valor = raw_period_map_data.get("valor_minimo")
             min_region = raw_period_map_data.get("region_min_intakes") # Or region_minima?
             
        final_period_result["map_analysis"][period] = {
            "analysis": llm_map.get("analysis") or raw_period_map_data.get("analysis", {}).get("patterns", "Análisis no disponible"), # Use LLM text or fallback 
            "region_max_intakes": max_region,
            "intake_maximo": max_valor,
            "region_min_intakes": min_region,
            "intake_minimo": min_valor
        }
        final_period_result["map_analysis"][period] = {k: v for k, v in final_period_result["map_analysis"][period].items() if v is not None}

        # 4. Keep Overall Period Analysis from LLM
        final_period_result["period_overall_analysis"] = llm_period_overall_analysis

        # --- DEBUG COMMERCIAL FINAL PERIOD OUTPUT --- 
        print(f"\n--- DEBUG (CommercialAgent-{period}): Final combined analysis output for period --- ")
        print(json.dumps(final_period_result, indent=2, ensure_ascii=False))
        print(f"--- END DEBUG (CommercialAgent-{period} Final Output) ---\n")
        # --- END DEBUG --- 

        return final_period_result

    def _create_period_analysis_prompt(self, period: str, raw_data: Dict[str, Any], thresholds: Dict[str, Any]) -> str:
        """Create a prompt for the model to generate a structured analysis for a specific period."""
        prompt_parts = []

        # Add KPI data
        prompt_parts.append("### Datos de KPIs")
        prompt_parts.append(json.dumps(raw_data["kpi_data"], indent=2))
        
        # Extract the actual KPI values for easier reference by the model
        kpi_values = {}
        if period in raw_data["kpi_data"] and "raw_kpis" in raw_data["kpi_data"][period]:
            kpi_values = raw_data["kpi_data"][period]["raw_kpis"]
            
            # Add a section with the specific KPI values to make them very explicit
            prompt_parts.append("\n\n### Valores exactos de KPIs para este período")
            prompt_parts.append(f"""
- intakes: {kpi_values.get('intakes')}
- intakes_prev_week: {kpi_values.get('intakes_prev_week')}
- weekly_target: {kpi_values.get('weekly_target')}
- official_target: {kpi_values.get('official_target')}
- yield: {kpi_values.get('yield')}
- yield_prev_week: {kpi_values.get('yield_prev_week')}
- passengers: {kpi_values.get('passengers')}
- passengers_prev_week: {kpi_values.get('passengers_prev_week')}
""")
        
        # Add Trend data
        prompt_parts.append("\n\n### Datos de Tendencias")
        prompt_parts.append(json.dumps(raw_data["trend_data"], indent=2))
        
        # Add Map data
        prompt_parts.append("\n\n### Datos de Mapas")
        prompt_parts.append(json.dumps(raw_data["map_data"], indent=2))
        
        # Add missing files information if available
        if "missing_files" in raw_data:
            prompt_parts.append("\n\n### Archivos Faltantes")
            prompt_parts.append(json.dumps(raw_data["missing_files"], indent=2))
            prompt_parts.append("\n\nIMPORTANTE: Ten en cuenta que faltan algunos archivos. En tu análisis, menciona explícitamente qué datos faltan.")
        
        # Add thresholds information
        prompt_parts.append("\n\n## Umbrales definidos para evaluar los datos:")
        prompt_parts.append(json.dumps(thresholds, indent=2))
        
        # Add Task and JSON Structure instructions with STRONG emphasis
        task_and_format = f"""

        **TAREA:**
        1. Evalúa todos los KPIs relevantes del período '{period}' contra umbrales.
        2. **Tendencias:** Describe patrones clave y **OBLIGATORIAMENTE incluye `intake_maximo` y `intake_minimo`** para cada gráfico si los datos de entrada (`trend_data`) los contienen.
        3. **Mapas:** Describe patrones clave y **OBLIGATORIAMENTE incluye `region_max_intakes`, `intake_maximo`, `region_min_intakes`, `intake_minimo`** si los datos de entrada (`map_data`) los contienen.
        4. **Overall:** Resume hallazgos clave del PERÍODO, incluyendo los **máximos y mínimos de intakes MÁS SIGNIFICATIVOS** de tendencias y mapas.
        5. Genera un análisis estructurado siguiendo **ESTRICTAMENTE** el formato JSON de salida especificado para ESTE PERÍODO '{period}'.

        **Formato JSON de Salida Requerido (¡SEGUIR ESTRICTAMENTE! INCLUIR *TODOS* LOS CAMPOS):**
        ```json
        {{{{
          "kpi_analysis": {{{{ "{period}": {{
            "intakes": {{ "value": number, "analysis": "string" }},
            "intakes_prev_week": {{ "value": number, "previous_value": number | null, "difference": number | null, "percentage_change": number | null, "is_relevant": boolean, "analysis": "string" }},
            "weekly_target": {{ "value": number, "analysis": "string" }},
            "weekly_target_prev_week": {{ "value": number | null, "previous_value": number | null, "difference": number | null, "percentage_change": number | null, "is_relevant": boolean, "analysis": "string" }},
            "official_target": {{ "value": number, "analysis": "string" }},
            "yield": {{ "value": number, "analysis": "string" }},
            "yield_prev_week": {{ "value": number | null, "previous_value": number | null, "difference": number | null, "percentage_change": number | null, "is_relevant": boolean, "analysis": "string" }},
            "passengers": {{ "value": number, "analysis": "string" }},
            "passengers_prev_week": {{ "value": number | null, "previous_value": number | null, "difference": number | null, "percentage_change": number | null, "is_relevant": boolean, "analysis": "string" }}
          }} }}}},
          "trend_analysis": {{{{
            "{period}": {{{{
              "evolution_intakes_weekly_by_flight_month": {{ "overall_analysis": "string", "intake_maximo": number | null, "intake_minimo": number | null }},
              "evolution_intakes_by_salesdateregion": {{ "overall_analysis": "string", "intake_maximo": number | null, "intake_minimo": number | null }},
              "evolution_intakes_by_salesdatehaul": {{ "overall_analysis": "string", "intake_maximo": number | null, "intake_minimo": number | null }}
            }}}}
          }}}},
          "map_analysis": {{{{
            "{period}": {{ "analysis": "string", "region_max_intakes": string | null, "intake_maximo": number | null, "region_min_intakes": string | null, "intake_minimo": number | null }}
          }}}},
          "period_overall_analysis": "string (resumen del período '{period}', incluyendo max/min intakes)"
        }}}}
        ```

        **Reglas CRÍTICAS:**
        - **DEBES INCLUIR TODOS LOS CAMPOS** del formato JSON especificado, especialmente `intake_maximo`, `intake_minimo`, `region_max_intakes`, `region_min_intakes`. Si los datos de entrada no los proporcionan para un gráfico o mapa, usa el valor `null`, pero la clave DEBE estar presente.
        - Usa los valores EXACTOS de KPIs proporcionados.
        - Menciona KPIs solo si son relevantes.
        - No inventes datos.
        - **RESPONDE ÚNICAMENTE CON EL JSON.**
        """
        prompt_parts.append(task_and_format)
        
        return "\n".join(prompt_parts)

    def _create_empty_period_structure(self, period: str) -> Dict[str, Any]:
        """Create an empty structure for a specific period following the expected format."""
        return {
            "kpi_analysis": {
                period: {
                    "intakes": {},
                    "intakes_prev_week": {},
                    "weekly_target": {},
                    "weekly_target_prev_week": {},
                    "official_target": {},
                    "yield": {},
                    "yield_prev_week": {},
                    "passengers": {},
                    "passengers_prev_week": {}
                }
            },
            "trend_analysis": {
                period: {
                    "evolution_intakes_weekly_by_flight_month": {},
                    "evolution_intakes_by_salesdateregion": {},
                    "evolution_intakes_by_salesdatehaul": {}
                }
            },
            "map_analysis": {
                period: {}
            },
            "period_overall_analysis": f"No se pudo generar un análisis para {period} debido a un error."
        }
    
    def _combine_period_analyses(self, last_reported_analysis: Dict[str, Any], last_week_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Combine analyses from different periods and generate comparison insights."""
        print("Generating comparison between last_reported and last_week...")
        
        # Extract KPI data first to ensure we have it for the combined structure
        last_reported_kpis = None
        last_week_kpis = None
        
        # Extraer datos de last_reported
        if "kpi_data" in last_reported_analysis and "last_reported" in last_reported_analysis["kpi_data"]:
            # Primero intentamos obtener directamente desde raw_kpis
            lr_data = last_reported_analysis["kpi_data"]["last_reported"]
            if "raw_kpis" in lr_data:
                last_reported_kpis = lr_data["raw_kpis"]
                print(f"✅ Last reported KPIs extraídos de raw_kpis: {last_reported_kpis}")
            # Si no hay raw_kpis, intentamos desde kpis_formatted
            elif "kpis_formatted" in lr_data:
                last_reported_kpis = {k: v.get("value") 
                                     for k, v in lr_data["kpis_formatted"].items() 
                                     if isinstance(v, dict) and "value" in v}
                print(f"✅ Last reported KPIs extraídos de kpis_formatted: {last_reported_kpis}")
        else:
            # Plan B: Intentar obtener de kpi_analysis en caso de que raw_data no esté disponible
            lr_kpi_analysis = last_reported_analysis.get("kpi_analysis", {}).get("last_reported", {})
            if lr_kpi_analysis:
                last_reported_kpis = {}
                for kpi_key, kpi_data in lr_kpi_analysis.items():
                    if isinstance(kpi_data, dict) and "value" in kpi_data:
                        last_reported_kpis[kpi_key] = kpi_data.get("value")
                print(f"⚠️ Last reported KPIs extraídos de kpi_analysis (fallback): {last_reported_kpis}")
                
        # Extraer datos de last_week
        if "kpi_data" in last_week_analysis and "last_week" in last_week_analysis["kpi_data"]:
            # Primero intentamos obtener directamente desde raw_kpis
            lw_data = last_week_analysis["kpi_data"]["last_week"]
            if "raw_kpis" in lw_data:
                last_week_kpis = lw_data["raw_kpis"]
                print(f"✅ Last week KPIs extraídos de raw_kpis: {last_week_kpis}")
            # Si no hay raw_kpis, intentamos desde kpis_formatted
            elif "kpis_formatted" in lw_data:
                last_week_kpis = {k: v.get("value") 
                                 for k, v in lw_data["kpis_formatted"].items() 
                                 if isinstance(v, dict) and "value" in v}
                print(f"✅ Last week KPIs extraídos de kpis_formatted: {last_week_kpis}")
        else:
            # Plan B: Intentar obtener de kpi_analysis en caso de que raw_data no esté disponible
            lw_kpi_analysis = last_week_analysis.get("kpi_analysis", {}).get("last_week", {})
            if lw_kpi_analysis:
                last_week_kpis = {}
                for kpi_key, kpi_data in lw_kpi_analysis.items():
                    if isinstance(kpi_data, dict) and "value" in kpi_data:
                        last_week_kpis[kpi_key] = kpi_data.get("value")
                print(f"⚠️ Last week KPIs extraídos de kpi_analysis (fallback): {last_week_kpis}")
        
        # Print the KPI data available for comparison
        print(f"KPI data for comparison - Last Reported: {str(last_reported_kpis)}")
        print(f"KPI data for comparison - Last Week: {str(last_week_kpis)}")
        
        # Create the combined structure including the raw KPI data
        combined_analysis = {
            "raw_kpi_data": {
                "last_reported": last_reported_kpis,
                "last_week": last_week_kpis
            },
            "kpi_analysis": {
                "last_reported": last_reported_analysis.get("kpi_analysis", {}).get("last_reported", {}),
                "last_week": last_week_analysis.get("kpi_analysis", {}).get("last_week", {}),
                "comparison": {}
            },
            "trend_analysis": {
                "last_reported": last_reported_analysis.get("trend_analysis", {}).get("last_reported", {}),
                "last_week": last_week_analysis.get("trend_analysis", {}).get("last_week", {}),
                "comparison": {"analysis": ""}
            },
            "map_analysis": {
                "last_reported": last_reported_analysis.get("map_analysis", {}).get("last_reported", {}),
                "last_week": last_week_analysis.get("map_analysis", {}).get("last_week", {}),
                "comparison": {"analysis": ""}
            }
        }
        
        # Check for missing data in either period
        missing_data_info = []
        if "missing_data" in last_reported_analysis:
            missing_data_info.append(last_reported_analysis["missing_data"])
        if "missing_data" in last_week_analysis:
            missing_data_info.append(last_week_analysis["missing_data"])
            
        if missing_data_info:
            combined_analysis["missing_data"] = " ".join(missing_data_info)
        
        # Extract insights from both periods
        last_reported_insights = last_reported_analysis.get("period_overall_analysis", "")
        last_week_insights = last_week_analysis.get("period_overall_analysis", "")
        
        # --- Extract Specific Trend data for the prompt ---
        specific_trend_data_lw_haul = last_week_analysis.get("trend_analysis", {}).get("last_week", {}).get("evolution_intakes_by_salesdatehaul_last_week", {})
        print(f"DEBUG (CombinePeriods): Specific trend data (haul lw) extracted: {specific_trend_data_lw_haul}")
        # --- End Extraction --- 
        
        # --- RESTORE CALCULATION OF comparison_data ---
        comparison_data = {}
        if last_reported_kpis and last_week_kpis:
            kpi_metrics = ["intakes", "weekly_target", "yield", "passengers"]
            for metric in kpi_metrics:
                lr_value = last_reported_kpis.get(metric)
                lw_value = last_week_kpis.get(metric)
                difference = None
                percentage_change = None
                is_relevant = False
                calculation_error = None
                if isinstance(lr_value, (int, float)) and isinstance(lw_value, (int, float)):
                    try:
                        difference = lr_value - lw_value
                        if lw_value != 0:
                            percentage_change = (difference / lw_value) * 100
                            is_relevant = abs(percentage_change) > 5 
                        else:
                            percentage_change = None
                            is_relevant = difference != 0
                    except Exception as e:
                        calculation_error = str(e)
                        print(f"Error calculating comparison for {metric}: {calculation_error}")
                else:
                    print(f"Skipping comparison for {metric} due to None/non-numeric: lr={lr_value}, lw={lw_value}")
                    comparison_data[metric] = {
                            "last_reported_value": lr_value,
                            "last_week_value": lw_value,
                            "difference": difference,
                            "percentage_change": percentage_change,
                    "is_relevant": is_relevant,
                    **({"calculation_error": calculation_error} if calculation_error else {})
                        }
            print(f"Pre-calculated comparison data: {str(comparison_data)}")
            # Add to combined_analysis (optional, but good practice)
            if "kpi_analysis" not in combined_analysis: combined_analysis["kpi_analysis"] = {}
            combined_analysis["kpi_analysis"]["pre_calculated_comparison"] = comparison_data
        else:
            print("⚠️ No se pudieron pre-calcular comparaciones debido a datos faltantes")
        # --- END RESTORE --- 
        
        import json
        
        # Generate comparison prompt (this prompt USES comparison_data)
        comparison_prompt = f"""
## ANÁLISIS COMPARATIVO DE DATOS COMERCIALES

### Periodo de Análisis: Last Reported vs Last Week

#### Análisis del Último Periodo Reportado (Last Reported):
{last_reported_insights}

#### Análisis de la Última Semana (Last Week):
{last_week_insights}

## Datos de KPIs para Comparación:

### Last Reported:
```json
{json.dumps(last_reported_kpis, indent=2) if last_reported_kpis else "No hay datos disponibles para este periodo"}
```

### Last Week:
```json
{json.dumps(last_week_kpis, indent=2) if last_week_kpis else "No hay datos disponibles para este periodo"}
```

### Comparación Pre-calculada (KPIs):
```json
{json.dumps(comparison_data, indent=2) if comparison_data else "No se pudieron calcular comparaciones debido a datos faltantes"}
```

### Datos Específicos de Tendencia (Haul - Last Week):
```json
{json.dumps(specific_trend_data_lw_haul, indent=2) if specific_trend_data_lw_haul else "No hay datos específicos de tendencia haul last_week disponibles."}
```

## INSTRUCCIONES:
IMPORTANTE: Debes analizar y comparar los datos de AMBOS periodos. 
Los KPIs y sus valores están disponibles directamente en este prompt.

VALORES CONCRETOS DE KPIs LAST_REPORTED:
{json.dumps(last_reported_kpis, indent=2) if last_reported_kpis else "No hay datos disponibles"}

VALORES CONCRETOS DE KPIs LAST_WEEK:
{json.dumps(last_week_kpis, indent=2) if last_week_kpis else "No hay datos disponibles"}

---
**Contexto Temporal y Prioridad de Análisis:**
-   **`last_reported`:** Refleja los datos más recientes presentados al comité (datos hasta miércoles para reunión del jueves). **Usa estos datos principalmente para evaluar el rendimiento actual frente a `target`** (`weekly_target`, `official_target`).
-   **`last_week`:** Son los 7 días previos.
-   **Evolución Semanal:** Para analizar la **evolución** o cambios entre las dos semanas (ej. en intakes, passengers, yield), utiliza la comparación entre `last_reported` y `last_week`, apoyándote en la sección `Comparación Pre-calculada`.
---

Tu tarea es analizar los datos de los KPIs y tendencias de los periodos "last_reported" y "last_week", e identificar:
1.  Diferencias significativas entre ambos periodos (usa `Comparación Pre-calculada`).
2.  **Tendencias:** Basa tu análisis comparativo de tendencias (`trend_comparison`) **principalmente en la evolución por haul de la última semana (`evolution_intake_by_salesdatehaul_last_week`)** cuyos datos específicos se proporcionan arriba. Compara esta evolución con la situación general.
3.  Anomalías específicas.
4.  El rendimiento actual (`last_reported`) frente a los targets.

ESTRUCTURA DE RESPUESTA REQUERIDA (formato JSON):
```json
{{
  "kpi_comparison": {{
    "intakes": {{ 
      "last_reported_value": {last_reported_kpis.get("intakes") if last_reported_kpis else "null"},
      "last_week_value": {last_week_kpis.get("intakes") if last_week_kpis else "null"},
      "difference": {comparison_data.get("intakes", {}).get("difference") if comparison_data and "intakes" in comparison_data else "null"},
      "percentage_change": {comparison_data.get("intakes", {}).get("percentage_change") if comparison_data and "intakes" in comparison_data else "null"},
      "is_relevant": {str(comparison_data.get("intakes", {}).get("is_relevant", False)).lower() if comparison_data and "intakes" in comparison_data else "false"},
      "analysis": "análisis de la diferencia" 
    }},
    "weekly_target": {{ 
      "last_reported_value": {last_reported_kpis.get("weekly_target") if last_reported_kpis else "null"},
      "last_week_value": {last_week_kpis.get("weekly_target") if last_week_kpis else "null"},
      "difference": {comparison_data.get("weekly_target", {}).get("difference") if comparison_data and "weekly_target" in comparison_data else "null"},
      "percentage_change": {comparison_data.get("weekly_target", {}).get("percentage_change") if comparison_data and "weekly_target" in comparison_data else "null"},
      "is_relevant": {str(comparison_data.get("weekly_target", {}).get("is_relevant", False)).lower() if comparison_data and "weekly_target" in comparison_data else "false"},
      "analysis": "análisis de la diferencia (comparación vs target)" 
    }},
    "yield": {{ 
      "last_reported_value": {last_reported_kpis.get("yield") if last_reported_kpis else "null"},
      "last_week_value": {last_week_kpis.get("yield") if last_week_kpis else "null"},
      "difference": {comparison_data.get("yield", {}).get("difference") if comparison_data and "yield" in comparison_data else "null"},
      "percentage_change": {comparison_data.get("yield", {}).get("percentage_change") if comparison_data and "yield" in comparison_data else "null"},
      "is_relevant": {str(comparison_data.get("yield", {}).get("is_relevant", False)).lower() if comparison_data and "yield" in comparison_data else "false"},
      "analysis": "análisis de la diferencia" 
    }},
    "passengers": {{ 
      "last_reported_value": {last_reported_kpis.get("passengers") if last_reported_kpis else "null"},
      "last_week_value": {last_week_kpis.get("passengers") if last_week_kpis else "null"},
      "difference": {comparison_data.get("passengers", {}).get("difference") if comparison_data and "passengers" in comparison_data else "null"},
      "percentage_change": {comparison_data.get("passengers", {}).get("percentage_change") if comparison_data and "passengers" in comparison_data else "null"},
      "is_relevant": {str(comparison_data.get("passengers", {}).get("is_relevant", False)).lower() if comparison_data and "passengers" in comparison_data else "false"},
      "analysis": "análisis de la diferencia" 
    }}
  }},
  "trend_comparison": {{ "analysis": "análisis comparativo de tendencias, **enfocado en la evolución por haul de last_week**" }},
  "map_comparison": {{ "analysis": "análisis comparativo de mapas" }},
  "overall_analysis": "análisis general de las comparaciones, incluyendo rendimiento vs target (basado en last_reported) y evolución semanal (enfocada en haul)"
}}
```

CRÍTICO: Debes utilizar EXACTAMENTE los valores numéricos de KPIs que ves arriba. NO inventes valores diferentes ni indiques que no hay datos si tienes los valores numéricos. 

ASEGÚRATE de que tu JSON sea válido. Utiliza los valores exactos que se muestran arriba para last_reported_value, last_week_value, difference, percentage_change, etc. 
NO omitas ningún periodo o valor con la excusa de falta de datos, ya que los datos están claramente proporcionados en este prompt.
"""
        
        # Create a messages array for the model
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": comparison_prompt
                    }
                ]
            }
        ]
        
        # --- RESTORE SYSTEM PROMPT DEFINITION --- 
        system_prompt = """Eres un/a especialista en la comparación y síntesis de análisis comerciales para aerolíneas. 
Tu tarea es identificar los cambios más relevantes entre los períodos 'last_reported' y 'last_week', detectar tendencias y proporcionar 
un análisis estructurado en formato JSON siguiendo exactamente el esquema proporcionado.

FUNDAMENTAL: NO inventes NINGÚN dato, fecha o cifra. Trabaja exclusivamente con la información proporcionada en los datos extraídos.
Si algún dato no está disponible, indícalo claramente pero NUNCA lo sustituyas con valores inventados.

IMPORTANTE: NO debes indicar que "no hay datos disponibles" o que "no es posible hacer comparación" cuando los datos sí están disponibles.
Si los datos de ambos períodos están presentes en el prompt, DEBES usarlos para la comparación.

CRÍTICO: Debes incluir TODOS los KPIs disponibles en tu análisis, con sus valores exactos. No crees o inventes datos, pero tampoco omites ningún dato que esté disponible.

Enfócate en los cambios que tengan mayor impacto comercial y que puedan requerir atención de los tomadores de decisiones.
Mantén estrictamente la estructura JSON proporcionada en el prompt."""
        # --- END RESTORE --- 

        # --- DEBUG PROMPT LENGTHS --- 
        print(f"\n--- DEBUG (CombinePeriods): Prompt Lengths Before Invoke --- ")
        print(f"System Prompt Length: {len(system_prompt)}")
        # Content is a list, get length of the text part
        comparison_prompt_len = len(messages[0]['content'][0]['text'])
        print(f"Comparison Prompt (User Message Text) Length: {comparison_prompt_len}")
        print("--- END DEBUG --- \n")
        # --- END DEBUG --- 
        
        # Call the model for comparison
        comparison_result = {}
        response = "" 
        try:
            response = self.invoke_model(messages, system_prompt)
            
            # --- Robust response handling --- 
            # Check if invoke_model returned an error string
            if isinstance(response, str) and response.startswith("ERROR_"):
                 print(f"❌ Error received directly from invoke_model during comparison: {response}")
                 # Populate with error message
                 combined_analysis["overall_analysis"] = f"Error en la comparación: {response}"
                 # Potentially add error flags to other sections as well
                 combined_analysis["kpi_comparison"] = {"error": response}
                 combined_analysis["trend_comparison"] = {"analysis": response}
                 combined_analysis["map_comparison"] = {"analysis": response}
                 return combined_analysis # Return early with error info
            
            # If not an error string, proceed with JSON parsing
            try:
                # Find JSON content in the response
                import re
                json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    json_str = response
                
                # Parse the JSON
                comparison_result = json.loads(json_str)
                
                # Add the comparison to the combined analysis
                if isinstance(comparison_result, dict):
                    if "kpi_comparison" in comparison_result:
                        combined_analysis["kpi_analysis"]["comparison"] = comparison_result["kpi_comparison"]
                    if "trend_comparison" in comparison_result:
                        combined_analysis["trend_analysis"]["comparison"] = comparison_result["trend_comparison"]
                    if "map_comparison" in comparison_result:
                        combined_analysis["map_analysis"]["comparison"] = comparison_result["map_comparison"]
                        combined_analysis["overall_analysis"] = comparison_result.get("overall_analysis", "Análisis comparativo no generado.")
                    print(f"✅ Combined analysis success. Structure: {list(combined_analysis.keys())}")
                else:
                    print(f"❌ Parsed comparison result is not a dictionary: {type(comparison_result)}")
                    combined_analysis["overall_analysis"] = "Error: Resultado de comparación con formato inesperado."
                
            except json.JSONDecodeError as e:
                print(f"Error: Could not parse JSON from model response for comparison: {e}")
                print(f"Response: {response}")
                combined_analysis["overall_analysis"] = "Error: No se pudo decodificar JSON de comparación."
                
        # Catch errors from the invoke_model call itself (e.g., network issues)
        except Exception as e:
            print(f"Error calling model for comparison: {e}")
            combined_analysis["overall_analysis"] = f"Error en llamada al modelo de comparación: {e}"
        
        # Always return the combined_analysis dictionary, possibly populated with errors
        return combined_analysis

    def _compare_periods(self, combined_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Compare KPIs between periods and generate analysis."""
        print("Generating KPI comparison analysis...")
        
        # Extract raw KPI data directly from our stored structure
        last_reported_kpis = combined_analysis.get("raw_kpi_data", {}).get("last_reported", {})
        last_week_kpis = combined_analysis.get("raw_kpi_data", {}).get("last_week", {})
        
        if not last_reported_kpis or not last_week_kpis:
            print("⚠️ Warning: Missing KPI data for comparison")
            combined_analysis["kpi_analysis"]["comparison"] = {
                "error": "Insufficient data to perform comparison"
            }
            return combined_analysis
            
        # Pre-calculate differences for key KPIs
        comparison_data = {}
        
        # Log what we're working with
        print(f"Comparing KPIs: {last_reported_kpis.keys()} with {last_week_kpis.keys()}")
        
        # Find common KPIs to compare
        common_kpis = set(last_reported_kpis.keys()) & set(last_week_kpis.keys())
        print(f"Common KPIs for comparison: {common_kpis}")
        
        for kpi in common_kpis:
            try:
                # Get values, ensuring they are numeric
                lr_value = float(last_reported_kpis[kpi]) if last_reported_kpis[kpi] is not None else None
                lw_value = float(last_week_kpis[kpi]) if last_week_kpis[kpi] is not None else None
                
                # Skip if either value is None
                if lr_value is None or lw_value is None:
                    comparison_data[kpi] = {
                        "last_reported": lr_value,
                        "last_week": lw_value,
                        "change": None,
                        "percent_change": None,
                        "analysis": "Incomplete data for comparison"
                    }
                    continue
                    
                # Calculate changes
                absolute_change = lr_value - lw_value
                percent_change = (absolute_change / lw_value * 100) if lw_value != 0 else None
                
                comparison_data[kpi] = {
                    "last_reported": lr_value,
                    "last_week": lw_value,
                    "change": absolute_change,
                    "percent_change": percent_change
                }
                
                # Simple pre-analysis based on percent change
                if percent_change is not None:
                    if percent_change > 5:
                        comparison_data[kpi]["preliminary_assessment"] = "Significant increase"
                    elif percent_change < -5:
                        comparison_data[kpi]["preliminary_assessment"] = "Significant decrease"
                    else:
                        comparison_data[kpi]["preliminary_assessment"] = "Relatively stable"
                
            except (ValueError, TypeError) as e:
                print(f"Error processing KPI {kpi}: {e}")
                comparison_data[kpi] = {
                    "error": f"Data processing error: {e}",
                    "last_reported": last_reported_kpis.get(kpi),
                    "last_week": last_week_kpis.get(kpi)
                }
                
        print(f"Pre-calculated comparison data: {comparison_data}")
        
        # Format system prompt with detailed instruction and context
        system_prompt = f"""You are Iberia's commercial performance analyzer. Your task is to compare KPI data between the last reported period and last week.

IMPORTANT: Use ONLY the KPI data provided. DO NOT invent data. Be precise in your analysis and focus on significant changes.

Compare these periods:
- Last reported: The most recent available data
- Last week: Data from one week earlier

Analyze the following metrics based on the provided comparison data:
{json.dumps(comparison_data, indent=2)}

Your analysis should:
1. Focus on the most significant changes (positive or negative)
2. Identify trends or patterns across related metrics
3. Provide business-relevant context for the changes
4. Use factual, quantitative language with exact figures

The response MUST be in Spanish and follow this JSON structure:
{{
  "kpi_name": {{
    "last_reported": value,
    "last_week": value,
    "change": value,
    "percent_change": value,
    "analysis": "Brief analysis of this specific KPI's performance"
  }},
  "overall_analysis": "A comprehensive analysis of all KPIs considered together"
}}

Do not include any text or explanation outside the JSON structure."""

        user_prompt = "Generate a detailed comparison analysis between last reported and last week periods."
        
        comparison_analysis = self._llm_client.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,
            json_mode=True
        )
        
        try:
            # Parse response and integrate into our structure
            parsed_comparison = json.loads(comparison_analysis)
            
            # Copy calculated values to ensure they're preserved
            for kpi in comparison_data:
                if kpi in parsed_comparison and kpi != "overall_analysis":
                    # Ensure we preserve our calculated values if they're missing in the response
                    for key in ["last_reported", "last_week", "change", "percent_change"]:
                        if key not in parsed_comparison[kpi] and key in comparison_data[kpi]:
                            parsed_comparison[kpi][key] = comparison_data[kpi][key]
            
            # Assign to the structure
            combined_analysis["kpi_analysis"]["comparison"] = parsed_comparison
            
            # Extract overall analysis if available
            if "overall_analysis" in parsed_comparison:
                overall = parsed_comparison.pop("overall_analysis")
                combined_analysis["kpi_analysis"]["comparison"]["overall_analysis"] = overall
        
        except json.JSONDecodeError as e:
            print(f"Error parsing comparison response: {e}")
            combined_analysis["kpi_analysis"]["comparison"] = {
                "error": "Failed to parse comparison analysis",
                "raw_data": comparison_analysis
            }
            
        return combined_analysis

    def generate_executive_summary(self, combined_analysis: Dict[str, Any]) -> str:
        """
        Generate an executive summary in Spanish based on the combined analysis.
        This provides a high-level overview for executives and decision-makers.
        """
        print("Generating executive summary...")
        
        # Extract relevant data from our combined analysis
        kpi_comparison = combined_analysis.get("kpi_analysis", {}).get("comparison", {})
        overall_analysis = combined_analysis.get("overall_analysis", "")
        trend_analysis = combined_analysis.get("trend_analysis", {})
        
        # Create context for the LLM with the key data points
        summary_context = {
            "kpi_data": {k: v for k, v in kpi_comparison.items() if k != "overall_analysis"},
            "overall_analysis": overall_analysis,
            "key_trends": trend_analysis
        }
        
        # Format system prompt
        system_prompt = f"""Eres el asistente ejecutivo para el departamento comercial de Iberia. 
Tu tarea es crear un resumen ejecutivo conciso en español basado en el análisis de KPIs comerciales.

DATOS DE ANÁLISIS:
{json.dumps(summary_context, indent=2, ensure_ascii=False)}

INSTRUCCIONES:
1. Crea un resumen ejecutivo de máximo 3-4 párrafos.
2. Enfócate en los cambios más significativos en los KPIs comerciales.
3. Destaca tendencias importantes y sus posibles implicaciones.
4. Usa un lenguaje claro, directo y profesional orientado a ejecutivos.
5. Incluye datos numéricos precisos (porcentajes, cambios) para respaldar los puntos clave.
6. No inventes datos ni saques conclusiones que no estén respaldadas por la información proporcionada.
7. El formato debe tener un título "RESUMEN EJECUTIVO: RENDIMIENTO COMERCIAL" seguido del contenido.

El resumen debe ser informativo pero conciso, proporcionando una visión general clara que permita a los ejecutivos entender rápidamente la situación comercial actual.
"""

        user_prompt = "Genera un resumen ejecutivo basado en el análisis de KPIs comerciales de Iberia."
        
        try:
            # Generate the summary
            executive_summary = self.invoke_model(
                [{"role": "user", "content": [{"type": "text", "text": user_prompt}]}],
                system_prompt
            )
            
            # Store the summary in our analysis structure
            combined_analysis["executive_summary"] = executive_summary
            
            return executive_summary
            
        except Exception as e:
            error_msg = f"Error generating executive summary: {str(e)}"
            print(f"❌ {error_msg}")
            combined_analysis["executive_summary"] = f"Error: {error_msg}"
            return error_msg
            
    def _analyze_kpi_data(self, last_reported_period_data: Dict[str, Any]):
        """
        Analyze KPI data from the parsed dashboard.
        
        Args:
            last_reported_period_data: Dictionary containing the latest KPI data
            
        Returns:
            Dict with analyzed KPI data
        """
        analyzed_data = {}
        
        try:
            # Process each KPI in the data
            for kpi_name, kpi_value in last_reported_period_data.items():
                if isinstance(kpi_value, (int, float)):
                    analyzed_data[kpi_name] = {
                        "value": kpi_value,
                        "unit": self._determine_kpi_unit(kpi_name),
                    }
            
            return analyzed_data
            
        except Exception as e:
            print(f"Error analyzing KPI data: {str(e)}")
            return {"error": str(e)}

    def _determine_kpi_unit(self, kpi_name: str) -> str:
        """
        Determine the appropriate unit for a KPI based on its name.
        
        Args:
            kpi_name: The name of the KPI
            
        Returns:
            String representing the unit for the KPI
        """
        kpi_name_lower = kpi_name.lower()
        
        if "percentaje" in kpi_name_lower or "porcentaje" in kpi_name_lower:
            return "%"
        elif "yield" in kpi_name_lower:
            return "€"
        elif "passengers" in kpi_name_lower or "pasajeros" in kpi_name_lower:
            return "pax"
        elif "intakes" in kpi_name_lower:
            return "bookings"
        elif "revenue" in kpi_name_lower or "ingresos" in kpi_name_lower:
            return "€"
        else:
            return ""
