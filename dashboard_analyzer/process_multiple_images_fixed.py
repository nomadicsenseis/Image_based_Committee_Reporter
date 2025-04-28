#!/usr/bin/env python
"""
Script para procesar múltiples imágenes con los agentes de Commercial y Disruptions
Versión corregida que maneja la codificación de múltiples imágenes correctamente
"""
import os
import sys
import json
import argparse
import base64
from typing import List, Dict, Any

# Importar los agentes
from agents.commercial_agent import CommercialAgent
from agents.disruptions_agent import DisruptionsAgent

def encode_image(image_path: str) -> str:
    """Codifica una imagen en base64"""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        print(f"Error encoding image {image_path}: {e}")
        return None

def process_commercial_images(image_paths: List[str]) -> Dict[str, Any]:
    """Procesa imágenes comerciales"""
    if len(image_paths) == 0:
        print("No se proporcionaron imágenes comerciales")
        return {"error": "No se proporcionaron imágenes"}
    
    print(f"\n🔍 Procesando {len(image_paths)} imágenes comerciales...")
    for img in image_paths:
        print(f"- {os.path.basename(img)}")
    
    # Codificar todas las imágenes
    encoded_images = []
    for image_path in image_paths:
        encoded_image = encode_image(image_path)
        if not encoded_image:
            return {"error": f"Failed to encode image: {image_path}"}
        encoded_images.append(encoded_image)
    
    # Preparar contenido con múltiples imágenes
    content = [
        {
            "type": "text",
            "text": """Analiza las imágenes del dashboard comercial y proporciona un análisis detallado de los siguientes elementos:

1. KPIs principales:
   - Intakes (ingresos)
   - Objetivo semanal (weekly target)
   - Yield (ingreso por pasajero)
   - Pasajeros

2. Sección "Last reported":
   - Diferencia entre intakes y target
   - Análisis del mapa de distribución geográfica

3. Sección "Last week":
   - Tendencia de evolución de intakes

El análisis debe incluir:
1. Valores actuales de cada KPI
2. Diferencia exacta entre intakes y target
3. Patrones geográficos observados
4. Tendencias de evolución temporal
5. Especificación de qué datos faltan si no están todas las imágenes necesarias

Es importante verificar si tienes todas las imágenes necesarias para hacer un análisis completo.
Si falta alguna imagen, indica claramente qué datos no se pueden analizar debido a ello.

Proporciona la respuesta en formato JSON con la siguiente estructura:
{
  "left_kpis": {
    "intakes": <valor>,
    "weekly_target": <valor>,
    "yield": <valor>,
    "passengers": <valor>
  },
  "last_reported": {
    "intakes_vs_target_difference": <valor>,
    "map_analysis": "Análisis de la distribución geográfica"
  },
  "last_week": {
    "intake_trend": "Descripción de la evolución temporal"
  },
  "missing_data": "Descripción de cualquier dato faltante debido a la ausencia de imágenes (si aplica)"
}"""
        }
    ]
    
    # Agregar todas las imágenes al contenido
    for i, encoded_image in enumerate(encoded_images):
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": encoded_image
            }
        })
    
    # Inicializar el agente comercial
    commercial_agent = CommercialAgent()
    
    # Preparar el mensaje para el modelo con formato multimodal adecuado
    messages = [{
        "role": "user",
        "content": content
    }]
    
    # Obtener el system prompt predeterminado
    system_prompt = commercial_agent.get_system_prompt()
    
    # Invocar el modelo
    response = commercial_agent.invoke_model(messages, system_prompt=system_prompt)
    
    # Parsear la respuesta
    try:
        analysis = json.loads(response)
        
        # Agregar información sobre datos faltantes si no hay suficientes imágenes
        expected_images = 2
        if len(image_paths) < expected_images and "missing_data" not in analysis:
            analysis["missing_data"] = f"Faltan {expected_images - len(image_paths)} imágenes necesarias para completar el análisis. El análisis puede ser parcial."
            
        return analysis
    except json.JSONDecodeError:
        return {
            "error": "Invalid JSON response",
            "raw_response": response,
            "missing_data": "No se pudo analizar la respuesta JSON del modelo"
        }

def process_disruptions_images(image_paths: List[str]) -> Dict[str, Any]:
    """Procesa imágenes de disrupciones"""
    if len(image_paths) == 0:
        print("No se proporcionaron imágenes de disrupciones")
        return {"error": "No se proporcionaron imágenes"}
    
    print(f"\n🔍 Procesando {len(image_paths)} imágenes de disrupciones...")
    for img in image_paths:
        print(f"- {os.path.basename(img)}")
    
    # Codificar todas las imágenes
    encoded_images = []
    for image_path in image_paths:
        encoded_image = encode_image(image_path)
        if not encoded_image:
            return {"error": f"Failed to encode image: {image_path}"}
        encoded_images.append(encoded_image)
    
    # Preparar contenido con múltiples imágenes
    content = [
        {
            "type": "text",
            "text": """Analiza las imágenes del dashboard de disrupciones y proporciona un análisis detallado de los siguientes KPIs:
- Cancelaciones (Cancellations)
- Retrasos (Delays)
- Misconnections (%)
- Mishandling (%)
- DNB (Do Not Board)

El análisis debe incluir:
1. Valores actuales de cada KPI
2. Tendencias observadas para cada KPI
3. Identificación de picos o anomalías en las gráficas temporales
4. Especificación de qué datos faltan si no están todas las imágenes necesarias

Es importante verificar si tienes todas las imágenes necesarias (deberían ser 2) para hacer un análisis completo.
Si falta alguna imagen, indica claramente qué datos no se pueden analizar debido a ello.

Proporciona la respuesta en formato JSON con la siguiente estructura:
{
  "left_panel_kpis": {
    "cancelled": <valor o insights>,
    "delayed_arr_c15": <valor o insights>,
    "misconnections_percentage": <valor o insights>,
    "mishandling_percentage": <valor o insights>,
    "dnb": <valor o insights>
  },
  "trends": {
    "cancellations_trend": "Observaciones sobre la evolución de los vuelos cancelados",
    "delays_trend": "Observaciones sobre la evolución de los retrasos",
    "misconnections_trend": "Observaciones sobre la evolución de las misconnections",
    "mishandling_trend": "Observaciones sobre la evolución del mishandling",
    "dnb_trend": "Observaciones sobre la evolución del DNB"
  },
  "missing_data": "Descripción de cualquier dato faltante debido a la ausencia de imágenes (si aplica)"
}"""
        }
    ]
    
    # Agregar todas las imágenes al contenido
    for i, encoded_image in enumerate(encoded_images):
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": encoded_image
            }
        })
    
    # Inicializar el agente de disrupciones
    disruptions_agent = DisruptionsAgent()
    
    # Preparar el mensaje para el modelo con formato multimodal adecuado
    messages = [{
        "role": "user",
        "content": content
    }]
    
    # Obtener el system prompt predeterminado
    system_prompt = disruptions_agent.get_system_prompt()
    
    # Invocar el modelo
    response = disruptions_agent.invoke_model(messages, system_prompt=system_prompt)
    
    # Parsear la respuesta
    try:
        analysis = json.loads(response)
        
        # Agregar información sobre datos faltantes si no hay suficientes imágenes
        expected_images = 2
        if len(image_paths) < expected_images and "missing_data" not in analysis:
            analysis["missing_data"] = f"Faltan {expected_images - len(image_paths)} imágenes necesarias para completar el análisis. El análisis puede ser parcial."
            
        return analysis
    except json.JSONDecodeError:
        return {
            "error": "Invalid JSON response",
            "raw_response": response,
            "missing_data": "No se pudo analizar la respuesta JSON del modelo"
        }

def main():
    """Función principal"""
    # Configurar parser de argumentos
    parser = argparse.ArgumentParser(description='Procesar múltiples imágenes con agentes de análisis')
    parser.add_argument('--commercial', nargs='+', help='Rutas a imágenes comerciales')
    parser.add_argument('--disruptions', nargs='+', help='Rutas a imágenes de disrupciones')
    parser.add_argument('--output-dir', default='multiple_images_test', help='Directorio de salida para los informes')
    
    args = parser.parse_args()
    
    # Si no se proporcionaron argumentos, buscar imágenes en el directorio por defecto
    if not args.commercial and not args.disruptions:
        # Directorio de imágenes para inferencia
        img_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "img", "inference", "07-04-2025")
        
        # Verificar que exista el directorio
        if not os.path.exists(img_dir):
            print(f"❌ No se encontró el directorio de imágenes: {img_dir}")
            return
        
        # Buscar imágenes comerciales
        commercial_images = []
        for filename in os.listdir(img_dir):
            if filename.lower().startswith("commercial") and filename.endswith(".png"):
                commercial_images.append(os.path.join(img_dir, filename))
        
        # Buscar imágenes de disrupciones
        disruptions_images = []
        for filename in os.listdir(img_dir):
            if (filename.lower().startswith("disruptions") or filename.lower().startswith("disrruptions")) and filename.endswith(".png"):
                disruptions_images.append(os.path.join(img_dir, filename))
    else:
        commercial_images = args.commercial or []
        disruptions_images = args.disruptions or []
    
    print(f"\n📊 Encontradas {len(commercial_images)} imágenes comerciales y {len(disruptions_images)} imágenes de disrupciones")
    
    # Procesar imágenes
    commercial_analysis = None
    disruptions_analysis = None
    
    if commercial_images:
        commercial_analysis = process_commercial_images(commercial_images)
    
    if disruptions_images:
        disruptions_analysis = process_disruptions_images(disruptions_images)
    
    # Crear directorio para informes
    reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports", args.output_dir)
    os.makedirs(reports_dir, exist_ok=True)
    
    # Guardar resultados
    if commercial_analysis:
        commercial_path = os.path.join(reports_dir, "commercial_analysis.json")
        with open(commercial_path, 'w') as f:
            json.dump(commercial_analysis, f, indent=2)
        print(f"\n✅ Análisis comercial guardado en: {commercial_path}")
    
    if disruptions_analysis:
        disruptions_path = os.path.join(reports_dir, "disruptions_analysis.json")
        with open(disruptions_path, 'w') as f:
            json.dump(disruptions_analysis, f, indent=2)
        print(f"\n✅ Análisis de disrupciones guardado en: {disruptions_path}")

if __name__ == "__main__":
    main() 