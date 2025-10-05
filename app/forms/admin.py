from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import FileField, FloatField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, NumberRange, Optional

from ..models import PatternType


class AntennaForm(FlaskForm):
    name = StringField("Nome", validators=[DataRequired()])
    model_number = StringField("Modelo", validators=[Optional()])
    description = TextAreaField("Descrição", validators=[Optional()])
    nominal_gain_dbd = FloatField("Ganho nominal (dBd)", validators=[Optional()])
    polarization = StringField("Polarização", validators=[Optional()])
    frequency_min_mhz = FloatField("Frequência mínima (MHz)", validators=[Optional()])
    frequency_max_mhz = FloatField("Frequência máxima (MHz)", validators=[Optional()])
    manufacturer = StringField("Fabricante", validators=[Optional()])
    datasheet_path = StringField("Caminho do datasheet", validators=[Optional()])
    gain_table = TextAreaField("Tabela de ganho (JSON)", validators=[Optional()])
    category = SelectField(
        "Categoria",
        choices=[("TV", "TV"), ("FM", "FM"), ("Microondas", "Microondas"), ("Telecom", "Telecom")],
        validators=[Optional()],
    )
    thumbnail_path = StringField("Thumbnail", validators=[Optional()])
    submit = SubmitField("Salvar")


class CableForm(FlaskForm):
    display_name = StringField("Nome de exibição", validators=[DataRequired()])
    model_code = StringField("Código/modelo", validators=[DataRequired()])
    size_inch = StringField("Bitola (pol)", validators=[Optional()])
    impedance_ohms = FloatField("Impedancia (ohms)", validators=[Optional(), NumberRange(min=1)])
    manufacturer = StringField("Fabricante", validators=[Optional()])
    notes = TextAreaField("Notas", validators=[Optional()])
    # Campos estendidos
    frequency_min_mhz = FloatField("Frequência mínima (MHz)", validators=[Optional(), NumberRange(min=0)])
    frequency_max_mhz = FloatField("Frequência máxima (MHz)", validators=[Optional(), NumberRange(min=0)])
    velocity_factor = FloatField("Fator de velocidade", validators=[Optional(), NumberRange(min=0, max=1.0)])
    max_power_w = FloatField("Potência máx (W)", validators=[Optional(), NumberRange(min=0)])
    min_bend_radius_mm = FloatField("Raio mínimo de curvatura (mm)", validators=[Optional(), NumberRange(min=0)])
    outer_diameter_mm = FloatField("Diâmetro externo (mm)", validators=[Optional(), NumberRange(min=0)])
    weight_kg_per_km = FloatField("Peso (kg/km)", validators=[Optional(), NumberRange(min=0)])
    vswr_max = FloatField("VSWR máx", validators=[Optional(), NumberRange(min=1)])
    shielding_db = FloatField("Blindagem (dB)", validators=[Optional(), NumberRange(min=0)])
    temperature_min_c = FloatField("Temperatura mín (°C)", validators=[Optional()])
    temperature_max_c = FloatField("Temperatura máx (°C)", validators=[Optional()])
    conductor_material = StringField("Material condutor", validators=[Optional()])
    dielectric_material = StringField("Material dielétrico", validators=[Optional()])
    jacket_material = StringField("Capa (jacket)", validators=[Optional()])
    shielding_type = StringField("Tipo de blindagem", validators=[Optional()])
    conductor_diameter_mm = FloatField("Ø condutor (mm)", validators=[Optional(), NumberRange(min=0)])
    dielectric_diameter_mm = FloatField("Ø dielétrico (mm)", validators=[Optional(), NumberRange(min=0)])
    attenuation_db_per_100m_curve = TextAreaField("Curva de atenuação (JSON)", validators=[Optional()])
    datasheet_path = StringField("Caminho do datasheet", validators=[Optional()])
    submit = SubmitField("Salvar")


class PatternUploadForm(FlaskForm):
    pattern_type = SelectField(
        "Tipo",
        coerce=str,
        choices=[(PatternType.HRP.value, "HRP"), (PatternType.VRP.value, "VRP")],
        validators=[DataRequired()],
    )
    file = FileField("Arquivo CSV/TSV", validators=[DataRequired()])
    submit = SubmitField("Importar")
