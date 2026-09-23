from executor import run_sandbox
from pathlib import Path

csv_path = Path(__file__).parent / "sales.csv"
code="""
df = pd.read_csv(csv_path)
result = df.groupby("region")["revenue"].sum()
print(result)
"""
result=run_sandbox(code,str(csv_path))
print(result)
