"""Smart OCR engine — cascading Baidu APIs: invoice → train ticket → general."""

import click
from PIL import Image

from .base import BaseOCREngine


class SmartOCREngine(BaseOCREngine):
    """Composite engine using Baidu Cloud OCR with auto-detection.

    Cascade order:
        1. 增值税发票识别 (invoice)  — structured, best for invoices
        2. 火车票识别 (train_ticket)  — structured, for train tickets
        3. 通用高精度 OCR (general)  — universal fallback

    Only requires Baidu API Key / Secret Key (same credentials for all).
    """

    def __init__(self, **kwargs):
        baidu_kwargs = {k: v for k, v in kwargs.items() if k in ("api_key", "secret_key")}

        from .engine_baidu import BaiduOCREngine

        self._engine = BaiduOCREngine(**baidu_kwargs, mode="invoice")

    def recognize_text(self, image: Image.Image) -> str:
        """Try invoice → train_ticket → general, stopping at first success."""

        # --- 1. Try invoice ---
        try:
            result = self._engine.recognize_with_mode(image, "invoice")
            click.echo("  [smart] ✅ 百度发票识别成功")
            return result
        except RuntimeError as e:
            if "282103" not in str(e):
                raise  # unexpected error, propagate

        # --- 2. Try train ticket ---
        click.echo("  [smart] ⚠️ 非发票，尝试火车票识别...")
        try:
            result = self._engine.recognize_with_mode(image, "train_ticket")
            click.echo("  [smart] ✅ 百度火车票识别成功")
            return result
        except RuntimeError as e:
            if "282103" not in str(e) and "282110" not in str(e):
                raise

        # --- 3. Fallback to general OCR ---
        click.echo("  [smart] ⚠️ 非火车票，使用通用高精度 OCR...")
        result = self._engine.recognize_with_mode(image, "general")
        click.echo("  [smart] ✅ 通用 OCR 完成")
        return result
