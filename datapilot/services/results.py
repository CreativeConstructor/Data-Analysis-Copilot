"""Turn bounded executor results into factual insights, charts, and tables."""
from datetime import datetime


def format_result(result):
    if result.get("kind") == "table":
        columns, rows = result.get("columns", []), result.get("rows", [])
        table = {**result, "rows": rows[:50], "truncated": result.get("truncated", False) or len(rows) > 50}
        chart = None
        if len(columns) >= 2 and rows:
            values = [row[1] for row in rows if len(row) > 1 and isinstance(row[1], (int, float))]
            if len(values) == len(rows):
                date_like = all(isinstance(row[0], str) and _is_datetime(row[0]) for row in rows)
                if date_like:
                    chart = {"type": "line", "x": columns[0], "y": columns[1], "data": [dict(zip(columns, row)) for row in rows[:50]]}
                elif all(isinstance(row[0], str) for row in rows):
                    chart = {"type": "bar", "x": columns[0], "y": columns[1], "data": [dict(zip(columns, row)) for row in rows[:20]]}
        return table, chart, _insight(columns, rows[:50])
    if result.get("kind") == "scalar":
        text = str(result.get("value"))[:300]
    else:
        text = str(result.get("value", {}))[:300]
    return {"kind": result.get("kind"), "columns": ["value"], "rows": [[text]], "truncated": False}, None, f"The analysis returned {text}."


def _insight(columns, rows):
    if not rows:
        return "The analysis returned no rows."
    if len(columns) >= 2 and rows and all(len(row) > 1 and isinstance(row[1], (int, float)) for row in rows):
        highest = max(rows, key=lambda row: row[1])
        return f"The result contains {len(rows)} rows. {highest[0]} has the highest {columns[1]} value at {highest[1]}."
    return f"The analysis returned {len(rows)} rows across {len(columns)} columns."


def _is_datetime(value):
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False
