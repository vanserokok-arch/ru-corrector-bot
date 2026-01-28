"""Russian text corrector package."""
from .config import config
from .services import correct_text

__version__ = "1.0.0"

__all__ = [
    "config",
    "correct_text",
    "__version__",
]
