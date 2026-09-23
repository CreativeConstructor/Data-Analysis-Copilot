import subprocess,sys
from validate_input import validate_code
def run_sandbox(code,csv_path):
    valid,error_msg=validate_code(code)
    if not valid:
        return {
            "success": False,
            "stdout": "",
            "stderr": error_msg
        }
        
    full_code =f"""
import pandas as pd
csv_path = {repr(csv_path)}
{code}
    """
    
    try:
        process=subprocess.run([sys.executable,'-c',full_code],capture_output=True,text=True,timeout=10)
        if process.returncode == 0:
            return {
                "success": True,
                "stdout": process.stdout.strip(),
                "stderr": None
            }
        else:
            return {
                "success": False,
                "stdout": process.stdout.strip(),
                "stderr": process.stderr.strip()
            }
        
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": "",
            "error": "Execution timed out"
        }
    
    
