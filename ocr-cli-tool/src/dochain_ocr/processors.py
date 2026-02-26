from pathlib import Path

import cv2
import fitz  # pymupdf
import numpy as np
from PIL import Image

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"}
PDF_SUFFIXES = {".pdf"}
SUPPORTED_SUFFIXES = IMAGE_SUFFIXES | PDF_SUFFIXES


class ImageProcessor:
    def load_image(self, image_path: str) -> Image.Image:
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
        return Image.open(path)

    def load_images_from_pdf(self, pdf_path: str, dpi: int = 300) -> list[Image.Image]:
        """Convert each page of a PDF to a PIL Image."""
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        doc = fitz.open(str(path))
        images: list[Image.Image] = []
        for page in doc:
            mat = fitz.Matrix(dpi / 72, dpi / 72)
            pix = page.get_pixmap(matrix=mat)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            images.append(img)
        doc.close()
        return images

    def preprocess_image(self, image: Image.Image) -> Image.Image:
        """Convert to RGB for PaddleOCR compatibility."""
        if image.mode != "RGB":
            image = image.convert("RGB")
        return image