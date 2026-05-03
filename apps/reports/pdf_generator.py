import calendar
import re
from dataclasses import dataclass
from datetime import date, datetime
from io import BytesIO
from pathlib import Path

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle

from apps.ingestion.models import UploadedFile
from apps.ingestion.parsers import parse_excel, parse_pdf, parse_word
from apps.kpis.calculators import (
    get_field_production_summary,
    get_monthly_trend,
    get_top_producers,
    get_well_kpis,
)
from apps.warehouse.models import DimWell

from .models import Anomalie


MONTHS_FR = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December",
}


@dataclass
class ReportAnomaly:
    detected_at: datetime | None
    well_code: str = ""
    anomaly_type: str = ""
    severity: str = ""
    description: str = ""
    source: str = "DWH"


class EzzaouiaReportGenerator:
    def __init__(self):
        self.buffer = BytesIO()
        self.canvas = canvas.Canvas(self.buffer, pagesize=A4)
        self.page_width, self.page_height = A4
        self.primary_red = colors.HexColor("#C0392B")
        self.border_gray = colors.HexColor("#D9D9D9")
        self.text_dark = colors.HexColor("#1C1C1C")
        self.text_muted = colors.HexColor("#666666")
        self.today = datetime.now()

    def generate_monthly_report(self, year, month, role):
        self.year = int(year)
        self.month = int(month)
        self.role = (role or "").lower()

        self.current_summary = self._safe_summary(self.year, self.month)
        prev_year, prev_month = self._get_previous_month(self.year, self.month)
        self.previous_summary = self._safe_summary(prev_year, prev_month)

        self.month_anomalies = self._safe_month_anomalies(self.year, self.month)
        self.month_imported_files = self._safe_month_imported_files(self.year, self.month)
        self.month_comments = self._get_month_comments(self.year, self.month)
        self.imported_file_anomalies = self._safe_imported_file_anomalies(self.month_imported_files)
        self.all_anomalies = self._merge_anomalies(self.month_anomalies, self.imported_file_anomalies)

        self.ranking_rows = self._safe_ranking_rows(self.year, self.month)
        self.trend_rows = self._safe_trend_rows(self.year)

        pages = [self._draw_cover_page, self._draw_executive_page]
        if self.ranking_rows:
            pages.append(self._draw_wells_page)
        if self.trend_rows:
            pages.append(self._draw_trend_page)
        if self.all_anomalies or self.month_imported_files:
            pages.append(self._draw_anomalies_page)

        total_pages = len(pages)
        for index, draw_page in enumerate(pages, start=1):
            draw_page()
            self._draw_footer(index, total_pages)
            self.canvas.showPage()

        self.canvas.save()
        self.buffer.seek(0)
        return self.buffer

    def _draw_cover_page(self):
        c = self.canvas
        self._draw_logo(center_y=self.page_height - 95 * mm, width_mm=45, height_mm=45)

        c.setFillColor(self.text_dark)
        c.setFont("Helvetica-Bold", 24)
        c.drawCentredString(self.page_width / 2, self.page_height - 150 * mm, "MONTHLY PRODUCTION REPORT")

        c.setFont("Helvetica", 14)
        c.setFillColor(self.text_muted)
        c.drawCentredString(self.page_width / 2, self.page_height - 162 * mm, "EZZAOUIA Field - CPF Zarzis")

        c.setFont("Helvetica-Bold", 16)
        c.setFillColor(self.text_dark)
        c.drawCentredString(
            self.page_width / 2,
            self.page_height - 188 * mm,
            f"{MONTHS_FR.get(self.month, self.month)} {self.year}",
        )
        c.setFont("Helvetica", 11)
        c.setFillColor(self.text_muted)
        c.drawCentredString(
            self.page_width / 2,
            self.page_height - 197 * mm,
            f"Generated on {self.today.strftime('%d/%m/%Y %H:%M')}",
        )

        c.setStrokeColor(self.primary_red)
        c.setLineWidth(2.5)
        c.line(32 * mm, self.page_height - 208 * mm, self.page_width - 32 * mm, self.page_height - 208 * mm)

    def _draw_executive_page(self):
        c = self.canvas
        self._draw_page_title("Executive Summary")

        kpis = [
            ("avg_bopd", "Average BOPD", "STB/day"),
            ("total_oil_stbd", "Total Oil", "STB"),
            ("avg_bsw", "Average BSW", "%"),
            ("avg_gor", "Average GOR", "SCF/STB"),
        ]

        box_w = (self.page_width - 46 * mm) / 2
        box_h = 34 * mm
        start_x = 20 * mm
        start_y = self.page_height - 68 * mm

        for idx, (key, label, unit) in enumerate(kpis):
            row = idx // 2
            col = idx % 2
            x = start_x + col * (box_w + 6 * mm)
            y = start_y - row * (box_h + 8 * mm)
            self._draw_kpi_box(x, y, box_w, box_h, key, label, unit)

        c.setFont("Helvetica", 9.5)
        c.setFillColor(self.text_muted)
        c.drawString(
            20 * mm,
            self.page_height - 158 * mm,
            (
                f"Imported files checked: {len(self.month_imported_files)}"
                f" | file anomalies detected: {len(self.imported_file_anomalies)}"
            ),
        )

        c.setFont("Helvetica-Bold", 12)
        c.setFillColor(self.text_dark)
        c.drawString(20 * mm, self.page_height - 165 * mm, "Critical anomalies of the month")

        anomalies = self._critical_anomalies(self.all_anomalies)
        c.setFont("Helvetica", 10)
        y = self.page_height - 174 * mm
        if anomalies:
            for anomaly in anomalies[:7]:
                text = self._anomaly_line(anomaly, max_len=120)
                c.setFillColor(self.text_dark)
                c.drawString(22 * mm, y, f"- {text}")
                y -= 7 * mm
                if y < 30 * mm:
                    break
        else:
            c.setFillColor(self.text_muted)
            c.drawString(22 * mm, y, "No critical anomalies detected in this period.")

        if self.month_comments:
            self._draw_remarks_box(y - 8 * mm, self.month_comments)

    def _draw_wells_page(self):
        self._draw_page_title(
            f"Well ranking - Top 16 ({MONTHS_FR.get(self.month, self.month)} {self.year})"
        )

        data = [["#", "Well", "BOPD", "BSW %", "GOR", "Status"]]
        for idx, row in enumerate(self.ranking_rows[:16], start=1):
            data.append(
                [
                    str(idx),
                    row.get("well_code", "-"),
                    self._fmt_num(row.get("avg_bopd"), 1),
                    self._fmt_num(row.get("avg_bsw"), 2),
                    self._fmt_num(row.get("avg_gor"), 0),
                    row.get("status", "Active"),
                ]
            )

        table = Table(data, colWidths=[12 * mm, 38 * mm, 28 * mm, 28 * mm, 30 * mm, 28 * mm], repeatRows=1)
        style = TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), self.primary_red),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.4, self.border_gray),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]
        )
        for row_idx in range(1, len(data)):
            bg = colors.HexColor("#F8F8F8") if row_idx % 2 == 0 else colors.white
            style.add("BACKGROUND", (0, row_idx), (-1, row_idx), bg)
        table.setStyle(style)

        self._draw_table_under_title(table)

    def _draw_trend_page(self):
        self._draw_page_title("Monthly trend - current year")

        data = [["Month", "Oil (STB)", "Water (BLS)", "Gas (MSCF)", "BSW %", "GOR"]]
        month_map = {int(item.get("month", 0)): item for item in self.trend_rows if item.get("month")}

        for m in range(1, 13):
            row = month_map.get(m, {})
            data.append(
                [
                    MONTHS_FR[m],
                    self._fmt_num(row.get("total_oil"), 0),
                    self._fmt_num(row.get("total_water"), 0),
                    self._fmt_num(row.get("total_gas"), 0),
                    self._fmt_num(row.get("avg_bsw"), 2),
                    self._fmt_num(row.get("avg_gor"), 0),
                ]
            )

        table = Table(
            data,
            colWidths=[32 * mm, 32 * mm, 30 * mm, 30 * mm, 24 * mm, 24 * mm],
            repeatRows=1,
        )
        style = TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), self.primary_red),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.4, self.border_gray),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ]
        )
        for row_idx in range(1, len(data)):
            bg = colors.HexColor("#F8F8F8") if row_idx % 2 == 0 else colors.white
            style.add("BACKGROUND", (0, row_idx), (-1, row_idx), bg)
        table.setStyle(style)

        self._draw_table_under_title(table)

    def _draw_anomalies_page(self):
        self._draw_page_title("Detected anomalies")

        data = [["Date", "Well", "Type", "Severity", "Source", "Description"]]
        if self.all_anomalies:
            for anomaly in self.all_anomalies[:22]:
                detected = getattr(anomaly, "detected_at", None)
                data.append(
                    [
                        detected.strftime("%d/%m/%Y") if detected else "-",
                        str(getattr(anomaly, "well_code", "-") or "-"),
                        str(getattr(anomaly, "anomaly_type", "-") or "-"),
                        str(getattr(anomaly, "severity", "-") or "-"),
                        self._anomaly_source(anomaly),
                        self._truncate(str(getattr(anomaly, "description", "") or "-"), 44),
                    ]
                )
        elif self.month_imported_files:
            data.append(
                [
                    "-",
                    "-",
                    "-",
                    "-",
                    "FILES",
                    f"No anomaly mention found in {len(self.month_imported_files)} imported file(s).",
                ]
            )
        else:
            data.append(["-", "-", "-", "-", "-", "No anomalies in this period."])

        table = Table(
            data,
            colWidths=[22 * mm, 18 * mm, 24 * mm, 18 * mm, 22 * mm, 66 * mm],
            repeatRows=1,
        )
        style = TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), self.primary_red),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("GRID", (0, 0), (-1, -1), 0.4, self.border_gray),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
        for row_idx in range(1, len(data)):
            bg = colors.HexColor("#F8F8F8") if row_idx % 2 == 0 else colors.white
            style.add("BACKGROUND", (0, row_idx), (-1, row_idx), bg)
        table.setStyle(style)

        self._draw_table_under_title(table)

    def _draw_page_title(self, title):
        c = self.canvas
        c.setFillColor(self.text_dark)
        c.setFont("Helvetica-Bold", 18)
        c.drawString(20 * mm, self.page_height - 22 * mm, title)
        c.setStrokeColor(self.primary_red)
        c.setLineWidth(1.8)
        c.line(20 * mm, self.page_height - 25 * mm, self.page_width - 20 * mm, self.page_height - 25 * mm)

    def _draw_table_under_title(self, table, top_margin_mm=34, bottom_margin_mm=22):
        max_width = self.page_width - 40 * mm
        _, table_height = table.wrap(max_width, self.page_height)
        y = self.page_height - (top_margin_mm * mm) - table_height
        min_y = bottom_margin_mm * mm
        if y < min_y:
            y = min_y
        table.drawOn(self.canvas, 20 * mm, y)

    def _draw_kpi_box(self, x, y, width, height, key, label, unit):
        c = self.canvas
        c.setStrokeColor(self.border_gray)
        c.setFillColor(colors.HexColor("#FAFAFA"))
        c.roundRect(x, y - height, width, height, 4, stroke=1, fill=1)

        current_value = self.current_summary.get(key, 0)
        previous_value = self.previous_summary.get(key, 0)
        delta = current_value - previous_value
        direction = "UP" if delta >= 0 else "DOWN"
        delta_color = colors.HexColor("#2E7D32") if delta >= 0 else colors.HexColor("#B71C1C")

        c.setFillColor(self.text_muted)
        c.setFont("Helvetica", 9.5)
        c.drawString(x + 4 * mm, y - 7 * mm, label)

        c.setFillColor(self.text_dark)
        c.setFont("Helvetica-Bold", 15)
        c.drawString(x + 4 * mm, y - 16 * mm, f"{self._fmt_num(current_value, 2)} {unit}")

        c.setFillColor(delta_color)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(
            x + 4 * mm,
            y - 25 * mm,
            f"{direction} {self._fmt_num(abs(delta), 2)} vs previous month",
        )

    def _draw_logo(self, center_y, width_mm=40, height_mm=40):
        logo_path = Path(settings.BASE_DIR) / "static" / "img" / "logomaretap.png"
        width = width_mm * mm
        height = height_mm * mm
        x = (self.page_width - width) / 2
        y = center_y - (height / 2)

        if logo_path.exists():
            self.canvas.drawImage(str(logo_path), x, y, width=width, height=height, preserveAspectRatio=True, mask="auto")
        else:
            self.canvas.setFillColor(self.text_muted)
            self.canvas.setFont("Helvetica-Bold", 16)
            self.canvas.drawCentredString(self.page_width / 2, center_y, "MARETAP")

    def _draw_footer(self, page_number, total_pages):
        c = self.canvas
        c.setStrokeColor(self.border_gray)
        c.setLineWidth(0.6)
        c.line(15 * mm, 14 * mm, self.page_width - 15 * mm, 14 * mm)
        c.setFont("Helvetica", 8.5)
        c.setFillColor(self.text_muted)
        c.drawCentredString(
            self.page_width / 2,
            8 * mm,
            f"MARETAP S.A. - Confidential - Page {page_number}/{total_pages}",
        )

    def _get_month_comments(self, year, month):
        """Return the most recent non-empty DimDate.comments for the given month, or None."""
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT TOP 1 comments FROM dbo.DimDate
                    WHERE [Year] = %s AND [Month] = %s
                      AND comments IS NOT NULL AND LTRIM(RTRIM(comments)) <> ''
                    ORDER BY FullDate DESC
                    """,
                    [year, month]
                )
                row = cursor.fetchone()
                if row and row[0] and str(row[0]).strip():
                    return str(row[0]).strip()
        except Exception:
            pass
        return None

    def _draw_remarks_box(self, y_top, text):
        """Draw a highlighted note box with field operator remarks."""
        if y_top < 38 * mm:
            return
        c = self.canvas
        box_x = 20 * mm
        box_w = self.page_width - 40 * mm

        words = text.split()
        lines, current = [], ""
        for word in words:
            test = (current + " " + word).strip()
            if c.stringWidth(test, "Helvetica", 9) < float(box_w - 8 * mm):
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)

        line_h = 5 * mm
        label_h = 7 * mm
        box_h = label_h + len(lines) * line_h + 5 * mm

        if y_top - box_h < 20 * mm:
            return

        c.setFillColor(colors.HexColor("#FFFDE7"))
        c.setStrokeColor(colors.HexColor("#F9A825"))
        c.setLineWidth(0.8)
        c.roundRect(box_x, y_top - box_h, box_w, box_h, 3, stroke=1, fill=1)

        date_label = f"{MONTHS_FR.get(self.month, str(self.month))} {self.year}"
        c.setFillColor(colors.HexColor("#F57F17"))
        c.setFont("Helvetica-Bold", 9)
        c.drawString(box_x + 3 * mm, y_top - label_h + 2 * mm, f"Remarques journalieres — {date_label}")

        c.setFillColor(self.text_dark)
        c.setFont("Helvetica", 9)
        text_y = y_top - label_h - 3 * mm
        for line in lines:
            c.drawString(box_x + 3 * mm, text_y, line)
            text_y -= line_h

    def _safe_summary(self, year, month):
        try:
            return get_field_production_summary(year=year, month=month) or {}
        except Exception:
            return {}

    def _safe_ranking_rows(self, year, month):
        try:
            top_rows = get_top_producers(limit=16, year=year, month=month) or []
        except Exception:
            top_rows = []

        if not top_rows:
            return []

        try:
            detail_rows = get_well_kpis(year=year, month=month) or []
        except Exception:
            detail_rows = []
        detail_map = {row.get("well_code"): row for row in detail_rows}

        codes = [row.get("well_code") for row in top_rows if row.get("well_code")]
        status_map = {}
        try:
            for well in DimWell.objects.filter(well_code__in=codes):
                status_map[well.well_code] = "Closed" if well.closed == "Y" else "Active"
        except Exception:
            pass

        out = []
        for row in top_rows:
            code = row.get("well_code")
            details = detail_map.get(code, {})
            out.append(
                {
                    "well_code": code or "-",
                    "avg_bopd": row.get("avg_bopd", 0),
                    "avg_bsw": row.get("avg_bsw", details.get("avg_bsw", 0)),
                    "avg_gor": details.get("avg_gor", 0),
                    "status": status_map.get(code, "Active"),
                }
            )
        return out

    def _safe_trend_rows(self, year):
        try:
            return get_monthly_trend(year=year) or []
        except Exception:
            return []

    def _safe_month_anomalies(self, year, month):
        try:
            start = date(year, month, 1)
            end = date(year, month, calendar.monthrange(year, month)[1])
            return list(
                Anomalie.objects.filter(
                    detected_at__date__gte=start,
                    detected_at__date__lte=end,
                ).order_by("-detected_at")[:50]
            )
        except Exception:
            return []

    def _safe_month_imported_files(self, year, month):
        try:
            start = date(year, month, 1)
            end = date(year, month, calendar.monthrange(year, month)[1])
            return list(
                UploadedFile.objects.filter(
                    status=UploadedFile.Status.SUCCESS,
                    created_at__date__gte=start,
                    created_at__date__lte=end,
                )
                .order_by("-created_at")[:12]
            )
        except Exception:
            return []

    def _safe_imported_file_anomalies(self, uploaded_files):
        anomalies = []
        for uploaded in uploaded_files:
            try:
                filepath = uploaded.file.path
            except Exception:
                continue

            if not filepath:
                continue

            try:
                if uploaded.file_type == UploadedFile.FileType.PDF:
                    text, error = parse_pdf(filepath)
                    if error:
                        continue
                    anomalies.extend(self._extract_anomaly_mentions(text, uploaded))
                    continue

                if uploaded.file_type == UploadedFile.FileType.DOCX:
                    text, error = parse_word(filepath)
                    if error:
                        continue
                    anomalies.extend(self._extract_anomaly_mentions(text, uploaded))
                    continue

                if uploaded.file_type == UploadedFile.FileType.XLSX:
                    records, error = parse_excel(filepath)
                    if error:
                        continue
                    for row in records[:250]:
                        row_text = " | ".join(f"{k}: {v}" for k, v in row.items() if str(v).strip())
                        anomalies.extend(self._extract_anomaly_mentions(row_text, uploaded))
            except Exception:
                continue

        return anomalies[:60]

    def _extract_anomaly_mentions(self, raw_text, uploaded):
        if not raw_text:
            return []

        keywords = (
            "anomaly",
            "anomalie",
            "incident",
            "failure",
            "critical",
            "critique",
            "warning",
            "alerte",
            "leak",
            "fuite",
            "corrosion",
            "shutdown",
            "shut-in",
        )

        mentions = []
        seen = set()
        lines = re.split(r"[\r\n]+", str(raw_text))

        for line in lines:
            normalized = re.sub(r"\s+", " ", line).strip()
            if len(normalized) < 12:
                continue

            lower_line = normalized.lower()
            if not any(keyword in lower_line for keyword in keywords):
                continue

            key = normalized[:180]
            if key in seen:
                continue
            seen.add(key)

            mentions.append(
                ReportAnomaly(
                    detected_at=getattr(uploaded, "created_at", None),
                    well_code=self._extract_well_code(normalized),
                    anomaly_type="Imported file mention",
                    severity=self._severity_from_text(lower_line),
                    description=f"{uploaded.original_name}: {self._truncate(normalized, 140)}",
                    source="FILES",
                )
            )
            if len(mentions) >= 6:
                break

        return mentions

    def _merge_anomalies(self, dwh_anomalies, file_anomalies):
        merged = list(dwh_anomalies or [])
        merged.extend(file_anomalies or [])
        merged.sort(
            key=lambda item: getattr(item, "detected_at", None) or datetime.min,
            reverse=True,
        )
        return merged

    def _critical_anomalies(self, anomalies):
        critical_labels = ("critique", "critical", "high", "majeure", "majeur", "urgent")
        selected = []
        for anomaly in anomalies:
            severity = str(getattr(anomaly, "severity", "")).strip().lower()
            if any(label in severity for label in critical_labels):
                selected.append(anomaly)
        return selected if selected else anomalies

    @staticmethod
    def _severity_from_text(text):
        if any(token in text for token in ("critical", "critique", "urgent", "majeur", "majeure")):
            return "Critical"
        if any(token in text for token in ("warning", "alerte", "high")):
            return "High"
        return "Medium"

    @staticmethod
    def _extract_well_code(text):
        match = re.search(r"\bEZZ\d{1,3}\b", text.upper())
        return match.group(0) if match else "-"

    @staticmethod
    def _anomaly_source(anomaly):
        source = str(getattr(anomaly, "source", "DWH") or "DWH").strip().upper()
        return source[:12]

    @staticmethod
    def _fmt_num(value, decimals):
        try:
            number = float(value or 0)
            return f"{number:,.{decimals}f}".replace(",", " ")
        except Exception:
            return "-"

    @staticmethod
    def _truncate(value, max_len):
        if len(value) <= max_len:
            return value
        return value[: max_len - 3] + "..."

    @staticmethod
    def _get_previous_month(year, month):
        if month == 1:
            return year - 1, 12
        return year, month - 1

    @staticmethod
    def _anomaly_line(anomaly, max_len=100):
        detected = getattr(anomaly, "detected_at", None)
        date_str = detected.strftime("%d/%m/%Y") if detected else "-"
        well_code = str(getattr(anomaly, "well_code", "-") or "-")
        anomaly_type = str(getattr(anomaly, "anomaly_type", "-") or "-")
        severity = str(getattr(anomaly, "severity", "-") or "-")
        source = str(getattr(anomaly, "source", "DWH") or "DWH")
        line = f"{date_str} | {well_code} | {anomaly_type} | {severity} | {source}"
        return EzzaouiaReportGenerator._truncate(line, max_len)

