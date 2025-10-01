# --- app/extensions.py (MODIFIED) ---
from celery import Celery # NEW

class FirestoreClient:
    """A wrapper for the Firestore client to avoid circular imports."""
    def __init__(self):
        self.client = None

# Create a single, shared instance of our db wrapper
db = FirestoreClient()

# NEW: Create a single, shared instance of Celery
# The main app will configure it later.
celery = Celery(__name__)