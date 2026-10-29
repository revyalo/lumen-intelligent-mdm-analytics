"""Execute notebooks using this interpreter, keeping outputs inside each notebook."""
import sys
from pathlib import Path

import nbformat
from jupyter_client import KernelManager
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
for path in sorted((ROOT / "notebooks").glob("*.ipynb")):
    notebook = nbformat.read(path, as_version=4)
    manager = KernelManager(kernel_name="python3")
    manager.kernel_spec.argv = [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"]
    client = NotebookClient(notebook, timeout=120, resources={"metadata": {"path": str(path.parent)}})
    client.km = manager
    client.execute()
    nbformat.write(notebook, path)
    print(f"Executed {path.name}", flush=True)
