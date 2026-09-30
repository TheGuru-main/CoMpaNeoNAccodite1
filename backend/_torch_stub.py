"""
Torch stub for environments where torch is not installed.

Purpose: allow modules that `import torch` at load time to import
successfully, while raising a clear error only when torch features are
actually used.

On the training host (with real torch installed), this file is never used.
On the Render response host (no torch), this keeps the app bootable.
"""
from __future__ import annotations


class _TorchUnavailableError(RuntimeError):
    pass


class _StubTensor:
    """Minimal placeholder so type annotations like torch.Tensor resolve."""

    def __init__(self, *a, **k):
        raise _TorchUnavailableError(
            "torch is not installed on this runtime. "
            "This operation requires torch — deploy on a host with torch."
        )

    def __getattr__(self, name):
        raise _TorchUnavailableError(
            f"torch.Tensor.{name} called without torch installed"
        )


def _raise(*a, **k):
    raise _TorchUnavailableError(
        "torch is not installed on this runtime"
    )


class _StubNamespace:
    """Attribute access returns either a raise-only callable or _raise."""
    def __init__(self, name):
        self.__name = name

    def __getattr__(self, name):
        # return a callable that raises when invoked
        def _call(*a, **k):
            raise _TorchUnavailableError(
                f"torch.{self.__name}.{name} called without torch installed"
            )
        return _call

    def __call__(self, *a, **k):
        raise _TorchUnavailableError(
            f"torch.{self.__name} called without torch installed"
        )


class _StubTorch:
    """Top-level torch namespace. Every attribute access is deferred."""
    Tensor = _StubTensor
    float32 = "float32"
    float16 = "float16"
    long = "long"
    int32 = "int32"
    bool = "bool"

    def __getattr__(self, name):
        return _StubNamespace(name)

    def __call__(self, *a, **k):
        raise _TorchUnavailableError(
            "torch is not installed on this runtime"
        )


TORCH_STUB = _StubTorch()
TORCH_STUB_FUNCTIONAL = _StubNamespace("nn.functional")
TORCH_STUB_NN = _StubNamespace("nn")
TORCH_STUB_OPTIM = _StubNamespace("optim")


def install() -> None:
    """
    Register the stub in sys.modules under 'torch', 'torch.nn', and
    'torch.nn.functional' so `import torch` succeeds but any use raises.
    Safe to call even if real torch exists — checks sys.modules first.
    """
    import sys, types

    if "torch" in sys.modules:
        try:
            import torch  # noqa: F401
            return  # real torch
        except Exception:
            pass

    torch_mod = types.ModuleType("torch")
    torch_mod.Tensor = _StubTensor
    torch_mod.float32 = "float32"
    torch_mod.float16 = "float16"
    torch_mod.long = "long"
    torch_mod.bool = "bool"

    # submodules
    nn_mod = types.ModuleType("torch.nn")
    nn_functional = types.ModuleType("torch.nn.functional")
    optim_mod = types.ModuleType("torch.optim")

    # mark class constructors as raising
    class _StubModuleBase:
        def __init__(self, *a, **k):
            raise _TorchUnavailableError("torch.nn.Module unavailable")

    nn_mod.Module = _StubModuleBase
    nn_mod.Linear = _StubModuleBase
    nn_mod.Embedding = _StubModuleBase
    nn_mod.LayerNorm = _StubModuleBase
    nn_mod.Dropout = _StubModuleBase
    nn_mod.Sequential = _StubModuleBase
    nn_mod.ModuleList = _StubModuleBase
    nn_mod.ReLU = _StubModuleBase
    nn_mod.GELU = _StubModuleBase

    def _fs(*a, **k):
        raise _TorchUnavailableError("torch.nn.functional unavailable")
    nn_functional.softmax = _fs
    nn_functional.relu = _fs
    nn_functional.gelu = _fs

    # allow `torch.nn` / `torch.optim` attribute chains
    torch_mod.nn = nn_mod
    torch_mod.optim = optim_mod

    # `from torch import Tensor` style
    torch_mod.set_default_dtype = _fs

    sys.modules.setdefault("torch", torch_mod)
    sys.modules.setdefault("torch.nn", nn_mod)
    sys.modules.setdefault("torch.nn.functional", nn_functional)
    sys.modules.setdefault("torch.optim", optim_mod)
