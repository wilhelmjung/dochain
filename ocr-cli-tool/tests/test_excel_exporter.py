"""Tests for structured OCR to Excel record mapping."""

from dochain_ocr.excel_exporter import extract_invoice_record


class TestExtractInvoiceRecord:

    def test_train_ticket_uses_ticket_price_alias(self):
        rec = extract_invoice_record(
            mode="train_ticket",
            raw_data={
                "words_result": {
                    "ticket_price": "553.00",
                    "date": "2025年01月01日",
                    "name": "张三",
                    "seat_category": "二等座",
                }
            },
            source_file="ticket.png",
            seq=1,
        )

        assert rec.票种 == "数电发票（铁路电子客票）"
        assert rec.金额 == "553.00"
        assert rec.开票日期 == "2025年01月01日"
        assert rec.旅客姓名 == "张三"
        assert rec.座位类型 == "二等座"

    def test_invoice_type_mapping_prefers_invoice_type_org(self):
        rec = extract_invoice_record(
            mode="invoice",
            raw_data={
                "words_result": {
                    "InvoiceType": "普通发票",
                    "InvoiceTypeOrg": "电子发票(增值税专用发票)",
                    "InvoiceNum": "12345678",
                    "InvoiceDate": "2025年01月01日",
                    "TotalAmount": "100.00",
                    "TotalTax": "6.00",
                }
            },
            source_file="invoice.pdf",
            seq=2,
        )

        assert rec.票种 == "数电发票（增值税专用发票）"
        assert rec.发票号码 == "12345678"
        assert rec.金额 == "100.00"
        assert rec.票面税额 == "6.00"

    def test_general_mode_returns_unknown_record(self):
        rec = extract_invoice_record(
            mode="general",
            raw_data={"words_result": [{"words": "random document"}]},
            source_file="other.png",
            seq=3,
        )

        assert rec.票种 == "未知"
        assert rec.金额 == ""
        assert rec.开票日期 == ""
