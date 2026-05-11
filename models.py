from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from flask_bcrypt import Bcrypt
from datetime import datetime
from pytz import timezone
import enum
import secrets
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
db = SQLAlchemy()
bcrypt = Bcrypt()


class EstadoUser(enum.Enum):
    ativo = "ativo"
    inativo = "inativo"

class EstadoReserva(enum.Enum):
	pendente = "pendente"
	confirmada = "confirmada"
	cancelada = "cancelada"

class EstadoQuarto(enum.Enum):
	disponivel = "disponivel"
	ocupado = "ocupado"
	em_manutencao = "em_manutencao"

class User(UserMixin, db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(30), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    #isAdmin = db.Column(db.Boolean, default = False)
    role = db.Column(db.String(20), nullable=False)  
    dataNascimento = db.Column(db.Date)
    estado = db.Column(db.Enum(EstadoUser), default=EstadoUser.ativo)
    reservas = db.relationship("Reserva", back_populates="user", lazy=True)
    pedidos = db.relationship("Pedido", backref='requester', lazy=True)
    pagamentos = db.relationship("Pagamento", back_populates="user", lazy=True)
    reset_token = db.Column(db.String(100), nullable=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)

    def check_password(self, passe):
        return check_password_hash(self.password, passe)


    def set_reset_token(self):

        self.reset_token = secrets.token_urlsafe(32)
        self.reset_token_expiry = datetime.utcnow() + timedelta(hours=3)
        return self.reset_token
    
    def verify_reset_token(self, token):
        """Verify if the reset token is valid and not expired"""
        if token != self.reset_token:
            return False
        if datetime.utcnow() > self.reset_token_expiry:
            return False
        return True



class Reserva(db.Model):
    __tablename__ = "reserva"
    id = db.Column(db.Integer, primary_key=True)
    idUser = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    idQuarto = db.Column(db.Integer, db.ForeignKey('quarto.id'), nullable=False)
    check_in = db.Column(db.Date, nullable=False)
    check_out = db.Column(db.Date, nullable=False)
    estado = db.Column(db.Enum(EstadoReserva), default=EstadoReserva.pendente) 
    total_price = db.Column(db.Float, nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.now())
    user = db.relationship("User",back_populates="reservas")
    quarto=db.relationship("Quarto",back_populates="reservas")
    pagamento = db.relationship("Pagamento", back_populates="reserva", uselist=False)
    pedidos = db.relationship('Pedido', backref='reserva', lazy=True)


class Quarto(db.Model):
    __tablename__ = "quarto"
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.Integer, unique=True, nullable=False)
    tipo = db.Column(db.String(20), nullable=False) 
    preco_base = db.Column(db.Float, nullable=False)
    imagem = db.Column(db.String(200))
    estado = db.Column(db.Enum(EstadoQuarto), nullable=False, default=EstadoQuarto.disponivel) 
    descricao = db.Column(db.String(300))
    classificacao=db.Column(db.Float,nullable=False,default=0)
    reservas = db.relationship("Reserva", back_populates="quarto", lazy=True)
    #feedback = db.relationship("Feedback",back_populates="quarto",lazy=True)

class Pedido(db.Model):
    __tablename__ = "pedido"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    booking_id = db.Column(db.Integer, db.ForeignKey('reserva.id'), nullable=True)
    tipo = db.Column(db.String(30), nullable=False)  
    descricao = db.Column(db.String(500))
    estado = db.Column(db.String(20), nullable=False, default='pendente')  
    criado_em = db.Column(db.DateTime, default=datetime.now())
    updated_at = db.Column(db.DateTime, default=datetime.now(), onupdate=datetime.now())

"""class Resposta(db.Model):
    __tablename__ = "resposta"
    id = db.Column(db.Integer, primary_key=True)
    id_pedido= db.Column(db.Integer,db.ForeignKey('pedido.id'))
    criado_em = db.Column(db.DateTime, default=datetime.now())
    pedido = db.relationship("Pedido",back_populates="resposta")
"""
class Pagamento(db.Model):
    
	id = db.Column(db.Integer, primary_key=True)
	idUser = db.Column(db.Integer, db.ForeignKey('user.id'), nullable = False)
	idReserva = db.Column(db.Integer, db.ForeignKey('reserva.id'), nullable = False, unique=True)
	nomeFaturacao = db.Column(db.String(80))
	emailFaturacao = db.Column(db.String(120))
	valor = db.Column(db.Float, nullable = False)
	dataPagamento = db.Column(db.DateTime,default=datetime.now())
	estado = db.Column(db.String(20), default="pendente")
	user = db.relationship("User", back_populates="pagamentos")
	reserva = db.relationship("Reserva", back_populates="pagamento")


class Feedback(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    nota = db.Column(db.Integer,nullable=False)
    idQuarto = db.Column(db.Integer,db.ForeignKey('quarto.id'),nullable=False)
    opiniao = db.Column(db.String(200))


class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('chats', lazy=True))
    chat_list = db.Column(db.JSON, nullable=False, default=list)

    def save_to_db(self):
        db.session.add(self)
        db.session.commit()



class Mensagem(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.String(50), nullable=False, unique=True)
    messages = db.relationship('ChatMessage', backref='mensagem', lazy=True)

    def save_to_db(self):
        db.session.add(self)
        db.session.commit()


class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(400))
    # timestamp = db.Column(db.TIMESTAMP, server_default=0db.func.current_timestamp(), nullable=False)
    timestamp = db.Column(db.String(20), nullable=False)
    sender_id = db.Column(db.Integer, nullable=False)
    sender_username = db.Column(db.String(50), nullable=False)
    room_id = db.Column(db.String(50), db.ForeignKey('messages.room_id'), nullable=False)

    def save_to_db(self):
        db.session.add(self)
        db.session.commit()