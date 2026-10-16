import io
from app.analytics.exporter import sanitize_csv_cell, export_analysis_to_csv


def test_csv_formula_injection_sanitization():
    # Dangerous formulas that can trigger DDE execution in Excel
    dangerous_inputs = [
        "=cmd|'/C calc'!A0",
        "@SUM(1+1)",
        "+2+5",
        "-10*5",
        "\tmalicious",
        "\rmalicious",
    ]

    for val in dangerous_inputs:
        sanitized = sanitize_csv_cell(val)
        assert sanitized.startswith("'"), f"Failed to sanitize dangerous input: {val}"

    # Safe inputs should remain unchanged
    safe_inputs = ["Laptop", "Electronics", "1200.50", "North"]
    for val in safe_inputs:
        sanitized = sanitize_csv_cell(val)
        assert sanitized == val


def test_csv_export_format():
    columns = ["product", "revenue"]
    rows = [
        {"product": "Laptop", "revenue": 1200.0},
        {"product": "=DangerousFormula()", "revenue": 500.0},
    ]
    csv_str = export_analysis_to_csv(columns, rows)
    lines = csv_str.strip().splitlines()
    assert len(lines) == 3
    assert lines[0] == "product,revenue"
    assert "Laptop,1200.0" in lines[1]
    # Sanitized cell must start with quote
    assert "'=DangerousFormula()" in lines[2]
