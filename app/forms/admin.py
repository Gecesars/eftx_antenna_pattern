from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import FileField, FloatField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Optional

from ..models import PatternType


class AntennaForm(FlaskForm):
    name = StringField("Nome", validators=[DataRequired()])
    model_number = StringField("Modelo", validators=[Optional()])
    description = TextAreaField("Descrição", validators=[Optional()])
    nominal_gain_dbd = FloatField("Ganho nominal (dBd)", validators=[Optional()])
    polarization = StringField("Polarização", validators=[Optional()])
    frequency_min_mhz = FloatField("Frequência mínima (MHz)", validators=[Optional()])
    frequency_max_mhz = FloatField("Frequência máxima (MHz)", validators=[Optional()])
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
