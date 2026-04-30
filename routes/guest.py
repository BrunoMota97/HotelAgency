from flask import Blueprint, render_template, redirect, url_for, flash, session, request, send_file
from flask_login import login_required, current_user
from models import db, Quarto, Reserva, Pedido, User, EstadoUser, EstadoReserva, Pagamento, EstadoQuarto
from datetime import datetime, date
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io
import time
from routes.auth import logout
from PIL import Image,ImageTk,ImageDraw, ImageFont
from PyPDF2 import PdfFileWriter, PdfFileReader

guest_bp = Blueprint('guest', __name__, url_prefix='/guest')


@guest_bp.route('/dashboard')
@login_required
def dashboard():
    my_bookings = Reserva.query.filter_by(idUser=current_user.id).order_by(Reserva.criado_em.desc()).limit(3).all()
    my_requests = Pedido.query.filter_by(user_id=current_user.id).order_by(Pedido.criado_em.desc()).limit(3).all()
    return render_template('guest/dashboard.html', bookings=my_bookings, requests=my_requests)


@guest_bp.route('/book', methods=['GET', 'POST'])
@login_required
def book():
    available_rooms = []
    check_in = request.args.get('check_in') or request.form.get('check_in')
    check_out = request.args.get('check_out') or request.form.get('check_out')
    room_type = request.args.get('room_type') or request.form.get('room_type')

    if check_in and check_out:
        try:
            ci = datetime.strptime(check_in, '%Y-%m-%d').date()
            co = datetime.strptime(check_out, '%Y-%m-%d').date()
            if ci < date.today():
                flash('A data do check-in tem de ser igual ou superior à data atual.', 'danger')
                return redirect(url_for('guest.book'))
            if co <= ci:
                flash('A data do check-in tem de ser inferior à do check-out.', 'danger')
                return redirect(url_for('guest.book'))

            booked_room_ids = db.session.query(Reserva.idQuarto).filter(
                Reserva.estado.in_([EstadoReserva.confirmada]),
                Reserva.check_in < co,
                Reserva.check_out > ci,
            ).all()
            booked_ids = [r[0] for r in booked_room_ids]

            query = Quarto.query.filter(
                Quarto.estado == EstadoQuarto.disponivel,
                ~Quarto.id.in_(booked_ids),
            )
            if room_type:
                query = query.filter_by(tipo=room_type)
            available_rooms = query.all()
        except ValueError:
            flash('Invalid date format.', 'danger')

    return render_template('guest/book.html', rooms=available_rooms,
                           check_in=check_in, check_out=check_out, room_type=room_type)


@guest_bp.route('/book/confirm/<int:room_id>', methods=['POST'])
@login_required
def confirm_booking(room_id):
    check_in = request.form.get('check_in')
    check_out = request.form.get('check_out')
    try:
        ci = datetime.strptime(check_in, '%Y-%m-%d').date()
        co = datetime.strptime(check_out, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        flash('Datas inválidas.', 'danger')
        return redirect(url_for('guest.book'))

    room = Quarto.query.get_or_404(room_id)
    nights = (co - ci).days
    total = room.preco_base * nights
    booking = Reserva(
        idUser=current_user.id,
        idQuarto=room_id,
        check_in=ci,
        check_out=co,
        total_price=total,
        criado_em=datetime.now(),
        estado=EstadoReserva.pendente,
    )

    if Reserva.query.filter_by(idUser=current_user.id, estado=EstadoReserva.pendente).count() >= 1 or Reserva.query.filter_by(idUser=current_user.id, estado=EstadoReserva.confirmada).count() >= 1:
        flash('Não pode efetuar mais do que uma reserva. Necessita de cancelar outras.', 'danger')
    else:
        room.estado = EstadoQuarto.ocupado
        db.session.add(booking)
        db.session.commit()
        flash(f'Reserva confirmada! Quarto {room.numero} para {nights} noite(s). Total: ${total:.2f}', 'success')

    return redirect(url_for('guest.bookings'))


@guest_bp.route('/bookings')
@login_required
def bookings():
    if current_user.role == 'admin':
        my_bookings = Reserva.query.all()
    else:
        my_bookings = Reserva.query.filter_by(idUser=current_user.id).order_by(Reserva.criado_em.asc()).all()
    return render_template('guest/bookings.html', bookings=my_bookings)


@guest_bp.route('/bookings/<int:booking_id>/cancel', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    booking = Reserva.query.get_or_404(booking_id)
    quarto = booking.quarto

    if booking.idUser != current_user.id and current_user.role != 'admin':
        flash('Não tem permissão para cancelar esta reserva.', 'danger')
        return redirect(url_for('guest.bookings'))

    if booking.estado == EstadoReserva.confirmada:
        booking.estado = EstadoReserva.cancelada
        quarto.estado = EstadoQuarto.disponivel
        if date.today() > booking.check_in:
            dias_restantes = max((booking.check_out - date.today()).days, 0)
            valor_reembolso = quarto.preco_base * dias_restantes
        else:
            valor_reembolso = booking.total_price

        pagamento = Pagamento.query.filter_by(idReserva=booking.id).first()
        if pagamento:
            pagamento.estado = 'reembolsado'
            pagamento.valor = valor_reembolso
            pagamento.dataPagamento = datetime.now()

        flash(f'A sua reserva foi cancelada e vai ser reembolsado em {valor_reembolso:.2f} €.', 'success')
    elif booking.estado == EstadoReserva.pendente:
        booking.estado = EstadoReserva.cancelada
        quarto.estado = EstadoQuarto.disponivel
        pagamento = Pagamento.query.filter_by(idReserva=booking.id).first()
        if pagamento:
            pagamento.estado = 'cancelado'
        flash('A sua reserva foi cancelada.', 'success')
    else:
        flash('A reserva já não pode ser cancelada.', 'warning')

    db.session.commit()
    return redirect(url_for('guest.bookings'))



@guest_bp.route('/bookings/<int:booking_id>/pagar', methods=['POST'])
@login_required
def pay_booking(booking_id):
    booking = Reserva.query.filter_by(id=booking_id, idUser=current_user.id).first_or_404()

    if booking.estado != EstadoReserva.pendente:
        flash('Esta reserva já não se encontra pendente.', 'warning')
        return redirect(url_for('guest.bookings'))

    nome_faturacao = request.form.get('nomeFaturacao', '').strip() or current_user.name
    email_faturacao = request.form.get('emailFaturacao', '').strip() or current_user.email
    numero_cartao = ''.join(ch for ch in request.form.get('numeroCartao', '') if ch.isdigit())

    if not nome_faturacao or not email_faturacao or len(numero_cartao) < 12:
        flash('Preencha corretamente os dados de pagamento.', 'danger')
        return render_template('guest/ato_pagamento.html', booking=booking, pagamento=booking.pagamento)

    pagamento = Pagamento.query.filter_by(idReserva=booking.id).first()
    if pagamento is None:
        pagamento = Pagamento(
            idUser=current_user.id,
            idReserva=booking.id,
            valor=booking.total_price,
        )
        db.session.add(pagamento)

    pagamento.nomeFaturacao = nome_faturacao
    pagamento.emailFaturacao = email_faturacao
    pagamento.valor = booking.total_price
    pagamento.estado = 'pago'
    pagamento.dataPagamento = datetime.now()
    booking.estado = EstadoReserva.confirmada

    db.session.commit()
    flash('Pagamento efetuado com sucesso.', 'success')
    return redirect(url_for('guest.pagamentos'))


@guest_bp.route('/bookings/<int:booking_id>/fatura', methods=['POST'])
@login_required
def recipe(booking_id):
    pagamento = Pagamento.query.get_or_404(booking_id)

    if pagamento.idUser != current_user.id and current_user.role != 'admin':
        flash('Não tem permissão para emitir esta fatura.', 'danger')
        return redirect(url_for('guest.pagamentos'))

    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=A4)
    width, height = A4
    c.setTitle(f'Fatura_{pagamento.id}.pdf')
    c.setFillColor(colors.HexColor('#7979e3'))
    c.rect(0, height - 90, width, 100, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.drawImage("C:/25361 - Programação em Python/10794/BrunoMota(hotel)/reserva_quartos_hotel/Hotel/static/img/HotelAgency.png", 10, 200, width=70, preserveAspectRatio=True, mask='auto')
    c.setFont('Helvetica-Bold', 24)
    c.drawString(90, height - 50, 'HotelAgency')
    c.setFont('Helvetica', 11)
    c.drawString(90, height - 70, 'Fatura / Recibo de pagamento')



    c.setFillColor(colors.black)
    c.setStrokeColor(colors.HexColor('#d1d5db'))
    c.roundRect(35, height - 245, width - 70, 125, 10, stroke=1, fill=0)
    c.roundRect(35, height - 410, width - 70, 140, 10, stroke=1, fill=0)
    c.roundRect(35, height - 590, width - 70, 145, 10, stroke=1, fill=0)

    c.setFont('Helvetica-Bold', 12)
    c.drawString(50, height - 140, 'Dados da fatura')
    _draw_label_value(c, 'Nº da fatura:', f'FA-{pagamento.id:05d}', 50, height - 165)
    _draw_label_value(c, 'Data de emissao:', _format_date(pagamento.dataPagamento), 50, height - 185)
    _draw_label_value(c, 'Estado:', pagamento.estado.capitalize(), 50, height - 205)

    c.setFont('Helvetica-Bold', 12)
    c.drawString(50, height - 285, 'Dados do cliente')
    _draw_label_value(c, 'Cliente:', pagamento.nomeFaturacao or pagamento.user.name, 50, height - 310)
    _draw_label_value(c, 'Email:', pagamento.emailFaturacao or pagamento.user.email, 50, height - 330)
    _draw_label_value(c, 'Nº de cliente:', pagamento.idUser, 50, height - 350)
    _draw_label_value(c, 'Reserva:', pagamento.idReserva, 50, height - 370)


    reserva = pagamento.reserva
    quarto = reserva.quarto
    noites = max((reserva.check_out - reserva.check_in).days, 1)

    c.setFont('Helvetica-Bold', 12)
    c.drawString(50, height - 460, 'Detalhes da estadia')
    _draw_label_value(c, 'Quarto:', quarto.numero, 50, height - 485)
    _draw_label_value(c, 'Tipo:', quarto.tipo.title(), 50, height - 505)
    _draw_label_value(c, 'Check-in:', _format_date(reserva.check_in), 50, height - 525)
    _draw_label_value(c, 'Check-out:', _format_date(reserva.check_out), 50, height - 545)
    _draw_label_value(c, 'Noites:', noites, 50, height - 565)

    c.setFont('Helvetica-Bold', 12)
    c.drawString(50, height - 620, 'Resumo financeiro')
    c.line(50, height - 635, width - 50, height - 635)
    c.setFont('Helvetica-Bold', 10)
    c.drawString(50, height - 655, 'Descricao')
    c.drawString(330, height - 655, 'Qt.')
    c.drawRightString(width - 50, height - 655, 'Valor')

    c.setFont('Helvetica', 10)
    c.drawString(50, height - 680, f'Estadia - quarto {quarto.numero} ({quarto.tipo.title()})')
    c.drawString(335, height - 680, str(noites))
    c.drawRightString(width - 50, height - 680, f'{pagamento.valor:.2f} €')

    c.setFont('Helvetica-Bold', 12)
    c.drawRightString(width - 50, height - 720, f'Total pago: {pagamento.valor:.2f} €')

    c.setFont('Helvetica', 9)
    c.setFillColor(colors.HexColor('#6b7280'))
    c.drawString(40, 35, 'Documento gerado automaticamente pelo sistema HotelAgency.')
    c.drawRightString(width - 40, 35, 'Obrigado pela sua preferência.')

    c.save()
    pdf_buffer.seek(0)
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=f'fatura_{pagamento.id}.pdf',
        mimetype='application/pdf',
    )

def _draw_label_value(c, label, value, x, y, label_width=140):
    c.setFont('Helvetica-Bold', 10)
    c.drawString(x, y, label)
    c.setFont('Helvetica', 10)
    c.drawString(x + label_width, y, str(value))


def _format_date(value):
    if not value:
        return '—'
    if isinstance(value, datetime):
        return value.strftime('%d-%m-%Y %H:%M')
    return value.strftime('%d-%m-%Y')

@guest_bp.route('/services', methods=['GET', 'POST'])
@login_required
def services():
    if request.method == 'POST':
        req_type = request.form.get('type')
        description = request.form.get('description')
        #html.escape(description)
        active_booking = Reserva.query.filter_by(idUser=current_user.id, estado='checked_in').first()
        sr = Pedido(
            user_id=current_user.id,
            booking_id=active_booking.id if active_booking else None,
            tipo=req_type,
            descricao=description,
        )
        db.session.add(sr)
        db.session.commit()
        flash('Pedido submetido com sucesso!', 'success')
        return redirect(url_for('guest.services'))

    my_requests = Pedido.query.filter_by(user_id=current_user.id).order_by(Pedido.criado_em.desc()).all()
    return render_template('guest/services.html', requests=my_requests)


@guest_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = User.query.filter_by(id=User.id).first_or_404()
    return render_template('guest/profile.html', User=user)


@guest_bp.route('/pagamentos')
@login_required
def pagamentos():
    if current_user.role == 'admin':
        pagamento = Pagamento.query.all()
    else:
        pagamento = Pagamento.query.filter_by(idUser=current_user.id)
    return render_template('guest/pagamento.html', pagamentos=pagamento)


@guest_bp.route('/table', methods=['GET', 'POST'])
@login_required
def table_user():
    utilizadores = User.query.filter_by(role='guest')
    return render_template('guest/tabela_user.html', users=utilizadores)


def _obter_reservas_ativas_do_utilizador(user_id):
    hoje = date.today()
    return Reserva.query.filter(
        Reserva.idUser == user_id,
        Reserva.check_out >= hoje,
        Reserva.estado.in_([EstadoReserva.pendente, EstadoReserva.confirmada]),
    ).all()

def _pode_inativar_conta(user):
    reservas_ativas = _obter_reservas_ativas_do_utilizador(user.id)
    reservas_confirmadas = [reserva for reserva in reservas_ativas if reserva.estado == EstadoReserva.confirmada]

    if reservas_confirmadas:
        return False, 'Nao é possivel inativar a conta porque existem reservas confirmadas.'

    reservas_pendentes = [reserva for reserva in reservas_ativas if reserva.estado == EstadoReserva.pendente]

    for reserva in reservas_pendentes:
        reserva.estado = EstadoReserva.cancelada
        if reserva.quarto:
            reserva.quarto.estado = EstadoQuarto.disponivel
        pagamento = Pagamento.query.filter_by(idReserva=reserva.id).first()
        if pagamento and pagamento.estado != 'pago':
            pagamento.estado = 'cancelado'
            pagamento.dataPagamento = None

    return True, None


def _normalizar_estado_utilizador(estado):
    return EstadoUser.ativo if estado == 'ativo' else EstadoUser.inativo

@guest_bp.route('/alterar-estado-utilizador/<int:user_id>', methods=['POST'])
@login_required
def alterar_estado_utilizador(user_id):
    user = User.query.get_or_404(user_id)
    novo_estado = request.form.get('estado', '').strip()

    if novo_estado not in {'ativo', 'inativo'}:
        flash('Estado invalido.', 'danger')
        return redirect(url_for('guest.table_user'))

    estado_enum = _normalizar_estado_utilizador(novo_estado)
    if user.estado == estado_enum:
        return redirect(url_for('guest.table_user'))

    if estado_enum == EstadoUser.inativo:
        pode_inativar, mensagem = _pode_inativar_conta(user)
        if not pode_inativar:
            db.session.rollback()
            flash(mensagem, 'danger')
            return redirect(url_for('guest.table_user'))

    user.estado = estado_enum
    db.session.commit()

    flash(
        'Conta ativada com sucesso.' if user.estado == EstadoUser.ativo else 'Conta inativada com sucesso.',
        'success',
    )
    return redirect(url_for('guest.table_user'))

@guest_bp.route("/editar_utilizador/<int:user_id>", methods=["GET","POST"])
@login_required
def editar_utilizador(user_id):

    user = User.query.get(user_id)
    
    if request.method=='POST':
      user.name = request.form.get("name", "").strip()
      user.username = request.form.get("username", "").strip()
      user.email = request.form.get("email", "").strip()
      data_str = request.form.get("dataNascimento", "")
      user.estado = request.form.get("estado", "")
      user.nova_password = request.form.get("password", "")

      estado_enum = _normalizar_estado_utilizador(user.estado)
      if estado_enum == EstadoUser.inativo:
        pode_inativar, mensagem = _pode_inativar_conta(user)
        if not pode_inativar:
            db.session.rollback()
            flash(mensagem, 'danger')
            return redirect(url_for('guest.profile'))

        user.estado = estado_enum
        db.session.commit()
        
        return redirect(url_for('auth.logout'))

    return render_template('/guest/profile.html', user=user)
