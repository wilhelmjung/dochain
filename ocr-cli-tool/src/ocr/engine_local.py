"""Local PaddleOCR engine — runs entirely on CPU."""

import os
import pathlib

from PIL import Image

os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

from paddleocr import PaddleOCR  # noqa: E402

from .base import BaseOCREngine


class LocalOCREngine(BaseOCREngine):
    """OCR engine using PaddleOCR local model inference."""

    def __init__(self, lang: str = "ch"):
        self.lang = lang
        self._ocr = PaddleOCR(lang=self.lang)

    def recognize_text(self, image: Image.Image) -> str:
        tmp_path = "_temp_ocr_input.jpg"
        image.save(tmp_path)
        try:
            results = list(self._ocr.predict(tmp_path))
            lines: list[str] = []
            for res in results:
                if "rec_texts" in res:
                    lines.extend(res["rec_texts"])
            return "\n".join(lines)
        finally:
            pathlib.Path(tmp_path).unlink(missing_ok=True)
