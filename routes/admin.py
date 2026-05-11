import os
import uuid
from flask import Flask,Blueprint, session,render_template, redirect, url_for, flash, request,current_app,send_from_directory
from flask_login import login_required, current_user
from models import db, Quarto, Reserva, User, Pedido, EstadoQuarto, EstadoReserva,Feedback,Chat,Mensagem,ChatMessage
from datetime import date,datetime
from werkzeug.utils import secure_filename
import socket
import re

#import html
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

EXTENSOES_IMAGEM_PERMITIDAS = {"png", "jpg", "jpeg", "gif", "webp", "jfif","avif"}

"""
def admin_required(view):
    @wraps(view)
    @login_required
    def wrapper(*args, **kwargs):
        if not session.get("is_admin"):
            flash("Acesso restrito ao administrador.", "danger")
            return redirect(url_for("main.index"))

        return view(*args, **kwargs)

    return wrapper
"""
@admin_bp.route('/dashboard')
@login_required
def dashboard():
    total_rooms = Quarto.query.count()
    occupied = Quarto.query.filter_by(estado='ocupado').count()
    available = Quarto.query.filter_by(estado='disponivel').count()
    em_manutencao=Quarto.query.filter_by(estado='em_manutencao').count()
    total_guests = User.query.filter_by(role='guest').count()
    pending_requests = Pedido.query.filter_by(estado='pendente').count()
    recent_bookings = Reserva.query.filter_by(estado='confirmada').order_by(Reserva.criado_em.desc()).limit(5).all()
    user_ativo = User.query.filter_by(estado='ativo',role='guest').count()
    user_inativo = User.query.filter_by(estado='inativo').count()
    return render_template('admin/dashboard.html',
                           total_rooms=total_rooms, occupied=occupied,
                           available=available, total_guests=total_guests,
                           em_manutencao=em_manutencao,
                           pending_requests=pending_requests,
                           recent_bookings=recent_bookings,user_ativo=user_ativo,user_inativo=user_inativo)

@admin_bp.route('/rooms')
@login_required
def rooms():
    all_rooms = Quarto.query.order_by(Quarto.numero).all()
    for quarto in all_rooms:
        quarto.imagem_listagem = _imagem_listagem(quarto)
    return render_template('admin/rooms.html', rooms=all_rooms)


def _guardar_imagem(imagem_file):
    if not imagem_file or not imagem_file.filename:
        return current_app.config["ESPACO_IMAGEM_DEFAULT"]

    nome_seguro = secure_filename(imagem_file.filename)
    extensao = nome_seguro.rsplit(".", 1)[-1].lower() if "." in nome_seguro else ""

    if extensao not in EXTENSOES_IMAGEM_PERMITIDAS:
        return None

    nome_unico = f"{uuid.uuid4().hex}.{extensao}"
    pasta_upload = current_app.config["ESPACOS_IMG_UPLOAD_FOLDER"]
    caminho_ficheiro = os.path.join(pasta_upload, nome_unico)

    imagem_file.save(caminho_ficheiro)
    return f"img/quartos/{nome_unico}"


def _imagem_espaco(imagem_file, imagem_atual=None):
    if not imagem_file or not imagem_file.filename:
        if imagem_atual:
            return imagem_atual

        return current_app.config["ESPACO_IMAGEM_DEFAULT"]

    return _guardar_imagem(imagem_file)


def _imagem_listagem(espaco):
    imagem = espaco.imagem or current_app.config["ESPACO_IMAGEM_DEFAULT"]
    caminho_imagem = os.path.join(current_app.static_folder, imagem.replace("/", os.sep))

    if not os.path.exists(caminho_imagem):
        return current_app.config["ESPACO_IMAGEM_DEFAULT"]

    return imagem

@admin_bp.route('/rooms/add', methods=['POST'])
@login_required
def add_room():
    number = request.form.get('number', '').strip()
    room_type = request.form.get('type', '').strip()
    price = request.form.get('price', '').strip()
    description = request.form.get('description', '')
    #html.escape(description)
    imagem_file = request.files.get("imagem")
    

    if not number or not room_type or not price:
        flash('Preencha os campos obrigatórios do quarto.', 'danger')
        return redirect(url_for('admin.rooms'))

    if Quarto.query.filter_by(numero=number).first():
        flash(f'Quarto nº {number} já existe.', 'danger')
        return redirect(url_for('admin.rooms'))

    try:
        price_value = float(price)
    except ValueError:
        flash('Preço inválido.', 'danger')
        return redirect(url_for('admin.rooms'))

    imagem = _imagem_espaco(imagem_file)
    if imagem_file and imagem is None:
        flash("Formato de imagem inválido", "danger")
        return _render_form_criar(form_data)

    room = Quarto(numero=number, tipo=room_type, preco_base=price_value, descricao=description,imagem=imagem)
    db.session.add(room)
    db.session.commit()
    flash(f'Quarto nº {number} adicionado com sucesso.', 'success')
    return redirect(url_for('admin.rooms'))


@admin_bp.route('/rooms/<int:room_id>/delete', methods=['POST'])
@login_required
def delete_room(room_id):
    room = Quarto.query.get_or_404(room_id)
    

    if Reserva.query.filter(Reserva.idQuarto==room.id, 
    Reserva.estado.in_([EstadoReserva.pendente, EstadoReserva.confirmada]),).all():
        flash('Não é possível eliminar o quarto porque já existem reservas associadas.', 'danger')
        return redirect(url_for('admin.rooms'))
    else:
        db.session.delete(room)
        db.session.commit()
        flash(f'Quarto nº {room.numero} eliminado com sucesso.', 'success')
    return redirect(url_for('admin.rooms'))


@admin_bp.route('/rooms/<int:room_id>/edit', methods=['GET', 'POST'])
@login_required
def update_room(room_id):
    room = Quarto.query.get_or_404(room_id)

    if request.method == 'POST':
        numero = request.form.get('numero', '').strip()
        tipo = request.form.get('tipo', '').strip()
        preco = request.form.get('preco', '').strip()
        descricao = request.form.get('descricao', '').strip()
        imagem_file = request.files.get("imagem")


        if not numero or not tipo or not preco:
            flash('Preencha os campos obrigatórios do quarto.', 'danger')
            return render_template('admin/editar_quarto.html', room=room)

        quarto_existente = Quarto.query.filter(Quarto.numero == numero, Quarto.id != room.id).first()
        if quarto_existente:
            flash('Já existe outro quarto com esse número.', 'danger')
            return render_template('admin/editar_quarto.html', room=room)

        try:
            room.preco_base = float(preco)
        except ValueError:
            flash('Preço inválido.', 'danger')
            return render_template('guest/editar_quarto.html', room=room)
        

        imagem = _imagem_espaco(imagem_file, room.imagem)
        if imagem_file and imagem is None:
            flash("Formato de imagem inválido", "danger")
            return redirect(url_for('admin.rooms'))

        room.numero = numero
        room.tipo = tipo
        room.descricao = descricao
        room.imagem = imagem
        db.session.commit()
        flash(f'Quarto nº {room.numero} atualizado com sucesso.', 'success')
        return redirect(url_for('admin.rooms'))

    return render_template('admin/editar_quarto.html', room=room)


@admin_bp.route('/rooms/<int:room_id>/estado', methods=['POST'])
@login_required
def update_room_status(room_id):
    room = Quarto.query.get_or_404(room_id)
    novo_estado = request.form.get('estado', '').strip()

    estados_validos = {estado.value for estado in EstadoQuarto}
    if novo_estado not in estados_validos:
        flash('Estado inválido para o quarto.', 'danger')
        return redirect(url_for('admin.rooms'))

    reservas_ativas = Reserva.query.filter(
        Reserva.idQuarto == room.id,
        Reserva.estado.in_([EstadoReserva.pendente, EstadoReserva.confirmada])
    ).count()

    if novo_estado == 'disponivel' and reservas_ativas > 0:
        flash('Não é possível colocar o quarto como disponível enquanto existirem reservas ativas.', 'danger')
        return redirect(url_for('admin.rooms'))

    room.estado = novo_estado
    db.session.commit()
    flash(f'Estado do quarto nº {room.numero} atualizado.', 'success')
    return redirect(url_for('admin.rooms'))

@admin_bp.route('/feedbacks',methods=['POST','GET'])
@login_required
def show_feedback_status():

    all_feedbacks = Feedback.query.all()

    labels = ['1', '2', '3', '4', '5']

    numero=200
    data_quarto=[]
    data = [Feedback.query.filter_by(nota=i).count() for  i in range (1,6)]
    rooms = Quarto.query.order_by(Quarto.numero).all()
    if request.method=='POST':
      num = request.form['numero']
      data_quarto = [Feedback.query.filter_by(idQuarto=num,nota=i).count() for  i in range (1,6)]
      return render_template('/admin/show_feedback_status.html',all_feedbacks=all_feedbacks,num=num,rooms=rooms,labels=labels, data=data,data_quarto=data_quarto)
    else:
      return render_template('/admin/show_feedback_status.html',all_feedbacks=all_feedbacks,rooms=rooms,numero=numero,labels=labels, data=data,data_quarto=data_quarto)


@admin_bp.route("/new-chat", methods=["POST"])
@login_required
def new_chat():

    user_id = current_user.id
    new_chat_email = request.form["email"].strip().lower()

    if new_chat_email == current_user.email:
        return redirect(url_for("admin.chat"))
  
    recipient_user = User.query.filter_by(email=new_chat_email).first()
    if not recipient_user:
        return redirect(url_for("admin.chat"))
    
    existing_chat = Chat.query.filter_by(user_id=user_id).first()
    if not existing_chat:
        existing_chat = Chat(user_id=user_id, chat_list=[])
        db.session.add(existing_chat)
        db.session.commit()
   
    if recipient_user.id not in [user_chat["user_id"] for user_chat in existing_chat.chat_list]:
        room_id = str(int(recipient_user.id) + int(user_id))[-4:]
        # Add the new chat to the chat list of the current user
        updated_chat_list = existing_chat.chat_list + [{"user_id": recipient_user.id, "room_id": room_id}]
        existing_chat.chat_list = updated_chat_list

        existing_chat.save_to_db()
        recipient_chat = Chat.query.filter_by(user_id=recipient_user.id).first()
        if not recipient_chat:
            recipient_chat = Chat(user_id=recipient_user.id, chat_list=[])
            db.session.add(recipient_chat)
            db.session.commit()
        updated_chat_list = recipient_chat.chat_list + [{"user_id": user_id, "room_id": room_id}]
        recipient_chat.chat_list = updated_chat_list
        recipient_chat.save_to_db()
        # Create a new message entry for the chat room
        new_message = Mensagem(room_id=room_id)
        db.session.add(new_message)
        db.session.commit()
    return redirect(url_for("admin.chat"))


@admin_bp.route("/chat/", methods=["GET", "POST"])
@login_required
def chat():
    room_id = request.args.get("rid", None)

    current_user_id = current_user.id
    current_user_chats = Chat.query.filter_by(user_id=current_user_id).first()
    chat_list = current_user_chats.chat_list if current_user_chats else []

    data = []
    for chat in chat_list:
        username = User.query.get(chat["user_id"]).username
        is_active = room_id == chat["room_id"]
        try:
            message = Mensagem.query.filter_by(room_id=chat["room_id"]).first()
            last_message = message.messages[-1]
            last_message_content = last_message.content
        except (AttributeError, IndexError):
            last_message_content = "Sem mensagens ainda."
        data.append({
            "username": username,
            "room_id": chat["room_id"],
            "is_active": is_active,
            "last_message": last_message_content,
        })
    messages = Mensagem.query.filter_by(room_id=room_id).first().messages if room_id else []

    return render_template("guest/chat.html", user_data=current_user, room_id=room_id, data=data, messages=messages )



@admin_bp.route("/chat/<int:message_id>/delete", methods=["GET", "POST"])
@login_required
def delete_message(message_id):
    message = ChatMessage.query.get_or_404(message_id)
    db.session.delete(message)
    db.session.commit()
    return redirect(url_for("admin.chat"))

@admin_bp.app_template_filter("ftime")
def ftime(date):
    dt = datetime.fromtimestamp(int(date))
    time_format = "%I:%M %p"  # Use  %I for 12-hour clock format and %p for AM/PM
    formatted_time = dt.strftime(time_format)

    formatted_time += " | " + dt.strftime("%m/%d")
    return formatted_time


@admin_bp.route('/get_name')
def get_name():

    data = {'name': ''}
    if 'username' in session:
        data = {'name': session['username']}
    return jsonify(data)
