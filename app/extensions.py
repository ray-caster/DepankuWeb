class FirestoreClient:
    """A wrapper for the Firestore client to avoid circular imports."""
    def __init__(self):
        self.client = None

# Create a single, shared instance of our db wrapper
db = FirestoreClient()