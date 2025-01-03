from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from os import path
from flask_login import LoginManager
from web.celery_config import celery
from flask_mail import Mail
from werkzeug.security import generate_password_hash
import os
from flask_caching import Cache


mail = Mail()
cache = Cache()
# Initialize the SQLAlchemy object for database interactions
db = SQLAlchemy()
DB_NAME = "database.db"  # Define the name of the database file

def create_app():
    # Create an instance of the Flask application
    app = Flask(__name__)

    # Configure the app's secret key and database URI
    app.config["SECRET_KEY"] = "qwerty"
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_NAME}"

    # Flask-Mail configuration
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', 'your-email@gmail.com')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', 'your-key')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', 'your-email@gmail.com')

    mail.init_app(app)

    app.config['CACHE_TYPE'] = 'RedisCache'
    app.config['CACHE_REDIS_URL'] = "redis://192.168.29.118:6379/0"
    app.config['CACHE_DEFAULT_TIMEOUT'] = 30
    
    # Initialize the SQLAlchemy instance with the app
    db.init_app(app)
    cache.init_app(app)
    
    # Initialize Celery with the app context
    celery.conf.update(app.config)

    # Import views and authentication blueprints
    from .views import views
    from .auth import auth

    # Register the blueprints with specified URL prefixes
    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')

    # Import the database models
    from .models import User, Professional, Admin

    # Create the database tables if they don't exist
    if not path.exists(f"web/{DB_NAME}"):
        with app.app_context():
            db.create_all()
            print("Database created!")

            # Check if the admin user already exists
            admin = Admin.query.filter_by(email="admin@gmail.com").first()
            if not admin:
                admin = Admin(
                    email="admin@gmail.com",
                    password=generate_password_hash("124578", method="pbkdf2:sha256")
                )
                db.session.add(admin)
                db.session.commit()
                print("Admin user created!")

    # Initialize the LoginManager for user authentication
    login_manager = LoginManager()
    login_manager.login_view = "auth.login"  # Login view for redirection
    login_manager.init_app(app)  # Initialize the LoginManager with the app

    @login_manager.user_loader
    def load_user(id):
        # Attempt to find the user in User model
        user = User.query.get(int(id))
        if user:
            return user

        # Attempt to find the user in Professional model
        professional = Professional.query.get(int(id))
        if professional:
            return professional

        # Attempt to find the user in the Admin model
        admin = Admin.query.get(int(id))
        if admin:
            return admin

        # If not found in any model
        return None

    return app
