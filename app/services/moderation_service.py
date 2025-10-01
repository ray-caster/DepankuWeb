import asyncio
import json
import logging
import re
from datetime import datetime
from typing import Dict, List

from .openrouter_client import OpenRouterClient

logger = logging.getLogger(__name__)

class ModerationService:
    def __init__(self, db):
        self.db = db
        self.basic_keywords = self._load_basic_keywords()
        
    def _load_basic_keywords(self) -> List[str]:
        """Load basic inappropriate keywords for initial filtering"""
        return [
            'fuck', 'shit', 'asshole', 'bitch', 'cunt', 'nigger', 'retard',
            'porn', 'sex', 'xxx', 'adult', 'explicit',
            'hate', 'violence', 'kill', 'murder', 'suicide',
            'scam', 'fraud', 'phishing', 'malware', 'virus',
            'illegal', 'drugs', 'weapons', 'guns', 'explosives',
            'racist', 'sexist', 'homophobic', 'transphobic',
            'spam', 'advertisement', 'promotion', 'marketing'
        ]
    
    async def moderate_content(self, content_data: Dict) -> Dict:
        """Comprehensive content moderation with multi-level checks."""
        try:
            basic_result = self._basic_keyword_check(content_data)
            if not basic_result['approved']:
                await self._log_moderation_result(content_data, basic_result, 'basic')
                return basic_result
            
            ai_result = await self._ai_moderation_check(content_data)
            await self._log_moderation_result(content_data, ai_result, 'ai')
            return ai_result
            
        except Exception as e:
            logger.error(f"Moderation error: {str(e)}")
            basic_result = self._basic_keyword_check(content_data)
            await self._log_moderation_result(content_data, basic_result, 'error_fallback')
            return basic_result
    
    def _basic_keyword_check(self, content_data: Dict) -> Dict:
        """Basic keyword-based moderation check"""
        reasons = []
        text_to_check = [
            content_data.get('name', ''),
            content_data.get('description', ''),
            *content_data.get('tags', [])
        ]
        
        for text in text_to_check:
            issues = self._check_text_for_inappropriate_content(text)
            if issues:
                reasons.extend(issues)
        
        if reasons:
            return {'approved': False, 'level': 'basic', 'reasons': list(set(reasons))}
        return {'approved': True, 'level': 'basic'}
    
    def _check_text_for_inappropriate_content(self, text: str) -> List[str]:
        """Check a single string for inappropriate content."""
        if not text: return []
        issues = []
        text_lower = text.lower()
        for keyword in self.basic_keywords:
            if re.search(rf'\b{re.escape(keyword)}\b', text_lower):
                issues.append(f"Contains blocked keyword: '{keyword}'")
        return issues
    
    async def _ai_moderation_check(self, content_data: Dict) -> Dict:
        """AI-based moderation for context understanding."""
        try:
            async with OpenRouterClient() as client:
                analysis_text = json.dumps(content_data, indent=2)
                moderation_prompt = f"""
                Analyze this organization content for appropriateness on an educational platform for students.
                Return JSON with: approved (boolean), confidence (0-100), reasons (array of strings if not approved).
                Content: {analysis_text}
                """
                
                response = await client.query_model("deepseek", [
                    {"role": "system", "content": "You are a content moderator. Analyze content and return valid JSON only."},
                    {"role": "user", "content": moderation_prompt}
                ])
                
                return self._parse_ai_moderation_response(response)
        except Exception as e:
            logger.error(f"AI moderation failed: {str(e)}")
            return {'approved': True, 'confidence': 50, 'reasons': ['AI moderation temporarily unavailable']}
    
    def _parse_ai_moderation_response(self, response: str) -> Dict:
        """Parse AI moderation response and extract JSON result."""
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(0))
                if 'approved' in result and 'confidence' in result:
                    return result
            raise ValueError("No valid JSON found in AI response")
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse AI moderation response: {e}")
            return {'approved': True, 'confidence': 50, 'reasons': ['AI response parsing failed']}
    
    async def _log_moderation_result(self, content_data: Dict, result: Dict, source: str):
        """Log moderation results to Firestore for audit purposes."""
        if not self.db: return
        try:
            log_ref = self.db.collection('moderation_logs').document()
            log_ref.set({
                'timestamp': datetime.now(),
                'organization_name': content_data.get('name', 'Unknown'),
                'moderation_result': result,
                'moderation_source': source
            })
        except Exception as e:
            logger.error(f"Failed to log moderation result: {str(e)}")