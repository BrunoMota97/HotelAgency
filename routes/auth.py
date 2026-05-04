from flask import Flask,Blueprint, render_template, redirect, url_for, flash, request, session,current_app
from flask_login import login_user, logout_user, login_required, current_user,LoginManager
from models import db, User,EstadoUser
from datetime import date, datetime,timedelta,timezone
from werkzeug.security import generate_password_hash,check_password_hash
from itsdangerous import URLSafeTimedSerializer
from pytz import timezone
import bcrypt
import os
from sqlalchemy.orm import sessionmaker
import re
#from ozekilibsrest import Configuration, Message, MessageApi

auth_bp = Blueprint('auth', __name__)

PERMANENT_SESSION_LIFETIME = timedelta(minutes=3)
SESSION_REFRESH_EACH_REQUEST = True
SESSION_COOKIE_HTTPONLY = True
REMEMBER_COOKIE_HTTPONLY = True

LOGIN_MAX_ATTEMPTS = 3
LOGIN_WINDOW = timedelta(minutes=5)
LOGIN_LOCKOUT = timedelta(minutes=10)
login_attempts: Dict[str, Dict[str, Any]] = {}

@auth_bp.route('/')
def index():
    if current_user.is_authenticated:
        session.permanent = True
        return redirect(url_for(f'{current_user.role}.dashboard') if current_user.role != 'service_staff' else url_for('staff.dashboard'))
    return redirect(url_for('auth.login'))

@auth_bp.route('/landing')
def landing():
    return render_template('auth/landing.html')

"""Autenticação na consola
def autenticacao_segura(hash_correto: bytes, max_tentativas: int = 3) -> bool:

    tentativas = 0
    while tentativas < max_tentativas:
        restantes = max_tentativas - tentativas
        password = input(f"  Password ({restantes} tentativa(s) restante(s)): ")

        if password == hash_correto:
            print("  [OK] Login com sucesso.")
            return True

        tentativas += 1
        print("  [ERRO] Password errada.")

    print("  [BLOQUEADO] Conta bloqueada após demasiadas tentativas falhadas.")
    return False
"""
def login_key(username: str) -> str:
        ip = request.remote_addr or "unknown-ip"
        return f"{ip}:{username.lower()}"

def is_login_locked(username: str) -> Tuple[bool, int]:
        key = login_key(username)
        record = login_attempts.get(key)
        if not record:
            return False, 0

        locked_until = record.get("locked_until")
        now = datetime.utcnow()
        if locked_until and now < locked_until:
            remaining = int((locked_until - now).total_seconds() // 60) + 1
            return True, remaining

        first_attempt = record.get("first_attempt")
        if first_attempt and now - first_attempt > LOGIN_WINDOW:
            login_attempts.pop(key, None)
        return False, 0

def register_failed_login(username: str) -> None:
        key = login_key(username)
        now = datetime.utcnow()
        record = login_attempts.get(key)

        if not record or now - record.get("first_attempt", now) > LOGIN_WINDOW:
            record = {"count": 1, "first_attempt": now, "locked_until": None}
        else:
            record["count"] = int(record.get("count", 0)) + 1

        if int(record["count"]) >= LOGIN_MAX_ATTEMPTS:
            record["locked_until"] = now + LOGIN_LOCKOUT
            flash("Login temporarily locked for username=%s", user.username)

        login_attempts[key] = record

def clear_failed_logins(username: str) -> None:
        login_attempts.pop(login_key(username), None)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('auth.index'))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()

        locked, minutes = is_login_locked(email)
        if locked:
            flash(f"Excedeu o número de tentativas. Tente novamente dentro de {minutes} minutos.")
            return redirect(url_for("auth.login"))

        if not user or not user.check_password(password):
           register_failed_login(email)
           flash("Credenciais invalidas", "danger")
           return redirect(url_for('auth.login'))

        if user.estado == EstadoUser.inativo:
            flash("A conta está inativa pelo que não é possível iniciar sessão.", "danger")
            return redirect(url_for('auth.login'))
        if user and user.password:
            login_user(user)
            #session.permanent = True
            role_redirects = {
                'guest': 'guest.dashboard',
                'admin': 'admin.dashboard',
            }
            #clear_failed_logins(email)
            #session.clear()
            #session.permanent = True
            #session["user_id"] = user.id
            return redirect(url_for(role_redirects.get(user.role, 'guest.dashboard')))
        else:
             flash('Email ou password inválidos.', 'danger')
             return redirect(url_for('auth.login'))
    return render_template('auth/login.html')

def idade(data_nascimento):
    anos = datetime.now().year - data_nascimento.year -  ((datetime.now().month, datetime.now().day) < (data_nascimento.month, data_nascimento.day))
    return anos

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('auth.index'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        username= request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        dataNascimento = request.form.get('dataNascimento')
        data_nascimento = datetime.strptime(dataNascimento, "%Y-%m-%d").date()

        numero = False
        maiuscula = False
        minuscula = False
        especial = False

        for char in password:
              if char.isdigit():
                numero = True
              elif char.isalpha():
                if char.isupper():
                  maiuscula = True
                else:
                  minuscula = True
              else:
                  especial = True
        #validação do nome
        if not re.match(r'^[a-zA-Z]',name):
            flash("O nome introduzido é inválido.")
            return render_template('auth/register.html')

        #validacao do username
        if not re.match(r'^[a-zA-z0-9]',username):
            flash("O username introduzido é inválido.")
            return render_template('auth/register.html')

        #validacao do email
        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$',email):
            flash("O email introduzido é inválido.")
            return render_template('auth/register.html')

        if not numero or not maiuscula or not minuscula or not especial and len(password)>=20:
            flash("A password precisa de ter uma maiuscula, uma minuscula, um numero e um caracter especial.",'danger')
            return render_template('auth/register.html')

        if User.query.filter_by(username=username).first():
           flash("Username ja existe", "danger")
           return render_template('auth/register.html')

        if User.query.filter_by(email=email).first():
            flash('Email já existe.', 'danger')
            return render_template('auth/register.html')

        if data_nascimento > date.today():
           flash("Data de nascimento invalida", "danger")
           return render_template('auth/register.html')

        if idade(data_nascimento)<18:
            flash("Tem de ter pelo menos 18 anos para se registar","danger")
            return render_template('auth/register.html')

        if User.query.count()==0:
           user = User(name=name, username=username, email=email,dataNascimento=data_nascimento,role="admin")
        else:
           user = User(name=name, username=username, email=email,dataNascimento=data_nascimento,role="guest")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash('Conta criada! Bem-vindo(a).', 'success')
        return redirect(url_for('guest.dashboard'))
    return render_template('auth/register.html')

def is_session_expired():
    if 'last_active' in session:
        if (datetime.now() - session['last_active']).total_seconds() > 10:
            return True
    return False

@auth_bp.route('/logout')
@login_required
def logout():
      session.clear()
      logout_user()
      return redirect(url_for('auth.login'))





"""
configuration = Configuration(
    username="http_user",
    password="qwe123",
    api_url="http://127.0.0.1:9509/api"
)
         
api = MessageApi(configuration)
         
logs = []


@auth_bp.route('/recover')
def recover():
    return render_template('auth/recuperar.html')

@auth_bp.route('/recover',methods=['GET','POST'])
def send_sms(email):
    if request.method=='POST':
      email = request.form.get('email')
      message = Message(
            to_address=email,
            text="Olá"
        )
      log = api.send(message)
      logs.append(log)
    return render_template('recover.html', logs=logs)


"""