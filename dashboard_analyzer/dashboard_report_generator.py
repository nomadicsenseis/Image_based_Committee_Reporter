#!/usr/bin/env python
"""
Dashboard Report Generator - Creates insightful airline committee reports from dashboard images
"""
import os
import sys
import argparse
import base64
import json
from datetime import datetime
import boto3
from dotenv import load_dotenv
from PIL import Image
import io
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Any
from dashboard_analyzer.agents.operations_agent import OperationsAgent
from dashboard_analyzer.agents.customer_agent import CustomerAgent
from dashboard_analyzer.agents.disruptions_agent import DisruptionsAgent
from dashboard_analyzer.agents.commercial_agent import CommercialAgent
from dashboard_analyzer.agents.synthesis_agent import SynthesisAgent
from dashboard_analyzer.agents.verification_agent import VerificationAgent

# Get the directory of the current file
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_ROOT = os.path.dirname(SCRIPT_DIR)
DEVCONTAINER_ENV_PATH = os.path.join(WORKSPACE_ROOT, '.devcontainer', '.env')
IMG_DIR = os.path.join(SCRIPT_DIR, "img")
CONTEXT_IMG_DIR = os.path.join(IMG_DIR, "context")
INFERENCE_IMG_DIR = os.path.join(IMG_DIR, "inference")
REPORTS_DIR = os.path.join(SCRIPT_DIR, "reports")

def encode_image(image_path):
    """Encode an image as base64"""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        print(f"❌ Error encoding image {image_path}: {e}")
        return None

def compress_image(image_path, max_size_mb=5):
    """Compress an image if it's larger than max_size_mb"""
    try:
        # Get file size in MB
        file_size_mb = os.path.getsize(image_path) / (1024 * 1024)
        
        # If file is already small enough, return the original path
        if file_size_mb <= max_size_mb:
            return image_path
        
        # Open the image
        img = Image.open(image_path)
        
        # Calculate compression ratio needed
        compression_ratio = max_size_mb / file_size_mb
        # Convert to quality percentage (0-100)
        quality = int(100 * compression_ratio)
        quality = max(1, min(95, quality))  # Ensure quality is between 1 and 95
        
        # Create a temporary file for the compressed image
        temp_path = f"{image_path}.compressed.jpg"
        
        # Save with compression
        img.save(temp_path, format="JPEG", quality=quality, optimize=True)
        
        print(f"✅ Compressed {image_path} from {file_size_mb:.2f}MB to {os.path.getsize(temp_path) / (1024 * 1024):.2f}MB")
        return temp_path
    
    except Exception as e:
        print(f"❌ Error compressing image {image_path}: {e}")
        return image_path

def get_context_images(context_date=None, max_images=5):
    """Get a list of context images"""
    context_images = []
    
    if not os.path.exists(CONTEXT_IMG_DIR):
        print(f"⚠️ Context image directory doesn't exist: {CONTEXT_IMG_DIR}")
        os.makedirs(CONTEXT_IMG_DIR, exist_ok=True)
        return context_images
    
    # Create date folder path
    date_folder = os.path.join(CONTEXT_IMG_DIR, context_date) if context_date else CONTEXT_IMG_DIR
    
    if not os.path.exists(date_folder):
        print(f"⚠️ Context date folder doesn't exist: {date_folder}")
        return context_images
    
    # Get all images in the date folder
    for filename in os.listdir(date_folder):
        if filename.endswith(".png"):
            context_images.append(os.path.join(date_folder, filename))
    
    if not context_images:
        print(f"⚠️ No context images found in {date_folder}")
    
    return context_images[:max_images]

def get_example_reports(example_report_date=None):
    """Get example reports for the given date"""
    example_reports = []
    
    if not example_report_date:
        return example_reports
    
    # Create reports directory path
    reports_dir = os.path.join(REPORTS_DIR, example_report_date)
    
    if not os.path.exists(reports_dir):
        print(f"⚠️ Example reports directory doesn't exist: {reports_dir}")
        return example_reports
    
    # Get all reports in the directory
    for filename in os.listdir(reports_dir):
        if filename.endswith(".md"):
            example_reports.append(os.path.join(reports_dir, filename))
    
    if not example_reports:
        print(f"⚠️ No example reports found in {reports_dir}")
    
    return example_reports

def build_system_prompt_with_context(context_images, example_reports):
    """Build the system prompt with context images and example reports"""
    # Build the base system prompt without hardcoded examples
    system_prompt = """You are an expert at generating extremely concise committee reports for an airline company based on dashboard images. Your task is to create BRIEF, high-impact insights highlighting ONLY the 2-3 most critical KPIs and trends. 

CRITICAL INSTRUCTIONS:
1. Be EXTREMELY BRIEF - no more than 1 paragraph per image.
2. Focus ONLY on critical decision-making insights, omit routine details
3. Match the example report's length and terseness
4. Your analysis must focus ONLY on the new image presented, NOT on the example images

Remember: Your report will be judged on its brevity and impact. Decision-makers need just the critical insights, not exhaustive analysis.
"""
    
    # Add example reports if available
    if example_reports:
        system_prompt += "\n\nHere are examples of previous reports that show the expected format and level of analysis. Use these as a guide for style, structure, and depth:\n\n"
        
        for report_content in example_reports:
            system_prompt += f"## EXAMPLE REPORT\n\n"
            system_prompt += report_content
            system_prompt += "\n\n---\n\n"
    else:
        # Fall back to a minimal structure guidance if no reports are available
        system_prompt += """
Use the following structure for your report:

- **Operations**: Analyze operational metrics like punctuality and flight performance
- **Customer**: Analyze customer experience metrics including NPS scores
- **Disruptions**: Analyze cancellations, mishandlings, and other disruption data
- **Commercial**: Analyze commercial performance metrics against targets
"""
    
    system_prompt += "\n\nEnsure your analysis is clear, structured, and insightful, suitable for decision-making purposes within the airline's committee meetings. Try to stick to a similar length to the example report."
    
    if not context_images:
        print("⚠️ No context images found for the specified date. Using text-only prompt.")
        return {"text": system_prompt, "context_images": []}
    
    # Add context images to the prompt
    context_image_contents = []
    
    for img_path in context_images:
        # Compress image if needed
        processed_path = compress_image(img_path)
        
        # Extract filename without extension for reference
        img_name = os.path.basename(img_path).split('.')[0]
        
        # Encode the image
        encoded_image = encode_image(processed_path)
        if encoded_image:
            context_image_contents.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": encoded_image
                }
            })
            print(f"✅ Added context image to system prompt: {img_name}")
        
        # Remove temporary compressed file if created
        if processed_path != img_path and os.path.exists(processed_path):
            os.remove(processed_path)
    
    return {"text": system_prompt, "context_images": context_image_contents}

def setup_environment():
    """Set up environment variables and directories"""
    # Load environment variables from .devcontainer/.env
    if os.path.exists(DEVCONTAINER_ENV_PATH):
        load_dotenv(DEVCONTAINER_ENV_PATH)
        print(f"✅ Loaded environment variables from {DEVCONTAINER_ENV_PATH}")
    else:
        print(f"❌ No .env file found in .devcontainer folder at {DEVCONTAINER_ENV_PATH}")
        return False
    
    # Check for AWS credentials
    if not os.getenv('AWS_ACCESS_KEY_ID'):
        print("❌ Missing AWS_ACCESS_KEY_ID environment variable")
        return False
    
    if not os.getenv('AWS_SECRET_ACCESS_KEY'):
        print("❌ Missing AWS_SECRET_ACCESS_KEY environment variable")
        return False
    
    # Check for AWS region - support both AWS_REGION and AWS_DEFAULT_REGION
    if os.getenv('AWS_REGION'):
        aws_region = os.getenv('AWS_REGION')
    elif os.getenv('AWS_DEFAULT_REGION'):
        aws_region = os.getenv('AWS_DEFAULT_REGION')
        # Set AWS_REGION to match AWS_DEFAULT_REGION for compatibility
        os.environ['AWS_REGION'] = aws_region
        print(f"✅ Using AWS_DEFAULT_REGION ({aws_region}) as AWS_REGION")
    else:
        print("❌ Missing AWS_REGION or AWS_DEFAULT_REGION environment variable")
        return False
    
    # Check that required directories exist
    for directory in [IMG_DIR, REPORTS_DIR]:
        if not os.path.exists(directory):
            print(f"⚠️ Directory doesn't exist: {directory}")
            print(f"Creating directory: {directory}")
            try:
                os.makedirs(directory, exist_ok=True)
            except Exception as e:
                print(f"❌ Error creating directory {directory}: {e}")
                return False
    
    # Check context and inference directories - these should be mounted, not created
    for directory in [CONTEXT_IMG_DIR, INFERENCE_IMG_DIR]:
        if not os.path.exists(directory):
            print(f"⚠️ Directory doesn't exist: {directory} (should be mounted in container)")
    
    return True

def get_bedrock_client():
    """Initialize and return a Bedrock client"""
    try:
        # Check if region is set
        if not os.environ.get('AWS_REGION'):
            raise ValueError("AWS_REGION environment variable not set")
        
        # Create a Bedrock Runtime client
        client = boto3.client(
            service_name='bedrock-runtime',
            region_name=os.environ.get('AWS_REGION')
        )
        
        # Verify that MODEL_ARN is set
        model_id = os.getenv('MODEL_ARN')
        if not model_id:
            print("⚠️ MODEL_ARN not set in environment variables. Will use default Claude model.")
            model_id = 'anthropic.claude-3-sonnet-20240229-v1:0'
        else:
            print(f"✅ Using MODEL_ARN: {model_id}")
        
        # No need to call any API method here, just return the client
        return client
    except Exception as e:
        print(f"❌ Error initializing Bedrock client: {str(e)}")
        return None

def analyze_images(bedrock_client, image_paths, user_query, context_date="07042025", example_report_date=None):
    """Analyze dashboard images and generate a report"""
    model_id = os.getenv('MODEL_ARN', 'anthropic.claude-3-sonnet-20240229-v1:0')
    
    # Get context images
    context_images = get_context_images(context_date)
    
    # Get example reports
    example_reports = get_example_reports(example_report_date)
    
    # Build system prompt with context images
    system_prompt_data = build_system_prompt_with_context(context_images, example_reports)
    system_prompt_text = system_prompt_data["text"]
    context_image_contents = system_prompt_data["context_images"]
    
    # Process and encode input images for analysis
    input_image_contents = []
    for img_path in image_paths:
        # Compress image if needed
        processed_path = compress_image(img_path)
        
        # Extract filename without extension for reference
        img_name = os.path.basename(img_path).split('.')[0]
        
        # Encode the image
        encoded_image = encode_image(processed_path)
        if encoded_image:
            input_image_contents.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": encoded_image
                }
            })
            print(f"✅ Added input image for analysis: {img_name}")
        
        # Remove temporary compressed file if created
        if processed_path != img_path and os.path.exists(processed_path):
            os.remove(processed_path)
    
    # In Claude Bedrock API, system must be a plain text string
    # We can't include context images in the system, so we'll include them in the user message
    system_prompt = system_prompt_text
    
    # Create user message with query, context images, and input images
    user_content = [{"type": "text", "text": user_query or "Create an EXTREMELY CONCISE committee report based on these dashboard images. Focus ONLY on the 2-3 most business-critical insights per section. Use bullet points liberally. Match the brevity of the example report - aim for minimal text that delivers maximum impact."}]
    
    # Add context images to user message
    if context_image_contents:
        # Add a message explaining the context images
        user_content.append({"type": "text", "text": "\nThe following are EXAMPLE dashboard images from a DIFFERENT DATE. They are provided ONLY as references for format and style. DO NOT analyze these examples:"})
        user_content.extend(context_image_contents)
        user_content.append({"type": "text", "text": "\nNow, please analyze ONLY the following dashboard images. Your report should be about THESE IMAGES, not the examples above:"})
    
    # Add input images to user message
    user_content.extend(input_image_contents)
    
    # Create the messages array with user message only
    messages = [
        {"role": "user", "content": user_content}
    ]
    
    try:
        # Call Bedrock with the prepared prompt
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4000,
            "messages": messages,
            "system": system_prompt
        }
        
        # Invoke the model
        response = bedrock_client.invoke_model(
            modelId=model_id,
            body=json.dumps(request_body)
        )
        
        # Parse the response
        response_body = json.loads(response['body'].read().decode('utf-8'))
        report_content = response_body['content'][0]['text']
        
        return report_content
    
    except Exception as e:
        print(f"❌ Error analyzing images with Bedrock: {str(e)}")
        return None

def save_report(report_content, report_name=None, date_folder=None):
    """Save the generated report to a file, optionally in a date subfolder"""
    if not report_content:
        print("❌ No report content to save")
        return None
    
    # Generate a default filename if none provided
    if not report_name:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_name = f"airline_committee_report_{timestamp}"
    
    # Ensure the report has a .md extension
    if not report_name.endswith('.md'):
        report_name += '.md'
    
    # Create date-based subfolder if specified
    if date_folder:
        date_reports_dir = os.path.join(REPORTS_DIR, date_folder)
        # Create the subfolder if it doesn't exist
        if not os.path.exists(date_reports_dir):
            try:
                os.makedirs(date_reports_dir, exist_ok=True)
                print(f"✅ Created reports subfolder: {date_reports_dir}")
            except Exception as e:
                print(f"❌ Error creating report subfolder {date_reports_dir}: {e}")
                # Fall back to the main reports directory
                date_reports_dir = REPORTS_DIR
        
        # Use the date subfolder
        report_path = os.path.join(date_reports_dir, report_name)
    else:
        # Use the main reports directory
        report_path = os.path.join(REPORTS_DIR, report_name)
    
    try:
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        print(f"✅ Report saved to {report_path}")
        return report_path
    except Exception as e:
        print(f"❌ Error saving report: {e}")
        return None

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Analyze dashboard images and generate a report.')
    parser.add_argument('--date', type=str, required=True, help='Date for analysis (DD-MM-YYYY)')
    parser.add_argument('--context-date', type=str, help='Date for context images (DD-MM-YYYY)')
    parser.add_argument('--folder', action='store_true', help='Analyze all images in the date folder')
    parser.add_argument('--save-report', action='store_true', help='Save the report')
    args, unknown = parser.parse_known_args()
    
    # Initialize the report generator
    report_generator = DashboardReportGenerator()
    
    if unknown and not args.folder:
        # Check if unknown arguments are image files
        image_files = [arg for arg in unknown if arg.endswith('.png')]
        print(f"Image files specified: {', '.join(image_files)}")
        
        # Analyze the specified images
        analyses = report_generator.analyze_images(args.date, args.context_date, image_files)
    else:
        # Analyze all images in the date folder
        analyses = report_generator.analyze_images(args.date, args.context_date)
    
    if not analyses:
        print("No analyses generated. Exiting.")
        return
    
    # Generate the final report using the new structure
    print("\n📝 Generating final report with new concise structure...")
    report_content = report_generator.generate_report(analyses, args.date, args.context_date)
    
    if not report_content:
        print("❌ Failed to generate report")
        return
    
    # Save the report if requested
    if args.save_report:
        # Save the report using the report generator's method
        report_path = report_generator.save_report(report_content, args.date)
        print(f"\n✅ Main report path: {report_path}") # Clarify this is the main path returned
        
        # El guardado doble ya no es necesario, save_report guarda ambos.
        # main_report_path = os.path.join('reports', args.date, "synthesized_report.md")
        # with open(main_report_path, 'w') as f:
        #     f.write(report_content)
        # print(f"✅ También se guardó una copia principal en: {main_report_path}")
    else:
        print("\n📄 Report content:")
        print(report_content)

class DashboardImageAnalyzer:
    """Class to analyze dashboard images using Bedrock"""
    
    def __init__(self, system_prompt=None, debug=False):
        self.debug = debug
        self.system_prompt = system_prompt
    
    def analyze_image(self, image_path):
        """Analyze dashboard images and generate a report"""
        model_id = os.getenv('MODEL_ARN', 'anthropic.claude-3-sonnet-20240229-v1:0')
        
        # Process and encode input images for analysis
        encoded_image = encode_image(image_path)
        if not encoded_image:
            print(f"❌ Failed to encode image: {image_path}")
            return None
        
        # Create image message
        image_message = {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": encoded_image
            }
        }
        
        # Create user message with image and query
        user_content = [
            {"type": "text", "text": "Analyze this dashboard image with EXTREME BREVITY. Focus ONLY on this specific image (not the reference examples). Generate a report that:  \n1. Identifies only the 2-3 MOST CRITICAL insights  \n2. Uses minimal text - no more than 1-2 short paragraphs per section  \n3. Employs bullet points for efficient information delivery  \n4. Matches the terse, concise style of the example report:"},
            image_message
        ]
        
        # Get context images from system prompt
        context_image_contents = []
        if self.system_prompt and "context_images" in self.system_prompt:
            context_image_contents = self.system_prompt["context_images"]
        
        # Add context images to user message
        if context_image_contents:
            # Add a message explaining the context images
            user_content.insert(0, {"type": "text", "text": "\nThe following are EXAMPLE dashboard images from a DIFFERENT DATE. They are provided ONLY as references for format and style. DO NOT analyze these examples:"})
            # Insert context images after the explanation
            for i, img_content in enumerate(context_image_contents):
                user_content.insert(i+1, img_content)
            # Add separator before the main image
            user_content.insert(len(context_image_contents)+1, {"type": "text", "text": "\nNow, please analyze ONLY the following dashboard image. Your report should be about THIS IMAGE, not the examples above:"})
        
        # Create the messages array
        messages = [
            {
                "role": "user",
                "content": user_content
            }
        ]
        
        # Configure the Bedrock client
        bedrock = boto3.client(
            service_name='bedrock-runtime',
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
        
        # Debug print
        if self.debug:
            print(f"Using model: {model_id}")
            print(f"Messages structure contains {len(messages)} messages")
            print(f"System prompt length: {len(self.system_prompt['text']) if self.system_prompt and 'text' in self.system_prompt else 'N/A'}")
            print(f"User message contains {len(user_content)} content items")
        
        try:
            # Call Bedrock with rate limiting and retries
            max_retries = 3
            retry_delay = 5  # seconds
            
            for attempt in range(max_retries):
                try:
                    system_content = self.system_prompt["text"] if self.system_prompt and "text" in self.system_prompt else "You are an expert at analyzing airline dashboard images."
                    
                    response = bedrock.invoke_model(
                        modelId=model_id,
                        body=json.dumps({
                            "anthropic_version": "bedrock-2023-05-31",
                            "max_tokens": 4000,
                            "temperature": 0.2,
                            "system": system_content,
                            "messages": messages
                        })
                    )
                    
                    # Parse the response
                    response_body = json.loads(response['body'].read().decode('utf-8'))
                    if 'content' in response_body and len(response_body['content']) > 0:
                        for content in response_body['content']:
                            if content['type'] == 'text':
                                return content['text']
                    
                    # If we didn't find any text content
                    print("⚠️ No text content found in the response")
                    return None
                    
                except Exception as e:
                    if "ThrottlingException" in str(e) and attempt < max_retries - 1:
                        print(f"⚠️ Rate limited. Retrying in {retry_delay} seconds...")
                        import time
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        # Re-raise if it's not a throttling error or we've exhausted retries
                        raise
            
            print("❌ Exceeded maximum retries")
            return None
            
        except Exception as e:
            print(f"❌ Error analyzing image: {str(e)}")
            return None

def combine_analyses(analyses):
    """Combine multiple analyses into a single report"""
    combined_report = "# Airline Committee Report\n\n"
    
    # Add each image analysis to the report
    for analysis in analyses:
        image_name = analysis["image"]
        image_analysis = analysis["analysis"]
        
        if image_analysis:
            # Add a section header for each image
            combined_report += f"## Analysis of {image_name}\n\n"
            combined_report += image_analysis
            combined_report += "\n\n"
    
    return combined_report

class DashboardReportGenerator:
    """Class to analyze dashboard images and generate reports."""
    
    def __init__(self):
        """Initialize the DashboardReportGenerator."""
        print("Initializing DashboardReportGenerator...")
        
        # Initialize agents
        print("Initializing agents...")
        self.operations_agent = OperationsAgent()
        self.customer_agent = CustomerAgent()
        self.disruptions_agent = DisruptionsAgent()
        self.commercial_agent = CommercialAgent()
        self.synthesis_agent = SynthesisAgent()
        self.verification_agent = VerificationAgent()
        
        print("✅ DashboardReportGenerator initialized")
    
    def get_context_images(self, context_date: str) -> List[str]:
        """Get context images for the given date."""
        # Use the absolute path from the workspace root
        context_dir = os.path.join(WORKSPACE_ROOT, 'dashboard_analyzer', 'img', 'context', context_date)
        if not os.path.exists(context_dir):
            print(f"⚠️ Context directory doesn't exist: {context_dir}")
            return []
        
        # Get all images in the context directory
        context_images = []
        for filename in os.listdir(context_dir):
            if filename.endswith(".png"):
                context_images.append(os.path.join(context_dir, filename))
        
        if not context_images:
            print(f"⚠️ No context images found in {context_dir}")
        
        return context_images
    
    def get_example_reports(self, context_date: str) -> List[str]:
        """Get example reports for the given date."""
        example_dir = os.path.join('reports', context_date)
        if not os.path.exists(example_dir):
            print(f"⚠️ Example reports directory doesn't exist: {example_dir}")
            return []
        
        # Get all reports in the example directory
        example_reports = []
        for filename in os.listdir(example_dir):
            if filename.endswith(".md"):
                example_reports.append(os.path.join(example_dir, filename))
        
        if not example_reports:
            print(f"⚠️ No example reports found in: {example_dir}")
        
        return example_reports
    
    def build_system_prompt_with_context(self, context_images: List[str], example_reports: List[str]) -> str:
        """Build a system prompt with context images and example reports."""
        # Start with the base prompt
        prompt = """You are the Data Director of Iberia Airlines, reporting directly to the CEO. 
Your role is to analyze dashboard images and provide concise, actionable insights.
Focus on identifying key trends, relationships between metrics, and strategic recommendations.
Keep the report extremely brief and focused on the most critical insights."""

        # Add context images if available
        if context_images:
            prompt += "\n\nContext Images (for reference only):"
            for image in context_images:
                prompt += f"\n- {os.path.basename(image)}"
        
        # Add example reports if available
        if example_reports:
            prompt += "\n\nExample Reports (for reference only):"
            for report in example_reports:
                prompt += f"\n- {os.path.basename(report)}"
        
        return prompt
    
    def analyze_images(self, date: str, context_date: str = None, specific_images: List[str] = None) -> List[Dict[str, Any]]:
        """Analiza las imágenes de los dashboards y genera un informe."""
        print(f"Starting analysis for date: {date}")
        
        # Get inference images
        inference_images = self.get_inference_images(date, specific_images)
        if not inference_images:
            print("No inference images found")
            return []
        
        print(f"Found {len(inference_images)} inference images")
        
        # Group images by type
        image_groups = self._group_images_by_type(inference_images)
        
        analyses = []
        
        # Paralelizar la ejecución de los agentes principales
        from concurrent.futures import ThreadPoolExecutor
        import time
        
        # Función para ejecutar análisis de cada agente
        def run_agent_analysis(agent_type, agent_obj, images):
            if not images:
                print(f"No {agent_type} images to analyze")
                return None
                
            start_time = time.time()
            print(f"Starting {agent_type} analysis...")
            analysis_result = agent_obj.analyze_image(images)
            elapsed_time = time.time() - start_time
            print(f"✅ {agent_type.capitalize()} analysis completed in {elapsed_time:.2f} seconds")
            
            return {
                "type": agent_type,
                "analysis": analysis_result # Devolver el original
            }
        
        # Preparar las tareas para ejecutar en paralelo
        analysis_tasks = []
        
        if image_groups["operations"]:
            analysis_tasks.append(
                ("operations", self.operations_agent, image_groups["operations"])
            )
        
        if image_groups["customer"]:
            analysis_tasks.append(
                ("customer", self.customer_agent, image_groups["customer"])
            )
        
        if image_groups["disruptions"]:
            analysis_tasks.append(
                ("disruptions", self.disruptions_agent, image_groups["disruptions"])
            )
        
        if image_groups["commercial"]:
            analysis_tasks.append(
                ("commercial", self.commercial_agent, image_groups["commercial"])
            )
        
        # Ejecutar tareas en paralelo con un máximo de 4 workers
        with ThreadPoolExecutor(max_workers=4) as executor:
            # Iniciar todas las tareas
            future_to_agent = {
                executor.submit(run_agent_analysis, agent_type, agent_obj, images): agent_type
                for agent_type, agent_obj, images in analysis_tasks
            }
            
            # Recoger resultados a medida que se completan
            for future in future_to_agent:
                agent_type = future_to_agent[future]
                try:
                    # Ensure json is imported in this scope for result processing/logging
                    import json 
                    result = future.result()
                    if result:
                        analyses.append(result) # Guardar el análisis original
                        print(f"{agent_type.capitalize()} Analysis Summary:")
                        # Print only first 1000 chars to avoid flooding logs
                        analysis_str = json.dumps(result.get("analysis", {}), indent=2, ensure_ascii=False)
                        print(analysis_str[:1000] + ("..." if len(analysis_str) > 1000 else "")) 
                except Exception as e:
                    # Ensure json is imported in this scope for potential error formatting
                    import json 
                    print(f"❌ Error in {agent_type} analysis: {str(e)}")
                    # Optionally, append a placeholder error analysis
                    analyses.append({
                        "type": agent_type,
                        "analysis": {"error": f"Error grave durante el análisis de {agent_type}: {str(e)}"}
                    })
        
        return analyses
    
    def _analyze_image(self, agent: Any, image_path: str, date: str) -> Dict[str, Any]:
        """Analyze a single image with the given agent."""
        return agent.analyze_image(image_path)
    
    def generate_report(self, analyses: List[Dict[str, Any]], date: str, context_date: str = None) -> str:
        """Generate a report based on the analyses."""
        # Removed verification loop for simplicity with two-step synthesis
        print("\n📝 Generating synthesis...")
        
        # Call synthesize_analyses (which now handles both steps internally)
        # Assuming it now returns only the final synthesis dictionary
        synthesis_result = self.synthesis_agent.synthesize_analyses(analyses)
        
        if not synthesis_result or 'weekly_report' not in synthesis_result:
             print("❌ Failed to generate valid synthesis structure.")
             # Create a minimal structure to avoid error in generate_final_report
             synthesis_result = {
                 'weekly_report': {
                     'commercial': 'Error en síntesis',
                     'customer': 'Error en síntesis',
                     'operations': 'Error en síntesis',
                     'disruptions': 'Error en síntesis',
                     'overall_interpretation': 'Error en síntesis'
                 }
             }
             
        # Log the exact synthesis dictionary received
        print("\nDEBUG: Final Synthesis dictionary RECEIVED by generate_report:")
        print(json.dumps(synthesis_result, indent=2))

        # Generate the final report using the new concise format
        print("\n📄 Generating final markdown report...")
        return self.synthesis_agent.generate_final_report(synthesis_result, date)
    
    def _format_list(self, items: List[str]) -> str:
        """Format a list of items as markdown bullet points."""
        return "\n".join(f"- {item}" for item in items)
    
    def save_report(self, markdown: str, date: str) -> str:
        """Save the final report to a file."""
        # Create date-specific directory if it doesn't exist
        date_dir = os.path.join('reports', date)
        os.makedirs(date_dir, exist_ok=True)
        
        # Generate filename
        filename = f"synthesized_report.md"
        filepath = os.path.join(date_dir, filename)
        
        # Save the report
        with open(filepath, 'w') as f:
            f.write(markdown)
        
        # Also save a timestamped copy for history
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        history_filename = f"synthesized_report_{timestamp}.md"
        history_filepath = os.path.join(date_dir, history_filename)
        
        with open(history_filepath, 'w') as f:
            f.write(markdown)
        
        return filepath

    def get_inference_images(self, date: str, specific_images: List[str] = None) -> List[str]:
        """Get the paths to inference images for a given date."""
        # If specific images are provided, use those
        if specific_images:
            full_paths = []
            for img in specific_images:
                # Check if it's a full path or just a filename
                if os.path.isfile(img):
                    full_paths.append(os.path.abspath(img))
                else:
                    # Try to find it in the inference directory
                    img_path = os.path.join(INFERENCE_IMG_DIR, date, img)
                    if os.path.isfile(img_path):
                        full_paths.append(img_path)
                    else:
                        print(f"Could not find image: {img}")
            return full_paths
        
        # Otherwise, get all images for the date
        inference_dir = os.path.join(INFERENCE_IMG_DIR, date)
        if not os.path.exists(inference_dir):
            print(f"No inference directory found for date: {date}")
            return []
        
        # Find all png images in the directory and its subdirectories
        images = []
        for root, _, files in os.walk(inference_dir):
            for file in files:
                if file.endswith('.png'):
                    full_path = os.path.join(root, file)
                    images.append(full_path)
        
        if not images:
            print(f"No images found in {inference_dir}")
        
        return sorted(images)

    def _group_images_by_type(self, image_paths: List[str]) -> Dict[str, Dict[str, str]]:
        """Group images by their type and specific panel."""
        print(f"Grouping {len(image_paths)} images by type...")
        
        # DEBUG: Print all image paths
        print("DEBUG: All image paths:")
        for img in image_paths:
            print(f"DEBUG: - {img}")
        
        image_groups = {
            "operations": {},
            "customer": {},
            "disruptions": {},
            "commercial": {}
        }
        
        # Group operations images
        operations_images = [img for img in image_paths if 'operations' in img.lower()]
        print(f"Found {len(operations_images)} operations images")
        if operations_images:
            image_groups["operations"]["panel_kpis_operations"] = next(
                (img for img in operations_images if 'panel_kpis_operations.png' in img.lower()), None
            )
            image_groups["operations"]["inbound_PuncDep15_evolution"] = next(
                (img for img in operations_images if 'inbound_puncdep15_evolution.png' in img.lower()), None
            )
            image_groups["operations"]["outbound_PuncDep15_evolution"] = next(
                (img for img in operations_images if 'outbound_puncdep15_evolution.png' in img.lower()), None
            )
            image_groups["operations"]["inbound_PuncDep15_byregion"] = next(
                (img for img in operations_images if 'inbound_puncdep15_byregion.png' in img.lower()), None
            )
            image_groups["operations"]["outbound_PuncDep15_byregion"] = next(
                (img for img in operations_images if 'outbound_puncdep15_byregion.png' in img.lower()), None
            )
        
        # Group customer images
        customer_images = [img for img in image_paths if 'customer' in img.lower()]
        print(f"Found {len(customer_images)} customer images")
        if customer_images:
            image_groups["customer"]["panel_kpis_customer"] = next(
                (img for img in customer_images if 'panel_kpis_customer.png' in img.lower()), None
            )
            image_groups["customer"]["inbound_NPS_evolution"] = next(
                (img for img in customer_images if 'inbound_nps_evolution.png' in img.lower()), None
            )
            image_groups["customer"]["outbound_NPS_evolution"] = next(
                (img for img in customer_images if 'outbound_nps_evolution.png' in img.lower()), None
            )
            image_groups["customer"]["inbound_NPS_byregion"] = next(
                (img for img in customer_images if 'inbound_nps_byregion.png' in img.lower()), None
            )
            image_groups["customer"]["outbound_NPS_byregion"] = next(
                (img for img in customer_images if 'outbound_nps_byregion.png' in img.lower()), None
            )
        
        # Group disruptions images
        disruptions_images = [img for img in image_paths if 'disruptions' in img.lower()]
        print(f"Found {len(disruptions_images)} disruptions images")
        if disruptions_images:
            image_groups["disruptions"]["panel_kpis_missconexions"] = next(
                (img for img in disruptions_images if 'panel_kpis_disruptions_missconexions.png' in img.lower()), None
            )
            image_groups["disruptions"]["panel_kpis_misshandling"] = next(
                (img for img in disruptions_images if 'panel_kpis_disruptions_misshandling.png' in img.lower()), None
            )
            image_groups["disruptions"]["inbound_cancelled_evolution"] = next(
                (img for img in disruptions_images if 'inbound_cancelled_evolution.png' in img.lower()), None
            )
            image_groups["disruptions"]["outbound_cancelled_evolution"] = next(
                (img for img in disruptions_images if 'outbound_cancelled_evolution.png' in img.lower()), None
            )
            image_groups["disruptions"]["inbound_cancelled_byregion"] = next(
                (img for img in disruptions_images if 'inbound_cancelled_byregion.png' in img.lower()), None
            )
            image_groups["disruptions"]["outbound_cancelled_byregion"] = next(
                (img for img in disruptions_images if 'outbound_cancelled_byregion.png' in img.lower()), None
            )
        
        # Group commercial images
        commercial_images = [img for img in image_paths if 'commercial' in img.lower()]
        print(f"Found {len(commercial_images)} commercial images")
        
        # DEBUG: Print all commercial image paths
        print("DEBUG: Commercial image paths:")
        for img in commercial_images:
            print(f"DEBUG: - {img}")
            
        if commercial_images:
            # DEBUG: Check the pattern matching for panel KPI images
            print("DEBUG: Testing panel KPI matches:")
            for img in commercial_images:
                if 'panel_kpis_commercial_last_reported.png' in img.lower():
                    print(f"DEBUG: MATCH for panel_kpis_commercial_last_reported.png: {img}")
                if 'panel_kpis_commercial_last_week.png' in img.lower():
                    print(f"DEBUG: MATCH for panel_kpis_commercial_last_week.png: {img}")
            
            image_groups["commercial"]["panel_kpis_commercial_last_reported"] = next(
                (img for img in commercial_images if 'panel_kpis_commercial_last_reported.png' in img.lower()), None
            )
            image_groups["commercial"]["panel_kpis_commercial_last_week"] = next(
                (img for img in commercial_images if 'panel_kpis_commercial_last_week.png' in img.lower()), None
            )
            image_groups["commercial"]["evolution_intakes_weekly_by_flight_month_last_reported"] = next(
                (img for img in commercial_images if 'evolution_intakes_weekly_by_flight_month_last_reported.png' in img.lower()), None
            )
            image_groups["commercial"]["evolution_intakes_by_salesdateregion_last_reported"] = next(
                (img for img in commercial_images if 'evolution_intakes_by_salesdateregion_last_reported.png' in img.lower()), None
            )
            image_groups["commercial"]["evolution_intakes_by_salesdatehaul_last_reported"] = next(
                (img for img in commercial_images if 'evolution_intakes_by_salesdatehaul_last_reported.png' in img.lower()), None
            )
            image_groups["commercial"]["evolution_intakes_weekly_by_flight_month_last_week"] = next(
                (img for img in commercial_images if 'evolution_intakes_weekly_by_flight_month_last_week.png' in img.lower()), None
            )
            image_groups["commercial"]["evolution_intakes_by_salesdateregion_last_week"] = next(
                (img for img in commercial_images if 'evolution_intakes_by_salesdateregion_last_week.png' in img.lower()), None
            )
            image_groups["commercial"]["evolution_intakes_by_salesdatehaul_last_week"] = next(
                (img for img in commercial_images if 'evolution_intakes_by_salesdatehaul_last_week.png' in img.lower()), None
            )
            image_groups["commercial"]["intakes_by_region_last_reported"] = next(
                (img for img in commercial_images if 'intakes_by_region_last_reported.png' in img.lower()), None
            )
            image_groups["commercial"]["intakes_by_region_last_week"] = next(
                (img for img in commercial_images if 'intakes_by_region_last_week.png' in img.lower()), None
            )
        
        return image_groups

if __name__ == "__main__":
    main() 