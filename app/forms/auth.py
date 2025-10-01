from __future__ import annotations

import re

from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, Regexp, ValidationError

from ..models import User


class RegistrationForm(FlaskForm):
    full_name = StringField("Nome completo", validators=[DataRequired(), Length(min=3, max=255)])
    email = StringField("E-mail", validators=[DataRequired(), Email(), Length(max=255)])
    phone = StringField("Telefone", validators=[DataRequired(), Length(max=32)])
    address_line = StringField("Endereco", validators=[DataRequired(), Length(max=255)])
    city = StringField("Cidade", validators=[DataRequired(), Length(max=128)])
    state = StringField("Estado", validators=[DataRequired(), Length(max=64)])
    postal_code = StringField("CEP", validators=[DataRequired(), Length(max=16)])
    country = StringField("Pais", validators=[DataRequired(), Length(max=64)], default="Brasil")
    cpf = StringField(
        "CPF",
        validators=[
            Optional(),
            Regexp(r"^\d{11}$", message="Informe 11 digitos sem pontuacao"),
        ],
    )
    cnpj = StringField(
        "CNPJ",
        validators=[
            Optional(),
            Regexp(r"^\d{14}$", message="Informe 14 digitos sem pontuacao"),
        ],
    )
    password = PasswordField(
        "Senha",
        validators=[DataRequired(), Length(min=6)],
        render_kw={"autocomplete": "new-password"},
    )
    confirm_password = PasswordField(
        "Confirme a senha",
        validators=[DataRequired(), EqualTo("password", message="As senhas devem coincidir.")],
        render_kw={"autocomplete": "new-password"},
    )
    accept_terms = BooleanField("Aceito os termos", validators=[DataRequired()])
    submit = SubmitField("Criar conta")

    def validate(self, extra_validators=None):  # type: ignore[override]
        if not super().validate(extra_validators=extra_validators):
            return False

        # Normaliza campos de texto
        self.email.data = self.email.data.strip().lower()
        for field_name in ("full_name", "phone", "address_line", "city", "state", "postal_code", "country"):
            field = getattr(self, field_name)
            if field.data:
                field.data = field.data.strip()

        for doc_name in ("cpf", "cnpj"):
            field = getattr(self, doc_name)
            if field.data:
                field.data = re.sub(r"\D", "", field.data)

        if not self.cpf.data and not self.cnpj.data:
            msg = "Informe CPF ou CNPJ."
            self.cpf.errors.append(msg)
            self.cnpj.errors.append(msg)
            return False
        return True

    def validate_email(self, field):
        value = field.data.strip().lower()
        field.data = value
        existing = User.query.filter_by(email=value).first()
        if existing:
            raise ValidationError("E-mail ja cadastrado.")

    def validate_cpf(self, field):
        if field.data:
            digits = re.sub(r"\D", "", field.data)
            field.data = digits
            existing = User.query.filter_by(cpf=digits).first()
            if existing:
                raise ValidationError("CPF ja cadastrado.")

    def validate_cnpj(self, field):
        if field.data:
            digits = re.sub(r"\D", "", field.data)
            field.data = digits
            existing = User.query.filter_by(cnpj=digits).first()
            if existing:
                raise ValidationError("CNPJ ja cadastrado.")


class LoginForm(FlaskForm):
    email = StringField("E-mail", validators=[DataRequired(), Email()])
    password = PasswordField("Senha", validators=[DataRequired()], render_kw={"autocomplete": "current-password"})
    remember = BooleanField("Lembrar")
    submit = SubmitField("Entrar")


class EmailTokenForm(FlaskForm):
    token = StringField("Token", validators=[DataRequired(), Length(min=10, max=255)])
    submit = SubmitField("Confirmar")


class ResendConfirmationForm(FlaskForm):
    email = StringField("E-mail", validators=[DataRequired(), Email()])
    submit = SubmitField("Reenviar")
