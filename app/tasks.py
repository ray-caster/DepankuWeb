# --- app/tasks.py ---
import logging
from .extensions import celery, db
from .services.ai_analysis_service import AIAnalysisService
from .services.moderation_service import ModerationService
from .services.openai_service import OpenAIService
from datetime import datetime 
logger = logging.getLogger(__name__)

@celery.task(bind=True)
def perform_ai_analysis(self, user_id: str, refined_goal: str, session_id: str):
    """Celery task to run the full AI analysis flow without blocking the web server."""
    try:
        self.update_state(state='PROGRESS', meta={'status': 'Initializing AI services...'})
        
        openai_service = OpenAIService()
        ai_analysis_service = AIAnalysisService(db.client, openai_service)
        
        self.update_state(state='PROGRESS', meta={'status': 'Conducting multi-expert debate...'})
        result = ai_analysis_service.full_ai_analysis_flow(user_id, refined_goal, session_id)
        
        if not result.get("success"):
             raise Exception(result.get("error", "Unknown error in analysis flow"))

        self.update_state(state='SUCCESS', meta={'status': 'Analysis complete!'})
        return {'status': 'Complete', 'sessionId': result['sessionId']}

    except Exception as e:
        logger.error(f"AI analysis task failed for session {session_id}: {e}", exc_info=True)
        self.update_state(state='FAILURE', meta={'exc_type': type(e).__name__, 'exc_message': str(e)})
        raise

@celery.task
def moderate_and_index_organization(org_data: dict, org_id: str):
    """Celery task for content moderation and (future) search indexing."""
    try:
        moderation_service = ModerationService(db.client, OpenAIService())
        moderation_result = moderation_service.moderate_content(org_data)
        
        org_ref = db.client.collection('organizations').document(org_id)
        update_data = {
            'aiModeration': moderation_result,
            'updatedAt': datetime.now()
        }
        
        if moderation_result.get('approved', True):
            update_data['status'] = 'approved'
            logger.info(f"Organization {org_id} approved by moderation.")
            # Future integration: Add to search index
            # from app.services.search_service import algolia_client
            # algolia_client.index_organization(org_id, org_data)
        else:
            update_data['status'] = 'rejected'
            logger.warning(f"Organization {org_id} rejected by moderation. Reasons: {moderation_result.get('reasons')}")
        
        org_ref.update(update_data)
            
    except Exception as e:
        logger.error(f"Moderation task failed for org {org_id}: {e}", exc_info=True)
        # Mark the org as having a moderation failure for manual review
        org_ref = db.client.collection('organizations').document(org_id)
        org_ref.update({'status': 'moderation_failed', 'error': str(e)})
        raise