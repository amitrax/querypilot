import csv
import io
import json
from typing import List, Dict, Any


def sanitize_csv_cell(value: Any) -> str:
    """
    Protects CSV output against formula injection attacks (CSV Injection / DDE).
    If a string starts with =, +, -, @, \t, \r, %, or | (even with leading spaces),
    prepend a single quote '.
    """
    if value is None:
        return ""
    str_val = str(value)
    if not str_val:
        return ""
    if str_val[0] in ("\t", "\r"):
        return f"'{str_val}"
    space_stripped = str_val.lstrip(" ")
    if space_stripped and space_stripped[0] in ("=", "+", "-", "@", "\t", "\r", "%", "|"):
        return f"'{str_val}"
    return str_val


def export_analysis_to_csv(columns: List[str], rows: List[Dict[str, Any]]) -> str:
    """Generates a secure CSV string from analysis result rows."""
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    # Write headers
    writer.writerow([sanitize_csv_cell(col) for col in columns])

    # Write data rows
    for row in rows:
        writer.writerow([sanitize_csv_cell(row.get(col, "")) for col in columns])

    return output.getvalue()


def generate_text_summary_report(
    question: str,
    operation_summary: str,
    explanation: str,
    columns: List[str],
    rows: List[Dict[str, Any]],
    execution_time_ms: float
) -> str:
    """Generates an executive textual summary report."""
    report_lines = [
        "=" * 60,
        "QUERYPILOT - EXECUTIVE DATA ANALYSIS REPORT",
        "=" * 60,
        f"Question: {question}",
        f"Operation: {operation_summary}",
        f"Execution Time: {execution_time_ms:.2f} ms",
        "-" * 60,
        "EXECUTIVE SUMMARY & FINDINGS:",
        explanation or "No explanation generated.",
        "-" * 60,
        f"RESULT DATA ({min(len(rows), 20)} of {len(rows)} records shown):",
    ]

    # Add tabular preview
    if columns:
        header_line = " | ".join(columns[:6])
        report_lines.append(header_line)
        report_lines.append("-" * len(header_line))
        for row in rows[:20]:
            vals = [str(row.get(c, "")) for c in columns[:6]]
            report_lines.append(" | ".join(vals))

    report_lines.append("=" * 60)
    return "\n".join(report_lines)
