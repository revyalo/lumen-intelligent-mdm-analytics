"""Launch locally, reusing an existing environment or installing the base package once."""
import argparse
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description="Start the Lumen local Streamlit application")
parser.add_argument("--check", action="store_true", help="Check readiness without creating an environment or starting a server")
args = parser.parse_args()
binary = "Scripts/python.exe" if os.name == "nt" else "bin/python"
candidates = [ROOT / ".venv" / binary]
interpreter = next((p for p in candidates if p.is_file()), None)
if interpreter is None and importlib.util.find_spec("streamlit") and importlib.util.find_spec("intelligent_mdm"):
    interpreter = Path(sys.executable)
if interpreter is None:
    if args.check:
        raise SystemExit("No prepared environment found. Run without --check to install the application locally.")
    if sys.version_info < (3, 11):
        raise SystemExit("Python 3.11+ is required (tested with 3.12).")
    print("Preparing .venv and installing Lumen from the Python package registry…", flush=True)
    subprocess.run([sys.executable, "-m", "venv", str(ROOT / ".venv")], check=True)
    interpreter = ROOT / ".venv" / binary
    subprocess.run([str(interpreter), "-m", "pip", "install", "-e", str(ROOT)], check=True)
if args.check:
    subprocess.run([str(interpreter), "-c", "import streamlit, intelligent_mdm; print('Lumen environment ready')"], check=True)
else:
    os.chdir(ROOT)
    os.execv(str(interpreter), [str(interpreter), "-m", "streamlit", "run", "dashboard/app.py", "--server.address", "127.0.0.1"])
