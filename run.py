import os
from app import create_app
from dotenv import load_dotenv

load_dotenv()
# Create the Flask app instance using the app factory
app = create_app()

if __name__ == '__main__':
    # Use port 6000 as specified in your original code
    port = int(os.environ.get('PORT', 6000))
    # Debug mode should be based on environment (off in production)
    debug = os.environ.get('FLASK_ENV', 'development') == 'development'
    app.run(debug=debug, port=port, host='0.0.0.0')