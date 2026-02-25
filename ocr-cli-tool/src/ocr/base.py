"""OCR Engine base class and factory."""

from abc import ABC, abstractmethod

from PIL import Image


class BaseOCREngine(ABC):
    """Abstract base class for OCR engines."""

    @abstractmethod
    def recognize_text(self, image: Image.Image) -> str:
        """Recognize text from a PIL Image and return as string."""
        ...


def create_engine(engine_type: str = "local", **kwargs) -> BaseOCREngine:
    """Factory function to create an OCR engine.

    Args:
        engine_type: "local" for PaddleOCR local model, "api" for PaddleOCR AI Studio API.
        **kwargs: Additional arguments passed to the engine constructor.
    """
    if engine_type == "local":
        from .engine_local import LocalOCREngine
        return LocalOCREngine(**kwargs)
    elif engine_type == "api":
        from .engine_api import APIOCREngine
        return APIOCREngine(**kwargs)
    elif engine_type == "baidu":
        from .engine_baidu import BaiduOCREngine
        return BaiduOCREngine(**kwargs)
    elif engine_type == "smart":
        from .engine_smart import SmartOCREngine
        return SmartOCREngine(**kwargs)
    else:
        raise ValueError(f"Unknown engine type: {engine_type}. Use 'local', 'api', 'baidu', or 'smart'.")
