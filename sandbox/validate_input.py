import ast
from typing import Tuple

FORBIDDEN_MODULES = {
    "os", "sys", "subprocess", "shutil", "socket", 
    "requests", "urllib", "http", "importlib", "pathlib", "ctypes"
}

FORBIDDEN_FUNCTIONS = {
    "exec", "eval", "open", "__import__", "compile"
}

def validate_code(code_str: str) -> Tuple[bool, str]:
    
    try:
        tree = ast.parse(code_str)
    except SyntaxError as e:
        return False, f"SyntaxError during validation: {e}"

    for node in ast.walk(tree):
        #direct imports catch
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_module = alias.name.split('.')[0]
                if root_module in FORBIDDEN_MODULES:
                    return False, f"SecurityError: Import of module '{alias.name}' is strictly forbidden."

        #Catch sub-module imports
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root_module = node.module.split('.')[0]
                if root_module in FORBIDDEN_MODULES:
                    return False, f"SecurityError: Import from module '{node.module}' is strictly forbidden."

        #Catch dangerous built-in function calls
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_FUNCTIONS:
                return False, f"SecurityError: Call to built-in function '{node.func.id}()' is strictly forbidden."

    return True, ""