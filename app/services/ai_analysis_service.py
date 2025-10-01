# --- app/services/ai_analysis_service.py ---
import logging
import json
from datetime import datetime
from .openai_service import OpenAIService, SYSTEM_PROMPTS

logger = logging.getLogger(__name__)

MAX_SOCRATIC_QUESTIONS = 3
MAX_CONSENSUS_ITERATIONS = 2

class AIAnalysisService:
    def __init__(self, db_client, openai_service: OpenAIService):
        self.db = db_client
        self.openai_service = openai_service

    def start_socratic_session(self, user_id: str, initial_goal: str) -> dict:
        """Creates a session document and asks the first question."""
        session_ref = self.db.collection('ai_sessions').document()
        session_id = session_ref.id
        
        first_question = "What is the single most important outcome you hope to achieve from this opportunity?"
        
        session_data = {
            "id": session_id,
            "userId": user_id,
            "initialGoal": initial_goal,
            "questions": [first_question],
            "userResponses": [],
            "status": "questioning_started",
            "createdAt": datetime.now(),
            "updatedAt": datetime.now()
        }
        session_ref.set(session_data)
        
        return {"sessionId": session_id, "question": first_question}

    def continue_socratic_session(self, session_id: str, answer: str) -> dict:
        """Processes a user's answer and either asks another question or refines the goal."""
        session_ref = self.db.collection('ai_sessions').document(session_id)
        session_doc = session_ref.get()
        if not session_doc.exists:
            raise ValueError("AI session not found.")
        
        session_data = session_doc.to_dict()
        session_data.setdefault('userResponses', []).append(answer)
        
        if len(session_data['userResponses']) >= MAX_SOCRATIC_QUESTIONS:
            refined_goal = self._refine_goal_from_conversation(session_data)
            session_ref.update({
                'userResponses': session_data['userResponses'],
                'refinedGoal': refined_goal,
                'status': 'questioning_completed',
                'updatedAt': datetime.now()
            })
            return {"isComplete": True, "refinedGoal": refined_goal, "sessionId": session_id}
        else:
            next_question = self._get_next_socratic_question(session_data)
            session_data.setdefault('questions', []).append(next_question)
            session_ref.update({
                'userResponses': session_data['userResponses'],
                'questions': session_data['questions'],
                'updatedAt': datetime.now()
            })
            return {"isComplete": False, "question": next_question, "sessionId": session_id}

    def _get_next_socratic_question(self, session_data: dict) -> str:
        """Uses AI to generate the next logical question based on conversation history."""
        conversation_history = f"Initial Goal: {session_data['initialGoal']}\n\n"
        for i, q in enumerate(session_data['questions']):
            conversation_history += f"Q: {q}\n"
            if i < len(session_data['userResponses']):
                conversation_history += f"A: {session_data['userResponses'][i]}\n"
        
        prompt = f"Based on this conversation, ask the single most insightful follow-up question to deeply understand the user's priorities. The question should be open-ended. Return only the question text.\n\nHistory:\n{conversation_history}"
        messages = [{"role": "system", "content": SYSTEM_PROMPTS['socratic_questioner']}, {"role": "user", "content": prompt}]
        return self.openai_service.query_model("deepseek", messages)

    def _refine_goal_from_conversation(self, session_data: dict) -> str:
        """Uses AI to summarize the conversation into a refined goal."""
        conversation_history = f"Initial Goal: {session_data['initialGoal']}\n\n"
        for i, q in enumerate(session_data['questions']):
            conversation_history += f"Q: {q}\nA: {session_data.get('userResponses', [])[i]}\n"
            
        prompt = f"Synthesize the following conversation into a concise, actionable goal for an AI career advisory panel. The goal should be a single paragraph that captures all the user's stated priorities and concerns.\n\nConversation:\n{conversation_history}"
        messages = [{"role": "system", "content": SYSTEM_PROMPTS['summarizer']}, {"role": "user", "content": prompt}]
        return self.openai_service.query_model("deepseek", messages)

    def full_ai_analysis_flow(self, user_id: str, refined_goal: str, session_id: str) -> dict:
        """The main AI debate flow, designed to be run synchronously in a Celery task."""
        try:
            session_ref = self.db.collection('ai_sessions').document(session_id)
            session_ref.update({'status': 'debate_in_progress', 'updatedAt': datetime.now()})

            responses = self._conduct_round_table_debate(session_id, refined_goal)
            critique = self._devil_advocate_analysis(session_id, responses)
            consensus_result = self._build_consensus(session_id, responses, critique)
            
            self.complete_ai_analysis_record(user_id, session_id)
            
            session_ref.update({'status': 'completed', 'updatedAt': datetime.now()})
            return {"success": True, "sessionId": session_id}
        except Exception as e:
            logger.error(f"Full AI analysis failed for session {session_id}: {e}", exc_info=True)
            self.db.collection('ai_sessions').document(session_id).update({
                'status': 'failed', 'error': str(e), 'updatedAt': datetime.now()
            })
            return {"success": False, "error": "AI analysis process failed."}

    def _conduct_round_table_debate(self, session_id: str, refined_goal: str) -> dict:
        """Conducts the initial round of analysis from all primary personas."""
        personas = ["deepseek", "maverick", "qwen", "glm"]
        responses = {}
        prompt = f"Given the user's goal, provide your expert analysis and recommendations. Goal: '{refined_goal}'"
        session_ref = self.db.collection('ai_sessions').document(session_id)
        
        for persona in personas:
            try:
                response_text = self.openai_service.query_persona(persona, prompt)
                responses[persona] = response_text
                session_ref.update({f'personas.{persona}.initialResponse': response_text})
            except Exception as e:
                logger.warning(f"Persona {persona} failed in debate for session {session_id}: {e}")
                responses[persona] = "This expert was unavailable for comment."
        return responses

    def _devil_advocate_analysis(self, session_id: str, responses: dict) -> str:
        """Gets a critique of the initial analyses."""
        formatted_responses = json.dumps(responses, indent=2)
        prompt = f"Review the following expert analyses regarding a user's goal. Your task is to play devil's advocate. Identify potential flaws, risks, overlooked details, and conflicting advice in their recommendations. Be concise and direct.\n\nAnalyses:\n{formatted_responses}"
        critique = self.openai_service.query_persona("grok", prompt)
        self.db.collection('ai_sessions').document(session_id).update({'personas.grok.critique': critique})
        return critique

    def _build_consensus(self, session_id: str, initial_responses: dict, critique: str) -> dict:
        """Iteratively refines analyses to reach consensus or a final compromise."""
        current_responses = initial_responses
        
        for i in range(MAX_CONSENSUS_ITERATIONS):
            # Revise analyses
            revised_responses = {}
            for persona, previous_response in current_responses.items():
                prompt = f"Your previous analysis was: '{previous_response}'.\nOther experts said: {json.dumps({k: v for k, v in current_responses.items() if k != persona})}\n\nA critique was raised: '{critique}'.\n\nPlease provide a revised, improved analysis that addresses the critique and considers the other perspectives to move towards a unified recommendation."
                try:
                    revised_responses[persona] = self.openai_service.query_persona(persona, prompt)
                except Exception as e:
                    logger.warning(f"Persona {persona} failed in consensus round {i+1}: {e}")
                    revised_responses[persona] = previous_response # Carry over old response on failure
            current_responses = revised_responses

            # Check for consensus
            consensus_check_prompt = f"Analyze these revised expert opinions. Have they reached a clear consensus? Respond ONLY with a JSON object containing 'consensus' (boolean), and if true, a 'recommendation' (string summarizing the unified advice) and 'reasoning' (string explaining why it's a consensus).\n\nOpinions:\n{json.dumps(current_responses)}"
            messages = [{"role": "system", "content": "You are a consensus analyzer. Return valid JSON only."}, {"role": "user", "content": consensus_check_prompt}]
            
            try:
                consensus_data = self.openai_service.query_model("deepseek", messages, is_json=True)
                if consensus_data.get("consensus"):
                    result = {"reached": True, "finalRecommendation": consensus_data["recommendation"], "reasoning": consensus_data["reasoning"]}
                    self.db.collection('ai_sessions').document(session_id).update({'consensus': result, 'finalResponses': current_responses})
                    return result
            except Exception as e:
                logger.error(f"Consensus check failed in iteration {i+1}: {e}")

        # If loop finishes, create a final compromise
        compromise_prompt = f"These experts could not agree. Act as a final mediator. Synthesize their conflicting final opinions into a single, balanced, and actionable recommendation for the user. Explain the key tradeoffs.\n\nFinal Opinions:\n{json.dumps(current_responses)}"
        messages = [{"role": "system", "content": "You are an expert mediator who creates balanced recommendations."}, {"role": "user", "content": compromise_prompt}]
        compromise_text = self.openai_service.query_model("maverick", messages) # Use a strong model for this
        
        result = {"reached": False, "finalRecommendation": compromise_text, "reasoning": "A final compromise was generated after the experts could not reach full consensus."}
        self.db.collection('ai_sessions').document(session_id).update({'consensus': result, 'finalResponses': current_responses})
        return result

    def complete_ai_analysis_record(self, user_id: str, session_id: str):
        """Updates the user's remaining analysis count and logs the completed analysis."""
        try:
            user_ref = self.db.collection('users').document(user_id)
            user_doc = user_ref.get()
            if not user_doc.exists:
                return

            user_data = user_doc.to_dict()
            subscription = user_data.get('subscription', {})
            
            if subscription.get('plan', 'free') == 'free':
                remaining = subscription.get('aiAnalysesRemaining', 0)
                if remaining > 0:
                    user_ref.update({'subscription.aiAnalysesRemaining': remaining - 1})

            analysis_ref = self.db.collection('ai_analyses').document()
            analysis_ref.set({
                'userId': user_id,
                'sessionId': session_id,
                'status': 'success',
                'createdAt': datetime.now(),
            })
        except Exception as e:
            logger.error(f"Error completing AI analysis record for user {user_id}: {e}")