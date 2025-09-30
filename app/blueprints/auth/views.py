from __future__ import annotations

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user

from ...extensions import db, limiter
from ...forms.auth import LoginForm, RegistrationForm, ResendConfirmationForm
from ...models import SexEnum, User
from ...services.email import send_admin_cnpj_alert, send_confirmation_email
from ...utils.security import confirm_email_token, generate_email_token, hash_password, verify_password


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

auth_limit = lambda: current_app.config.get("RATE_LIMIT_AUTH", "5 per minute")


@auth_bp.route("/register", methods=["GET", "POST"])
@limiter.limit(auth_limit)
def register() -> str:
    if current_user.is_authenticated:
        return redirect(url_for("projects.dashboard"))

    form = RegistrationForm()
    if form.validate_on_submit():
        if not form.cpf.data and not form.cnpj.data:
            form.cpf.errors.append("Informe CPF ou CNPJ.")
            form.cnpj.errors.append("Informe CPF ou CNPJ.")
            return render_template("auth/register.html", form=form)

        if User.query.filter_by(email=form.email.data.lower()).first():
            form.email.errors.append("E-mail já cadastrado.")
            return render_template("auth/register.html", form=form)

        if form.cpf.data and User.query.filter_by(cpf=form.cpf.data).first():
            form.cpf.errors.append("CPF já cadastrado.")
            return render_template("auth/register.html", form=form)

        if form.cnpj.data and User.query.filter_by(cnpj=form.cnpj.data).first():
            form.cnpj.errors.append("CNPJ já cadastrado.")
            return render_template("auth/register.html", form=form)

        user = User(
            email=form.email.data.lower(),
            password_hash=hash_password(form.password.data),
            full_name=form.full_name.data,
            sex=SexEnum(form.sex.data) if form.sex.data else None,
            phone=form.phone.data or None,
            address_line=form.address_line.data or None,
            city=form.city.data or None,
            state=form.state.data or None,
            postal_code=form.postal_code.data or None,
            country=form.country.data or "Brasil",
            cpf=form.cpf.data or None,
            cnpj=form.cnpj.data or None,
        )
        db.session.add(user)
        db.session.commit()

        token = generate_email_token(user.email)
        send_confirmation_email(user.email, token)
        if user.cnpj:
            send_admin_cnpj_alert(user.email, user.full_name)

        flash("Conta criada! Confirme seu e-mail.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form)


@auth_bp.route("/confirm/<token>")
@limiter.limit(auth_limit)
def confirm_email(token: str):
    email = confirm_email_token(token)
    if not email:
        flash("Token inválido ou expirado.", "danger")
        return redirect(url_for("auth.login"))

    user = User.query.filter_by(email=email.lower()).first()
    if not user:
        flash("Usuário não encontrado.", "danger")
        return redirect(url_for("auth.register"))

    if not user.email_confirmed:
        user.email_confirmed = True
        db.session.commit()
        flash("E-mail confirmado!", "success")
    else:
        flash("E-mail já confirmado.", "info")

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
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user:
            token = generate_email_token(user.email)
            send_confirmation_email(user.email, token)
        flash("Se o e-mail existir, reenviamos a confirmação.", "info")
        return redirect(url_for("auth.login"))

    return render_template("auth/resend.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit(auth_limit)
def login():
    if current_user.is_authenticated:
        return redirect(url_for("projects.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if not user or not verify_password(user.password_hash, form.password.data):
            flash("Credenciais inválidas.", "danger")
        elif not user.email_confirmed:
            flash("Confirme seu e-mail antes de entrar.", "warning")
            return redirect(url_for("auth.resend_confirmation"))
        elif not user.is_active:
            flash("Conta desativada.", "danger")
        else:
            login_user(user, remember=form.remember.data)
            return redirect(request.args.get("next") or url_for("projects.dashboard"))
    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
def logout():
    if current_user.is_authenticated:
        logout_user()
        flash("Sessão encerrada.", "info")
    return redirect(url_for("public.home"))
