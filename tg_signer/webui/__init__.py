"""WebUI package exports.

Do not import optional NiceGUI dependencies merely to read WebUI configuration
or use non-UI helpers. Load the GUI implementation only on demand.
"""

from importlib import import_module
from typing import Any

__all__ = ["build_ui", "main", "AUTH_CODE_ENV"]


def __getattr__(name: str) -> Any:
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(import_module("tg_signer.webui.app"), name)
