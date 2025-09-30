from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from ..extensions import db
from ..models import Project, ProjectExport
from .pattern_composer import compute_erp, export_pat, export_prn


class ExportPaths:
    def __init__(self, root: Path, project: Project) -> None:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        self.base_dir = root / str(project.id) / timestamp
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.pat = self.base_dir / "pattern.pat"
        self.prn = self.base_dir / "pattern.prn"
        self.pdf = self.base_dir / "report.pdf"


def polar_plot(angles_deg: np.ndarray, values: np.ndarray, title: str) -> Image.Image:
    fig = plt.figure(figsize=(4, 4))
    ax = fig.add_subplot(111, projection="polar")
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    theta = np.radians(angles_deg % 360)
    ax.plot(theta, values, linewidth=1.2)
    ax.set_title(title)
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buffer.seek(0)
    return Image.open(buffer)


def image_reader_from_pillow(image: Image.Image) -> ImageReader:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return ImageReader(buffer)


def create_pdf(report_path: Path, project: Project, data: dict) -> None:
    hrp_img = polar_plot(data["angles_deg"], data["hrp_linear"], "HRP Composto")
    vrp_img = polar_plot(data["vrp_angles_deg"], data["vrp_linear"], "VRP Composto")

    c = canvas.Canvas(str(report_path), pagesize=A4)
    width, height = A4
    c.setFont("Helvetica-Bold", 16)
    c.drawString(2 * cm, height - 2 * cm, "EFTX - Relatório de Projeto")

    c.setFont("Helvetica", 11)
    c.drawString(2 * cm, height - 3 * cm, f"Projeto: {project.name}")
    c.drawString(2 * cm, height - 3.7 * cm, f"Antena: {project.antenna.name}")
    c.drawString(2 * cm, height - 4.4 * cm, f"Frequência: {project.frequency_mhz:.2f} MHz")

    c.drawImage(image_reader_from_pillow(hrp_img), 2 * cm, height - 14 * cm, width=7 * cm, preserveAspectRatio=True, mask="auto")
    c.drawImage(image_reader_from_pillow(vrp_img), 11 * cm, height - 14 * cm, width=7 * cm, preserveAspectRatio=True, mask="auto")

    c.setFont("Helvetica", 10)
    c.drawString(2 * cm, 6 * cm, "ERP pico (dBW): {:.2f}".format(float(np.max(data["erp_dbw"]))))
    c.drawString(2 * cm, 5.2 * cm, "Perdas feeder (dB): {:.2f}".format(project.feeder_loss_db or 0.0))

    c.showPage()
    c.save()

    reader = PdfReader(str(report_path))
    writer = PdfWriter()
    writer.append_pages_from_reader(reader)
    with report_path.open("wb") as fh:
        writer.write(fh)


def generate_project_export(project: Project, export_root: Path) -> ProjectExport:
    data = compute_erp(project)
    paths = ExportPaths(export_root, project)
    export_pat(paths.pat, data)
    export_prn(paths.prn, data)
    create_pdf(paths.pdf, project, data)

    export = ProjectExport(
        project=project,
        erp_metadata={
            "angles_deg": data["angles_deg"].tolist(),
            "erp_dbw": data["erp_dbw"].tolist(),
            "erp_w": data["erp_w"].tolist(),
            "vertical_scalar": float(data["vertical_scalar"]),
        },
        pat_path=paths.pat.as_posix(),
        prn_path=paths.prn.as_posix(),
        pdf_path=paths.pdf.as_posix(),
    )
    db.session.add(export)
    db.session.commit()
    return export
