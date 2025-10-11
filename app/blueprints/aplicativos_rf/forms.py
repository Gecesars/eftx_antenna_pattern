from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import (
    FloatField,
    HiddenField,
    IntegerField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import InputRequired, NumberRange, Optional


class BaseRFForm(FlaskForm):
    form_id = HiddenField(validators=[InputRequired()])


class SParametersForm(BaseRFForm):
    magnitude_value = FloatField("Magnitude", validators=[InputRequired(), NumberRange(min=0)], default=0.5)
    magnitude_unit = SelectField(
        "Unidade",
        choices=[("linear", "|S| (linear)"), ("db", "|S| (dB)")],
        default="linear",
    )
    phase_deg = FloatField("Fase (°)", validators=[InputRequired()], default=0.0)
    submit = SubmitField("Calcular")


class VSWRForm(BaseRFForm):
    input_kind = SelectField(
        "Entrada",
        choices=[("vswr", "VSWR"), ("rl", "Return Loss (dB)"), ("gamma", "|Γ|")],
        default="vswr",
    )
    value = FloatField("Valor", validators=[InputRequired(), NumberRange(min=0)])
    submit = SubmitField("Converter")


class DbLinearForm(BaseRFForm):
    direction = SelectField(
        "Conversão",
        choices=[("db_to_lin", "dB → Linear"), ("lin_to_db", "Linear → dB")],
        default="db_to_lin",
    )
    magnitude_kind = SelectField(
        "Tipo",
        choices=[("amplitude", "Amplitude (20·log10)"), ("power", "Potência (10·log10)")],
        default="amplitude",
    )
    value = FloatField("Valor", validators=[InputRequired()])
    submit = SubmitField("Converter")


class MicrostripForm(BaseRFForm):
    relative_permittivity = FloatField("εᵣ", validators=[InputRequired(), NumberRange(min=1.0)], default=4.3)
    target_impedance = FloatField("Z₀ (Ω)", validators=[InputRequired(), NumberRange(min=1.0)], default=50.0)
    substrate_height_value = FloatField("Altura h", validators=[InputRequired(), NumberRange(min=1e-6)], default=1.6)
    substrate_height_unit = SelectField(
        "Unidade h",
        choices=[("mm", "mm"), ("mil", "mil"), ("cm", "cm")],
        default="mm",
    )
    conductor_thickness_value = FloatField("Espessura t", validators=[Optional()], default=0.035)
    conductor_thickness_unit = SelectField(
        "Unidade t",
        choices=[("mm", "mm"), ("mil", "mil"), ("um", "µm")],
        default="mm",
    )
    submit = SubmitField("Calcular largura")


class WaveguideForm(BaseRFForm):
    mode = SelectField("Modo", choices=[("TE", "TE"), ("TM", "TM")], default="TE")
    index_m = IntegerField("m", validators=[InputRequired(), NumberRange(min=0)], default=1)
    index_n = IntegerField("n", validators=[InputRequired(), NumberRange(min=0)], default=0)
    dimension_a_value = FloatField("Dimensão a", validators=[InputRequired(), NumberRange(min=1e-6)], default=22.86)
    dimension_a_unit = SelectField(
        "Unidade a",
        choices=[("mm", "mm"), ("cm", "cm"), ("in", "pol"), ("m", "m")],
        default="mm",
    )
    dimension_b_value = FloatField("Dimensão b", validators=[InputRequired(), NumberRange(min=1e-6)], default=10.16)
    dimension_b_unit = SelectField(
        "Unidade b",
        choices=[("mm", "mm"), ("cm", "cm"), ("in", "pol"), ("m", "m")],
        default="mm",
    )
    frequency_value = FloatField("Frequência", validators=[Optional(), NumberRange(min=0)])
    frequency_unit = SelectField(
        "Unidade f",
        choices=[("ghz", "GHz"), ("mhz", "MHz"), ("khz", "kHz")],
        default="ghz",
    )
    submit = SubmitField("Calcular corte")


class TransmissionLineForm(BaseRFForm):
    mode = SelectField(
        "Cálculo",
        choices=[("length_to_phase", "Comprimento → Fase"), ("phase_to_length", "Fase → Comprimento")],
        default="length_to_phase",
    )
    frequency_value = FloatField("Frequência", validators=[InputRequired(), NumberRange(min=0)], default=100.0)
    frequency_unit = SelectField(
        "Unidade f",
        choices=[("mhz", "MHz"), ("ghz", "GHz"), ("khz", "kHz")],
        default="mhz",
    )
    length_value = FloatField("Comprimento", validators=[Optional(), NumberRange(min=0)])
    length_unit = SelectField(
        "Unidade L",
        choices=[("m", "m"), ("cm", "cm"), ("mm", "mm"), ("in", "pol"), ("ft", "ft")],
        default="m",
    )
    phase_value = FloatField("Fase (°)", validators=[Optional()])
    velocity_factor = FloatField("Fator de velocidade", validators=[Optional(), NumberRange(min=0, max=1)], default=0.85)
    eps_eff = FloatField("ε_eff", validators=[Optional(), NumberRange(min=1.0)])
    submit = SubmitField("Calcular")


class CableLossForm(BaseRFForm):
    cable_id = SelectField("Modelo de cabo", choices=[], validators=[InputRequired()])
    frequency_value = FloatField("Frequência", validators=[InputRequired(), NumberRange(min=0)], default=100.0)
    frequency_unit = SelectField(
        "Unidade f",
        choices=[("mhz", "MHz"), ("ghz", "GHz"), ("khz", "kHz")],
        default="mhz",
    )
    length_value = FloatField("Comprimento", validators=[InputRequired(), NumberRange(min=0)], default=50.0)
    length_unit = SelectField(
        "Unidade L",
        choices=[("m", "m"), ("cm", "cm"), ("ft", "ft"), ("in", "pol"), ("mm", "mm")],
        default="m",
    )
    connectors_losses = TextAreaField("Perdas dos conectores (dB)", description="Informe valores separados por vírgula ou linha.")
    submit = SubmitField("Calcular perda")


class KnifeEdgeForm(BaseRFForm):
    frequency_value = FloatField("Frequência", validators=[InputRequired(), NumberRange(min=0)], default=2.4)
    frequency_unit = SelectField(
        "Unidade f",
        choices=[("ghz", "GHz"), ("mhz", "MHz")],
        default="ghz",
    )
    d1_value = FloatField("Distância Tx → obstáculo", validators=[InputRequired(), NumberRange(min=0)], default=5000.0)
    d1_unit = SelectField(
        "Unidade d₁",
        choices=[("m", "m"), ("km", "km"), ("ft", "ft")],
        default="m",
    )
    d2_value = FloatField("Distância obstáculo → Rx", validators=[InputRequired(), NumberRange(min=0)], default=5000.0)
    d2_unit = SelectField(
        "Unidade d₂",
        choices=[("m", "m"), ("km", "km"), ("ft", "ft")],
        default="m",
    )
    tx_height = FloatField("Altura Tx (m)", validators=[InputRequired()], default=30.0)
    rx_height = FloatField("Altura Rx (m)", validators=[InputRequired()], default=20.0)
    obstacle_height = FloatField("Altura obstáculo (m)", validators=[InputRequired()], default=50.0)
    submit = SubmitField("Calcular difração")
