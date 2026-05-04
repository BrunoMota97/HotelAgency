import os
import secrets

from flask import current_app, flash, redirect, request, session
from werkzeug.security import safe_join


CSRF_SESSION_KEY = "_csrf_token"


def csrf_token():
    if CSRF_SESSION_KEY not in session:
        session[CSRF_SESSION_KEY] = secrets.token_urlsafe(32)

    return session[CSRF_SESSION_KEY]


def init_security(app):
    app.jinja_env.globals["csrf_token"] = csrf_token

    @app.before_request
    def validar_csrf():
        if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
            return None

        token_sessao = session.get(CSRF_SESSION_KEY)
        token_pedido = request.form.get("csrf_token") or request.headers.get("X-CSRFToken")

        if token_sessao and secrets.compare_digest(token_sessao, token_pedido or ""):
            return None

        flash("Pedido invalido ou expirado. Tenta novamente.", "danger")
        return redirect(request.referrer or "/")

    @app.after_request
    def adicionar_headers_seguranca(response):
       
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
        # Em producao, remover/mascarar o Server e normalmente feito no Nginx, Apache ou Gunicorn.
        response.headers.pop("Server", None)
        return response


def caminho_seguro(filename, pasta_obrigatoria=None):
    if not filename:
        return None

    filename = filename.replace("\\", "/").lstrip("/")
    if os.path.isabs(filename) or ".." in filename.split("/"):
        return None

    caminho = safe_join(current_app.static_folder, filename)
    if not caminho:
        return None

    static_root = os.path.abspath(current_app.static_folder)
    caminho_abs = os.path.abspath(caminho)

    if os.path.commonpath([static_root, caminho_abs]) != static_root:
        return None

    if pasta_obrigatoria:
        pasta_abs = os.path.abspath(os.path.join(current_app.static_folder, pasta_obrigatoria))
        if os.path.commonpath([pasta_abs, caminho_abs]) != pasta_abs:
            return None

    if not os.path.isfile(caminho_abs):
        return None

    return filename


def imagem_segura(imagem, default=None):
    default = default or current_app.config["ESPACO_IMAGEM_DEFAULT"]
    imagem = (imagem or default).replace("\\", "/").lstrip("/")

    if not imagem.startswith("img/"):
        return default

    return caminho_seguro(imagem, "img") or default