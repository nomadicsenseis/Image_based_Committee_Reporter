#!/usr/bin/env python
"""
Script para procesar múltiples imágenes con los agentes de Commercial y Disruptions
"""
import os
import sys
import json
import argparse
from agents.commercial_agent import CommercialAgent
from agents.disruptions_agent import DisruptionsAgent
from agents.synthesis_agent import SynthesisAgent

def process_commercial_images(image_paths):
    """Procesar múltiples imágenes comerciales con el agente CommercialAgent"""
    if len(image_paths) == 0:
        print("❌ No se proporcionaron imágenes comerciales")
        return {"error": "No se proporcionaron imágenes"}
    
    print(f"\n🔍 Procesando {len(image_paths)} imágenes comerciales...")
    print("Imágenes identificadas:")
    for img in image_paths:
        filename = os.path.basename(img)
        # Identify image type based on filename
        if "last_week" in filename.lower():
            image_type = "Last Week data"
        elif "last_reported" in filename.lower():
            image_type = "Last Reported data"
        else:
            image_type = "Commercial dashboard"
        print(f"- {filename} -> {image_type}")
    
    # Inicializar el agente
    commercial_agent = CommercialAgent()
    
    # Analizar las imágenes
    analysis = commercial_agent.analyze_image(image_paths)
    
    print("\n📊 Resultado del análisis comercial:")
    print(json.dumps(analysis, indent=2))
    
    return analysis

def process_disruptions_images(image_paths):
    """Procesar múltiples imágenes de disrupciones con el agente DisruptionsAgent"""
    if len(image_paths) == 0:
        print("❌ No se proporcionaron imágenes de disrupciones")
        return {"error": "No se proporcionaron imágenes"}
    
    print(f"\n🔍 Procesando {len(image_paths)} imágenes de disrupciones...")
    print("Imágenes identificadas:")
    for img in image_paths:
        filename = os.path.basename(img)
        # Identify image type based on filename
        if "missconnections" in filename.lower():
            image_type = "Missconnections KPI"
        elif "mishandling" in filename.lower():
            image_type = "Mishandling KPI"
        else:
            image_type = "Disruptions dashboard"
        print(f"- {filename} -> {image_type}")
    
    # Inicializar el agente
    disruptions_agent = DisruptionsAgent()
    
    # Analizar las imágenes
    analysis = disruptions_agent.analyze_image(image_paths)
    
    print("\n📊 Resultado del análisis de disrupciones:")
    print(json.dumps(analysis, indent=2))
    
    return analysis

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
        img_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "img", "inference")
        
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
    
    # Show detailed file list
    if commercial_images:
        print("\nImágenes comerciales:")
        for img in commercial_images:
            print(f"- {os.path.basename(img)}")
    
    if disruptions_images:
        print("\nImágenes de disrupciones:")
        for img in disruptions_images:
            print(f"- {os.path.basename(img)}")
    
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