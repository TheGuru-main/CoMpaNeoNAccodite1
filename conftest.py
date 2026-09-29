import sys, pathlib
ROOT = pathlib.Path(__file__).parent
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
for d in BACKEND.iterdir():
    if d.is_dir() and not d.name.startswith("__"):
        sys.path.insert(0, str(d))
