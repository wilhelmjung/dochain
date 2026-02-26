"""Tests for dochain-ocr CLI entry point."""

from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner
from PIL import Image

from dochain_ocr.cli import main
from dochain_ocr.base import BaseOCREngine


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def dummy_image(tmp_path) -> Path:
    """Create a minimal 10×10 white PNG for testing."""
    img = Image.new("RGB", (10, 10), color="white")
    p = tmp_path / "test.png"
    img.save(str(p))
    return p


@pytest.fixture
def dummy_pdf(tmp_path) -> Path:
    """Create a minimal 1-page PDF via pymupdf."""
    import fitz
    doc = fitz.open()
    page = doc.new_page(width=100, height=100)
    page.insert_text((10, 50), "hello")
    p = tmp_path / "test.pdf"
    doc.save(str(p))
    doc.close()
    return p


class FakeEngine(BaseOCREngine):
    """A trivial engine that always returns fixed text."""

    def __init__(self, text: str = "fake result"):
        self.text = text

    def recognize_text(self, image: Image.Image) -> str:
        return self.text


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------

class TestCLI:

    def test_help(self, runner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Usage:" in result.output
        assert "--engine" in result.output

    def test_missing_input(self, runner):
        result = runner.invoke(main, [])
        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

    def test_unsupported_file_type(self, runner, tmp_path):
        txt = tmp_path / "notes.txt"
        txt.write_text("hello")
        result = runner.invoke(main, ["--input", str(txt)])
        assert result.exit_code != 0
        assert "Unsupported file type" in result.output

    def test_file_not_found(self, runner):
        result = runner.invoke(main, ["--input", "/nonexistent/foo.png"])
        assert result.exit_code != 0

    @patch("dochain_ocr.cli.create_engine")
    def test_image_input(self, mock_create, runner, dummy_image):
        mock_create.return_value = FakeEngine("hello world")
        result = runner.invoke(main, ["--input", str(dummy_image)])
        assert result.exit_code == 0
        assert "hello world" in result.output

    @patch("dochain_ocr.cli.create_engine")
    def test_pdf_input(self, mock_create, runner, dummy_pdf):
        mock_create.return_value = FakeEngine("pdf text")
        result = runner.invoke(main, ["--input", str(dummy_pdf)])
        assert result.exit_code == 0
        assert "PDF loaded" in result.output
        assert "pdf text" in result.output

    @patch("dochain_ocr.cli.create_engine")
    def test_output_file(self, mock_create, runner, dummy_image, tmp_path):
        mock_create.return_value = FakeEngine("saved text")
        out = tmp_path / "sub" / "result.txt"
        result = runner.invoke(main, ["--input", str(dummy_image), "--output", str(out)])
        assert result.exit_code == 0
        assert out.exists()
        assert out.read_text(encoding="utf-8") == "saved text"

    @patch("dochain_ocr.cli.create_engine")
    def test_engine_choice_passed(self, mock_create, runner, dummy_image):
        mock_create.return_value = FakeEngine()
        runner.invoke(main, ["--input", str(dummy_image), "--engine", "baidu"])
        mock_create.assert_called_once()
        assert mock_create.call_args[0][0] == "baidu"

    def test_invalid_engine(self, runner, dummy_image):
        result = runner.invoke(main, ["--input", str(dummy_image), "--engine", "unknown"])
        assert result.exit_code != 0

    @patch("dochain_ocr.cli.create_engine")
    def test_multipage_pdf(self, mock_create, runner, tmp_path):
        """Multi-page PDF should produce page markers."""
        import fitz
        doc = fitz.open()
        doc.new_page(width=100, height=100)
        doc.new_page(width=100, height=100)
        p = tmp_path / "multi.pdf"
        doc.save(str(p))
        doc.close()

        mock_create.return_value = FakeEngine("page text")
        result = runner.invoke(main, ["--input", str(p)])
        assert result.exit_code == 0
        assert "--- Page 1 ---" in result.output
        assert "--- Page 2 ---" in result.output