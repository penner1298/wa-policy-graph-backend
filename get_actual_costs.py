import subprocess
result = subprocess.run(["cd sao-scraper && source ../.venv/bin/activate && python3 run_2024_membrane.py"], shell=True, capture_output=True, text=True)
print(result.stdout[-500:])
