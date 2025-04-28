from .base_agent import BaseAgent
from typing import Dict, Any, List, Optional
import json
import os
import boto3
from datetime import datetime
import sys
import logging
import re
from collections import defaultdict
from botocore.exceptions import ClientError
import copy # Import copy for deepcopy in original invoke_model if needed elsewhere

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

class SynthesisAgent(BaseAgent):
    """Agente especializado en sintetizar los análisis de los diferentes dashboards en un informe unificado."""
    
    def __init__(self):
        super().__init__()
        self.model_id = os.getenv('MODEL_ARN', 'arn:aws:bedrock:us-east-1:737192913161:inference-profile/us.anthropic.claude-3-7-sonnet-20250219-v1:0')
        # Ensure self.bedrock is initialized from BaseAgent
        # self.model = boto3.client('bedrock-runtime') # This is done in BaseAgent
        
        # Optimized System Prompt (Role, Goal, Audience, Key Context) - Used by helpers
        self.base_system_prompt = """Eres el Director de Datos de Iberia, responsable de sintetizar análisis complejos en informes semanales claros y accionables para el equipo ejecutivo.

        **Audiencia:** Equipo ejecutivo (CEO, directores). Necesitan información concisa pero suficiente para tomar decisiones.

        **Consideración Clave (NPS):** Siempre ten presente el decalaje implícito de 4 días de los datos NPS al interpretar posibles relaciones con otros indicadores operativos o comerciales.
        """
    
    def get_system_prompt(self) -> str:
        """Return the base system prompt for the synthesis agent."""
        return self.base_system_prompt
    
    def analyze_image(self, image_path: str) -> Dict[str, Any]:
        """Analyze an image and return insights."""
        # Returns a template structure matching the final output format
        return {
            "weekly_report": {
                "commercial": "Resumen comercial (2-3 frases)",
                "customer": "Resumen clientes (2-3 frases)",
                "operations": "Resumen operaciones (2-3 frases)",
                "disruptions": "Resumen disrupciones (2-3 frases)",
                "overall_interpretation": "Interpretación general basada en el análisis cruzado."
            }
        }

    # --- Helper Methods for Two-Step Synthesis --- 

    def _build_area_summaries_prompt(self, analyses_text: str) -> str:
        """Builds the prompt specifically for generating the 4 area summaries, using more explicit instructions based on the previous unified prompt."""
        prompt = f"""Tu tarea es generar resúmenes concisos (EXACTAMENTE 3 frases por área) para cada una de las 4 áreas (commercial, customer, operations, disruptions) basándote en los análisis detallados proporcionados. Cada resumen debe ser independiente y centrarse en su área.

        **ANÁLISIS DETALLADOS DE ENTRADA:**
        {analyses_text}

        **INSTRUCCIONES CRÍTICAS PARA GENERAR LOS RESÚMENES POR ÁREA:**

        **1. Lenguaje:**
           - Habla de \"target\" (no de objetivo), de \"load_factor\" (no de factor de carga), de \"inbound\" y \"outbound\" (no de entrada y salida), \"puntualidad en entradas/salidas\" (no de puntualidad C15) y de \"misshandling\" y \"missconnections\" (sin traducir).

        **2. Manejo de Datos y Fidelidad:**
           - **Comparaciones (`..._vs_..._prev_week`):** 
             - **Condición OBLIGATORIA:** Solo menciona estos KPIs comparativos si el campo `is_relevant` asociado en los datos de entrada es `true`. Si es `false`, NO lo incluyas en el resumen.
             - **Formato OBLIGATORIO (si es relevante):** Al mencionarlo, indica claramente el **valor actual** del KPI y la **diferencia absoluta** (`difference`) respecto a la semana anterior (puedes indicar si es positiva o negativa con un signo o palabras como 'aumento'/'disminución').
             - **Formato PROHIBIDO:** NO utilices ni menciones la diferencia porcentual (`percentage_change`).
             - *Ejemplo (si punctualidad_vs_prev_week es relevante y la diferencia fue -3):* "La puntualidad en salidas se situó en 87%, una diferencia de -3 puntos respecto a la semana previa." (NO decir: "cayó un 3.3%")
           - **Inbound/Outbound:** Siempre que hables de tendencias o mapas especifica si te refieres a `inbound` o `outbound`.
           - **Datos Faltantes:** Menciona brevemente si faltan datos específicos del área que estás resumiendo y si afectan el análisis de esa área.

        **3. Consideraciones Específicas por Área (Aplica a cada resumen individual):**
           - **Customer:** Céntrate en los valores y tendencias del NPS y datos geográficos si los hay. **Contexto Importante:** Es habitual y esperado que el NPS de Largo Radio (LH) sea generalmente más alto que el de Corto/Medio Radio (SH/MH). NO menciones el decalaje NPS aquí.
           - **Disruptions:** Solo ten en cuenta cancelaciones IB. Valora la relevancia operativa de las disrupciones (cancelaciones, retrasos, misshandling/missconnections) si procede.
           - **Commercial:** Solo compara intakes hasta 5 días antes. Para la evolución de intakes, fíjate solo en la información de `last_week`. Redondea la diferencia vs target. Combina vista general/evolución. Considera estacionalidad (y posible efecto vacacional en ratio business/leisure). Si el crecimiento es +10M vs target, menciona que es espectacular.
           - **Operations:** Habla de puntualidad en salidas/llegadas. Usa `load_factor`. Analiza la evolución por cabina, mencionando días con caídas o picos.

        **4. Qué Evitar en ESTOS Resúmenes Individuales:**
           - **Redundancia:** Evita repetir información dentro del resumen de una misma área.
           - **Obviedad:** No digas que KPIs malos necesitan seguimiento. No expliques la correlación básica Ops/Disruptions/NPS.
           - **Mención Explícita:** No menciones el decalaje NPS ni los umbrales de relevancia aquí.
           - **Análisis Cruzado:** NO conectes información entre diferentes áreas (Commercial, Customer, etc.) en estos resúmenes individuales. Céntrate solo en los datos del área que estás resumiendo.
           - **Interpretación General:** NO incluyas ninguna interpretación global o `overall_interpretation`.

        **5. Contenido y Estructura OBLIGATORIA por Área (3 frases):**
           - Genera **EXACTAMENTE 3 frases** para CADA área (Commercial, Customer, Operations, Disruptions).
           - **Frase 1: KPIs.** Resume el(los) KPI(s) más relevante(s) para esta área, siguiendo las reglas del punto 2 y 3.
           - **Frase 2: Tendencias.**
             - *Tarea:* Analiza los datos de tendencias proporcionados (`inbound` y `outbound`, si existen).
             - *Selección del Segmento:* Identifica cuál segmento (`inbound` o `outbound`) presenta el **valor mínimo más bajo** o la tendencia general más negativa/preocupante.
             - *Mención de Segmento(s):* Resume la tendencia clave del segmento seleccionado. Si los valores mínimos o las tendencias de ambos segmentos (`inbound` y `outbound`) son muy similares y relevantes, puedes mencionar brevemente ambos. **Siempre especifica** si hablas de `inbound` o `outbound`.
             - *Contenido:* Indica la tendencia observada (ej. decreciente, estable, creciente) y **OBLIGATORIAMENTE el valor numérico** relevante (ej. el valor mínimo alcanzado, el valor final).
             - *Ejemplo:* 'La puntualidad inbound mostró tendencia decreciente, alcanzando un mínimo de 85%, mientras que outbound se mantuvo estable sobre el 90%.' O solo: 'La tendencia de puntualidad inbound fue negativa, llegando al 85%.'
             - *Si NO hay datos de tendencias válidos/relevantes:* No menciones nada.
           - **Frase 3: Mapas.** Resume el patrón o hallazgo geográfico más significativo observado en los datos de mapas para esta área. **Si identificas una región con un valor extremo (máximo o mínimo), menciónala junto con su valor.** Si no hay datos de mapas relevantes, no menciones nada.

        **6. Formato de Salida JSON ESTRICTO:**
           - Tu respuesta debe ser **ÚNICAMENTE** un objeto JSON válido.
           - La estructura debe ser **EXACTA**: `{{\"commercial\": \"Frase KPIs. Frase Tendencias. Frase Mapas.\", \"customer\": \"Frase KPIs. Frase Tendencias. Frase Mapas.\", \"operations\": \"Frase KPIs. Frase Tendencias. Frase Mapas.\", \"disruptions\": \"Frase KPIs. Frase Tendencias. Frase Mapas.\"}}`
        """
        return prompt

    def _generate_area_summaries(self, analyses: List[Dict[str, Any]]) -> Dict[str, str]:
        """Generates the 4 area summaries using a dedicated LLM call."""
        print("\nGenerating area summaries...")
        system_prompt = self.get_system_prompt() # Use base system prompt
        analyses_text = "\n\n".join([
            f"""{analysis['type'].upper()} Analysis:\n{json.dumps(analysis.get('analysis', {}), indent=2)}"""
            for analysis in analyses
        ])
        
        message_prompt = self._build_area_summaries_prompt(analyses_text)
        messages = [{
            "role": "user",
            "content": [{"type": "text", "text": message_prompt}]
        }]

        try:
            # Use invoke_model from BaseAgent
            response = self.invoke_model(messages=messages, system_prompt=system_prompt)
            # --- REMOVE DEBUG RAW RESPONSE ---
            # print(f"DEBUG (Area Summaries): Raw LLM response: {response}")
            # --- END REMOVE --- 
            
            # Robust JSON cleaning/parsing
            cleaned_response = response.strip()
            if cleaned_response.startswith("```json"):
                 cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith("```"):
                 cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()
            
            try:
                 area_summaries = json.loads(cleaned_response)
                 if isinstance(area_summaries, dict) and all(k in area_summaries for k in ["commercial", "customer", "operations", "disruptions"]):
                     print("✅ Area summaries generated successfully.")
                     # --- REMOVE DEBUG AREA SUMMARIES OUTPUT ---
                     # print("\n--- DEBUG (SynthAgent): Area Summaries Generated --- ")
                     # print(json.dumps(area_summaries, indent=2, ensure_ascii=False))
                     # print("--- END DEBUG --- \n")
                     # --- END REMOVE --- 
                     return {k: str(v) for k, v in area_summaries.items()} 
                 else:
                     print(f"❌ Area summaries response structure invalid. Got: {area_summaries}")
                     # Fallback structure
                     return {"commercial": "Error: estructura inválida", "customer": "Error: estructura inválida", "operations": "Error: estructura inválida", "disruptions": "Error: estructura inválida"}
            except json.JSONDecodeError as e:
                 print(f"❌ Error decoding area summaries JSON: {e}")
                 print(f"Raw response excerpt: {cleaned_response[:500]}...")
                 return {"commercial": "Error: JSON inválido", "customer": "Error: JSON inválido", "operations": "Error: JSON inválido", "disruptions": "Error: JSON inválido"}

        except Exception as e:
            print(f"❌ Error generating area summaries: {e}")
            return {"commercial": "Error: llamada LLM", "customer": "Error: llamada LLM", "operations": "Error: llamada LLM", "disruptions": "Error: llamada LLM"}

    def _build_overall_interpretation_prompt(self, area_summaries: Dict[str, str], analyses_text: str) -> str:
        """Builds the prompt specifically for generating the overall interpretation."""
        area_summaries_text = json.dumps(area_summaries, indent=2, ensure_ascii=False)
        # Updated instructions for overall_interpretation generation
        prompt = f"""Tu tarea es generar un párrafo de interpretación general (3-5 frases) conectando los puntos clave de los resúmenes por área y los análisis detallados proporcionados.

        **RESÚMENES POR ÁREA GENERADOS (Paso 1):**
        ```json
        {area_summaries_text}
        ```

        **ANÁLISIS DETALLADOS ORIGINALES (Contexto Adicional):**
        {analyses_text}

        **INSTRUCCIONES DETALLADAS PARA GENERAR `overall_interpretation` (Párrafo de Análisis Global):**

        **OBJETIVO PRINCIPAL:** Crear un párrafo conciso (3-5 frases) que ofrezca una **visión global y estratégica** del rendimiento semanal, conectando los puntos clave de los 4 resúmenes de área (Commercial, Customer, Operations, Disruptions) y los datos detallados originales. Busca la **narrativa** que une los diferentes aspectos.

        **CONTENIDO Y ANÁLISIS REQUERIDO:**

        1.  **Conexiones entre Áreas:** Identifica y describe las relaciones más significativas o patrones que emergen al considerar las áreas en conjunto. ¿Cómo interactúan los resultados comerciales, operativos, de cliente y de disrupciones?
        2.  **Impacto NPS (Verificación Decalaje 4+ días OBLIGATORIA):**
            *   *Recordatorio:* El impacto en NPS de eventos Ops/Disruptions se refleja **4 o más días después** (encuesta día 4, respuesta puede ser posterior).
            *   *Acción:* **Verifica MENTALMENTE** si las conexiones que propones entre Ops/Disruptions y NPS respetan este decalaje de 4 o más días. "Piensa si tu razonamiento respeta el decalaje".
            *   *Reporte (SI CUMPLE DECALAJE):* Si encuentras una conexión temporalmente plausible (ej. mala Ops día X -> caída NPS día X+4 o posterior), **describe la conexión aportando DATOS específicos** (días, valores, regiones/cabinas si aplica para ambos eventos).
            *   *Reporte (DIVERGENCIA):* Si la correlación esperada falla notablemente (ej. mala Ops/Disruptions sin caída NPS posterior; o NPS bajo sin causa clara en Ops/Disruptions 4+ días antes), **comenta esta divergencia** como una situación inesperada o sorprendente (ver ejemplos abajo). Considera que no hay correlación clara esperada con Commercial.
        3.  **Consistencia Inbound/Outbound:** Al comparar datos entre áreas (especialmente tendencias/mapas de Operations y Customer), **ASEGÚRATE** de mantener la perspectiva (`inbound` con `inbound`, `outbound` con `outbound`). Verifica también la consistencia temporal considerando el decalaje NPS.
        4.  **Ejemplos para Comentarios de Divergencia:** 'Sorprendentemente, a pesar del deterioro en [Operativa/Disrupciones], el NPS se mantuvo estable.' o 'La caída del NPS no parece tener una correspondencia directa con eventos operativos o de disrupción significativos en los 4+ días previos.' Solo mencionar si corresponde.

        **REGLAS IMPORTANTES Y QUÉ EVITAR:**

        *   **Lenguaje:** Habla de \"target\" (no de objetivo), de \"load_factor\" (no de factor de carga), de \"inbound\" y \"outbound\" (no de entrada y salida), \"puntualidad en entradas/salidas\" (no de puntualidad C15) y de \"misshandling\" y \"missconnections\" (sin traducir).
        *   **NO Mencionar Decalaje Explícitamente:** La consideración del decalaje de 4+ días es interna, **NUNCA** lo menciones en el texto final.
        *   **NO Mencionar Umbrales Explícitamente:** No cites los valores numéricos de los umbrales de relevancia, ni menciones que existen. Solo tenlos en cuenta en añadir un comentario o no añadirlo.
        *   **NO Explicar Correlación Básica Ops/NPS:** Evita decir simplemente "la mala operativa afecta al NPS". Solo menciona la relación si aportas datos específicos que la sustenten (ver punto 2) o si comentas una divergencia (ver punto 4).
        *   **NO Ser Redundante:** No repitas información ya dada en los resúmenes por área.
        *   **NO Añadir Obviedades:** Evita comentarios como "hay que monitorizar este KPI".

        **FORMATO DE SALIDA:**

        *   Devuelve **SOLAMENTE** el texto del párrafo de interpretación general (3-5 frases). Sin claves JSON, sin formato Markdown extra.
        """
        return prompt

    def _generate_overall_interpretation(self, area_summaries: Dict[str, str], analyses: List[Dict[str, Any]]) -> str:
        """Generates the overall interpretation using a dedicated LLM call."""
        print("\nGenerating overall interpretation...")
        system_prompt = self.get_system_prompt() # Use base system prompt
        analyses_text = "\n\n".join([
            f"""{analysis['type'].upper()} Analysis:\n{json.dumps(analysis.get('analysis', {}), indent=2)}"""
            for analysis in analyses
        ])
        message_prompt = self._build_overall_interpretation_prompt(area_summaries, analyses_text)
        messages = [{
            "role": "user",
            "content": [{"type": "text", "text": message_prompt}]
        }]

        try:
            # Use invoke_model from BaseAgent
            response = self.invoke_model(messages=messages, system_prompt=system_prompt)
            # --- REMOVE DEBUG RAW RESPONSE ---
            # print(f"DEBUG (Interpretation): Raw LLM response: {response}")
            # --- END REMOVE --- 
            interpretation = response.strip()
            if not interpretation:
                 print("⚠️ Interpretation LLM returned empty string.")
                 interpretation = "No se pudo generar interpretación general."
            else:
                print("✅ Overall interpretation generated successfully.")
                # --- REMOVE DEBUG INTERPRETATION OUTPUT ---
                # print("\n--- DEBUG (SynthAgent): Overall Interpretation Generated --- ")
                # print(interpretation)
                # print("--- END DEBUG --- \n")
                # --- END REMOVE --- 
            return interpretation
        except Exception as e:
            print(f"❌ Error generating overall interpretation: {e}")
            return "Error al generar la interpretación general."

    # Refactored synthesize_analyses to orchestrate the two steps
    def synthesize_analyses(self, analyses: List[Dict[str, Any]], example_report: str = None, refinement_reason: str = None) -> Dict[str, Any]:
        """Synthesize multiple detailed analyses using a two-step LLM process."""
        # Note: refinement_reason and example_report are currently ignored in this two-step approach.
        if refinement_reason:
             print("⚠️ Refinement reason provided but currently ignored in two-step synthesis.")
        if example_report:
             print("⚠️ Example report provided but currently ignored in two-step synthesis.")
             
        # Step 1: Generate Area Summaries
        area_summaries = self._generate_area_summaries(analyses)
        
        # Check for errors in area summaries before proceeding
        if any("Error" in v for v in area_summaries.values()):
            print("❌ Aborting synthesis due to error in area summary generation.")
            # Return structure indicating error, ensuring all keys exist
            return {
                "weekly_report": {
                     "commercial": area_summaries.get("commercial", "Error desconocido"),
                     "customer": area_summaries.get("customer", "Error desconocido"),
                     "operations": area_summaries.get("operations", "Error desconocido"),
                     "disruptions": area_summaries.get("disruptions", "Error desconocido"),
                     "overall_interpretation": "Error: No se pudo generar resumen por áreas."
                 } 
            }
            
        # Step 2: Generate Overall Interpretation based on summaries and original analyses
        overall_interpretation = self._generate_overall_interpretation(area_summaries, analyses)
        
        # Step 3: Combine results into the final structure
        final_synthesis = {
            "weekly_report": {
                **area_summaries, # Unpack the area summaries
                "overall_interpretation": overall_interpretation
            }
        }
        
        # --- REMOVE DEBUG FINAL COMBINED SYNTHESIS --- 
        # print("\n📊 Final Combined Synthesis:")
        # print(json.dumps(final_synthesis, indent=2))
        # --- END REMOVE --- 
        
        # Return only the final synthesis dictionary
        return final_synthesis

    # --- Original Methods (keep for reference or specific use cases if needed) --- 
    # def synthesize_analyses_single_call(self, ...): # Original method renamed
    #    ... 

    # --- Helper and Output Methods --- 
    
    def _extract_json_from_raw_response(self, raw_response: str) -> Dict[str, Any]:
        """Extrae un objeto JSON válido de una respuesta raw que puede contener bloques de código."""
        import json
        try: # Outer try
            cleaned_response = raw_response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()
            
            # Attempt to parse directly first
            try: # Inner try 1
                 return json.loads(cleaned_response)
            except json.JSONDecodeError: # Matches Inner try 1
                 # If direct parsing fails, try finding the first { and last }
                 if "{" in cleaned_response and "}" in cleaned_response:
                     start_idx = cleaned_response.find("{")
                     end_idx = cleaned_response.rfind("}") + 1
                     json_text = cleaned_response[start_idx:end_idx]
                     try: # Inner try 2
                         # Try parsing the extracted substring
                        return json.loads(json_text)
                     except json.JSONDecodeError as inner_e: # Matches Inner try 2
                         # Correctly indented except for inner try
                         print(f"Error extracting JSON even after finding {{}}: {inner_e}")
                         return None # Indicate failure
                 else: # Matches if "{" in cleaned_response...
                     # Correctly indented else 
                     print("Could not find JSON structure in response.")
                     return None # Indicate failure
        # Correctly indented outer except, aligned with outer try
        except Exception as e:
            print(f"Error extracting JSON from raw_response: {str(e)}")
            return None
    
    def generate_final_report(self, synthesis: Dict[str, Any], date: str) -> str:
        """Generate the final report in markdown format."""
        print("\n📝 Generating final report...")
        
        # Get the weekly_report dictionary, handling potential absence
        weekly_report_data = synthesis.get('weekly_report', {})
        print(f"Synthesis keys (weekly_report content): {weekly_report_data.keys()}")
        
        # Update structure check for nested interpretation
        # Check for the 5 expected keys within weekly_report
        expected_keys = ["commercial", "customer", "operations", "disruptions", "overall_interpretation"]
        if not all(k in weekly_report_data for k in expected_keys):
            print("⚠️ La estructura del synthesis['weekly_report'] no es la esperada. Faltan claves.")
            # Ensure keys exist with default values if missing
            for k in expected_keys:
                 weekly_report_data.setdefault(k, f'No disponible ({k})')
        
        markdown = f"""# Airline Performance Report - {date}\n\n"""

        # Add weekly report section with items in the desired order
        markdown += "## Weekly Report\n\n"
        
        # 1. Operations
        markdown += f"- **Operations**: {weekly_report_data.get('operations')}\n\n" 
        
        # 2. Customer
        markdown += f"- **Customer**: {weekly_report_data.get('customer')}\n\n" 
        
        # 3. Disruptions
        markdown += f"- **Disruptions**: {weekly_report_data.get('disruptions')}\n\n" 
        
        # 4. Commercial
        markdown += f"- **Commercial**: {weekly_report_data.get('commercial')}\n\n" 
        
        # 5. Interpretación General (Last)
        markdown += f"- **Interpretación General**: {weekly_report_data.get('overall_interpretation')}\n\n" 

        print("✅ Informe semanal con interpretación integrada generado correctamente.")
        
        # Log the full report for debugging
        print("\n📋 Contenido completo del informe generado:")
        print(markdown)

        return markdown
    
    def _format_list(self, items: List[str]) -> str:
        """Format a list of items as a bullet point list."""
        return "\n".join([f"- {item}" for item in items])
    
    def _format_kpis(self, kpis: Dict[str, Any]) -> str:
        """Format KPIs as a bullet point list."""
        formatted_kpis = []
        for key, value in kpis.items():
            formatted_kpis.append(f"- **{key}**: {value}")
        return "\n".join(formatted_kpis)
    
    def _format_table(self, table_data: Any) -> str:
        """Format table data as markdown table."""
        if not table_data:
            return "*No data available*"
            
        # Si es un diccionario simple, convertirlo a lista para formatear
        if isinstance(table_data, dict):
            # Crear una tabla de dos columnas (clave - valor)
            md_table = "| Métrica | Valor |\n"
            md_table += "|--------|-------|\n"
            for key, value in table_data.items():
                md_table += f"| {key} | {value} |\n"
            return md_table
            
        # Si es una lista de diccionarios (formato tabla común)
        elif isinstance(table_data, list) and all(isinstance(item, dict) for item in table_data):
            if not table_data:
                return "*No data available*"
                
            # Extraer cabeceras de las columnas (todas las claves únicas)
            headers = set()
            for item in table_data:
                headers.update(item.keys())
            headers = sorted(list(headers))
            
            # Crear la primera fila de la tabla (cabeceras)
            md_table = "| " + " | ".join(headers) + " |\n"
            
            # Crear la fila de separadores
            md_table += "| " + " | ".join(["---"] * len(headers)) + " |\n"
            
            # Agregar cada fila de datos
            for item in table_data:
                row = []
                for header in headers:
                    row.append(str(item.get(header, "")))
                md_table += "| " + " | ".join(row) + " |\n"
                
            return md_table
            
        # Si es una estructura anidada (lista de listas)
        elif isinstance(table_data, list) and all(isinstance(item, list) for item in table_data):
            if not table_data:
                return "*No data available*"
                
            # Asumimos que la primera fila contiene las cabeceras
            md_table = "| " + " | ".join(str(h) for h in table_data[0]) + " |\n"
            
            # Crear la fila de separadores
            md_table += "| " + " | ".join(["---"] * len(table_data[0])) + " |\n"
            
            # Agregar cada fila de datos (saltando la primera que ya usamos como cabecera)
            for row in table_data[1:]:
                md_table += "| " + " | ".join(str(cell) for cell in row) + " |\n"
                
            return md_table
            
        # Si es un string, podría ser una tabla en formato texto
        elif isinstance(table_data, str):
            # Intentamos formatear como tabla markdown si parece contener filas
            if "\n" in table_data:
                lines = table_data.strip().split("\n")
                # Si las líneas tienen delimitadores comunes como tabulaciones, comas, etc.
                if "\t" in lines[0]:
                    # Tabla delimitada por tabulaciones
                    rows = [line.split("\t") for line in lines]
                    return self._format_table(rows)
                elif "," in lines[0]:
                    # Tabla delimitada por comas
                    rows = [line.split(",") for line in lines]
                    return self._format_table(rows)
                else:
                    # Si no detectamos un formato específico, devolverlo como texto con formato
                    return "```\n" + table_data + "\n```"
            else:
                return table_data
        else:
            # Si no sabemos cómo formatear los datos, convertirlos a string
            return str(table_data)
    
    def save_synthesis(self, synthesis: Dict[str, Any], output_dir: str) -> str:
        """Save the synthesis to a file."""
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "synthesis.json")
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(synthesis, f, ensure_ascii=False, indent=2)
            
        print(f"Synthesis saved to {output_path}")
        return output_path
    
    def save_report(self, markdown: str, date: str) -> str:
        """Save the report to a file."""
        # Create date-specific directory if it doesn't exist
        date_dir = os.path.join('reports', date)
        os.makedirs(date_dir, exist_ok=True)
        
        # Generate base filename
        base_filename = "synthesized_report"
        
        # Save main report
        main_filepath = os.path.join(date_dir, f"{base_filename}.md")
        with open(main_filepath, 'w') as f:
            f.write(markdown)
        
        # Also save a timestamped version for history
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        history_filepath = os.path.join(date_dir, f"{base_filename}_{timestamp}.md")
        with open(history_filepath, 'w') as f:
            f.write(markdown)
        
        print(f"✅ Informe guardado en: {main_filepath}")
        print(f"✅ Copia histórica guardada en: {history_filepath}")
        
        return main_filepath 