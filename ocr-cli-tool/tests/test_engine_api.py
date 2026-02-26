"""Tests for APIOCREngine text extraction."""

from unittest.mock import patch

import pytest


class TestAPIExtraction:

    @pytest.fixture(autouse=True)
    def _setup(self):
        from dochain_ocr.engine_api import APIOCREngine, _strip_html_tags
        self.EngineClass = APIOCREngine
        self.strip_html = _strip_html_tags

    def test_strip_html(self):
        assert self.strip_html("<p>hello</p>") == "hello"
        assert self.strip_html("<b>a</b> <i>b</i>") == "a b"
        assert self.strip_html("plain text") == "plain text"

    def test_extract_overall_ocr(self):
        data = {
            "result": {
                "layoutParsingResults": [{
                    "prunedResult": {
                        "overall_ocr_res": {
                            "rec_texts": ["line1", "line2", "line3"]
                        }
                    }
                }]
            }
        }
        result = self.EngineClass._extract_text(data)
        assert result == "line1\nline2\nline3"

    def test_extract_blocks(self):
        data = {
            "result": {
                "layoutParsingResults": [{
                    "prunedResult": {
                        "parsing_res_list": [
                            {"block_label": "text", "block_content": "paragraph 1"},
                            {"block_label": "text", "block_content": "paragraph 2"},
                        ]
                    }
                }]
            }
        }
        result = self.EngineClass._extract_text(data)
        assert "paragraph 1" in result
        assert "paragraph 2" in result

    def test_extract_table_html(self):
        data = {
            "result": {
                "layoutParsingResults": [{
                    "prunedResult": {
                        "parsing_res_list": [
                            {"block_label": "table", "block_content": "<td>cell</td>"}
                        ]
                    }
                }]
            }
        }
        result = self.EngineClass._extract_text(data)
        assert "cell" in result

    def test_extract_table_res_list(self):
        data = {
            "result": {
                "layoutParsingResults": [{
                    "prunedResult": {
                        "table_res_list": [{
                            "table_ocr_pred": {
                                "rec_texts": ["cell1", "cell2"]
                            }
                        }]
                    }
                }]
            }
        }
        result = self.EngineClass._extract_text(data)
        assert "cell1" in result
        assert "cell2" in result

    def test_extract_markdown_fallback(self):
        data = {
            "result": {
                "layoutParsingResults": [{
                    "prunedResult": {},
                    "markdown": {"text": "<p>markdown content</p>"}
                }]
            }
        }
        result = self.EngineClass._extract_text(data)
        assert "markdown content" in result

    def test_extract_missing_layout_results(self):
        with pytest.raises(RuntimeError, match="layoutParsingResults"):
            self.EngineClass._extract_text({"result": {}})

    def test_api_missing_credentials(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="PADDLEOCR"):
                self.EngineClass()
