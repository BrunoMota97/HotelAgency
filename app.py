from __future__ import annotations
from flask import Flask,g,abort,session,request
from flask_login import LoginManager
from config import Config
from models import db, bcrypt, User
from routes.auth import auth_bp
from routes.guest import guest_bp
from routes.staff import staff_bp
from routes.admin import admin_bp
import os
import secrets
import logging
from datetime import timedelta
from security import init_security
from functools import wraps
from logging.handlers import RotatingFileHandler


from flask_wtf import FlaskForm, CSRFProtect

csrf = CSRFProtect()




def create_app():
    app = Flask(__name__)
    csrf.init_app(app)

    app.config["ESPACO_IMAGEM_DEFAULT"] = "img/HotelAgency.png"
    app.config["ESPACOS_IMG_UPLOAD_FOLDER"] = os.path.join(app.static_folder, "img", "quartos")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app_env = os.environ.get("APP_ENV", "development").lower()
    production = app_env == "production"
    secret_key = os.environ.get("SECRET_KEY")
    if production and not secret_key:
        raise RuntimeError("SECRET_KEY environment variable is required in production.")

    app.config["SECRET_KEY"] = secret_key or "dev-secret-change-me"
    #app.config["SESSION_COOKIE_SECURE"] = os.environ.get("FLASK_ENV") == "production"
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = production
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)

    LOGIN_MAX_ATTEMPTS = 5
    LOGIN_WINDOW = timedelta(minutes=5)
    LOGIN_LOCKOUT = timedelta(minutes=10)

    app.config.from_object(Config)

    db.init_app(app)
    os.makedirs(app.config["ESPACOS_IMG_UPLOAD_FOLDER"], exist_ok=True)
    bcrypt.init_app(app)
    #app.jinja_env.globals["csrf_token"] = get_csrf_token

    login_manager = LoginManager(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'warning'
    

    def get_csrf_token() -> str:
      token = session.get("_csrf_token")
      if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
      return token


    
    @app.after_request
    def set_security_headers(response):
        # SECURITY: browser protections.
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
            "script-src 'self' https://cdn.jsdelivr.net; "
            "img-src 'self' data:; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "frame-ancestors 'none'"
        )
        if production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response
    


    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    app.register_blueprint(auth_bp)
    app.register_blueprint(guest_bp)
    app.register_blueprint(staff_bp)
    app.register_blueprint(admin_bp)

    with app.app_context():
        db.create_all()
        # Auto-seed if database is empty (e.g. fresh Render deployment)
        if User.query.count() == 0:
            from seed import seed_db
            seed_db()

    return app


app = create_app()

if __name__ == '__main__':
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    create_app().run(debug=debug_mode)

