"""Baidu Cloud OCR engine — supports invoice, train ticket, and general OCR."""

import base64
import io
import json
import os
import time

import requests
from PIL import Image

from .base import BaseOCREngine


class BaiduOCREngine(BaseOCREngine):
    """OCR engine using Baidu Cloud OCR APIs.

    Supports multiple recognition modes:
        - "invoice"      : 增值税发票识别 (structured, 500 free/month)
        - "train_ticket" : 火车票识别 (structured)
        - "general"      : 通用文字识别（高精度版）(1000 free/month)

    All modes use the same API Key / Secret Key.

    Environment variables:
        BAIDU_OCR_API_KEY      — Baidu Cloud API Key
        BAIDU_OCR_SECRET_KEY   — Baidu Cloud Secret Key
    """

    TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"

    API_URLS = {
        "invoice": "https://aip.baidubce.com/rest/2.0/ocr/v1/vat_invoice",
        "train_ticket": "https://aip.baidubce.com/rest/2.0/ocr/v1/train_ticket",
        "general": "https://aip.baidubce.com/rest/2.0/ocr/v1/accurate_basic",
    }

    def __init__(
        self,
        api_key: str | None = None,
        secret_key: str | None = None,
        mode: str = "invoice",
    ):
        self.api_key = api_key or os.environ.get("BAIDU_OCR_API_KEY", "")
        self.secret_key = secret_key or os.environ.get("BAIDU_OCR_SECRET_KEY", "")
        if not self.api_key or not self.secret_key:
            raise ValueError(
                "Baidu OCR requires BAIDU_OCR_API_KEY and BAIDU_OCR_SECRET_KEY. "
                "Set them as environment variables or pass via CLI options."
            )
        if mode not in self.API_URLS:
            raise ValueError(f"Unknown Baidu OCR mode: {mode}. Use: {', '.join(self.API_URLS)}")
        self.mode = mode
        self._access_token: str | None = None
        self._token_expires: float = 0

    # ------------------------------------------------------------------
    # OAuth token management
    # ------------------------------------------------------------------
    def _get_access_token(self) -> str:
        """Get or refresh Baidu OAuth2 access token."""
        if self._access_token and time.time() < self._token_expires:
            return self._access_token

        resp = requests.post(
            self.TOKEN_URL,
            params={
                "grant_type": "client_credentials",
                "client_id": self.api_key,
                "client_secret": self.secret_key,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        if "access_token" not in data:
            raise RuntimeError(
                f"Failed to get Baidu access token: {data.get('error_description', data)}"
            )

        self._access_token = data["access_token"]
        # Token is valid for ~30 days; refresh 1 hour early
        self._token_expires = time.time() + data.get("expires_in", 2592000) - 3600
        return self._access_token

    # ------------------------------------------------------------------
    # Recognition
    # ------------------------------------------------------------------
    def recognize_text(self, image: Image.Image) -> str:
        """Call the configured Baidu OCR API and return formatted result."""
        token = self._get_access_token()
        img_b64 = self._encode_image(image)
        url = self.API_URLS[self.mode]

        resp = requests.post(
            url,
            params={"access_token": token},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={"image": img_b64},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()

        if "error_code" in data:
            raise RuntimeError(
                f"Baidu OCR error {data['error_code']}: {data.get('error_msg', '')}"
            )

        formatter = {
            "invoice": self._format_invoice,
            "train_ticket": self._format_train_ticket,
            "general": self._format_general,
        }
        return formatter[self.mode](data)

    def recognize_with_mode(self, image: Image.Image, mode: str) -> str:
        """Call a specific Baidu OCR API regardless of the engine's default mode."""
        old_mode = self.mode
        self.mode = mode
        try:
            return self.recognize_text(image)
        finally:
            self.mode = old_mode

    @staticmethod
    def _encode_image(image: Image.Image) -> str:
        buf = io.BytesIO()
        image.save(buf, format="JPEG")
        return base64.b64encode(buf.getvalue()).decode("utf-8")

    # ------------------------------------------------------------------
    # Formatters
    # ------------------------------------------------------------------
    @staticmethod
    def _format_invoice(data: dict) -> str:
        """Format the structured API response into readable text + JSON."""
        results = data.get("words_result", {})
        if not results:
            return json.dumps(data, ensure_ascii=False, indent=2)

        lines: list[str] = []

        # --- Header fields ---
        field_map = [
            ("InvoiceType", "发票类型"),
            ("InvoiceNum", "发票号码"),
            ("InvoiceDate", "开票日期"),
            ("CheckCode", "校验码"),
            ("MachineNum", "机器编号"),
        ]
        for key, label in field_map:
            val = results.get(key, "")
            if val:
                lines.append(f"{label}：{val}")

        # --- Buyer / Seller ---
        for side, label in [("Purchaser", "购买方"), ("Seller", "销售方")]:
            name = results.get(f"{side}Name", "")
            tax_id = results.get(f"{side}RegisterNum", "")
            addr = results.get(f"{side}Address", "")
            bank = results.get(f"{side}Bank", "")
            if name or tax_id:
                lines.append(f"\n【{label}】")
                if name:
                    lines.append(f"  名称：{name}")
                if tax_id:
                    lines.append(f"  纳税人识别号：{tax_id}")
                if addr:
                    lines.append(f"  地址电话：{addr}")
                if bank:
                    lines.append(f"  开户行及账号：{bank}")

        # --- Items (commodity rows) ---
        items = results.get("CommodityName", [])
        if items and isinstance(items, list):
            lines.append("\n【明细项目】")
            # CommodityName is a list; other fields are also lists with same length
            commodity_amounts = results.get("CommodityAmount", [])
            commodity_tax_rates = results.get("CommodityTaxRate", [])
            commodity_taxes = results.get("CommodityTax", [])
            commodity_nums = results.get("CommodityNum", [])
            commodity_prices = results.get("CommodityPrice", [])
            commodity_units = results.get("CommodityUnit", [])
            commodity_types = results.get("CommodityType", [])

            for idx, name in enumerate(items):
                item_name = name.get("word", name) if isinstance(name, dict) else str(name)
                parts = [f"  {idx + 1}. {item_name}"]

                def _get(lst, i):
                    if isinstance(lst, list) and i < len(lst):
                        v = lst[i]
                        return v.get("word", v) if isinstance(v, dict) else str(v)
                    return ""

                spec = _get(commodity_types, idx)
                unit = _get(commodity_units, idx)
                qty = _get(commodity_nums, idx)
                price = _get(commodity_prices, idx)
                amount = _get(commodity_amounts, idx)
                tax_rate = _get(commodity_tax_rates, idx)
                tax = _get(commodity_taxes, idx)

                detail_parts = []
                if spec:
                    detail_parts.append(f"规格型号: {spec}")
                if unit:
                    detail_parts.append(f"单位: {unit}")
                if qty:
                    detail_parts.append(f"数量: {qty}")
                if price:
                    detail_parts.append(f"单价: {price}")
                if amount:
                    detail_parts.append(f"金额: {amount}")
                if tax_rate:
                    detail_parts.append(f"税率: {tax_rate}")
                if tax:
                    detail_parts.append(f"税额: {tax}")

                if detail_parts:
                    parts.append(f"     {', '.join(detail_parts)}")
                lines.extend(parts)

        # --- Totals ---
        lines.append("")
        total_amount = results.get("TotalAmount", "")
        total_tax = results.get("TotalTax", "")
        amount_in_figures = results.get("AmountInFiguers", "")
        amount_in_words = results.get("AmountInWords", "")

        if total_amount:
            lines.append(f"合计金额：{total_amount}")
        if total_tax:
            lines.append(f"合计税额：{total_tax}")
        if amount_in_words:
            lines.append(f"价税合计（大写）：{amount_in_words}")
        if amount_in_figures:
            lines.append(f"价税合计（小写）：{amount_in_figures}")

        # --- Remarks & Payee ---
        remarks = results.get("Remarks", "")
        if remarks:
            lines.append(f"\n备注：{remarks}")
        payee = results.get("Payee", "")
        if payee:
            lines.append(f"收款人：{payee}")
        reviewer = results.get("Checker", "")
        if reviewer:
            lines.append(f"复核：{reviewer}")
        drawer = results.get("NoteDrawer", "")
        if drawer:
            lines.append(f"开票人：{drawer}")

        text = "\n".join(lines)

        # Also append raw JSON for debugging / downstream processing
        text += "\n\n--- 原始 JSON ---\n"
        text += json.dumps(results, ensure_ascii=False, indent=2)

        return text

    # ------------------------------------------------------------------
    @staticmethod
    def _format_train_ticket(data: dict) -> str:
        """Format Baidu train ticket recognition result."""
        results = data.get("words_result", {})
        if not results:
            return json.dumps(data, ensure_ascii=False, indent=2)

        lines: list[str] = []
        field_map = [
            ("ticket_num", "车票号"),
            ("starting_station", "出发站"),
            ("destination_station", "到达站"),
            ("train_num", "车次"),
            ("date", "乘车日期"),
            ("ticket_price", "票价"),
            ("seat_category", "席别"),
            ("name", "姓名"),
            ("id_num", "证件号"),
            ("serial_number", "序列号"),
            ("sales_station", "售票站"),
        ]
        for key, label in field_map:
            val = results.get(key, "")
            if val:
                lines.append(f"{label}：{val}")

        text = "\n".join(lines)
        text += "\n\n--- 原始 JSON ---\n"
        text += json.dumps(results, ensure_ascii=False, indent=2)
        return text

    # ------------------------------------------------------------------
    @staticmethod
    def _format_general(data: dict) -> str:
        """Format Baidu general (accurate) OCR result."""
        words_result = data.get("words_result", [])
        if not words_result:
            return json.dumps(data, ensure_ascii=False, indent=2)

        lines = [item.get("words", "") for item in words_result if item.get("words")]
        return "\n".join(lines)
