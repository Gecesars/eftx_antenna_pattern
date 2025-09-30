from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import FloatField, IntegerField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, NumberRange, Optional


class ProjectForm(FlaskForm):
    name = StringField("Nome do projeto", validators=[DataRequired()])
    antenna_id = SelectField("Antena", coerce=str, validators=[DataRequired()])
    frequency_mhz = FloatField("Frequência (MHz)", validators=[DataRequired(), NumberRange(min=30)])
    tx_power_w = FloatField("Potência TX (W)", validators=[DataRequired(), NumberRange(min=0.1)])
    tower_height_m = FloatField("Altura torre (m)", validators=[DataRequired(), NumberRange(min=0)])
    cable_type = StringField("Tipo de cabo", validators=[Optional()])
    cable_length_m = FloatField("Comprimento cabo (m)", validators=[Optional(), NumberRange(min=0)])
    splitter_loss_db = FloatField("Perda splitter (dB)", validators=[Optional(), NumberRange(min=0)])
    connector_loss_db = FloatField("Perda conectores (dB)", validators=[Optional(), NumberRange(min=0)])
    vswr_target = FloatField("VSWR alvo", validators=[Optional(), NumberRange(min=1, max=5)])

    v_count = IntegerField("Elementos verticais", validators=[DataRequired(), NumberRange(min=1, max=16)])
    v_spacing_m = FloatField("Espaçamento vertical (m)", validators=[Optional(), NumberRange(min=0)])
    v_beta_deg = FloatField("Beta vertical (°)", validators=[Optional()])
    v_level_amp = FloatField("Nível vertical", validators=[Optional(), NumberRange(min=0)])
    v_norm_mode = SelectField(
        "Normalização vertical",
        choices=[("max", "Máximo"), ("first", "Primeiro"), ("sum", "Soma")],
        validators=[DataRequired()],
    )

    h_count = IntegerField("Elementos horizontais", validators=[DataRequired(), NumberRange(min=1, max=36)])
    h_spacing_m = FloatField("Espaçamento horizontal (m)", validators=[Optional(), NumberRange(min=0)])
    h_beta_deg = FloatField("Beta horizontal (°)", validators=[Optional()])
    h_step_deg = FloatField("Passo horizontal (°)", validators=[Optional()])
    h_level_amp = FloatField("Nível horizontal", validators=[Optional(), NumberRange(min=0)])
    h_norm_mode = SelectField(
        "Normalização horizontal",
        choices=[("max", "Máximo"), ("first", "Primeiro"), ("sum", "Soma")],
        validators=[DataRequired()],
    )

    notes = TextAreaField("Notas", validators=[Optional()])
    submit = SubmitField("Salvar")
