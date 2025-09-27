import aiohttp
import asyncio
import json
import logging
from typing import Dict, List, Optional
from openrouter_config import OPENROUTER_CONFIG, SYSTEM_PROMPTS

logger = logging.getLogger(__name__)

class OpenRouterClient:
    def __init__(self):
        self.config = OPENROUTER_CONFIG
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers={
            "Authorization": f"Bearer {self.config['api_key']}",
            "HTTP-Referer": "https://depanku.com",
            "X-Title": "Depanku AI Analysis",
            "Content-Type": "application/json"
        })
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def query_model(self, model_name: str, messages: List[Dict], temperature: float = 0.7) -> str:
        """Query a specific model with the given messages"""
        payload = {
            "model": self.config["models"][model_name],
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 1000
        }
        
        try:
            async with self.session.post(
                f"{self.config['base_url']}/chat/completions",
                json=payload,
                timeout=self.config["timeout"]
            ) as response:
                response.raise_for_status()
                result = await response.json()
                return result["choices"][0]["message"]["content"]
                
        except asyncio.TimeoutError:
            logger.error(f"OpenRouter timeout for {model_name}")
            raise Exception(f"OpenRouter API timeout for {model_name}")
        except aiohttp.ClientError as e:
            logger.error(f"OpenRouter client error for {model_name}: {str(e)}")
            raise Exception(f"OpenRouter API error for {model_name}: {str(e)}")
        except Exception as e:
            logger.error(f"OpenRouter API error for {model_name}: {str(e)}")
            raise Exception(f"OpenRouter API error for {model_name}: {str(e)}")
    
    async def query_persona(self, persona: str, user_message: str, temperature: float = 0.7) -> str:
        """Query a specific AI persona with the system prompt"""
        messages = [
            {"role": "system", "content": SYSTEM_PROMPTS[persona]},
            {"role": "user", "content": user_message}
        ]
        return await self.query_model(persona, messages, temperature)
    
    async def check_consensus(self, responses: Dict[str, str]) -> Dict:
        """Check if the AI personas have reached consensus"""
        consensus_prompt = f"""
        Analyze these responses from different AI personas and determine if they have reached consensus:
        
        {json.dumps(responses, indent=2)}
        
        Return JSON with:
        - consensus: boolean (true if all personas agree on the core recommendation)
        - recommendation: string (the agreed-upon recommendation if consensus reached)
        - reasoning: string (explanation of why consensus was or wasn't reached)
        """
        
        try:
            result = await self.query_model("deepseek", [
                {"role": "system", "content": "You are a consensus analyzer. Return valid JSON only."},
                {"role": "user", "content": consensus_prompt}
            ])
            
            # Extract JSON from the response
            json_start = result.find('{')
            json_end = result.rfind('}') + 1
            if json_start != -1 and json_end != -1:
                json_str = result[json_start:json_end]
                return json.loads(json_str)
            else:
                return {"consensus": False, "recommendation": "", "reasoning": "Could not parse consensus check result"}
                
        except Exception as e:
            logger.error(f"Consensus check failed: {str(e)}")
            return {"consensus": False, "recommendation": "", "reasoning": f"Consensus check error: {str(e)}"}

class CostManager:
    def __init__(self):
        self.token_usage = {}
    
    def track_usage(self, model_name: str, prompt_tokens: int, completion_tokens: int):
        """Track token usage for cost calculation"""
        cost = self.calculate_cost(model_name, prompt_tokens, completion_tokens)
        if model_name not in self.token_usage:
            self.token_usage[model_name] = {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_cost": 0.0
            }
        
        self.token_usage[model_name]["prompt_tokens"] += prompt_tokens
        self.token_usage[model_name]["completion_tokens"] += completion_tokens
        self.token_usage[model_name]["total_cost"] += cost
        
        logger.info(f"Token usage for {model_name}: {prompt_tokens} prompt + {completion_tokens} completion = ${cost:.6f}")
    
    def calculate_cost(self, model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate cost based on OpenRouter pricing"""
        pricing = {
            "deepseek": 0.0001,  # per token
            "maverick": 0.00015,
            "qwen": 0.00012,
            "glm": 0.00013,
            "grok": 0.00014
        }
        total_tokens = prompt_tokens + completion_tokens
        return total_tokens * pricing.get(model_name, 0.0001)
    
    def get_total_cost(self) -> float:
        """Get total cost across all models"""
        return sum(usage["total_cost"] for usage in self.token_usage.values())
    
    def enforce_limits(self, user_id: str, db) -> bool:
        """Check if user has exceeded free tier limits"""
        try:
            # Get user's analysis count from Firestore
            analyses_ref = db.collection('ai_analyses')
            query = analyses_ref.where('userId', '==', user_id)
            user_analyses = len(query.get())
            
            # Get user's subscription plan
            user_ref = db.collection('users').document(user_id)
            user_data = user_ref.get()
            
            if user_data.exists:
                user_dict = user_data.to_dict()
                subscription = user_dict.get('subscription', {})
                plan = subscription.get('plan', 'free')
                
                if plan == 'premium':
                    return True
                else:
                    return user_analyses < 3  # Free tier limit
            
            return False
            
        except Exception as e:
            logger.error(f"Error enforcing limits: {str(e)}")
            return False