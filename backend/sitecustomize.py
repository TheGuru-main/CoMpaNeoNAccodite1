import sys, pathlib
HERE = pathlib.Path(__file__).parent
for d in HERE.iterdir():
    if d.is_dir() and not d.name.startswith("__"):
        sys.path.insert(0, str(d))
