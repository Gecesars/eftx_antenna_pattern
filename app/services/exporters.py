from __future__ import annotations

import io
import math
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Sequence

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from reportlab.lib.utils import ImageReader

from ..extensions import db
from ..models import Project, ProjectExport, PatternType
from .metrics import (
    directivity_2d_cut,
    estimate_gain_dbi,
    first_null_deg,
    front_to_back_db,
    hpbw_deg,
    lin_to_db,
    lin_to_att_db,
    peak_angle_deg,
    ripple_p2p_db,
    sidelobe_level_db,
)
from .pattern_composer import (
    compute_erp,
    compose_horizontal_pattern,
    compose_vertical_pattern,
    resample_pattern,
    resample_vertical,
)

BASE_DIR = Path(__file__).resolve().parents[2]


def resource_path(relative_path: str) -> Path:
    return (BASE_DIR / relative_path).resolve()


class ExportPaths:
    def __init__(self, root: Path, project: Project) -> None:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        self.base_dir = root / str(project.id) / timestamp
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.pat = self.base_dir / "pattern.pat"
        self.prn = self.base_dir / "pattern.prn"
        self.pdf = self.base_dir / "relatorio.pdf"


def _format_value(value: float, suffix: str = "") -> str:
    if value is None or not np.isfinite(value):
        return f"N/A{suffix}"
    return f"{value:.2f}{suffix}"


def angles_to_full_circle(angles_deg: np.ndarray, values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    base_angles = (angles_deg + 360.0) % 360.0
    order = np.argsort(base_angles)
    base_angles = base_angles[order]
    base_values = values[order]
    extended_angles = np.concatenate([base_angles, base_angles[:1] + 360.0])
    extended_values = np.concatenate([base_values, base_values[:1]])
    target = np.arange(0, 360, 1, dtype=float)
    interp_values = np.interp(target, extended_angles, extended_values)
    return target, interp_values


def vertical_to_full_circle(angles_deg: np.ndarray, values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    shifted = angles_deg + 90.0
    base = np.clip(shifted, 0, 180)
    target = np.arange(0, 181, 1, dtype=float)
    interp = np.interp(target, base, values, left=values[0], right=values[-1])
    mirrored = interp[1:-1][::-1]
    angles = np.concatenate([target, np.arange(181, 360, 1, dtype=float)])
    amp = np.concatenate([interp, mirrored])
    return angles, amp


def _save_polar_plot(path: Path, angles: np.ndarray, values: np.ndarray, title: str) -> None:
    angles_mod = (angles + 360.0) % 360.0
    order = np.argsort(angles_mod)
    theta_sorted = angles_mod[order]
    values_sorted = values[order]
    theta_wrapped = np.concatenate([theta_sorted, [theta_sorted[0] + 360.0]])
    values_wrapped = np.concatenate([values_sorted, [values_sorted[0]]])
    theta_rad = np.deg2rad(theta_wrapped)

    fig = plt.figure(figsize=(4.5, 4.5))
    ax = fig.add_subplot(111, projection="polar")
    ax.plot(theta_rad, values_wrapped, linewidth=1.6, color="#0A4E8B")
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def _save_planar_plot(path: Path, angles: np.ndarray, values: np.ndarray, title: str) -> None:
    order = np.argsort(angles)
    fig, ax = plt.subplots(figsize=(5.5, 3.5))
    ax.plot(angles[order], values[order], linewidth=1.6, color="#0A4E8B")
    ax.set_xlabel("Angulo (deg)")
    ax.set_ylabel("Amplitude (linear)")
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def _build_table_chunks(angles: np.ndarray, values: np.ndarray, available_width: float, columns: int = 6) -> Sequence[Table]:
    if len(angles) == 0:
        return []
    db_vals = lin_to_db(values)
    rows = [(f"{a:.1f}", f"{v:.4f}", f"{d:.2f}") for a, v, d in zip(angles, values, db_vals)]
    rows_per_col = math.ceil(len(rows) / columns)
    header = ["Angulo", "Amplitude", "dB"]
    table_data = [header * columns]
    for i in range(rows_per_col):
        row_cells = []
        for c in range(columns):
            idx = i + c * rows_per_col
            if idx < len(rows):
                row_cells.extend(rows[idx])
            else:
                row_cells.extend(["", "", ""])
        table_data.append(row_cells)

    base_widths = [2.5, 2.5, 2.0]
    total_ratio = sum(base_widths) * columns
    unit = available_width / total_ratio
    col_widths = [unit * r for r in base_widths] * columns

    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.25, colors.gray),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTSIZE", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 1),
        ("RIGHTPADDING", (0, 0), (-1, -1), 1),
    ] + [
        ("BACKGROUND", (c * 3, 0), (c * 3 + 2, 0), colors.HexColor("#1f2a44"))
        for c in range(columns)
    ] + [
        ("TEXTCOLOR", (c * 3, 0), (c * 3 + 2, 0), colors.white)
        for c in range(columns)
    ] + [
        ("FONTNAME", (c * 3, 0), (c * 3 + 2, 0), "Helvetica-Bold")
        for c in range(columns)
    ]))
    usable_height = A4[1] - 70
    return table.split(available_width, usable_height)


def _prepare_raw_pattern(project: Project, pattern_type: PatternType) -> tuple[np.ndarray, np.ndarray]:
    pattern = project.antenna.pattern_for(pattern_type)
    if not pattern:
        if pattern_type is PatternType.HRP:
            angles = np.arange(-180, 181, 1, dtype=float)
        else:
            angles = np.round(np.arange(-90.0, 90.0 + 0.0001, 0.1), 1)
        return angles, np.ones_like(angles, dtype=float)
    angles = np.asarray(pattern.angles_deg, dtype=float)
    values = np.asarray(pattern.amplitudes_linear, dtype=float)
    values = np.clip(values, 0.0, None)
    if pattern_type is PatternType.HRP:
        return resample_pattern(angles, values, -180, 180, 1)
    return resample_vertical(angles, values)


def _create_pdf_report(project: Project,
                       paths: ExportPaths,
                       raw_hrp_angles: np.ndarray,
                       raw_hrp_values: np.ndarray,
                       raw_vrp_angles: np.ndarray,
                       raw_vrp_values: np.ndarray,
                       array_metrics: dict) -> None:
    modelo_path = resource_path("modelo.pdf")
    template_exists = modelo_path.exists()
    tmp_dir = tempfile.TemporaryDirectory(prefix="eftx_pdf_")
    try:
        hrp_full_angles, hrp_full_values = angles_to_full_circle(raw_hrp_angles, raw_hrp_values)

        hrp_img = Path(tmp_dir.name) / "hrp.png"
        vrp_img = Path(tmp_dir.name) / "vrp.png"
        _save_polar_plot(hrp_img, raw_hrp_angles, raw_hrp_values, "Padrão Horizontal (HRP)")
        _save_planar_plot(vrp_img, raw_vrp_angles, raw_vrp_values, "Padrão Vertical (VRP)")

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        margin = 18 * mm

        c.setFont("Helvetica-Bold", 17)
        c.drawCentredString(width / 2, height - margin, f"Relatório Técnico - {project.name}")
        c.setFont("Helvetica", 11)

        summary_left = [
            f"Antena: {project.antenna.name}",
            f"Projeto: {project.name}",
            f"Frequência: {project.frequency_mhz:.2f} MHz",
            f"Potência TX: {project.tx_power_w:.1f} W",
            f"Elementos (H/V): {project.h_count} / {project.v_count}",
        ]
        summary_right = [
            f"Espaçamento H: {project.h_spacing_m:.2f} m",
            f"Espaçamento V: {project.v_spacing_m:.2f} m",
            f"Tilt elétrico: {project.v_tilt_deg or 0:.2f} deg",
            f"Perda alimentação: {project.feeder_loss_db or 0:.2f} dB",
            f"VSWR alvo: {project.vswr_target or 0:.2f}",
        ]
        y_left = height - margin - 24
        for line in summary_left:
            c.drawString(margin, y_left, line)
            y_left -= 14
        y_right = height - margin - 24
        col_x = width / 2 + 10
        for line in summary_right:
            c.drawString(col_x, y_right, line)
            y_right -= 14

        chart_width = (width - margin * 3) / 2
        chart_height = 130
        charts_y = min(y_left, y_right) - 20
        c.drawImage(ImageReader(str(hrp_img)), margin, charts_y - chart_height, width=chart_width, height=chart_height, preserveAspectRatio=True, mask="auto")
        c.drawImage(ImageReader(str(vrp_img)), margin * 2 + chart_width, charts_y - chart_height, width=chart_width, height=chart_height, preserveAspectRatio=True, mask="auto")

        dir_hrp = directivity_2d_cut(raw_hrp_angles, raw_hrp_values)
        dir_hrp_db = 10 * np.log10(dir_hrp) if np.isfinite(dir_hrp) else float("nan")

        element_metrics = [
            "Elementos (HRP/VRP)",
            f"- HPBW HRP: {_format_value(hpbw_deg(raw_hrp_angles, raw_hrp_values), ' deg')}",
            f"- Diretividade HRP: {_format_value(dir_hrp_db, ' dB')}",
            f"- HPBW VRP: {_format_value(hpbw_deg(raw_vrp_angles, raw_vrp_values), ' deg')}",
            f"- Primeiro nulo VRP: {_format_value(first_null_deg(raw_vrp_angles, raw_vrp_values), ' deg')}",
        ]
        array_lines = [
            "Arranjo composto",
            f"- HPBW Horizontal: {_format_value(array_metrics['hrp_hpbw'], ' deg')}",
            f"- HPBW Vertical: {_format_value(array_metrics['vrp_hpbw'], ' deg')}",
            f"- Front/Back: {_format_value(array_metrics['front_to_back'], ' dB')}",
            f"- Ripple p2p: {_format_value(array_metrics['ripple_db'], ' dB')}",
            f"- SLL: {_format_value(array_metrics['sll_db'], ' dB')}",
            f"- Diretividade 2D: {_format_value(array_metrics['directivity_db'], ' dB')}",
            f"- Ganho estimado: {_format_value(array_metrics['gain_dbi'], ' dBi')}",
        ]
        metrics_y = charts_y - chart_height - 20
        c.setFont("Helvetica", 10)
        for idx, line in enumerate(element_metrics):
            c.drawString(margin, metrics_y - idx * 12, line)
        for idx, line in enumerate(array_lines):
            c.drawString(width / 2 + 10, metrics_y - idx * 12, line)

        c.showPage()

        available_width = width - 2 * margin
        hrp_chunks = _build_table_chunks(hrp_full_angles, hrp_full_values, available_width)
        vrp_chunks = _build_table_chunks(raw_vrp_angles, raw_vrp_values, available_width)

        for idx, chunk in enumerate(hrp_chunks):
            c.setFont("Helvetica-Bold", 14)
            title = "Tabela HRP" + (" (continuação)" if idx else "")
            c.drawCentredString(width / 2, height - margin, title)
            w, h = chunk.wrap(available_width, height - margin * 2)
            chunk.drawOn(c, margin, height - margin - h - 24)
            c.showPage()

        for idx, chunk in enumerate(vrp_chunks):
            c.setFont("Helvetica-Bold", 14)
            title = "Tabela VRP" + (" (continuação)" if idx else "")
            c.drawCentredString(width / 2, height - margin, title)
            w, h = chunk.wrap(available_width, height - margin * 2)
            chunk.drawOn(c, margin, height - margin - h - 24)
            c.showPage()

        c.save()
        buffer.seek(0)
        content_reader = PdfReader(buffer)
        writer = PdfWriter()
        if template_exists:
            template_bytes = modelo_path.read_bytes()
            for page in content_reader.pages:
                template_reader = PdfReader(io.BytesIO(template_bytes))
                base_page = template_reader.pages[0]
                base_page.merge_page(page)
                writer.add_page(base_page)
        else:
            for page in content_reader.pages:
                writer.add_page(page)
        with paths.pdf.open("wb") as fh:
            writer.write(fh)
    finally:
        tmp_dir.cleanup()


def write_pat_array(path: Path, description: str, gain: float, num_elems: int,
                    angles_0_359: np.ndarray, values_0_359: np.ndarray,
                    vertical_tail_angles: np.ndarray, vertical_tail_values: np.ndarray) -> None:
    with path.open("w", encoding="utf-8") as f:
        f.write(f"'{description}', {gain:.2f}, {num_elems}\n")
        for ang in range(360):
            val = float(np.interp(ang, angles_0_359, values_0_359))
            f.write(f"{ang}, {val:.4f}\n")
        for ang in [356, 357, 358, 359]:
            val = float(np.interp(ang, angles_0_359, values_0_359))
            f.write(f"{ang}, {val:.4f}\n")
        f.write("999\n")
        f.write("1, 91\n")
        f.write("269,\n")
        for ang in range(0, -91, -1):
            v = float(np.interp(ang, vertical_tail_angles, vertical_tail_values))
            f.write(f"{ang:.1f}, {v:.4f}\n")


def write_prn(path: Path, name: str, make: str, frequency: float, freq_unit: str,
              h_width: float, v_width: float, front_to_back: float, gain: float,
              h_angles: np.ndarray, h_values: np.ndarray,
              v_angles: np.ndarray, v_values: np.ndarray) -> None:
    with path.open("w", encoding="utf-8") as f:
        f.write(f"NAME {name}\n")
        f.write(f"MAKE {make}\n")
        f.write(f"FREQUENCY {frequency:.2f} {freq_unit}\n")
        f.write(f"H_WIDTH {h_width:.2f}\n")
        f.write(f"V_WIDTH {v_width:.2f}\n")
        f.write(f"FRONT_TO_BACK {front_to_back:.2f}\n")
        f.write(f"GAIN {gain:.2f} dBi\n")
        f.write("TILT MECHANICAL\n")
        f.write("HORIZONTAL 360\n")
        for ang in range(360):
            v = float(np.interp(ang, h_angles, h_values))
            f.write(f"{ang}\t{lin_to_att_db(v):.4f}\n")
        f.write("VERTICAL 360\n")
        for ang in range(360):
            v = float(np.interp(ang, v_angles, v_values))
            f.write(f"{ang}\t{lin_to_att_db(v):.4f}\n")


def generate_project_export(project: Project, export_root: Path) -> tuple[ProjectExport, ExportPaths]:
    export_root.mkdir(parents=True, exist_ok=True)
    data = compute_erp(project)
    hrp_angles, hrp_values = compose_horizontal_pattern(project)
    vrp_angles, vrp_values = compose_vertical_pattern(project)

    ang_full_hrp, val_full_hrp = angles_to_full_circle(hrp_angles, hrp_values)
    ang_full_vrp, val_full_vrp = vertical_to_full_circle(vrp_angles, vrp_values)

    metrics = {
        "hrp_hpbw": float(hpbw_deg(hrp_angles, hrp_values)),
        "vrp_hpbw": float(hpbw_deg(vrp_angles, vrp_values)),
        "front_to_back": float(front_to_back_db(hrp_angles, hrp_values)),
        "ripple_db": float(ripple_p2p_db(hrp_angles, hrp_values)),
        "sll_db": float(sidelobe_level_db(hrp_angles, hrp_values)),
        "peak_angle": float(peak_angle_deg(hrp_angles, hrp_values)),
        "gain_dbi": float(estimate_gain_dbi(hpbw_deg(hrp_angles, hrp_values), hpbw_deg(vrp_angles, vrp_values))),
        "directivity_db": float(10 * np.log10(directivity_2d_cut(hrp_angles, hrp_values))) if np.any(hrp_values) else float("nan"),
    }

    export_paths = ExportPaths(export_root, project)

    description = project.antenna.name or "EFTX"
    gain = metrics["gain_dbi"] if math.isfinite(metrics["gain_dbi"]) else float(project.antenna.nominal_gain_dbd or 0.0)
    num_elems = max(project.h_count or 1, 1) * max(project.v_count or 1, 1)

    tail_angles = np.linspace(0, -90, 91)
    tail_values = np.interp(tail_angles, vrp_angles[::-1], vrp_values[::-1], left=vrp_values[-1], right=vrp_values[0])

    write_pat_array(
        export_paths.pat,
        description,
        gain,
        num_elems,
        ang_full_hrp,
        val_full_hrp,
        tail_angles,
        tail_values,
    )

    prn_name = project.name
    prn_make = project.antenna.model_number or "EFTX"
    frequency = float(project.frequency_mhz)
    front_to_back = metrics["front_to_back"] if math.isfinite(metrics["front_to_back"]) else 0.0
    write_prn(
        export_paths.prn,
        prn_name,
        prn_make,
        frequency,
        "MHz",
        metrics["hrp_hpbw"] if math.isfinite(metrics["hrp_hpbw"]) else 0.0,
        metrics["vrp_hpbw"] if math.isfinite(metrics["vrp_hpbw"]) else 0.0,
        front_to_back,
        gain,
        ang_full_hrp,
        val_full_hrp,
        ang_full_vrp,
        val_full_vrp,
    )

    raw_hrp_angles, raw_hrp_values = _prepare_raw_pattern(project, PatternType.HRP)
    raw_vrp_angles, raw_vrp_values = _prepare_raw_pattern(project, PatternType.VRP)

    _create_pdf_report(
        project,
        export_paths,
        raw_hrp_angles,
        raw_hrp_values,
        raw_vrp_angles,
        raw_vrp_values,
        metrics,
    )

    export = ProjectExport(
        project=project,
        erp_metadata={
            "angles_deg": data["angles_deg"].tolist(),
            "erp_dbw": data["erp_dbw"].tolist(),
            "erp_w": data["erp_w"].tolist(),
            "metrics": metrics,
        },
        pat_path=str(export_paths.pat.relative_to(export_root)),
        prn_path=str(export_paths.prn.relative_to(export_root)),
        pdf_path=str(export_paths.pdf.relative_to(export_root)),
    )
    db.session.add(export)
    db.session.commit()
    return export, export_paths
