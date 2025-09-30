from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, SelectField, StringField, SubmitField
from wtforms.validators import Email, EqualTo, Length, Optional, Regexp, DataRequired

from ..models import SexEnum


class RegistrationForm(FlaskForm):
    full_name = StringField("Nome completo", validators=[DataRequired(), Length(min=3, max=255)])
    sex = SelectField(
        "Sexo",
        choices=[("", "Selecionar"), [
            ("M", "Masculino"),
            ("F", "Feminino"),
            ("X", "Nao binario"),
        ]],
        validators=[Optional()],
    )
    email = StringField("E-mail", validators=[DataRequired(), Email(), Length(max=255)])
    phone = StringField("Telefone", validators=[Optional(), Length(max=32)])
    address_line = StringField("Endereço", validators=[Optional(), Length(max=255)])
    city = StringField("Cidade", validators=[Optional(), Length(max=128)])
    state = StringField("Estado", validators=[Optional(), Length(max=64)])
    postal_code = StringField("CEP", validators=[Optional(), Length(max=16)])
    country = StringField("País", validators=[Optional(), Length(max=64)])
    cpf = StringField(
        "CPF",
        validators=[
            Optional(),
            Regexp(r"^\d{11}$", message="Informe 11 dígitos sem pontuação"),
        ],
    )
    cnpj = StringField(
        "CNPJ",
        validators=[
            Optional(),
            Regexp(r"^\d{14}$", message="Informe 14 dígitos sem pontuação"),
        ],
    )
    password = PasswordField(
        "Senha",
        validators=[DataRequired(), Length(min=10)],
    )
    confirm_password = PasswordField(
        "Confirme a senha",
        validators=[DataRequired(), EqualTo("password", message="As senhas devem coincidir.")],
    )
    accept_terms = BooleanField("Aceito os termos", validators=[DataRequired()])
    submit = SubmitField("Criar conta")


class LoginForm(FlaskForm):
    email = StringField("E-mail", validators=[DataRequired(), Email()])
    password = PasswordField("Senha", validators=[DataRequired()])
    remember = BooleanField("Lembrar")
    submit = SubmitField("Entrar")


class EmailTokenForm(FlaskForm):
    token = StringField("Token", validators=[DataRequired(), Length(min=10, max=255)])
    submit = SubmitField("Confirmar")


class ResendConfirmationForm(FlaskForm):
    email = StringField("E-mail", validators=[DataRequired(), Email()])
    submit = SubmitField("Reenviar")
