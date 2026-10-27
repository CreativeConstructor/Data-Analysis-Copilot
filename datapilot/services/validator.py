"""AST checks reduce risk; they do not prove arbitrary Python safe."""
import ast
import os

MAX_CODE_CHARS = int(os.getenv("ANALYSIS_MAX_CODE_CHARS", "12000"))
ALLOWED_IMPORTS = {"pandas", "numpy", "math", "datetime"}
FORBIDDEN_CALLS = {"open", "exec", "eval", "compile", "__import__", "input", "getattr", "setattr", "delattr", "globals", "locals", "vars", "dir", "breakpoint"}
FORBIDDEN_METHODS = {"read_csv", "read_excel", "read_json", "read_parquet", "read_pickle", "read_hdf", "read_sql", "read_fwf", "read_html", "read_xml", "read_feather", "read_stata", "read_sas", "read_spss", "read_gbq", "to_csv", "to_excel", "to_json", "to_pickle", "to_parquet", "to_hdf", "to_sql", "to_clipboard", "to_feather", "to_stata", "to_gbq", "to_xml", "to_html", "get_handle", "get_filepath_or_buffer"}
FORBIDDEN_PANDAS_CONSTRUCTORS = {"ExcelFile", "ExcelWriter", "HDFStore"}

def validate(code, columns=None):
    errors = []
    if not isinstance(code, str) or len(code) > MAX_CODE_CHARS:
        return [{"rule": "code_size", "line": 1, "message": "Code is missing or exceeds the size limit."}]
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return [{"rule": "syntax", "line": exc.lineno or 1, "message": "Generated code has invalid Python syntax."}]
    has_result = False
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.name.split(".")[0] for a in node.names] if isinstance(node, ast.Import) else [(node.module or "").split(".")[0]]
            imported_symbols = [a.name for a in node.names] if isinstance(node, ast.ImportFrom) else []
            if any(n not in ALLOWED_IMPORTS for n in names) or any(a.name == "*" for a in node.names) or any(name in FORBIDDEN_METHODS or name in FORBIDDEN_PANDAS_CONSTRUCTORS for name in imported_symbols):
                errors.append({"rule": "imports", "line": node.lineno, "message": "Only pandas, numpy, math, and datetime imports are allowed."})
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALLS:
                errors.append({"rule": "dangerous_call", "line": node.lineno, "message": "This built-in call is not allowed."})
        elif isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            errors.append({"rule": "dunder_attribute", "line": node.lineno, "message": "Dunder attribute access is not allowed."})
        elif isinstance(node, ast.Attribute) and (node.attr in FORBIDDEN_METHODS or node.attr in FORBIDDEN_PANDAS_CONSTRUCTORS):
            errors.append({"rule": "file_io", "line": node.lineno, "message": "Dataset file and clipboard operations are not allowed."})
        elif columns is not None and isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == "df":
            keys = []
            if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
                keys = [node.slice.value]
            elif isinstance(node.slice, (ast.List, ast.Tuple)):
                keys = [part.value for part in node.slice.elts if isinstance(part, ast.Constant) and isinstance(part.value, str)]
            for key in keys:
                if key not in columns:
                    errors.append({"rule": "missing_column", "line": node.lineno, "message": f"Referenced dataset column is missing: {key[:100]}"})
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(t, ast.Name) and t.id == "result" for t in targets):
                has_result = True
    if not has_result:
        errors.append({"rule": "result", "line": 1, "message": "Assign the final answer to a variable named result."})
    return errors
