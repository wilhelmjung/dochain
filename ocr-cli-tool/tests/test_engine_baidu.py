"""Tests for BaiduOCREngine formatters and token management."""

from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Formatter tests
# ---------------------------------------------------------------------------

class TestBaiduFormatters:
    """Test Baidu response formatters without making real API calls."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        with patch.dict("os.environ", {
            "BAIDU_OCR_API_KEY": "test_key",
            "BAIDU_OCR_SECRET_KEY": "test_secret",
        }):
            from dochain_ocr.engine_baidu import BaiduOCREngine
            self.EngineClass = BaiduOCREngine
            self.engine = BaiduOCREngine()

    def test_format_invoice_basic(self):
        data = {
            "words_result": {
                "InvoiceType": "电子发票(专用发票)",
                "InvoiceNum": "12345678",
                "InvoiceDate": "2025年01月01日",
                "PurchaserName": "测试公司",
                "PurchaserRegisterNum": "123456789",
                "SellerName": "销售公司",
                "TotalAmount": "100.00",
                "TotalTax": "6.00",
                "AmountInFiguers": "106.00",
            }
        }
        result = self.EngineClass._format_invoice(data)
        assert "发票类型：电子发票(专用发票)" in result
        assert "发票号码：12345678" in result
        assert "测试公司" in result
        assert "销售公司" in result
        assert "合计金额：100.00" in result
        assert "--- 原始 JSON ---" in result

    def test_format_invoice_empty(self):
        data = {"words_result": {}}
        result = self.EngineClass._format_invoice(data)
        assert "words_result" in result

    def test_format_invoice_with_items(self):
        data = {
            "words_result": {
                "CommodityName": [{"row": "1", "word": "*住宿*房费"}],
                "CommodityAmount": [{"row": "1", "word": "200.00"}],
                "CommodityTaxRate": [{"row": "1", "word": "6%"}],
                "CommodityTax": [{"row": "1", "word": "12.00"}],
                "CommodityNum": [{"row": "1", "word": "1"}],
                "CommodityUnit": [{"row": "1", "word": "间"}],
                "CommodityPrice": [{"row": "1", "word": "200.00"}],
                "TotalAmount": "200.00",
            }
        }
        result = self.EngineClass._format_invoice(data)
        assert "*住宿*房费" in result
        assert "金额: 200.00" in result
        assert "税率: 6%" in result

    def test_format_train_ticket(self):
        data = {
            "words_result": {
                "starting_station": "北京西",
                "destination_station": "上海虹桥",
                "train_num": "G1",
                "date": "2025年01月01日",
                "ticket_price": "553.00",
                "seat_category": "二等座",
                "name": "张三",
            }
        }
        result = self.EngineClass._format_train_ticket(data)
        assert "出发站：北京西" in result
        assert "到达站：上海虹桥" in result
        assert "车次：G1" in result
        assert "张三" in result
        assert "--- 原始 JSON ---" in result

    def test_format_train_ticket_empty(self):
        data = {"words_result": {}}
        result = self.EngineClass._format_train_ticket(data)
        assert "words_result" in result

    def test_format_general(self):
        data = {
            "words_result": [
                {"words": "第一行文本"},
                {"words": "第二行文本"},
            ]
        }
        result = self.EngineClass._format_general(data)
        assert "第一行文本" in result
        assert "第二行文本" in result
        assert result == "第一行文本\n第二行文本"

    def test_format_general_empty(self):
        data = {"words_result": []}
        result = self.EngineClass._format_general(data)
        assert "words_result" in result

    def test_invalid_mode(self):
        with pytest.raises(ValueError, match="Unknown Baidu OCR mode"):
            self.EngineClass(mode="invalid")


# ---------------------------------------------------------------------------
# Token management tests
# ---------------------------------------------------------------------------

class TestBaiduToken:

    @patch.dict("os.environ", {
        "BAIDU_OCR_API_KEY": "test_key",
        "BAIDU_OCR_SECRET_KEY": "test_secret",
    })
    @patch("dochain_ocr.engine_baidu.requests.post")
    def test_token_caching(self, mock_post):
        """Token should be cached and reused."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"access_token": "tok123", "expires_in": 86400}
        mock_post.return_value = mock_resp

        from dochain_ocr.engine_baidu import BaiduOCREngine
        engine = BaiduOCREngine()

        token1 = engine._get_access_token()
        token2 = engine._get_access_token()

        assert token1 == "tok123"
        assert token1 == token2
        mock_post.assert_called_once()

    @patch.dict("os.environ", {
        "BAIDU_OCR_API_KEY": "test_key",
        "BAIDU_OCR_SECRET_KEY": "test_secret",
    })
    @patch("dochain_ocr.engine_baidu.requests.post")
    def test_token_failure(self, mock_post):
        """Should raise RuntimeError on token failure."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"error": "invalid_client", "error_description": "bad key"}
        mock_post.return_value = mock_resp

        from dochain_ocr.engine_baidu import BaiduOCREngine
        engine = BaiduOCREngine()

        with pytest.raises(RuntimeError, match="Failed to get Baidu access token"):
            engine._get_access_token()
