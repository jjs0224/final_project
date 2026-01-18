from .base import RectifyBackend, RectifyResult
from .doctr_backend import DoctrBackend
from .dewarpnet_backend import DewarpNetBackend
from .docunet_backend import DocUNetBackend
from .auto_backend import AutoBackend

__all__ = [
    "RectifyBackend",
    "RectifyResult",
    "DoctrBackend",
    "DewarpNetBackend",
    "DocUNetBackend",
    "AutoBackend",
]
