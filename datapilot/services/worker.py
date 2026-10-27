"""Standalone worker: one JSON request on stdin and one JSON response on stdout."""
import contextlib
import datetime
import io
import json
import math
import re
import sys

class CappedTextIO(io.TextIOBase):
    def __init__(self, limit):
        self.limit = limit
        self.value = []
        self.size = 0
    def write(self, text):
        remaining = self.limit - self.size
        if remaining > 0:
            part = str(text)[:remaining]
            self.value.append(part)
            self.size += len(part)
        return len(text)

def main():
    request = json.loads(sys.stdin.readline())
    max_rows = max(1, int(request.get("max_rows", 100000)))
    max_result_rows = max(1, int(request.get("max_result_rows", 1000)))
    max_result_columns = max(1, int(request.get("max_result_columns", 100)))
    max_output_bytes = max(1024, int(request.get("max_output_bytes", 500000)))
    import numpy as np
    import pandas as pd
    allowed = {"pandas": pd, "numpy": np, "math": math, "datetime": datetime}
    def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
        root = name.split(".")[0]
        if root not in allowed:
            raise ImportError("Import is not allowed")
        return allowed[root]
    builtins = {"__import__": safe_import, "abs": abs, "all": all, "any": any, "bool": bool, "dict": dict,
        "enumerate": enumerate, "filter": filter, "float": float, "int": int, "len": len, "list": list,
        "map": map, "max": max, "min": min, "pow": pow, "range": range, "reversed": reversed,
        "round": round, "set": set, "slice": slice, "sorted": sorted, "str": str, "sum": sum,
        "tuple": tuple, "zip": zip, "Exception": Exception, "ValueError": ValueError, "KeyError": KeyError,
        "TypeError": TypeError, "print": print}
    path = request["dataset_path"]
    if path.lower().endswith(".csv"):
        df = pd.read_csv(path, nrows=max_rows)
    else:
        df = pd.read_excel(path, sheet_name=0, nrows=max_rows, engine="openpyxl")
    stdout = CappedTextIO(10000)
    namespace = {"__builtins__": builtins, "df": df, "pd": pd, "np": np, "math": math, "datetime": datetime}
    try:
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(io.StringIO()):
            exec(compile(request["code"], "<analysis>", "exec"), namespace, namespace)
        result = namespace["result"]
        def clean(value):
            if hasattr(value, "isoformat"):
                return value.isoformat()
            if hasattr(value, "item"):
                value = value.item()
            if isinstance(value, float) and not math.isfinite(value):
                return None
            if value is None or isinstance(value, (str, int, float, bool)):
                return value
            return str(value)[:500]
        if isinstance(result, pd.DataFrame):
            payload = {"kind": "table", "columns": [str(c)[:250] for c in result.columns[:max_result_columns]], "rows": [[clean(v) for v in row] for row in result.iloc[:max_result_rows, :max_result_columns].itertuples(index=False, name=None)], "truncated": len(result) > max_result_rows or len(result.columns) > max_result_columns}
        elif isinstance(result, pd.Series):
            result = result.to_frame()
            payload = {"kind": "table", "columns": [str(c)[:max_result_columns] for c in result.columns[:max_result_columns]], "rows": [[clean(v) for v in row] for row in result.iloc[:max_result_rows, :max_result_columns].itertuples(index=False, name=None)], "truncated": len(result) > max_result_rows or len(result.columns) > max_result_columns}
        elif isinstance(result, dict):
            payload = {"kind": "dict", "value": {str(k)[:100]: clean(v) for k, v in list(result.items())[:max_result_columns]}, "truncated": len(result) > max_result_columns}
        else:
            payload = {"kind": "scalar", "value": clean(result)}
        if payload.get("kind") == "table":
            payload["stdout"] = "".join(stdout.value)
            response = {"ok": True, "result": payload}
            output = json.dumps(response, ensure_ascii=False, allow_nan=False)
            while len(output.encode("utf-8")) > max_output_bytes and payload["rows"]:
                payload["rows"] = payload["rows"][:len(payload["rows"]) // 2]
                payload["truncated"] = True
                output = json.dumps(response, ensure_ascii=False, allow_nan=False)
        else:
            output = json.dumps({"ok": True, "result": payload}, ensure_ascii=False, allow_nan=False)
    except Exception as exc:
        messages = {"KeyError": "A referenced column or key was not found.", "NameError": "Generated code referred to an unknown name.",
            "TypeError": "Generated code used incompatible values.", "ValueError": "Generated code could not process the selected values.",
            "ZeroDivisionError": "Generated code attempted division by zero.", "IndexError": "Generated code selected an unavailable row or column."}
        output = json.dumps({"ok": False, "error": {"type": type(exc).__name__, "message": messages.get(type(exc).__name__, "Generated analysis failed.")}})
    sys.stdout.write(output)

if __name__ == "__main__":
    main()
