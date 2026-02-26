"""Tests for ImageProcessor and suffix sets."""

from pathlib import Path

import pytest
from PIL import Image

from dochain_ocr.processors import (
    ImageProcessor,
    IMAGE_SUFFIXES,
    PDF_SUFFIXES,
    SUPPORTED_SUFFIXES,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def dummy_image(tmp_path) -> Path:
    img = Image.new("RGB", (10, 10), color="white")
    p = tmp_path / "test.png"
    img.save(str(p))
    return p


@pytest.fixture
def dummy_pdf(tmp_path) -> Path:
    import fitz
    doc = fitz.open()
    page = doc.new_page(width=100, height=100)
    page.insert_text((10, 50), "hello")
    p = tmp_path / "test.pdf"
    doc.save(str(p))
    doc.close()
    return p


# ---------------------------------------------------------------------------
# ImageProcessor tests
# ---------------------------------------------------------------------------

class TestImageProcessor:

    def test_load_image(self, dummy_image):
        proc = ImageProcessor()
        img = proc.load_image(str(dummy_image))
        assert isinstance(img, Image.Image)
        assert img.size == (10, 10)

    def test_load_image_not_found(self):
        proc = ImageProcessor()
        with pytest.raises(FileNotFoundError):
            proc.load_image("/nonexistent/image.png")

    def test_load_pdf(self, dummy_pdf):
        proc = ImageProcessor()
        images = proc.load_images_from_pdf(str(dummy_pdf))
        assert len(images) == 1
        assert isinstance(images[0], Image.Image)

    def test_load_pdf_not_found(self):
        proc = ImageProcessor()
        with pytest.raises(FileNotFoundError):
            proc.load_images_from_pdf("/nonexistent/doc.pdf")

    def test_preprocess_rgba(self):
        """RGBA should be converted to RGB."""
        proc = ImageProcessor()
        rgba = Image.new("RGBA", (5, 5), color=(255, 0, 0, 128))
        rgb = proc.preprocess_image(rgba)
        assert rgb.mode == "RGB"

    def test_preprocess_rgb_passthrough(self):
        proc = ImageProcessor()
        rgb = Image.new("RGB", (5, 5))
        result = proc.preprocess_image(rgb)
        assert result.mode == "RGB"

    def test_preprocess_grayscale(self):
        proc = ImageProcessor()
        gray = Image.new("L", (5, 5))
        result = proc.preprocess_image(gray)
        assert result.mode == "RGB"


# ---------------------------------------------------------------------------
# Suffix sets tests
# ---------------------------------------------------------------------------

class TestSupportedSuffixes:

    def test_image_suffixes(self):
        for ext in (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"):
            assert ext in IMAGE_SUFFIXES
            assert ext in SUPPORTED_SUFFIXES

    def test_pdf_suffixes(self):
        assert ".pdf" in PDF_SUFFIXES
        assert ".pdf" in SUPPORTED_SUFFIXES

    def test_unsupported(self):
        assert ".txt" not in SUPPORTED_SUFFIXES
        assert ".doc" not in SUPPORTED_SUFFIXES
