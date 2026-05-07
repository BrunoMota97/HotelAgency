from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, Pedido
from datetime import datetime

staff_bp = Blueprint('staff', __name__, url_prefix='/staff')


@staff_bp.route('/dashboard')
@login_required
def dashboard():
    pending = Pedido.query.filter_by(estado='pendente').order_by(Pedido.criado_em).all()
    in_progress = Pedido.query.filter_by(estado='em_andamento').order_by(Pedido.criado_em).all()
    completed = Pedido.query.filter_by(estado='resolvido').order_by(Pedido.updated_at.desc()).limit(10).all()
    return render_template('staff/dashboard.html',
                           pending=pending,
                           in_progress=in_progress,
                           completed=completed)


@staff_bp.route('/requests/<int:req_id>/update', methods=['POST'])
@login_required
def update_request(req_id):
    sr = Pedido.query.get_or_404(req_id)
    new_status = request.form.get('status')
    if new_status in ['pendente', 'em_andamento', 'resolvido']:
        sr.estado = new_status
        sr.updated_at = datetime.now()
        #sr.descricao="Feito"
        db.session.commit()
        resposta = "Já vai a caminho"
        flash(f'Pedido nº{sr.id} mudado para "{new_status.replace("_", " ")}".', 'success')
        return redirect(url_for('staff.dashboard'))
