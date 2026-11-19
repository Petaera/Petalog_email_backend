"""Attachments: one Excel workbook per email (default) or CSV files.

REPORT_ATTACHMENT_FORMAT = xlsx (default) | csv | none
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from typing import List

from .models import LocationReport, OwnerReport
from .timeutil import to_ist

INR_FORMAT = '[>=10000000]"₹"##\\,##\\,##\\,##0;[>=100000]"₹"##\\,##\\,##0;"₹"#,##0'

TRANSACTION_HEADERS = [
    "Location", "Date & time (IST)", "Vehicle number", "Vehicle model", "Vehicle type", "Customer", "Phone",
    "Service", "Amount", "Discount", "Payment", "UPI account", "Status", "Entry type", "Nearby / B2B account",
    "Remarks", "Recorded by",
]


@dataclass
class Attachment:
    filename: str
    content: bytes
    maintype: str
    subtype: str


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")[:40] or "location"


def _transaction_rows(r: LocationReport) -> List[list]:
    rows = []
    for t in r.transactions:
        rows.append([
            r.location.name,
            to_ist(t.created_at).strftime("%d/%m/%Y %H:%M") if t.created_at else "",
            t.vehicle_number, t.vehicle_model, t.vehicle_category, t.customer, t.phone, t.service,
            round(t.amount, 2), round(t.discount, 2), t.payment, t.upi_account, t.status, t.entry_type,
            t.workshop, t.remarks, t.recorded_by,
        ])
    return rows


def _summary_rows(r: LocationReport) -> List[list]:
    f = r.figures
    return [
        ["Collections", f.collections], ["Cash", f.cash], ["UPI", f.upi], ["Card", f.card],
        ["Bank Transfer", f.bank], ["From advance", f.from_advance], ["Vehicles served", f.vehicles],
        ["4-wheelers", f.vehicles_4w], ["2-wheelers", f.vehicles_2w], ["Other vehicles", f.vehicles_other],
        ["Average per vehicle", round(f.avg_per_vehicle, 2)], ["Pay Later given (amount)", f.pay_later_amount],
        ["Pay Later given (tickets)", f.pay_later_count], ["Waiting for approval (tickets)", f.pending_count],
        ["Waiting for approval (amount)", f.pending_amount], ["Counter sales", f.counter_sales],
        ["Items sold (incl. with tickets)", f.items_sold], ["Advance received", f.advance_received],
        ["Old dues collected", f.old_dues_collected], ["Expenses", r.spending.expenses],
        ["Staff expenses", r.spending.staff_expenses], ["Salaries & staff advances", r.spending.salaries + r.spending.staff_payments],
        ["Total spending", r.spending.total], ["Net for the day", r.net],
        ["Cash in hand (now)", r.cash_balance if r.cash_balance is not None else "n/a"],
        ["Customers served", r.customers_served], ["New customers", r.customers_new],
    ]


COUNT_LABELS = {"Vehicles served", "4-wheelers", "2-wheelers", "Other vehicles", "Pay Later given (tickets)",
                "Waiting for approval (tickets)", "Customers served", "New customers"}


def build_xlsx(report: OwnerReport) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    head_font = Font(bold=True, color="FFFFFF")
    head_fill = PatternFill("solid", fgColor="004AC6")

    def header(ws, values):
        ws.append(values)
        for cell in ws[ws.max_row]:
            cell.font, cell.fill = head_font, head_fill
            cell.alignment = Alignment(vertical="center")
        ws.freeze_panes = "A2"  # (ws.cell() here would create an empty row 2)

    def widths(ws, sizes):
        for i, w in enumerate(sizes, start=1):
            ws.column_dimensions[get_column_letter(i)].width = w

    ws = wb.active
    ws.title = "Summary"
    names = [r.location.name for r in report.locations]
    header(ws, ["Figure"] + names + (["All locations"] if report.is_multi else []))
    per_location = [_summary_rows(r) for r in report.locations]
    for i, (label, _) in enumerate(per_location[0]):
        values = [rows[i][1] for rows in per_location]
        row = [label] + values
        if report.is_multi:
            row.append(sum(v for v in values if isinstance(v, (int, float))) if label != "Average per vehicle" else "")
        ws.append(row)
        if label not in COUNT_LABELS:
            for cell in ws[ws.max_row][1:]:
                cell.number_format = INR_FORMAT
    widths(ws, [34] + [20] * (len(names) + 1))

    ws = wb.create_sheet("Transactions")
    header(ws, TRANSACTION_HEADERS)
    for r in report.locations:
        for row in _transaction_rows(r):
            ws.append(row)
            ws.cell(row=ws.max_row, column=9).number_format = INR_FORMAT
            ws.cell(row=ws.max_row, column=10).number_format = INR_FORMAT
    widths(ws, [22, 17, 15, 18, 12, 20, 14, 26, 11, 10, 22, 22, 10, 11, 18, 24, 16])

    ws = wb.create_sheet("Payments")
    header(ws, ["Location", "Mode", "Account", "Amount", "Share of collections", "Tickets"])
    for r in report.locations:
        for p in r.payments:
            ws.append([r.location.name, p.label, "", p.amount, round(p.share, 1) / 100, p.count])
            ws.cell(row=ws.max_row, column=4).number_format = INR_FORMAT
            ws.cell(row=ws.max_row, column=5).number_format = "0.0%"
            for c in p.children:
                ws.append([r.location.name, p.label, c.label, c.amount, "", c.count or ""])
                ws.cell(row=ws.max_row, column=4).number_format = INR_FORMAT
    widths(ws, [22, 16, 30, 14, 20, 10])

    ws = wb.create_sheet("Services")
    header(ws, ["Location", "Service", "Vehicles", "Value", "Share"])
    for r in report.locations:
        for s in r.services:
            ws.append([r.location.name, s.label, s.count, s.amount, round(s.share, 1) / 100])
            ws.cell(row=ws.max_row, column=4).number_format = INR_FORMAT
            ws.cell(row=ws.max_row, column=5).number_format = "0.0%"
    widths(ws, [22, 30, 10, 14, 10])

    ws = wb.create_sheet("Spending")
    header(ws, ["Location", "Category", "Amount"])
    for r in report.locations:
        for c in r.spending.by_category:
            ws.append([r.location.name, c.label, c.amount])
            ws.cell(row=ws.max_row, column=3).number_format = INR_FORMAT
    widths(ws, [22, 30, 14])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _csv_bytes(headers: List[str], rows: List[list]) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\r\n")
    writer.writerow(headers)
    writer.writerows(rows)
    return ("﻿" + buf.getvalue()).encode("utf-8")  # BOM: Excel shows ₹ and Malayalam/Hindi names correctly


def build_attachments(report: OwnerReport, fmt_name: str) -> List[Attachment]:
    if fmt_name == "none" or not report.has_activity:
        return []
    day = report.day.isoformat()
    name = f"{len(report.locations)}-locations" if report.is_multi else slug(report.locations[0].location.name)
    if fmt_name == "csv":
        out = []
        for r in report.locations:
            loc = slug(r.location.name)
            out.append(Attachment(f"petalog_{loc}_{day}_transactions.csv",
                                  _csv_bytes(TRANSACTION_HEADERS, _transaction_rows(r)), "text", "csv"))
            out.append(Attachment(f"petalog_{loc}_{day}_summary.csv",
                                  _csv_bytes(["Figure", "Value"], _summary_rows(r)), "text", "csv"))
        return out
    return [Attachment(f"petalog_report_{name}_{day}.xlsx", build_xlsx(report), "application",
                       "vnd.openxmlformats-officedocument.spreadsheetml.sheet")]


def attachment_note(fmt_name: str, has_activity: bool) -> str:
    if fmt_name == "none" or not has_activity:
        return ""
    if fmt_name == "csv":
        return "Every entry of the day is attached as CSV files."
    return "Every entry of the day, with payments, services and spending, is in the attached Excel workbook."
