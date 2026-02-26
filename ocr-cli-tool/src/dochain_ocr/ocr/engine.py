"""Backward-compatible re-export. Use ocr.base.create_engine() for new code."""

from .engine_local import LocalOCREngine as OCREngine  # noqa: F401