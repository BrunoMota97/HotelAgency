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


auth_bp = Blueprint('auth', __name__)

#current_app.config['SECRET_KEY'] = '134566gfs'
#current_app.config['PERMANENT_SESSION_LIFETIME'] =  timedelta(minutes=1)

PERMANENT_SESSION_LIFETIME = timedelta(minutes=1)
SESSION_REFRESH_EACH_REQUEST = True
SESSION_COOKIE_HTTPONLY = True
REMEMBER_COOKIE_HTTPONLY = True

@auth_bp.route('/')
def index():
    if current_user.is_authenticated:
        session.permanent = True
        return redirect(url_for(f'{current_user.role}.dashboard') if current_user.role != 'service_staff' else url_for('staff.dashboard'))
    return redirect(url_for('auth.login'))


@auth_bp.route('/landing')
def landing():
    return render_template('auth/landing.html')


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



@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('auth.index'))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()

        if not user:
           flash("Credenciais invalidas", "danger")
           return redirect(url_for('auth.login'))
       
        if not user.check_password(password):
            flash("Credenciais invalidas", "danger")
            return redirect(url_for('auth.login'))

        if not autenticacao_segura(password):
            user.estado= EstadoUser.inativo
            flash("A sua conta foi bloqueada!","danger")
            return redirect(url_for('auth.login'))
       # else:
        #   if user.password != password:
         #     flash("Credenciais invalidas", "danger")
          #    return redirect(url_for('auth.login'))

        if user.estado == EstadoUser.inativo:
            flash("A conta está inativa pelo que não é possível iniciar sessão.", "danger")
            return redirect(url_for('auth.login'))
        if user and user.password:
            login_user(user)
            #session.permanent = True
            agora = datetime.now()
            role_redirects = {
                'guest': 'guest.dashboard',
                'admin': 'admin.dashboard',
            }
            
            #session['user_id'] = user.id
           # session['last_active'] = datetime.now()
            return redirect(url_for(role_redirects.get(user.role, 'guest.dashboard')))
        else:
             flash('Email ou passeword inválidos.', 'danger')
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
        #session['last_active'] = datetime.now()
    return render_template('auth/register.html')



def is_session_expired():
    if 'last_active' in session:
        if (datetime.now() - session['last_active']).total_seconds() > 10:
            return True
    return False


@auth_bp.route('/logout')
@login_required
def logout():
   # if is_session_expired():
   #    session.clear()
   #   logout_user()
    #  return redirect(url_for('auth.login'))
   # else:
      session.clear()
      logout_user()
      return redirect(url_for('auth.login'))
    #    logout_user()

