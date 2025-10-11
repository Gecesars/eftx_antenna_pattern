from __future__ import annotations
import base64
import io
import math
from pathlib import Path
import re
from typing import Any, Sequence
from flask import current_app, flash, render_template, request
from flask_login import login_required
from matplotlib.figure import Figure

from ...extensions import db
from ...rs_core import diffraction_knife_edge, lines, microstrip, sparams, units, waveguide
from ...services import cabos_service
from . import aplicativos_rf_bp
from .catalog_data import CATALOG_CATEGORIES
from .forms import (
    CableLossForm,
    DbLinearForm,
    KnifeEdgeForm,
    MicrostripForm,
    SParametersForm,
    TransmissionLineForm,
    VSWRForm,
    WaveguideForm,
)
CALCULATOR_ORDER = [
    ("sparams", "Conversões S"),
    ("vswr", "VSWR / Return Loss"),
    ("dblinear", "dB ↔ Linear"),
    ("microstrip", "Microfita Hammerstad"),
    ("waveguide", "Guias retangulares"),
    ("lines", "Linha de transmissão"),
    ("cables", "Perda total no cabo"),
    ("knife", "Difração borda de faca"),
]
@aplicativos_rf_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    active_calc = request.form.get("form_id") or request.args.get("calc") or CALCULATOR_ORDER[0][0]
    forms = {
        "sparams": SParametersForm(prefix="sparams"),
        "vswr": VSWRForm(prefix="vswr"),
        "dblinear": DbLinearForm(prefix="dblinear"),
        "microstrip": MicrostripForm(prefix="microstrip"),
        "waveguide": WaveguideForm(prefix="waveguide"),
        "lines": TransmissionLineForm(prefix="lines"),
        "cables": CableLossForm(prefix="cables"),
        "knife": KnifeEdgeForm(prefix="knife"),
    }
    resultados: dict[str, Any] = {}
    contexto: dict[str, Any] = {}
    # Preenche hidden id e escolhas dinâmicas
    cables = cabos_service.listar_cabos()
    cable_choices = [(str(c.id), c.display_name or c.model_code or str(c.id)) for c in cables]
    forms["cables"].cable_id.choices = cable_choices
    for key, form in forms.items():
        form.form_id.data = key
    if request.method == "POST":
        form = forms.get(active_calc)
        if form and form.validate_on_submit():
            try:
                if active_calc == "sparams":
                    resultados["sparams"] = _process_sparams(form)
                elif active_calc == "vswr":
                    resultados["vswr"] = _process_vswr(form)
                elif active_calc == "dblinear":
                    resultados["dblinear"] = _process_dblinear(form)
                elif active_calc == "microstrip":
                    resultados["microstrip"] = _process_microstrip(form)
                elif active_calc == "waveguide":
                    resultados["waveguide"] = _process_waveguide(form)
                elif active_calc == "lines":
                    resultados["lines"] = _process_lines(form)
                elif active_calc == "cables":
                    resultados["cables"] = _process_cables(form)
                elif active_calc == "knife":
                    resultados["knife"] = _process_knife_edge(form)
            except Exception as exc:  # pragma: no cover - mensagem amigável
                db.session.rollback()
                flash(str(exc), "danger")
        else:
            flash("Verifique os campos destacados antes de continuar.", "warning")
    contexto.update(
        active_calc=active_calc,
        forms=forms,
        resultados=resultados,
        calculators=CALCULATOR_ORDER,
    )
    return render_template("aplicativos_rf/index.html", **contexto)


@aplicativos_rf_bp.route("/catalogo", methods=["GET"])
@login_required
def catalog():
    return render_template(
        "aplicativos_rf/catalogo.html",
        categories=CATALOG_CATEGORIES,
    )
def _process_sparams(form: SParametersForm) -> dict[str, Any]:
    magnitude = float(form.magnitude_value.data or 0)
    phase = float(form.phase_deg.data or 0)
    if form.magnitude_unit.data == "db":
        result = sparams.sparameter_from_db_phase(magnitude, phase)
    else:
        result = sparams.sparameter_from_linear_phase(magnitude, phase)
    normalized_phase = sparams.normalized_phase(result.phase_deg)
    mismatch = (
        sparams.mismatch_loss_db(result.gamma_mag) if math.isfinite(result.vswr) and result.gamma_mag < 1 else math.inf
    )
    vswr_value = result.vswr
    vswr_display = '∞' if math.isinf(vswr_value) else f"{vswr_value:.4f}"
    mismatch_display = '—' if math.isinf(mismatch) else f"{mismatch:.3f} dB"
    return {
        "linear": result.magnitude_linear,
        "db": result.magnitude_db,
        "phase": result.phase_deg,
        "phase_normalized": normalized_phase,
        "gamma_complex": result.gamma_complex,
        "gamma_mag": result.gamma_mag,
        "vswr": vswr_value,
        "vswr_display": vswr_display,
        "return_loss": result.return_loss_db,
        "mismatch_loss": mismatch,
        "mismatch_display": mismatch_display,
        "rho": result.rho,
    }
def _process_vswr(form: VSWRForm) -> dict[str, Any]:
    value = float(form.value.data or 0)
    kind = form.input_kind.data
    if kind == "vswr":
        gamma = sparams.gamma_from_vswr(value)
        vswr_val = value
        rl = sparams.return_loss_from_vswr(value)
    elif kind == "rl":
        gamma = sparams.gamma_from_return_loss(value)
        vswr_val = sparams.vswr_from_gamma(gamma)
        rl = value
    else:
        if not 0 <= value < 1:
            raise sparams.SParameterError("|Γ| deve estar entre 0 e 1.")
        gamma = value
        vswr_val = sparams.vswr_from_gamma(gamma)
        rl = sparams.return_loss_from_gamma(max(gamma, 1e-9)) if gamma > 0 else math.inf
    mismatch = sparams.mismatch_loss_db(min(gamma, 0.999999)) if gamma < 1 else math.inf
    return {
        "vswr": vswr_val,
        "gamma": gamma,
        "return_loss": rl,
        "mismatch": mismatch,
    }
def _process_dblinear(form: DbLinearForm) -> dict[str, Any]:
    value = float(form.value.data or 0)
    direction = form.direction.data
    kind = form.magnitude_kind.data
    if direction == "db_to_lin":
        if kind == "amplitude":
            linear = sparams.magnitude_db_to_linear(value)
        else:
            linear = sparams.power_db_to_linear(value)
        db_value = value
    else:
        if value <= 0:
            raise ValueError("Valor linear deve ser positivo.")
        if kind == "amplitude":
            db_value = sparams.magnitude_linear_to_db(value)
        else:
            db_value = sparams.power_linear_to_db(value)
        linear = value
    return {
        "direction": direction,
        "kind": kind,
        "linear": linear,
        "db": db_value,
    }
def _process_microstrip(form: MicrostripForm) -> dict[str, Any]:
    eps_r = float(form.relative_permittivity.data or 0)
    z0 = float(form.target_impedance.data or 0)
    h = units.to_meters(float(form.substrate_height_value.data or 0), form.substrate_height_unit.data)
    thickness_raw = form.conductor_thickness_value.data
    if thickness_raw in (None, ""):
        thickness = 0.0
    else:
        unit = form.conductor_thickness_unit.data
        unit = "mil" if unit == "mil" else unit
        thickness = units.to_meters(float(thickness_raw), unit)
    result = microstrip.width_for_impedance(
        impedance_ohms=z0,
        eps_r=eps_r,
        substrate_height_m=h,
        conductor_thickness_m=thickness,
    )
    return {
        "width_m": result.width_m,
        "width_mm": units.from_meters(result.width_m, "mm"),
        "width_h": result.width_over_height,
        "effective_eps": result.effective_eps,
        "warnings": result.warnings,
    }
def _process_waveguide(form: WaveguideForm) -> dict[str, Any]:
    mode = form.mode.data
    m = int(form.index_m.data or 0)
    n = int(form.index_n.data or 0)
    a = units.to_meters(float(form.dimension_a_value.data or 0), form.dimension_a_unit.data)
    b = units.to_meters(float(form.dimension_b_value.data or 0), form.dimension_b_unit.data)
    freq_val = form.frequency_value.data
    freq_hz = None
    if freq_val not in (None, ""):
        freq_hz = units.to_hz(float(freq_val), form.frequency_unit.data)
    summary = waveguide.cutoff_summary(mode, m, n, a, b, freq_hz)
    propagation = waveguide.propagation_parameters(freq_hz, summary.cutoff_hz) if freq_hz else None
    return {
        "summary": summary,
        "propagation": propagation,
    }
def _process_lines(form: TransmissionLineForm) -> dict[str, Any]:
    freq_hz = units.to_hz(float(form.frequency_value.data or 0), form.frequency_unit.data)
    vf = form.velocity_factor.data
    eps_eff = form.eps_eff.data
    if vf in (None, "") and eps_eff in (None, ""):
        raise ValueError("Informe fator de velocidade ou ε_eff.")
    vf_value = float(vf) if vf not in (None, "") else None
    eps_value = float(eps_eff) if eps_eff not in (None, "") else None
    if form.mode.data == "length_to_phase":
        length_val = float(form.length_value.data or 0)
        length_m = units.to_meters(length_val, form.length_unit.data)
        result = lines.electrical_length(freq_hz, length_m, velocity_factor=vf_value, eps_eff=eps_value)
    else:
        phase_val = float(form.phase_value.data or 0)
        result = lines.length_from_phase(freq_hz, phase_val, velocity_factor=vf_value, eps_eff=eps_value)
    return {
        "frequency_hz": result.frequency_hz,
        "length_m": result.physical_length_m,
        "length_display": {
            "m": result.physical_length_m,
            "cm": units.from_meters(result.physical_length_m, "cm"),
            "mm": units.from_meters(result.physical_length_m, "mm"),
        },
        "guided_wavelength_m": result.guided_wavelength_m,
        "phase_deg": result.phase_deg,
        "beta": result.beta_rad_m,
        "propagation_velocity": result.propagation_velocity_m_s,
    }
def _process_cables(form: CableLossForm) -> dict[str, Any]:
    cable_id = form.cable_id.data
    freq_hz = units.to_hz(float(form.frequency_value.data or 0), form.frequency_unit.data)
    length_m = units.to_meters(float(form.length_value.data or 0), form.length_unit.data)
    connectors_text = form.connectors_losses.data or ""
    connectors = []
    if connectors_text.strip():
        tokens = re.split(r"[;,\n]+", connectors_text)
        for token in tokens:
            value = token.strip()
            if not value:
                continue
            try:
                connectors.append(float(value))
            except ValueError:
                raise ValueError(f"Valor de conector inválido: {value}")
    detalhes = cabos_service.calcular_perda_total(cable_id, freq_hz, length_m, conectores_db=connectors)
    return {
        "detalhes": detalhes,
        "connectors": connectors,
    }
def _process_knife_edge(form: KnifeEdgeForm) -> dict[str, Any]:
    freq_hz = units.to_hz(float(form.frequency_value.data or 0), form.frequency_unit.data)
    d1 = units.to_meters(float(form.d1_value.data or 0), form.d1_unit.data)
    d2 = units.to_meters(float(form.d2_value.data or 0), form.d2_unit.data)
    result = diffraction_knife_edge.compute_knife_edge(
        frequency_hz=freq_hz,
        d1_m=d1,
        d2_m=d2,
        tx_height_m=float(form.tx_height.data or 0),
        rx_height_m=float(form.rx_height.data or 0),
        obstacle_height_m=float(form.obstacle_height.data or 0),
    )
    plot_uri = _render_plot(result.plot_points, highlight_x=result.v)
    return {
        "result": result,
        "plot": plot_uri,
    }
@aplicativos_rf_bp.route('/docs')
@login_required
def docs():
    doc_path = Path(current_app.root_path).parent / 'docs' / 'aplicativos-rf.md'
    if not doc_path.exists():
        flash('Documento aplicativos-rf.md não encontrado.', 'warning')
        return render_template('aplicativos_rf/docs.html', html='')
    content = doc_path.read_text(encoding='utf-8')
    html = _render_markdown(content)
    return render_template('aplicativos_rf/docs.html', html=html)
def _render_markdown(raw: str) -> str:
    lines = raw.replace('\r\n', '\n').split('\n')
    html_lines: list[str] = []
    in_list = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append('<p></p>')
            continue
        if stripped.startswith('### '):
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            anchor = stripped[4:].lower().replace(' ', '-').replace('/', '-')
            html_lines.append(f"<h3 id='{anchor}'>" + stripped[4:] + '</h3>')
            continue
        if stripped.startswith('## '):
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            anchor = stripped[3:].lower().replace(' ', '-').replace('/', '-')
            html_lines.append(f"<h2 id='{anchor}'>" + stripped[3:] + '</h2>')
            continue
        if stripped.startswith('# '):
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            anchor = stripped[2:].lower().replace(' ', '-').replace('/', '-')
            html_lines.append(f"<h1 id='{anchor}'>" + stripped[2:] + '</h1>')
            continue
        if stripped.startswith('- '):
            if not in_list:
                html_lines.append('<ul>')
                in_list = True
            html_lines.append('<li>' + stripped[2:] + '</li>')
            continue
        html_lines.append('<p>' + stripped + '</p>')
    if in_list:
        html_lines.append('</ul>')
    return '\n'.join(html_lines)
def _render_plot(points: Sequence[tuple[float, float]], highlight_x: float | None = None) -> str:
    if not points:
        return ""
    fig = Figure(figsize=(4.8, 3.0), dpi=100)
    ax = fig.add_subplot(1, 1, 1)
    xs, ys = zip(*points)
    ax.plot(xs, ys, color="#FF6A3D", linewidth=2)
    ax.set_xlabel("v")
    ax.set_ylabel("L_d (dB)")
    ax.grid(True, linestyle="--", linewidth=0.4, alpha=0.4)
    ax.set_facecolor("#0f172a")
    fig.patch.set_facecolor("#0f172a")
    if highlight_x is not None:
        ax.axvline(highlight_x, color="#38bdf8", linestyle="--", linewidth=1.2)
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"
