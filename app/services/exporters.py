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
from ..models import Project, ProjectExport
from .pattern_composer import compute_erp, compose_horizontal_pattern, compose_vertical_pattern

C_LIGHT = 299_792_458.0
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


def lin_to_db(values: np.ndarray | float) -> np.ndarray | float:
    arr = np.maximum(values, 1e-12)
    return 20.0 * np.log10(arr)


def lin_to_att_db(value: float) -> float:
    if value <= 0:
        return 100.0
    return max(0.0, -20.0 * math.log10(value))


def hpbw_deg(angles_deg: np.ndarray, values: np.ndarray) -> float:
    if len(angles_deg) < 3:
        return float("nan")
    normalised = values / np.max(values) if np.max(values) > 0 else values
    threshold = math.sqrt(0.5)
    peak_idx = int(np.argmax(normalised))
    left = None
    for idx in range(peak_idx, 0, -1):
        if normalised[idx] >= threshold and normalised[idx - 1] < threshold:
            left = np.interp(
                threshold,
                [normalised[idx - 1], normalised[idx]],
                [angles_deg[idx - 1], angles_deg[idx]],
            )
            break
    right = None
    for idx in range(peak_idx, len(normalised) - 1):
        if normalised[idx] >= threshold and normalised[idx + 1] < threshold:
            right = np.interp(
                threshold,
                [normalised[idx], normalised[idx + 1]],
                [angles_deg[idx], angles_deg[idx + 1]],
            )
            break
    if left is None or right is None:
        return float("nan")
    return float(right - left)


def front_to_back_db(angles_deg: np.ndarray, values: np.ndarray, window: float = 30.0) -> float:
    normalised = values / np.max(values) if np.max(values) > 0 else values
    angles_norm = (angles_deg + 360.0) % 360.0
    mask = (angles_norm >= (180.0 - window)) & (angles_norm <= (180.0 + window))
    if not np.any(mask):
        return float("nan")
    back = np.max(normalised[mask])
    if back <= 0:
        return 100.0
    return max(0.0, -20.0 * math.log10(back))


def ripple_p2p_db(angles_deg: np.ndarray, values: np.ndarray, threshold_db: float = -6.0) -> float:
    normalised = values / np.max(values) if np.max(values) > 0 else values
    db_vals = lin_to_db(normalised)
    peak_idx = int(np.argmax(normalised))
    left = peak_idx
    while left > 0 and db_vals[left - 1] >= threshold_db:
        left -= 1
    right = peak_idx
    while right < len(db_vals) - 1 and db_vals[right + 1] >= threshold_db:
        right += 1
    sector = db_vals[left:right + 1]
    if sector.size == 0:
        return float("nan")
    return float(np.max(sector) - np.min(sector))


def sidelobe_level_db(angles_deg: np.ndarray, values: np.ndarray, threshold_db: float = -6.0) -> float:
    normalised = values / np.max(values) if np.max(values) > 0 else values
    db_vals = lin_to_db(normalised)
    peak_idx = int(np.argmax(normalised))
    left = peak_idx
    while left > 0 and db_vals[left - 1] >= threshold_db:
        left -= 1
    right = peak_idx
    while right < len(db_vals) - 1 and db_vals[right + 1] >= threshold_db:
        right += 1
    outside = np.concatenate([db_vals[:left], db_vals[right + 1:]]) if (left > 0 or right < len(db_vals) - 1) else np.array([])
    if outside.size == 0:
        return float("nan")
    return float(np.max(outside))


def peak_angle_deg(angles_deg: np.ndarray, values: np.ndarray) -> float:
    return float(angles_deg[int(np.argmax(values))])


def estimate_gain_dbi(h_hpbw: float, v_hpbw: float) -> float:
    if not (math.isfinite(h_hpbw) and math.isfinite(v_hpbw) and h_hpbw > 0 and v_hpbw > 0):
        return float("nan")
    directivity = 41253.0 / (h_hpbw * v_hpbw)
    return 10.0 * math.log10(directivity)


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
            f.write(f"{ang}	{lin_to_att_db(v):.4f}\n")
        f.write("VERTICAL 360\n")
        for ang in range(360):
            v = float(np.interp(ang, v_angles, v_values))
            f.write(f"{ang}	{lin_to_att_db(v):.4f}\n")
def _save_polar_plot(path: Path, angles: np.ndarray, values: np.ndarray, title: str) -> None:
    fig = plt.figure(figsize=(4.5, 4.5))
    ax = fig.add_subplot(111, projection="polar")
    theta = np.deg2rad((angles + 360.0) % 360.0)
    ax.plot(theta, values, linewidth=1.5, color="#0A4E8B")
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def _save_linear_plot(path: Path, angles: np.ndarray, values: np.ndarray, title: str) -> None:
    fig = plt.figure(figsize=(5.5, 3.5))
    ax = fig.add_subplot(111)
    ax.plot(angles, values, linewidth=1.5, color="#0A4E8B")
    ax.set_xlabel("Angulo (deg)")
    ax.set_ylabel("Amplitude (linear)")
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    fig.savefig(path, dpi=200, bbox_inches="tight")
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
    return table.split(available_width, A4[1] - 60)


def _create_pdf_report(project: Project,
                       paths: ExportPaths,
                       hrp_angles: np.ndarray,
                       hrp_values: np.ndarray,
                       vrp_angles: np.ndarray,
                       vrp_values: np.ndarray,
                       erp_data: dict,
                       metrics: dict) -> None:
    modelo_path = resource_path("modelo.pdf")
    template_exists = modelo_path.exists()
    tmp_dir = tempfile.TemporaryDirectory(prefix="eftx_pdf_")
    try:
        hrp_img = Path(tmp_dir.name) / "hrp.png"
        vrp_img = Path(tmp_dir.name) / "vrp.png"
        _save_polar_plot(hrp_img, hrp_angles, hrp_values, "HRP Composto")
        _save_linear_plot(vrp_img, vrp_angles, vrp_values, "VRP Composto")

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        margin = 18 * mm

        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(width / 2, height - margin, f"Relatorio de Projeto - {project.name}")
        c.setFont("Helvetica", 11)
        summary_lines = [
            f"Antena: {project.antenna.name}",
            f"Frequencia: {project.frequency_mhz:.2f} MHz",
            f"Tilt eletrico: {project.v_tilt_deg or 0:.2f} deg",
            f"ERP pico: {float(np.max(erp_data['erp_dbw'])):.2f} dBW ({float(np.max(erp_data['erp_w'])):.1f} W)",
        ]
        y = height - margin - 20
        for line in summary_lines:
            c.drawString(margin, y, line)
            y -= 14

        chart_width = (width - margin * 3) / 2
        chart_height = 120
        c.drawImage(ImageReader(str(hrp_img)), margin, y - chart_height, width=chart_width, height=chart_height, preserveAspectRatio=True, mask="auto")
        c.drawImage(ImageReader(str(vrp_img)), margin * 2 + chart_width, y - chart_height, width=chart_width, height=chart_height, preserveAspectRatio=True, mask="auto")

        def _fmt_value(value: float, suffix: str = "") -> str:
            return f"{value:.2f}{suffix}" if math.isfinite(value) else f"N/A{suffix}"

        metrics_lines = [
            f"HPBW Horizontal: {_fmt_value(metrics['hrp_hpbw'], ' deg')}",
            f"HPBW Vertical: {_fmt_value(metrics['vrp_hpbw'], ' deg')}",
            f"Front-to-Back: {_fmt_value(metrics['front_to_back'], ' dB')}",
            f"Ripple p2p: {_fmt_value(metrics['ripple_db'], ' dB')}",
            f"SLL: {_fmt_value(metrics['sll_db'], ' dB')}",
            f"Ganho estimado: {_fmt_value(metrics['gain_dbi'], ' dBi')}",
        ]
        y -= chart_height + 20
        c.setFont("Helvetica", 10)
        for line in metrics_lines:
            c.drawString(margin, y, line)
            y -= 12

        c.showPage()

        available_width = width - 2 * margin
        hrp_chunks = _build_table_chunks(hrp_angles, hrp_values, available_width)
        vrp_chunks = _build_table_chunks(vrp_angles, vrp_values, available_width)

        for idx, chunk in enumerate(hrp_chunks):
            c.setFont("Helvetica-Bold", 14)
            title = "Tabela HRP" + (" (continuacao)" if idx else "")
            c.drawCentredString(width / 2, height - margin, title)
            w, h = chunk.wrap(available_width, height - margin * 2)
            chunk.drawOn(c, margin, height - margin - h - 24)
            c.showPage()

        for idx, chunk in enumerate(vrp_chunks):
            c.setFont("Helvetica-Bold", 14)
            title = "Tabela VRP" + (" (continuacao)" if idx else "")
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


def generate_project_export(project: Project, export_root: Path) -> ProjectExport:
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

    _create_pdf_report(project, export_paths, ang_full_hrp, val_full_hrp, ang_full_vrp, val_full_vrp, data, metrics)

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
    return export
