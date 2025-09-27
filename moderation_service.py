import asyncio
import json
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from openrouter_client import OpenRouterClient
from openrouter_config import OPENROUTER_CONFIG

logger = logging.getLogger(__name__)

class ModerationService:
    def __init__(self, db):
        self.db = db
        self.basic_keywords = self._load_basic_keywords()
        
    def _load_basic_keywords(self) -> List[str]:
        """Load basic inappropriate keywords for initial filtering"""
        return [
            # Obvious inappropriate content
            'fuck', 'shit', 'asshole', 'bitch', 'cunt', 'nigger', 'retard',
            'porn', 'porno', 'sex', 'xxx', 'adult', 'explicit',
            'hate', 'violence', 'kill', 'murder', 'suicide',
            'scam', 'fraud', 'phishing', 'malware', 'virus',
            # More subtle inappropriate terms
            'illegal', 'drugs', 'weapons', 'guns', 'explosives',
            'racist', 'sexist', 'homophobic', 'transphobic',
            'spam', 'advertisement', 'promotion', 'marketing'
        ]
    
    async def moderate_content(self, content_data: Dict) -> Dict:
        """
        Comprehensive content moderation with multi-level checks
        Returns moderation result with approval status and detailed feedback
        """
        try:
            # Level 1: Basic keyword filtering
            basic_result = self._basic_keyword_check(content_data)
            if not basic_result['approved']:
                await self._log_moderation_result(content_data, basic_result, 'basic')
                return basic_result
            
            # Level 2: AI-based context understanding
            ai_result = await self._ai_moderation_check(content_data)
            
            # Combine results
            final_result = {
                'approved': ai_result['approved'],
                'level': 'ai',
                'reasons': ai_result.get('reasons', []),
                'confidence': ai_result.get('confidence', 0),
                'suggested_changes': ai_result.get('suggested_changes', []),
                'moderation_notes': ai_result.get('moderation_notes', '')
            }
            
            await self._log_moderation_result(content_data, final_result, 'ai')
            return final_result
            
        except Exception as e:
            logger.error(f"Moderation error: {str(e)}")
            # Fallback to basic moderation if AI fails
            basic_result = self._basic_keyword_check(content_data)
            await self._log_moderation_result(content_data, basic_result, 'error_fallback')
            return basic_result
    
    def _basic_keyword_check(self, content_data: Dict) -> Dict:
        """Basic keyword-based moderation check"""
        flagged_content = []
        reasons = []
        
        # Check organization name
        name = content_data.get('name', '').lower()
        name_issues = self._check_text_for_inappropriate_content(name, 'organization name')
        if name_issues:
            flagged_content.extend(name_issues)
            reasons.append(f"Inappropriate content in organization name: {', '.join(name_issues)}")
        
        # Check description
        description = content_data.get('description', '').lower()
        desc_issues = self._check_text_for_inappropriate_content(description, 'description')
        if desc_issues:
            flagged_content.extend(desc_issues)
            reasons.append(f"Inappropriate content in description: {', '.join(desc_issues)}")
        
        # Check tags
        tags = content_data.get('tags', [])
        tag_issues = []
        for tag in tags:
            tag_lower = tag.lower().strip('# ')
            tag_issues.extend(self._check_text_for_inappropriate_content(tag_lower, f'tag "{tag}"'))
        if tag_issues:
            flagged_content.extend(tag_issues)
            reasons.append(f"Inappropriate content in tags: {', '.join(tag_issues)}")
        
        # Check position details
        positions = content_data.get('openPositions', [])
        position_issues = []
        for i, position in enumerate(positions):
            pos_title = position.get('title', '').lower()
            pos_desc = position.get('description', '').lower()
            pos_reqs = ', '.join(position.get('requirements', [])).lower()
            
            title_issues = self._check_text_for_inappropriate_content(pos_title, f'position {i+1} title')
            desc_issues = self._check_text_for_inappropriate_content(pos_desc, f'position {i+1} description')
            req_issues = self._check_text_for_inappropriate_content(pos_reqs, f'position {i+1} requirements')
            
            if title_issues or desc_issues or req_issues:
                position_issues.append(f"Position {i+1}: {', '.join(title_issues + desc_issues + req_issues)}")
        
        if position_issues:
            flagged_content.extend(position_issues)
            reasons.append(f"Inappropriate content in positions: {', '.join(position_issues)}")
        
        if flagged_content:
            return {
                'approved': False,
                'level': 'basic',
                'reasons': reasons,
                'flagged_content': flagged_content,
                'moderation_notes': 'Content flagged by basic keyword filter'
            }
        
        return {
            'approved': True,
            'level': 'basic',
            'reasons': ['Content passed basic moderation'],
            'moderation_notes': 'Basic moderation check passed'
        }
    
    def _check_text_for_inappropriate_content(self, text: str, context: str) -> List[str]:
        """Check text for inappropriate content and return list of issues"""
        if not text:
            return []
        
        issues = []
        text_lower = text.lower()
        
        # Check for basic keywords
        for keyword in self.basic_keywords:
            if re.search(rf'\b{re.escape(keyword)}\b', text_lower):
                issues.append(f"contains '{keyword}'")
        
        # Check for excessive capitalization (potential spam)
        if len(re.findall(r'[A-Z]{4,}', text)) > 2:
            issues.append("excessive capitalization (potential spam)")
        
        # Check for URL spam
        if len(re.findall(r'http[s]?://', text)) > 3:
            issues.append("excessive URLs (potential spam)")
        
        # Check for email harvesting patterns
        if len(re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)) > 2:
            issues.append("multiple email addresses (potential harvesting)")
        
        return issues
    
    async def _ai_moderation_check(self, content_data: Dict) -> Dict:
        """AI-based moderation using OpenRouter for context understanding"""
        try:
            async with OpenRouterClient() as client:
                # Prepare content for AI analysis
                analysis_text = self._prepare_content_for_ai_analysis(content_data)
                
                # AI moderation prompt
                moderation_prompt = f"""
                Analyze this organization content for appropriateness and compliance with community guidelines:

                {analysis_text}

                Please evaluate for:
                1. Inappropriate language, hate speech, or offensive content
                2. Spam, promotional content, or commercial advertising
                3. Illegal activities, drugs, weapons, or harmful content
                4. Personal information harvesting or privacy violations
                5. Misleading or deceptive information

                Return JSON with:
                - approved: boolean (true if content is appropriate)
                - confidence: number (0-100 confidence in assessment)
                - reasons: array of strings (specific issues found, empty if approved)
                - suggested_changes: array of strings (suggested modifications if not approved)
                - moderation_notes: string (overall assessment notes)

                If content is borderline but not clearly inappropriate, consider approving with warnings.
                """
                
                # Query AI for moderation analysis
                response = await client.query_model("deepseek", [
                    {
                        "role": "system", 
                        "content": "You are a content moderator. Analyze content for appropriateness and return valid JSON only."
                    },
                    {
                        "role": "user", 
                        "content": moderation_prompt
                    }
                ])
                
                # Parse AI response
                ai_result = self._parse_ai_moderation_response(response)
                
                return ai_result
                
        except Exception as e:
            logger.error(f"AI moderation failed: {str(e)}")
            # Fallback to basic approval if AI fails
            return {
                'approved': True,
                'confidence': 50,
                'reasons': ['AI moderation temporarily unavailable'],
                'suggested_changes': [],
                'moderation_notes': 'AI moderation failed, content approved with caution'
            }
    
    def _prepare_content_for_ai_analysis(self, content_data: Dict) -> str:
        """Prepare organization content for AI analysis"""
        analysis_parts = []
        
        analysis_parts.append(f"Organization Name: {content_data.get('name', 'N/A')}")
        analysis_parts.append(f"Description: {content_data.get('description', 'N/A')}")
        
        if content_data.get('tags'):
            analysis_parts.append(f"Tags: {', '.join(content_data.get('tags', []))}")
        
        if content_data.get('website'):
            analysis_parts.append(f"Website: {content_data.get('website')}")
        
        # Analyze positions
        positions = content_data.get('openPositions', [])
        if positions:
            analysis_parts.append("\nOpen Positions:")
            for i, position in enumerate(positions):
                analysis_parts.append(f"  Position {i+1}:")
                analysis_parts.append(f"    Title: {position.get('title', 'N/A')}")
                analysis_parts.append(f"    Description: {position.get('description', 'N/A')}")
                if position.get('requirements'):
                    analysis_parts.append(f"    Requirements: {', '.join(position.get('requirements', []))}")
        
        return "\n".join(analysis_parts)
    
    def _parse_ai_moderation_response(self, response: str) -> Dict:
        """Parse AI moderation response and extract JSON result"""
        try:
            # Extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end != -1:
                json_str = response[json_start:json_end]
                result = json.loads(json_str)
                
                # Validate required fields
                if 'approved' not in result:
                    result['approved'] = True  # Default to approve if unsure
                
                if 'confidence' not in result:
                    result['confidence'] = 50  # Medium confidence
                
                if 'reasons' not in result:
                    result['reasons'] = []
                
                if 'suggested_changes' not in result:
                    result['suggested_changes'] = []
                
                if 'moderation_notes' not in result:
                    result['moderation_notes'] = 'AI moderation completed'
                
                return result
            else:
                raise ValueError("No JSON found in AI response")
                
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse AI moderation response: {str(e)}")
            return {
                'approved': True,
                'confidence': 50,
                'reasons': ['AI response parsing failed'],
                'suggested_changes': [],
                'moderation_notes': 'AI moderation response could not be parsed, content approved with caution'
            }
    
    async def _log_moderation_result(self, content_data: Dict, result: Dict, source: str):
        """Log moderation results to Firestore for audit purposes"""
        try:
            moderation_log = {
                'timestamp': datetime.now(),
                'organization_name': content_data.get('name', 'Unknown'),
                'organization_data': {
                    'name': content_data.get('name'),
                    'description_preview': content_data.get('description', '')[:200] + '...' if content_data.get('description') else '',
                    'tags_count': len(content_data.get('tags', [])),
                    'positions_count': len(content_data.get('openPositions', []))
                },
                'moderation_result': result,
                'moderation_source': source,
                'approved': result.get('approved', False),
                'reasons': result.get('reasons', []),
                'confidence': result.get('confidence', 0)
            }
            
            # Store in moderation_logs collection
            log_ref = self.db.collection('moderation_logs').document()
            log_ref.set(moderation_log)
            
            logger.info(f"Moderation log created: {log_ref.id} - Approved: {result.get('approved')}")
            
        except Exception as e:
            logger.error(f"Failed to log moderation result: {str(e)}")
    
    def get_moderation_stats(self) -> Dict:
        """Get moderation statistics (placeholder for future implementation)"""
        return {
            'total_moderated': 0,
            'approved_count': 0,
            'rejected_count': 0,
            'ai_moderation_count': 0,
            'basic_moderation_count': 0
        }

# Helper function for backward compatibility
def moderate_organization(data: Dict) -> Dict:
    """Basic moderation function for existing code compatibility"""
    service = ModerationService(None)  # No db for basic function
    basic_result = service._basic_keyword_check(data)
    return basic_result