"""Tests for SmartOCREngine cascade logic."""

from unittest.mock import patch

import pytest
from PIL import Image


class TestSmartCascade:

    @patch.dict("os.environ", {
        "BAIDU_OCR_API_KEY": "test_key",
        "BAIDU_OCR_SECRET_KEY": "test_secret",
    })
    @patch("dochain_ocr.engine_baidu.BaiduOCREngine.recognize_with_mode")
    def test_invoice_success(self, mock_recognize):
        """Smart engine should return invoice result on first try."""
        mock_recognize.return_value = "发票类型：电子发票"

        from dochain_ocr.engine_smart import SmartOCREngine
        engine = SmartOCREngine(api_key="k", secret_key="s")
        img = Image.new("RGB", (10, 10))
        result = engine.recognize_text(img)

        assert "发票类型" in result
        mock_recognize.assert_called_once_with(img, "invoice")

    @patch.dict("os.environ", {
        "BAIDU_OCR_API_KEY": "test_key",
        "BAIDU_OCR_SECRET_KEY": "test_secret",
    })
    @patch("dochain_ocr.engine_baidu.BaiduOCREngine.recognize_with_mode")
    def test_cascade_to_train_ticket(self, mock_recognize):
        """Should fall through to train ticket on invoice 282103 error."""
        def side_effect(image, mode):
            if mode == "invoice":
                raise RuntimeError("Baidu OCR error 282103: not invoice")
            if mode == "train_ticket":
                return "出发站：北京西"
            return "fallback"

        mock_recognize.side_effect = side_effect
        from dochain_ocr.engine_smart import SmartOCREngine
        engine = SmartOCREngine(api_key="k", secret_key="s")
        result = engine.recognize_text(Image.new("RGB", (10, 10)))

        assert "出发站" in result
        assert mock_recognize.call_count == 2

    @patch.dict("os.environ", {
        "BAIDU_OCR_API_KEY": "test_key",
        "BAIDU_OCR_SECRET_KEY": "test_secret",
    })
    @patch("dochain_ocr.engine_baidu.BaiduOCREngine.recognize_with_mode")
    def test_cascade_to_general(self, mock_recognize):
        """Should fall through to general OCR when both invoice and train ticket fail."""
        def side_effect(image, mode):
            if mode == "invoice":
                raise RuntimeError("Baidu OCR error 282103: not invoice")
            if mode == "train_ticket":
                raise RuntimeError("Baidu OCR error 282110: not train ticket")
            return "通用OCR结果"

        mock_recognize.side_effect = side_effect
        from dochain_ocr.engine_smart import SmartOCREngine
        engine = SmartOCREngine(api_key="k", secret_key="s")
        result = engine.recognize_text(Image.new("RGB", (10, 10)))

        assert "通用OCR结果" in result
        assert mock_recognize.call_count == 3

    @patch.dict("os.environ", {
        "BAIDU_OCR_API_KEY": "test_key",
        "BAIDU_OCR_SECRET_KEY": "test_secret",
    })
    @patch("dochain_ocr.engine_baidu.BaiduOCREngine.recognize_with_mode")
    def test_unexpected_error_propagates(self, mock_recognize):
        """Non-282103 errors should propagate, not cascade."""
        mock_recognize.side_effect = RuntimeError("Baidu OCR error 110: invalid token")

        from dochain_ocr.engine_smart import SmartOCREngine
        engine = SmartOCREngine(api_key="k", secret_key="s")

        with pytest.raises(RuntimeError, match="110"):
            engine.recognize_text(Image.new("RGB", (10, 10)))

        mock_recognize.assert_called_once()
