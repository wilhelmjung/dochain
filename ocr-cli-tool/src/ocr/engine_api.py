"""PaddleOCR AI Studio API engine — calls remote PaddleX serving API."""

import base64
import io
import os
import re

import requests
from PIL import Image

from .base import BaseOCREngine


def _strip_html_tags(html: str) -> str:
    """Remove HTML tags and return plain text, collapsing whitespace."""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    return text


class APIOCREngine(BaseOCREngine):
    """OCR engine using PaddleOCR AI Studio (PaddleX Serving) layout-parsing API.

    Set the following environment variables before use:
        PADDLEOCR_API_URL          — API endpoint URL (e.g. https://xxx.aistudio-app.com/layout-parsing)
        PADDLEOCR_ACCESS_TOKEN     — Access token for authentication

    Alternatively, pass them directly via constructor arguments.
    """

    def __init__(
        self,
        api_url: str | None = None,
        access_token: str | None = None,
    ):
        self.api_url = api_url or os.environ.get("PADDLEOCR_API_URL", "")
        self.access_token = access_token or os.environ.get("PADDLEOCR_ACCESS_TOKEN", "")
        if not self.api_url or not self.access_token:
            raise ValueError(
                "PaddleOCR API requires PADDLEOCR_API_URL and PADDLEOCR_ACCESS_TOKEN. "
                "Set them as environment variables or pass via --api-url / --access-token."
            )

    # ------------------------------------------------------------------
    # Recognition
    # ------------------------------------------------------------------
    def recognize_text(self, image: Image.Image) -> str:
        # Encode image to base64
        buf = io.BytesIO()
        image.save(buf, format="JPEG")
        img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

        resp = requests.post(
            self.api_url,
            headers={
                "Authorization": f"token {self.access_token}",
                "Content-Type": "application/json",
            },
            json={
                "file": img_b64,
                "fileType": 1,  # fileType 1 = IMAGE
                "useSealRecognition": True,
                "useTableRecognition": True,
            },
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()

        if "errorCode" in data and data["errorCode"] != 0:
            raise RuntimeError(
                f"PaddleOCR API error {data['errorCode']}: {data.get('errorMsg', '')}"
            )

        return self._extract_text(data)

    # ------------------------------------------------------------------
    # Extraction helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_text(data: dict) -> str:
        """Extract text from the API response, merging multiple data sources.

        Priority:
        1. overall_ocr_res.rec_texts  — full-page OCR (best coverage)
        2. parsing_res_list + table_res_list  — layout-aware extraction
        3. markdown.text — fallback to rendered markdown (HTML stripped)
        """
        lines: list[str] = []
        try:
            layout_results = data["result"]["layoutParsingResults"]
        except (KeyError, TypeError):
            raise RuntimeError("Unexpected API response format: missing layoutParsingResults")

        for page_result in layout_results:
            pruned = page_result.get("prunedResult", {})

            # --- Strategy 1: overall_ocr_res (full-page OCR) ---
            ocr_res = pruned.get("overall_ocr_res", {})
            if ocr_res and "rec_texts" in ocr_res:
                lines.extend(ocr_res["rec_texts"])
                continue  # skip per-block extraction for this page

            # --- Strategy 2: block-level extraction ---
            block_lines = APIOCREngine._extract_from_blocks(pruned)

            # --- Strategy 3: table_res_list ---
            table_lines = APIOCREngine._extract_from_tables(pruned)

            if block_lines or table_lines:
                lines.extend(block_lines)
                lines.extend(table_lines)
            else:
                # --- Fallback: markdown text ---
                md = page_result.get("markdown", {})
                md_text = md.get("text", "") if isinstance(md, dict) else ""
                if md_text:
                    plain = _strip_html_tags(md_text)
                    if plain:
                        lines.append(plain)

        return "\n".join(lines)

    @staticmethod
    def _extract_from_blocks(pruned: dict) -> list[str]:
        """Extract text from parsing_res_list blocks."""
        lines: list[str] = []
        for block in pruned.get("parsing_res_list", []):
            label = block.get("block_label", "")
            content = block.get("block_content", "").strip()
            if not content:
                continue
            if label == "table":
                # Table blocks contain HTML — strip tags to get plain text
                plain = _strip_html_tags(content)
                if plain:
                    lines.append(plain)
            else:
                lines.append(content)
        return lines

    @staticmethod
    def _extract_from_tables(pruned: dict) -> list[str]:
        """Extract text from table_res_list (table recognition results)."""
        lines: list[str] = []
        for table in pruned.get("table_res_list", []):
            # Prefer table_ocr_pred.rec_texts for raw cell text
            ocr_pred = table.get("table_ocr_pred", {})
            if ocr_pred and "rec_texts" in ocr_pred:
                lines.extend(ocr_pred["rec_texts"])
            elif "pred_html" in table:
                plain = _strip_html_tags(table["pred_html"])
                if plain:
                    lines.append(plain)
        return lines
