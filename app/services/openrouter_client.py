import aiohttp
import asyncio
import json
import logging
from typing import Dict, List

from openrouter_config import OPENROUTER_CONFIG, SYSTEM_PROMPTS

logger = logging.getLogger(__name__)

class OpenRouterClient:
    def __init__(self):
        self.config = OPENROUTER_CONFIG
        self.api_key = self.config.get('api_key')
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is not configured. Please set the environment variable.")
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers={
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://depanku.id", # Replace with your actual domain
            "X-Title": "Depanku AI",
            "Content-Type": "application/json"
        })
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def query_model(self, model_name: str, messages: List[Dict], temperature: float = 0.7) -> str:
        """Query a specific model with retry logic."""
        model_id = self.config["models"].get(model_name)
        if not model_id:
            raise ValueError(f"Model '{model_name}' not configured.")

        payload = {
            "model": model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 1500
        }
        
        last_exception = None
        for attempt in range(self.config["max_retries"]):
            try:
                async with self.session.post(
                    f"{self.config['base_url']}/chat/completions",
                    json=payload,
                    timeout=self.config["timeout"]
                ) as response:
                    response.raise_for_status()
                    result = await response.json()
                    return result["choices"][0]["message"]["content"]
            except (asyncio.TimeoutError, aiohttp.ClientError) as e:
                logger.warning(f"OpenRouter attempt {attempt + 1} failed for {model_name}: {e}")
                last_exception = e
                if attempt == self.config["max_retries"] - 1:
                    raise e
                await asyncio.sleep(2 ** attempt) # Exponential backoff
        raise last_exception or aiohttp.ClientError("API call failed after multiple retries.")


    async def query_persona(self, persona: str, user_message: str, temperature: float = 0.7) -> str:
        """Query a specific AI persona with its system prompt."""
        system_prompt = SYSTEM_PROMPTS.get(persona)
        if not system_prompt:
            raise ValueError(f"Persona '{persona}' not configured.")
            
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        return await self.query_model(persona, messages, temperature)
    
    async def check_consensus(self, responses: Dict[str, str]) -> Dict:
        """Check if the AI personas have reached consensus."""
        consensus_prompt = f"""
        Analyze these responses from different AI personas and determine if they have reached consensus.
        {json.dumps(responses, indent=2)}
        Return JSON with: consensus (boolean), recommendation (string), reasoning (string).
        """
        
        try:
            result_str = await self.query_model("deepseek", [
                {"role": "system", "content": "You are a consensus analyzer. Return valid JSON only."},
                {"role": "user", "content": consensus_prompt}
            ])
            # Find JSON in the response, as models can sometimes add extra text
            json_match = result_str[result_str.find('{'):result_str.rfind('}')+1]
            return json.loads(json_match)
        except Exception as e:
            logger.error(f"Consensus check failed: {str(e)}")
            return {"consensus": False, "recommendation": "", "reasoning": f"Consensus check error: {str(e)}"}

class CostManager:
    def __init__(self):
        self.token_usage = {}
        # Example pricing per 1M tokens (input/output)
        self.pricing = {
            "deepseek": (0.14, 0.28),
            "maverick": (3.0, 15.0),
            "qwen": (1.0, 2.0),
            "glm": (0.7, 0.7),
            "grok": (0.7, 0.7) # Placeholder
        }
    
    def track_usage(self, model_name: str, prompt_tokens: int, completion_tokens: int):
        # This would be implemented if the API returned token counts
        pass

    def enforce_limits(self, user_id: str, db) -> bool:
        """Check if user has exceeded free tier limits."""
        if not db: return False
        try:
            user_ref = db.collection('users').document(user_id)
            user_doc = user_ref.get()
            
            if user_doc.exists:
                user_dict = user_doc.to_dict()
                subscription = user_dict.get('subscription', {})
                if subscription.get('plan', 'free') == 'premium':
                    return True
                return subscription.get('aiAnalysesRemaining', 0) > 0
            return False
        except Exception as e:
            logger.error(f"Error enforcing limits for user {user_id}: {str(e)}")
            return False