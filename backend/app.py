from flask import Flask, jsonify, request
from flask_migrate import Migrate
from models import db,PdfDocument
from datetime import datetime
from datetime import timedelta
from flask_cors import CORS
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

app = Flask(__name__)

CORS(app)

# Database configuration with environment variables
# Default to local PostgreSQL if DATABASE_URL is not set
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://mpesa_user:your_password_here@localhost:5432/mpesa_clone_db')

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Flask configuration
app.config['DEBUG'] = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'

# migration initialization
migrate = Migrate(app, db)
db.init_app(app)


# imports functions from views
from parser import *

app.register_blueprint(upload_bp)
app.register_blueprint(summary_bp)
app.register_blueprint(extract_bp)
app.register_blueprint(fetching_bp)



if __name__ == '__main__':
    app.run(debug=True)