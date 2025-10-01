# --- app/services/openai_service.py ---
import logging
import json
import re
from openai import OpenAI
from flask import current_app

logger = logging.getLogger(__name__)

# System Prompts can be centralized here
SYSTEM_PROMPTS = {
    "deepseek": "You are an experienced university admissions officer...",
    "maverick": "You are a current high school/college student...",
    "qwen": "You are a seasoned HR manager...",
    "glm": "You are a philosophical advisor...",
    "grok": "You are a critical analyst...",
    "moderator": "You are a content moderator. Analyze content and return valid JSON only.",
    "socratic_questioner": "You are a helpful assistant conducting a Socratic dialogue...",
    "summarizer": "You are an expert at synthesizing conversations into concise goals."
}

class OpenAIService:
    """A wrapper for the OpenAI client, configured for OpenRouter."""
    
    def __init__(self):
        self.api_key = current_app.config.get('OPENROUTER_API_KEY')
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is not configured.")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=current_app.config.get('OPENROUTER_BASE_URL'),
            default_headers={
                "HTTP-Referer": "https://depanku.id",
                "X-Title": "Depanku AI",
            },
            timeout=45.0,
            max_retries=2,
        )
        self.models = current_app.config.get('OPENROUTER_MODELS', {})

    def query_model(self, model_name: str, messages: list, temperature: float = 0.7, max_tokens: int = 2048, is_json=False):
        """Queries a specific model. Designed to be run inside a Celery task."""
        model_id = self.models.get(model_name)
        if not model_id:
            raise ValueError(f"Model '{model_name}' not configured in OPENROUTER_MODELS.")

        try:
            params = {
                "model": model_id,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if is_json:
                params["response_format"] = {"type": "json_object"}

            completion = self.client.chat.completions.create(**params)
            content = completion.choices[0].message.content
            
            if is_json:
                return self._parse_json_from_response(content)
            return content

        except Exception as e:
            logger.error(f"API call to model {model_id} failed: {e}")
            raise

    def query_persona(self, persona: str, user_message: str) -> str:
        """Queries a specific persona using its pre-defined system prompt."""
        system_prompt = SYSTEM_PROMPTS.get(persona)
        if not system_prompt:
            raise ValueError(f"Persona '{persona}' is not configured.")
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        return self.query_model(persona, messages)

    def _parse_json_from_response(self, response_text: str) -> dict:
        """Robustly extracts a JSON object from a string."""
        # Find the first '{' and the last '}'
        start = response_text.find('{')
        end = response_text.rfind('}')
        if start != -1 and end != -1 and end > start:
            json_str = response_text[start:end+1]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                logger.error(f"Failed to decode JSON from substring: {json_str}")
        
        logger.error(f"No valid JSON object found in AI response: {response_text}")
        raise ValueError("AI response did not contain a valid JSON object.")