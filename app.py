from __future__ import annotations
from flask import Flask,g,abort,session,request
from flask_login import LoginManager
from config import Config
from models import db, bcrypt, User,Message,ChatMessage
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
from flask_socketio import emit, join_room, leave_room
from flask_socketio import SocketIO
from flask_cors import CORS
cors = CORS()

import socket

socket = SocketIO()
from flask_wtf import FlaskForm, CSRFProtect

csrf = CSRFProtect()

LOGIN_MAX_ATTEMPTS = 3
LOGIN_WINDOW = timedelta(minutes=5)
LOGIN_LOCKOUT = timedelta(minutes=10)


def create_app():
    app = Flask(__name__)
    socket.init_app(app, cors_allowed_origins="*")
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
    app.config["SESSION_COOKIE_SECURE"] = os.environ.get("FLASK_ENV") == "production"
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = production
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)


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
    

    def validate_csrf() -> None:
      form_token = request.form.get("_csrf_token")
      session_token = session.get("_csrf_token")
      if not form_token or not session_token or not secrets.compare_digest(form_token, session_token):
        abort(400, description="Invalid CSRF token.")


    
    @app.after_request
    def set_security_headers(response):
        # SECURITY: browser protections.
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        #response.headers["Content-Security-Policy"] = (
        #    "default-src 'self'; "
        #    "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
        #    "script-src 'self' https://cdn.jsdelivr.net; "
        #    "img-src 'self' data:; "
        #    "object-src 'none'; "
        #    "base-uri 'self'; "
        #    "frame-ancestors 'none'"
        #)
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
    

    
    @socket.on("join-chat")
    def join_private_chat(data):
      room = data["rid"]
      join_room(room=room)
      socket.emit(
        "joined-chat",
        {"msg": f"{room} is now online."},
        room=room,
        # include_self=False,
      )


# Outgoing event handler
    @socket.on("outgoing")
    def chatting_event(json, methods=["GET", "POST"]):

      room_id = json["rid"]
      timestamp = json["timestamp"]
      message = json["message"]
      sender_id = json["sender_id"]
      sender_username = json["sender_username"]

    # Get the message entry for the chat room
      message_entry = Message.query.filter_by(room_id=room_id).first()

    # Add the new message to the conversation
      chat_message = ChatMessage(
        content=message,
        timestamp=timestamp,
        sender_id=sender_id,
        sender_username=sender_username,
        room_id=room_id,
      )
    # Add the new chat message to the messages relationship of the message
      message_entry.messages.append(chat_message)

    # Updated the database with the new message
      try:
        chat_message.save_to_db()
        message_entry.save_to_db()
      except Exception as e:
        # Handle the database error, e.g., log the error or send an error response to the client.
        print(f"Error saving message to the database: {str(e)}")
        db.session.rollback()

    # Emit the message(s) sent to other users in the room
      socket.emit(
        "message",
        json,
        room=room_id,
        include_self=False,
      )

    return app,socket

app, socket = create_app()


if __name__ == '__main__':
    #debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    #create_app().run(debug=debug_mode)
    #create_app().run(debug=True)
    socket.run(app, allow_unsafe_werkzeug=True, debug=True)

