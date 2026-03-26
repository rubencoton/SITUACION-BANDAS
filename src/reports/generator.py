from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import logging

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.analytics import AnalyticsResult
from src.config import Settings
from src.reports.charts import build_report_charts
from src.reports.naming import ReportWindow
from src.reports.templates import build_brand_theme


@dataclass(slots=True)
class GeneratedReport:
    local_path: Path
    already_exists: bool
    chart_paths: dict[str, Path]


class PdfReportGenerator:
    def __init__(self, settings: Settings, logger: logging.Logger):
        self.settings = settings
        self.logger = logger
        self.theme = build_brand_theme()

    def generate(
        self,
        window: ReportWindow,
        analytics: AnalyticsResult,
        bands_df: pd.DataFrame,
        phases_df: pd.DataFrame,
        insights: list[str],
        force: bool = False,
    ) -> GeneratedReport:
        kind_dir = self.settings.reports_local_root / window.folder_name
        kind_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = kind_dir / window.file_name

        charts_dir = self.settings.output_dir / "_charts" / window.file_stem
        chart_paths = self._expected_chart_paths(charts_dir)

        if pdf_path.exists() and not force:
            self.logger.info("Informe ya existente (idempotente): %s", pdf_path)
            return GeneratedReport(
                local_path=pdf_path,
                already_exists=True,
                chart_paths=chart_paths,
            )

        chart_paths = build_report_charts(
            charts_dir,
            analytics.state_distribution,
            analytics.ranking_bands,
            analytics.ranking_phases_critical,
            analytics.heatmap_matrix,
        )

        doc = SimpleDocTemplate(
            str(pdf_path),
            pagesize=A4,
            leftMargin=1.5 * cm,
            rightMargin=1.5 * cm,
            topMargin=1.2 * cm,
            bottomMargin=1.2 * cm,
        )
        styles = self._build_styles()
        story = []

        # Cabecera corporativa
        logo = self._build_logo()
        if logo is not None:
            story.append(logo)
            story.append(Spacer(1, 0.2 * cm))

        story.append(Paragraph("ARTES BUHO", styles["company"]))
        story.append(Paragraph(window.file_stem, styles["title"]))
        story.append(Paragraph(f"Periodo: {window.period_label}", styles["meta"]))
        story.append(
            Paragraph(
                f"Generado: {window.generated_at_local.strftime('%d/%m/%Y %H:%M (%Z)')}",
                styles["meta"],
            )
        )
        story.append(Paragraph(f"Autor tecnico: {self.settings.author_name}", styles["meta"]))
        story.append(Spacer(1, 0.4 * cm))

        # Resumen ejecutivo
        story.append(Paragraph("Resumen ejecutivo", styles["section"]))
        for line in insights:
            story.append(Paragraph(f"- {line}", styles["body"]))
        story.append(Spacer(1, 0.3 * cm))

        # KPIs
        story.append(Paragraph("KPIs principales", styles["section"]))
        kpis = analytics.kpis
        kpi_rows = [
            ["Total bandas", str(kpis.get("total_bandas", 0))],
            ["Score medio global", str(kpis.get("score_medio_global", 0.0))],
            ["% CRITICO", f"{kpis.get('pct_critico', 0.0):.2f}%"],
            ["% EN PROCESO", f"{kpis.get('pct_en_proceso', 0.0):.2f}%"],
            ["% OPTIMO", f"{kpis.get('pct_optimo', 0.0):.2f}%"],
        ]
        story.append(self._styled_table(kpi_rows, [7 * cm, 8 * cm]))
        story.append(Spacer(1, 0.3 * cm))

        # Visualizaciones
        story.append(Paragraph("Visualizaciones", styles["section"]))
        for key in (
            "state_distribution",
            "ranking_bands",
            "ranking_phases_critical",
            "heatmap",
        ):
            if chart_paths[key].exists():
                story.append(Image(str(chart_paths[key]), width=16 * cm, height=8.8 * cm))
                story.append(Spacer(1, 0.25 * cm))

        # Detalle operativo
        story.append(Paragraph("Detalle operativo", styles["section"]))
        detail = analytics.detail_table.copy()
        if detail.empty:
            story.append(Paragraph("Sin datos operativos para mostrar.", styles["body"]))
        else:
            detail_cols = [
                "banda",
                "IMAGEN",
                "REDES SOCIALES",
                "PRODUCCION",
                "LANZAMIENTO",
                "BOOKING",
                "score_global",
            ]
            safe_cols = [col for col in detail_cols if col in detail.columns]
            detail = detail[safe_cols].fillna("")
            header = [col.replace("_", " ").upper() for col in detail.columns]
            rows = [header]
            for _, row in detail.iterrows():
                rows.append([str(x)[:60] for x in row.tolist()])
            table = Table(rows, repeatRows=1)
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), self.theme.red),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
                    ]
                )
            )
            story.append(table)

        doc.build(story)
        self.logger.info("PDF generado: %s", pdf_path)
        return GeneratedReport(
            local_path=pdf_path,
            already_exists=False,
            chart_paths=chart_paths,
        )

    def _build_styles(self) -> dict[str, ParagraphStyle]:
        base = getSampleStyleSheet()
        return {
            "title": ParagraphStyle(
                "title",
                parent=base["Title"],
                fontName="Helvetica-Bold",
                textColor=self.theme.red,
                fontSize=20,
                leading=24,
            ),
            "company": ParagraphStyle(
                "company",
                parent=base["Heading2"],
                fontName="Helvetica-Bold",
                textColor=self.theme.dark,
                fontSize=13,
            ),
            "meta": ParagraphStyle(
                "meta",
                parent=base["Normal"],
                fontSize=9,
                leading=12,
                textColor=self.theme.dark,
            ),
            "section": ParagraphStyle(
                "section",
                parent=base["Heading2"],
                fontName="Helvetica-Bold",
                textColor=self.theme.red,
                spaceBefore=8,
                spaceAfter=4,
            ),
            "body": ParagraphStyle(
                "body",
                parent=base["Normal"],
                fontSize=10,
                leading=13,
            ),
        }

    def _styled_table(self, rows: list[list[str]], col_widths: list[float]) -> Table:
        table = Table(rows, colWidths=col_widths)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("TEXTCOLOR", (0, 0), (0, -1), self.theme.red),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ]
            )
        )
        return table

    def _build_logo(self) -> Image | None:
        if not self.settings.logo_path.exists():
            return None
        return Image(str(self.settings.logo_path), width=3.5 * cm, height=3.5 * cm)

    @staticmethod
    def _expected_chart_paths(charts_dir: Path) -> dict[str, Path]:
        return {
            "state_distribution": charts_dir / "state_distribution.png",
            "ranking_bands": charts_dir / "ranking_bands.png",
            "ranking_phases_critical": charts_dir / "ranking_phases_critical.png",
            "heatmap": charts_dir / "heatmap.png",
        }
