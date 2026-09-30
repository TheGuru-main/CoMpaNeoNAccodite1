import sys, pathlib
HERE = pathlib.Path(__file__).parent
for d in HERE.iterdir():
    if d.is_dir() and not d.name.startswith("__"):
        sys.path.insert(0, str(d))


# TORCH-STUB: install stub torch into sys.modules if the real one is absent.
# Runs before any other module imports torch, so `import torch` always succeeds.
try:
    import torch  # noqa: F401
except ImportError:
    try:
        from _torch_stub import install as _install_torch_stub
        _install_torch_stub()
    except Exception:
        pass
