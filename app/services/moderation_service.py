# --- app/services/moderation_service.py (CORRECTED) ---

import logging
import re
from datetime import datetime
from typing import Dict, List

from .openai_service import OpenAIService # Correct import

logger = logging.getLogger(__name__)

class ModerationService:
    # MODIFIED: Accepts the new openai_service
    def __init__(self, db_client, openai_service: OpenAIService):
        self.db = db_client
        self.openai_service = openai_service
        self.basic_keywords = self._load_basic_keywords()

    def _load_basic_keywords(self) -> List[str]:
        return [
            'fuck', 'shit', 'asshole', 'bitch', 'cunt', 'nigger', 'retard',
            'porn', 'sex', 'xxx', 'adult', 'explicit', 'hate', 'violence', 
            'kill', 'murder', 'suicide', 'scam', 'fraud', 'phishing', 'malware',
            'illegal', 'drugs', 'weapons', 'guns', 'spam', 'advertisement'
        ]

    # MODIFIED: Removed async/await, as this now runs in a Celery worker
    def moderate_content(self, content_data: Dict) -> Dict:
        """Synchronous content moderation for use in Celery tasks."""
        try:
            # First, run a quick keyword check.
            basic_result = self._basic_keyword_check(content_data)
            if not basic_result['approved']:
                self._log_moderation_result(content_data, basic_result, 'basic_keyword_filter')
                return basic_result
            
            # If basic check passes, proceed to AI moderation.
            ai_result = self._ai_moderation_check(content_data)
            self._log_moderation_result(content_data, ai_result, 'ai_context_filter')
            return ai_result
            
        except Exception as e:
            logger.error(f"Moderation service failed: {e}", exc_info=True)
            # As a fallback, if AI fails, trust the basic check.
            # You could also choose to default to 'rejected' for safety.
            fallback_result = {'approved': True, 'level': 'fallback', 'reason': 'AI moderation service failed, passed basic filter.'}
            self._log_moderation_result(content_data, fallback_result, 'error_fallback')
            return fallback_result

    def _basic_keyword_check(self, content_data: Dict) -> Dict:
        """Performs a simple, fast keyword check on key text fields."""
        reasons = set()
        text_to_check = [
            str(content_data.get('name', '')),
            str(content_data.get('description', '')),
        ]
        if content_data.get('tags'):
            text_to_check.extend(content_data['tags'])

        for text in text_to_check:
            if not text: continue
            text_lower = text.lower()
            for keyword in self.basic_keywords:
                # Use word boundaries to avoid matching parts of words
                if re.search(rf'\b{re.escape(keyword)}\b', text_lower):
                    reasons.add(f"Contains blocked keyword: '{keyword}'")
        
        if reasons:
            return {'approved': False, 'level': 'basic', 'reasons': list(reasons)}
        return {'approved': True, 'level': 'basic'}
    
    # MODIFIED: Removed async/await
    def _ai_moderation_check(self, content_data: Dict) -> Dict:
        """Uses a large language model for contextual moderation."""
        analysis_text = f"Name: {content_data.get('name')}\nDescription: {content_data.get('description')}"
        
        moderation_prompt = f"""
        Analyze the following content for an educational platform for students.
        The content must be free of hate speech, explicit material, scams, violence, and illegal activities.
        Respond ONLY with a valid JSON object with three keys:
        1. "approved": a boolean (true or false).
        2. "confidence": an integer between 0 and 100.
        3. "reasons": an array of strings explaining the decision if not approved.

        Content to analyze:
        ---
        {analysis_text}
        ---
        """
        messages = [
            {"role": "system", "content": "You are a content moderator. Your only output must be a valid JSON object."},
            {"role": "user", "content": moderation_prompt}
        ]
        
        try:
            # Use the synchronous query_model method with JSON mode
            result = self.openai_service.query_model("deepseek", messages, is_json=True)
            # Add level for consistency
            result['level'] = 'ai'
            return result
        except Exception as e:
            logger.error(f"AI moderation query failed: {e}")
            # Fallback if the AI call itself fails
            return {'approved': True, 'confidence': 0, 'reasons': ['AI moderation check failed to execute.'], 'level': 'ai_error'}

    # MODIFIED: Removed async/await
    def _log_moderation_result(self, content_data: Dict, result: Dict, source: str):
        """Logs moderation results to Firestore for auditing."""
        if not self.db: return
        try:
            log_ref = self.db.collection('moderation_logs').document()
            log_ref.set({
                'timestamp': datetime.now(),
                'organization_name': content_data.get('name', 'N/A'),
                'moderation_result': result,
                'source': source,
                'ownerId': content_data.get('ownerId')
            })
        except Exception as e:
            logger.error(f"Failed to log moderation result: {e}")