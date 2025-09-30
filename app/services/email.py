from __future__ import annotations

from flask import current_app, render_template
from flask_mailman import EmailMessage


def send_confirmation_email(email: str, token: str) -> None:
    subject = "Confirme seu e-mail EFTX"
    confirm_url = current_app.url_for("auth.confirm_email", token=token, _external=True)
    html_body = render_template("emails/confirm_email.html", confirm_url=confirm_url)
    message = EmailMessage(subject=subject, body=html_body, to=[email])
    message.content_subtype = "html"
    message.send(fail_silently=True)


def send_admin_cnpj_alert(email: str, user_name: str) -> None:
    subject = "Novo usuário aguardando validação de CNPJ"
    html_body = render_template("emails/admin_cnpj_alert.html", email=email, user_name=user_name)
    admins = current_app.config.get("ADMIN_ALERT_RECIPIENTS")
    if not admins:
        return
    message = EmailMessage(subject=subject, body=html_body, to=admins)
    message.content_subtype = "html"
    message.send(fail_silently=True)
