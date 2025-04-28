from abc import ABC, abstractmethod
from typing import Dict, Any, List, Union
import boto3
import json
import os
from datetime import datetime
import copy

class BaseAgent(ABC):
    """Base class for all specialized agents in the system."""
    
    def __init__(self, model_arn: str = None):
        """Initialize the agent with Bedrock client and model configuration."""
        self.bedrock = boto3.client('bedrock-runtime')
        self.model_arn = model_arn or os.getenv('MODEL_ARN')
        if not self.model_arn:
            raise ValueError("MODEL_ARN environment variable is required")
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the system prompt for the agent. Should be overridden by subclasses."""
        return """Eres un agente especializado en el análisis de dashboards para aerolíneas.

IMPORTANTE: NO inventes NINGÚN dato, fecha o cifra. Trabaja exclusivamente con la información proporcionada. 
Si algún dato no está disponible, indícalo claramente pero NUNCA lo sustituyas con valores inventados."""
    
    @abstractmethod
    def analyze_image(self, image_path: Union[str, List[str], Dict[str, Any]], system_prompt: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analyze one or multiple images and return the results.
        
        Args:
            image_path: Either a single image path as string, a list of image paths, or a dictionary of image paths
            system_prompt: Optional system prompt to use instead of the default
            
        Returns:
            Dict containing the analysis results
        """
        pass
    
    # Original invoke_model without temperature and debugging
    def invoke_model(self, messages: List[Dict[str, Any]], system_prompt: str = None) -> str:
        """Invoke the Bedrock model with the given messages."""
        try:
            # Create a deep copy of messages for API request
            messages_for_api = copy.deepcopy(messages)
            for msg in messages_for_api:
                if 'content' in msg:
                    # This loop expects msg['content'] to be a list
                    for content_item in msg['content']:
                         # This expects content_item to be a dict
                        if content_item.get('type') == 'image' and 'image_path' in content_item:
                            # Remove local path info before sending to API
                            del content_item['image_path'] 
            
            # Prepare the request body
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4096,
                "messages": messages_for_api
            }
            
            # Add system prompt if provided
            if system_prompt:
                request_body["system"] = system_prompt
            
            # Invoke the model (Using hardcoded Sonnet ID from original version)
            response = self.bedrock.invoke_model(
                modelId="anthropic.claude-3-sonnet-20240229-v1:0", 
                body=json.dumps(request_body)
            )
            
            # Parse the response (Original parsing logic)
            response_body = json.loads(response.get('body').read())
            # Basic extraction assuming response structure is good
            content_list = response_body.get('content', [])
            if content_list and isinstance(content_list, list) and len(content_list) > 0 and isinstance(content_list[0], dict):
                 return content_list[0].get('text', '')
            else:
                # Handle cases where content might be missing or malformed
                print(f"⚠️ Unexpected content structure in response: {response_body}")
                return "" # Return empty string or handle as error
            
        except Exception as e:
            print(f"Error invoking model: {e}")
            # Re-raising the exception might be better for debugging flow control
            raise
    
    def save_analysis(self, analysis: Dict[str, Any], date: str) -> str:
        """Save the analysis results to a file."""
        # Create date-specific directory if it doesn't exist
        date_dir = os.path.join('reports', date)
        os.makedirs(date_dir, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{self.__class__.__name__.lower()}_analysis_{timestamp}.json"
        filepath = os.path.join(date_dir, filename)
        
        # Save the analysis
        with open(filepath, 'w') as f:
            json.dump(analysis, f, indent=2)
        
        return filepath 