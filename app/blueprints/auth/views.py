from __future__ import annotations

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for, jsonify
from flask_login import current_user, login_user, logout_user

from flask_jwt_extended import create_access_token, create_refresh_token, current_user as jwt_current_user, get_jwt_identity, jwt_required

from ...extensions import db, limiter
from ...forms.auth import LoginForm, RegistrationForm, ResendConfirmationForm
from ...models import User
from ...services.email import send_admin_cnpj_alert, send_confirmation_email
from ...utils.security import confirm_email_token, generate_email_token, hash_password, password_needs_rehash, verify_password


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

auth_limit = lambda: current_app.config.get("RATE_LIMIT_AUTH", "5 per minute")


@auth_bp.route("/register", methods=["GET", "POST"])
@limiter.limit(auth_limit)
def register() -> str:
    logger = current_app.logger

    if current_user.is_authenticated:
        logger.debug("Usuario %s tentou acessar registro estando autenticado", current_user.get_id())
        return redirect(url_for("projects.dashboard"))

    form = RegistrationForm()
    if form.validate_on_submit():
        logger.info("Processando novo cadastro para %s", form.email.data)

        user = User(
            email=form.email.data,
            password_hash=hash_password(form.password.data),
            full_name=form.full_name.data,
            phone=form.phone.data,
            address_line=form.address_line.data,
            city=form.city.data,
            state=form.state.data,
            postal_code=form.postal_code.data,
            country=form.country.data,
            cpf=form.cpf.data or None,
            cnpj=form.cnpj.data or None,
        )
        db.session.add(user)
        db.session.commit()
        logger.info("Usuario %s registrado com sucesso (id=%s)", user.email, user.id)

        token = generate_email_token(user.email)
        send_confirmation_email(user.email, token)
        if user.cnpj:
            send_admin_cnpj_alert(user.email, user.full_name)

        success_message = "Cadastro realizado! Enviamos um link de confirmação para o seu e-mail. Confirme para liberar o acesso."
        blank_form = RegistrationForm()
        return render_template("auth/register.html", form=blank_form, success_message=success_message, login_url=url_for("auth.login"))

    elif request.method == "POST":  # formulario enviado com erros
        logger.warning("Falha na validacao do cadastro: %s", form.errors)

    return render_template("auth/register.html", form=form, login_url=url_for("auth.login"))


@auth_bp.route("/confirm/<token>")
@limiter.limit(auth_limit)
def confirm_email(token: str):
    logger = current_app.logger
    email = confirm_email_token(token)
    if not email:
        logger.warning("Token de confirmacao invalido ou expirado: %s", token)
        flash("Token invalido ou expirado.", "danger")
        return redirect(url_for("auth.login"))

    user = User.query.filter_by(email=email.lower()).first()
    if not user:
        logger.warning("Token %s referenciou usuario inexistente (%s)", token, email)
        flash("Usuario nao encontrado.", "danger")
        return redirect(url_for("auth.register"))

    if not user.email_confirmed:
        user.email_confirmed = True
        db.session.commit()
        logger.info("Email confirmado para %s", user.email)
        flash("Email confirmado!", "success")
    else:
        logger.info("Email %s ja estava confirmado", user.email)
        flash("Email ja confirmado.", "info")

    if current_user.is_authenticated:
        return redirect(url_for("projects.dashboard"))
    return redirect(url_for("auth.login"))


@auth_bp.route("/resend", methods=["GET", "POST"])
@limiter.limit(auth_limit)
def resend_confirmation():
    if current_user.is_authenticated and current_user.email_confirmed:
        return redirect(url_for("projects.dashboard"))

    form = ResendConfirmationForm()
    if form.validate_on_submit():
        email_input = form.email.data.strip().lower()
        user = User.query.filter_by(email=email_input).first()
        if user:
            current_app.logger.info("Reenviando confirmacao para %s", user.email)
            token = generate_email_token(user.email)
            send_confirmation_email(user.email, token)
        else:
            current_app.logger.warning("Solicitado reenvio para email nao cadastrado: %s", email_input)
        flash("Se o email existir, reenviamos a confirmacao.", "info")
        return redirect(url_for("auth.login"))

    elif request.method == "POST":
        current_app.logger.warning("Erro de validacao ao reenviar confirmacao: %s", form.errors)

    return render_template("auth/resend.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit(auth_limit)
def login():
    if current_user.is_authenticated:
        return redirect(url_for("projects.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        email_input = form.email.data.strip().lower()
        user = User.query.filter_by(email=email_input).first()
        if not user or not verify_password(user.password_hash, form.password.data):
            current_app.logger.warning("Login invalido para %s", email_input)
            flash("Credenciais invalidas.", "danger")
        elif not user.email_confirmed:
            current_app.logger.info("Login bloqueado: email nao confirmado (%s)", user.email)
            flash("Confirme seu email antes de entrar.", "warning")
            return redirect(url_for("auth.resend_confirmation"))
        elif not user.is_active:
            current_app.logger.warning("Conta inativa tentou login: %s", user.email)
            flash("Conta desativada.", "danger")
        else:
            if password_needs_rehash(user.password_hash):
                user.password_hash = hash_password(form.password.data)
                db.session.commit()
            login_user(user, remember=form.remember.data)
            current_app.logger.info("Login bem-sucedido para %s", user.email)
            return redirect(request.args.get("next") or url_for("projects.dashboard"))
    elif request.method == "POST":
        current_app.logger.warning("Erro de validacao no login: %s", form.errors)
    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
def logout():
    if current_user.is_authenticated:
        current_app.logger.info("Logout realizado por %s", current_user.email)
        logout_user()
        flash("Sessao encerrada.", "info")
    return redirect(url_for("public.home"))



@auth_bp.route("/token", methods=["POST"])
@limiter.limit(auth_limit)
def issue_token():
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""
    if not email or not password:
        return jsonify({"error": "invalid_request", "message": "Informe email e senha."}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not verify_password(user.password_hash, password):
        current_app.logger.warning("Falha ao gerar token para %s", email)
        return jsonify({"error": "invalid_credentials"}), 401
    if not user.email_confirmed:
        return jsonify({"error": "email_not_confirmed"}), 403
    if not user.is_active:
        return jsonify({"error": "account_inactive"}), 403

    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
        db.session.commit()

    claims = {"role": user.role}
    access_token = create_access_token(identity=str(user.id), additional_claims=claims)
    refresh_token = create_refresh_token(identity=str(user.id), additional_claims=claims)
    current_app.logger.info("Token emitido para %s", user.email)
    return jsonify({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "email_confirmed": user.email_confirmed,
        },
    })


@auth_bp.route("/token/refresh", methods=["POST"])
@limiter.limit(auth_limit)
@jwt_required(refresh=True)
def refresh_access_token():
    identity = get_jwt_identity()
    role = getattr(jwt_current_user, "role", None)
    claims = {"role": role} if role else None
    access_token = create_access_token(identity=identity, additional_claims=claims)
    response = {
        "access_token": access_token,
        "token_type": "Bearer",
    }
    user = jwt_current_user
    if user:
        response["user"] = {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "email_confirmed": user.email_confirmed,
        }
    return jsonify(response)
