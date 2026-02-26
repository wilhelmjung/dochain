"""Tests for engine factory (create_engine)."""

from unittest.mock import MagicMock, patch

import pytest

from dochain_ocr.base import create_engine


class TestCreateEngine:

    def test_unknown_engine(self):
        with pytest.raises(ValueError, match="Unknown engine type"):
            create_engine("nonexistent")

    def test_baidu_missing_credentials(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="BAIDU_OCR"):
                create_engine("baidu")

    def test_api_missing_credentials(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="PADDLEOCR"):
                create_engine("api")

    def test_smart_missing_credentials(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="BAIDU_OCR"):
                create_engine("smart")

    def test_baidu_with_explicit_keys(self):
        with patch("dochain_ocr.engine_baidu.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"access_token": "tok", "expires_in": 86400}
            mock_post.return_value = mock_resp

            engine = create_engine("baidu", api_key="k", secret_key="s")
            assert engine.api_key == "k"
            assert engine.secret_key == "s"

    def test_api_with_explicit_args(self):
        engine = create_engine("api", api_url="http://example.com", access_token="tok")
        assert engine.api_url == "http://example.com"
        assert engine.access_token == "tok"
