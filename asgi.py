"""
ASGI entry point for Depanku Flask application.
This file provides ASGI compatibility for Uvicorn workers with lifespan support.
"""
import os
import sys
import asyncio
from a2wsgi import ASGIMiddleware

# Add the current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from app import app, db
from openrouter_client import OpenRouterClient
from ai_analysis_service import AIAnalysisService
from moderation_service import ModerationService

# Convert Flask WSGI app to ASGI
flask_asgi_app = ASGIMiddleware(app)

# Global variables for shared resources
openrouter_client = None
ai_service = None
moderation_service = None

async def startup():
    """Perform application startup tasks."""
    global openrouter_client, ai_service, moderation_service
    print("Starting up Depanku application...")
    
    # Initialize OpenRouter client with session
    openrouter_client = OpenRouterClient()
    # Create the aiohttp session manually since we're not using async with
    openrouter_client.session = await openrouter_client.__aenter__()
    print("OpenRouter client initialized")
    
    # Initialize AI services
    ai_service = AIAnalysisService(db)
    moderation_service = ModerationService(db)
    print("AI services initialized")
    
    # Any other startup tasks can be added here
    print("Startup complete")

async def shutdown():
    """Perform application shutdown tasks."""
    global openrouter_client
    print("Shutting down Depanku application...")
    
    # Clean up OpenRouter client session if it exists
    if openrouter_client:
        try:
            # Check if OpenRouterClient has a session and close it
            if hasattr(openrouter_client, 'session') and openrouter_client.session:
                await openrouter_client.session.close()
                print("OpenRouter session closed")
        except AttributeError as e:
            print(f"OpenRouterClient session close error: {e}")
        except Exception as e:
            print(f"Error closing OpenRouter session: {e}")
    
    # Any other cleanup tasks can be added here
    print("Shutdown complete")

async def application(scope, receive, send):
    if scope['type'] == 'lifespan':
        # Handle lifespan events
        while True:
            message = await receive()
            if message['type'] == 'lifespan.startup':
                try:
                    await startup()
                    await send({'type': 'lifespan.startup.complete'})
                except Exception as e:
                    await send({'type': 'lifespan.startup.failed', 'message': str(e)})
            elif message['type'] == 'lifespan.shutdown':
                try:
                    await shutdown()
                    await send({'type': 'lifespan.shutdown.complete'})
                except Exception as e:
                    await send({'type': 'lifespan.shutdown.failed', 'message': str(e)})
                break
    else:
        # Delegate to the Flask ASGI app for other requests
        await flask_asgi_app(scope, receive, send)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(application, host="0.0.0.0", port=6000)