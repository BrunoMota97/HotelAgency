from models import db, User, Quarto


def seed_db():

    """rooms = [
        Quarto(numero='101', tipo='singular', preco_base=80, descricao='Quarto singular com visão sobre a cidade'),
        Quarto(numero='102', tipo='singular', preco_base=80, descricao='Quarto singular com vista para jardim'),
        Quarto(numero='201', tipo='casal', preco_base=130, descricao='Quarto de casal com balcão'),
        Quarto(numero='202', tipo='casal', preco_base=130, descricao='Quarto de casal com cama de rei'),
        Quarto(numero='301', tipo='misto', preco_base=250, descricao='Quarto de luxo com vista para o mar'),
        Quarto(numero='302', tipo='misto', preco_base=280, descricao='Suite presidencial com terraço privado'),
    ]
    for r in rooms:
        db.session.add(r)
    """
    db.session.commit()
    print('Base de dados criada com sucesso!')


if __name__ == '__main__':
    from app import create_app
    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()
        seed_db()
