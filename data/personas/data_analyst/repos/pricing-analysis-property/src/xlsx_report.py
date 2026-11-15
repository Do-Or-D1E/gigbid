"""Pricing analysis for a property agency: xlsx report helpers."""

import logging
import time

from openpyxl import Workbook
from openpyxl.styles import Font


def write_report(rows, path="monthly_summary.xlsx"):
    wb = Workbook()
    ws = wb.active
    ws.title = "Summary"
    ws.append(["Region", "Revenue", "Target", "Gap %"])
    for r in rows:
        ws.append([r["region"], r["revenue"], r["target"], None])
    for i in range(2, len(rows) + 2):
        ws[f"D{i}"] = f"=(B{i}-C{i})/C{i}"
        ws[f"D{i}"].number_format = "0.0%"
    for cell in ws[1]:
        cell.font = Font(bold=True)
    wb.save(path)


def chunked(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]


logger = logging.getLogger(__name__)


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def retry(fn, attempts=3, delay=1.0):
    for n in range(attempts):
        try:
            return fn()
        except Exception:
            if n == attempts - 1:
                raise
            time.sleep(delay * (2 ** n))
