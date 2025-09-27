import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from openrouter_client import OpenRouterClient, CostManager
from openrouter_config import SYSTEM_PROMPTS

logger = logging.getLogger(__name__)

class AIAnalysisService:
    def __init__(self, db):
        self.db = db
        self.cost_manager = CostManager()
        
    async def socratic_questioning(self, user_id: str, initial_goal: str) -> Dict:
        """Conduct Socratic questioning to refine user goals"""
        questions = [
            "What specific skills or experiences are you hoping to gain?",
            "What time commitment can you realistically manage?",
            "What are your top priorities for this opportunity?",
            "What type of environment do you thrive in?",
            "What potential challenges are you willing to overcome?"
        ]
        
        session_data = {
            "userId": user_id,
            "goal": initial_goal,
            "questions": [],
            "userResponses": [],
            "status": "in_progress",
            "createdAt": datetime.now(),
            "updatedAt": datetime.now()
        }
        
        # Create AI session document
        session_ref = self.db.collection('ai_sessions').document()
        session_id = session_ref.id
        session_data['id'] = session_id
        session_ref.set(session_data)
        
        refined_goal = initial_goal
        for i, question in enumerate(questions):
            # Store question in session
            session_ref.update({
                f'questions.{i}': question,
                'updatedAt': datetime.now()
            })
            
            # In a real implementation, this would wait for user response via WebSocket/API
            # For now, we'll simulate user responses
            user_response = f"Response to: {question}"
            
            session_ref.update({
                f'userResponses.{i}': user_response,
                'updatedAt': datetime.now()
            })
            
            # Refine goal based on response (simplified)
            refined_goal += f" | {user_response}"
        
        session_ref.update({
            'goal': refined_goal,
            'status': 'questioning_completed',
            'updatedAt': datetime.now()
        })
        
        return {
            "sessionId": session_id,
            "refinedGoal": refined_goal,
            "questions": questions,
            "userResponses": [f"Response to: {q}" for q in questions]  # Simulated responses
        }
    
    async def conduct_round_table_debate(self, session_id: str, refined_goal: str) -> Dict:
        """Conduct round table debate with all AI personas"""
        personas = ["deepseek", "maverick", "qwen", "glm"]
        responses = {}
        
        async with OpenRouterClient() as client:
            for persona in personas:
                try:
                    response = await client.query_persona(
                        persona, 
                        f"Analyze this opportunity and provide recommendations: {refined_goal}"
                    )
                    responses[persona] = response
                    
                    # Update session with persona response
                    session_ref = self.db.collection('ai_sessions').document(session_id)
                    session_ref.update({
                        f'personas.{persona}.response': response,
                        f'personas.{persona}.timestamp': datetime.now(),
                        'updatedAt': datetime.now()
                    })
                    
                except Exception as e:
                    logger.error(f"Error querying {persona}: {str(e)}")
                    responses[persona] = f"Error: {str(e)}"
        
        return responses
    
    async def devil_advocate_analysis(self, session_id: str, responses: Dict[str, str]) -> str:
        """Get devil's advocate critique of the responses"""
        async with OpenRouterClient() as client:
            try:
                critique = await client.query_persona(
                    "grok",
                    f"Critique these analyses and identify potential flaws:\n{json.dumps(responses, indent=2)}"
                )
                
                # Update session with critique
                session_ref = self.db.collection('ai_sessions').document(session_id)
                session_ref.update({
                    'personas.grok.critique': critique,
                    'personas.grok.timestamp': datetime.now(),
                    'updatedAt': datetime.now()
                })
                
                return critique
            except Exception as e:
                logger.error(f"Error in devil's advocate analysis: {str(e)}")
                return f"Devil's advocate analysis failed: {str(e)}"
    
    async def build_consensus(self, session_id: str, responses: Dict[str, str], 
                           critique: str, max_iterations: int = 3) -> Dict:
        """Build consensus among AI personas through iterative debate"""
        iteration = 0
        consensus_reached = False
        current_responses = responses
        
        async with OpenRouterClient() as client:
            while not consensus_reached and iteration < max_iterations:
                # Have models respond to critique and each other
                revised_responses = {}
                for persona in current_responses.keys():
                    try:
                        revised_response = await client.query_persona(
                            persona,
                            f"""Previous responses: {json.dumps(current_responses)}
                            Critique: {critique}
                            Revise your analysis considering these perspectives and work towards consensus."""
                        )
                        revised_responses[persona] = revised_response
                        
                        # Update session
                        session_ref = self.db.collection('ai_sessions').document(session_id)
                        session_ref.update({
                            f'personas.{persona}.response': revised_response,
                            f'personas.{persona}.timestamp': datetime.now(),
                            'updatedAt': datetime.now()
                        })
                        
                    except Exception as e:
                        logger.error(f"Error in consensus iteration {iteration} for {persona}: {str(e)}")
                        revised_responses[persona] = current_responses[persona]
                
                # Check for consensus
                consensus_check = await client.check_consensus(revised_responses)
                
                if consensus_check.get("consensus", False):
                    consensus_reached = True
                    final_recommendation = consensus_check.get("recommendation", "")
                    reasoning = consensus_check.get("reasoning", "")
                    
                    # Update session with consensus
                    session_ref = self.db.collection('ai_sessions').document(session_id)
                    session_ref.update({
                        'consensus.reached': True,
                        'consensus.finalRecommendation': final_recommendation,
                        'consensus.reasoning': reasoning,
                        'consensus.timestamp': datetime.now(),
                        'status': 'completed',
                        'updatedAt': datetime.now()
                    })
                    
                    return {
                        "consensus": True,
                        "recommendation": final_recommendation,
                        "reasoning": reasoning,
                        "iterations": iteration + 1
                    }
                else:
                    current_responses = revised_responses
                    iteration += 1
        
        # If no consensus after max iterations, create compromise recommendation
        compromise = await self.create_compromise_recommendation(current_responses)
        
        session_ref = self.db.collection('ai_sessions').document(session_id)
        session_ref.update({
            'consensus.reached': False,
            'consensus.finalRecommendation': compromise,
            'consensus.reasoning': 'Compromise recommendation after maximum iterations',
            'consensus.timestamp': datetime.now(),
            'status': 'completed',
            'updatedAt': datetime.now()
        })
        
        return {
            "consensus": False,
            "recommendation": compromise,
            "reasoning": "Compromise recommendation after maximum debate iterations",
            "iterations": iteration
        }
    
    async def create_compromise_recommendation(self, responses: Dict[str, str]) -> str:
        """Create a compromise recommendation when consensus isn't reached"""
        async with OpenRouterClient() as client:
            try:
                compromise_prompt = f"""
                Create a balanced compromise recommendation from these conflicting analyses:
                
                {json.dumps(responses, indent=2)}
                
                Provide a comprehensive recommendation that incorporates the best aspects of each perspective.
                """
                
                return await client.query_model("deepseek", [
                    {"role": "system", "content": "You are a mediator creating balanced recommendations from conflicting perspectives."},
                    {"role": "user", "content": compromise_prompt}
                ])
            except Exception as e:
                logger.error(f"Error creating compromise recommendation: {str(e)}")
                return "Unable to create compromise recommendation due to technical issues."
    
    async def complete_ai_analysis(self, user_id: str, session_id: str):
        """Complete the AI analysis and update user's analysis count"""
        try:
            # Update user's analysis count
            user_ref = self.db.collection('users').document(user_id)
            user_data = user_ref.get()
            
            if user_data.exists:
                user_dict = user_data.to_dict()
                subscription = user_dict.get('subscription', {})
                plan = subscription.get('plan', 'free')
                
                if plan == 'free':
                    remaining = subscription.get('aiAnalysesRemaining', 3)
                    if remaining > 0:
                        user_ref.update({
                            'subscription.aiAnalysesRemaining': remaining - 1,
                            'updatedAt': datetime.now()
                        })
                
                # Create analysis record
                analysis_ref = self.db.collection('ai_analyses').document()
                analysis_ref.set({
                    'userId': user_id,
                    'sessionId': session_id,
                    'type': 'career_guidance',
                    'cost': 1,  # 1 credit per analysis
                    'status': 'success',
                    'createdAt': datetime.now(),
                    'modelUsed': 'multi-model-debate'
                })
                
        except Exception as e:
            logger.error(f"Error completing AI analysis: {str(e)}")
    
    async def full_ai_analysis(self, user_id: str, initial_goal: str) -> Dict:
        """Complete AI analysis workflow from start to finish"""
        try:
            # Phase 1: Socratic Questioning
            questioning_result = await self.socratic_questioning(user_id, initial_goal)
            refined_goal = questioning_result["refinedGoal"]
            session_id = questioning_result["sessionId"]
            
            # Phase 2: Round Table Debate
            responses = await self.conduct_round_table_debate(session_id, refined_goal)
            
            # Phase 3: Devil's Advocate Analysis
            critique = await self.devil_advocate_analysis(session_id, responses)
            
            # Phase 4: Consensus Building
            consensus_result = await self.build_consensus(session_id, responses, critique)
            
            # Complete analysis
            await self.complete_ai_analysis(user_id, session_id)
            
            return {
                "success": True,
                "sessionId": session_id,
                "refinedGoal": refined_goal,
                "responses": responses,
                "critique": critique,
                "consensus": consensus_result,
                "questions": questioning_result["questions"],
                "userResponses": questioning_result["userResponses"]
            }
            
        except Exception as e:
            logger.error(f"AI analysis failed: {str(e)}")
            
            # Update session status if it exists
            if 'session_id' in locals():
                session_ref = self.db.collection('ai_sessions').document(session_id)
                session_ref.update({
                    'status': 'failed',
                    'error': str(e),
                    'updatedAt': datetime.now()
                })
            
            return {
                "success": False,
                "error": str(e)
            }