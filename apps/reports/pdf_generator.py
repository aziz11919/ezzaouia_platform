import calendar
from datetime import date, datetime
from io import BytesIO
from pathlib import Path

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle

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
        self.ranking_rows = self._safe_ranking_rows(self.year, self.month)
        self.trend_rows = self._safe_trend_rows(self.year)

        pages = [self._draw_cover_page]
        if self.role in {"direction", "admin"}:
            pages.append(self._draw_executive_page)
        pages.append(self._draw_wells_page)
        if self.role == "ingenieur":
            pages.append(self._draw_trend_page)
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

        c.setFont("Helvetica-Bold", 12)
        c.setFillColor(self.text_dark)
        c.drawString(20 * mm, self.page_height - 165 * mm, "Critical anomalies of the month")

        anomalies = self._critical_anomalies(self.month_anomalies)
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

    def _draw_wells_page(self):
        self._draw_page_title(
            f"Well ranking - Top 16 ({MONTHS_FR.get(self.month, self.month)} {self.year})"
        )

        data = [["#", "Well", "BOPD", "BSW %", "GOR", "Status"]]
        if self.ranking_rows:
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
        else:
            data.append(["-", "No data", "-", "-", "-", "-"])

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

        table.wrapOn(self.canvas, self.page_width - 40 * mm, self.page_height - 70 * mm)
        table.drawOn(self.canvas, 20 * mm, self.page_height - 245 * mm)

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

        table.wrapOn(self.canvas, self.page_width - 40 * mm, self.page_height - 70 * mm)
        table.drawOn(self.canvas, 20 * mm, self.page_height - 250 * mm)

    def _draw_anomalies_page(self):
        self._draw_page_title("Detected anomalies")

        data = [["Date", "Well", "Type", "Severity", "Description"]]
        if self.month_anomalies:
            for anomaly in self.month_anomalies[:20]:
                detected = getattr(anomaly, "detected_at", None)
                data.append(
                    [
                        detected.strftime("%d/%m/%Y") if detected else "-",
                        str(getattr(anomaly, "well_code", "-") or "-"),
                        str(getattr(anomaly, "anomaly_type", "-") or "-"),
                        str(getattr(anomaly, "severity", "-") or "-"),
                        self._truncate(str(getattr(anomaly, "description", "") or "-"), 58),
                    ]
                )
        else:
            data.append(["-", "-", "-", "-", "No anomalies in this period."])

        table = Table(
            data,
            colWidths=[24 * mm, 20 * mm, 32 * mm, 24 * mm, 84 * mm],
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

        table.wrapOn(self.canvas, self.page_width - 40 * mm, self.page_height - 70 * mm)
        table.drawOn(self.canvas, 20 * mm, self.page_height - 250 * mm)

    def _draw_page_title(self, title):
        c = self.canvas
        c.setFillColor(self.text_dark)
        c.setFont("Helvetica-Bold", 18)
        c.drawString(20 * mm, self.page_height - 22 * mm, title)
        c.setStrokeColor(self.primary_red)
        c.setLineWidth(1.8)
        c.line(20 * mm, self.page_height - 25 * mm, self.page_width - 20 * mm, self.page_height - 25 * mm)

    def _draw_kpi_box(self, x, y, width, height, key, label, unit):
        c = self.canvas
        c.setStrokeColor(self.border_gray)
        c.setFillColor(colors.HexColor("#FAFAFA"))
        c.roundRect(x, y - height, width, height, 4, stroke=1, fill=1)

        current_value = self.current_summary.get(key, 0)
        previous_value = self.previous_summary.get(key, 0)
        delta = current_value - previous_value
        arrow = "↑" if delta >= 0 else "↓"
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
            f"{arrow} {self._fmt_num(abs(delta), 2)} vs previous month",
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
            for well in DimWell.objects.filter(wellcode__in=codes):
                status_map[well.wellcode] = "Closed" if well.closed == "Y" else "Active"
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

    def _critical_anomalies(self, anomalies):
        critical_labels = {"critique", "critical", "high", "majeure", "majeur"}
        selected = []
        for anomaly in anomalies:
            severity = str(getattr(anomaly, "severity", "")).strip().lower()
            if severity in critical_labels:
                selected.append(anomaly)
        return selected if selected else anomalies

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
        return value[: max_len - 1] + "…"

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
        line = f"{date_str} | {well_code} | {anomaly_type} | {severity}"
        return EzzaouiaReportGenerator._truncate(line, max_len)
