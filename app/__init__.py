from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mail import Mail  # <-- 1. Import Mail

# Initialize extensions
db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'login' # This redirects users to login page if they aren't logged in
login_manager.login_message_category = 'info'
mail = Mail() # <-- 2. Initialize Mail

def create_app():
    app = Flask(__name__)
    
    # --- CONFIGURATION ---
    app.config['SECRET_KEY'] = '5791628bb0b13ce0c676dfde280ba245' # Keep your secret key
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
    
    # Email Settings (Gmail)
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    # In app/__init__.py

    app.config['MAIL_USERNAME'] = 'sagaraodedra@gmail.com'  # Make sure this is your actual Gmail address
    app.config['MAIL_PASSWORD'] = 'kcwb payj nlgd xtsf'      # <--- Paste the code from your screenshot here
    # --- INITIALIZE APP ---
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app) # <-- 3. Connect Mail to App

    # --- IMPORT ROUTES ---
    # This imports the routes file so Flask knows about your pages
    # Make sure this matches your actual routes file name!
    from app.routes import main 
    app.register_blueprint(main)

    return app