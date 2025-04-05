from flask import Flask
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Initialize Flask extensions
db = SQLAlchemy()
socketio = SocketIO()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    
    # Configure app
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-please-change')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///firewall.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions
    db.init_app(app)
    socketio.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    # Register blueprints
    from app.routes import main, auth, game
    app.register_blueprint(main.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(game.bp)
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app 