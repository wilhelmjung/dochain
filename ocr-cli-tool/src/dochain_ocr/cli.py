from pathlib import Path

import click

from .base import create_engine
from .processors import ImageProcessor, SUPPORTED_SUFFIXES, PDF_SUFFIXES


@click.command()
@click.option("--input", "input_path", required=True, help="Path to an image, PDF file, or a directory of files")
@click.option("--output", "output_path", required=False, help="Path to save OCR text result (single-file mode)")
@click.option("--excel", "excel_path", required=False, help="Path to save Excel output (.xlsx). Enables batch mode when --input is a directory")
@click.option(
    "--engine",
    "engine_type",
    type=click.Choice(["local", "api", "baidu", "smart"], case_sensitive=False),
    default="smart",
    help="OCR engine: 'local' (PaddleOCR CPU), 'api' (PaddleX API), 'baidu' (Baidu Invoice), 'smart' (Baidu→API fallback)",
)
@click.option("--api-url", envvar="PADDLEOCR_API_URL", default=None, help="PaddleOCR API URL (or set PADDLEOCR_API_URL)")
@click.option("--access-token", envvar="PADDLEOCR_ACCESS_TOKEN", default=None, help="PaddleOCR access token (or set PADDLEOCR_ACCESS_TOKEN)")
@click.option("--baidu-api-key", envvar="BAIDU_OCR_API_KEY", default=None, help="Baidu OCR API Key (or set BAIDU_OCR_API_KEY)")
@click.option("--baidu-secret-key", envvar="BAIDU_OCR_SECRET_KEY", default=None, help="Baidu OCR Secret Key (or set BAIDU_OCR_SECRET_KEY)")
def main(
    input_path: str,
    output_path: str | None,
    excel_path: str | None,
    engine_type: str,
    api_url: str | None,
    access_token: str | None,
    baidu_api_key: str | None,
    baidu_secret_key: str | None,
):
    file_path = Path(input_path)

    if not file_path.exists():
        raise click.ClickException(f"Input path does not exist: {file_path}")

    # Validate input shape before constructing engines that may require credentials.
    if excel_path and engine_type not in {"baidu", "smart"}:
        raise click.ClickException(
            f"Engine '{engine_type}' does not support structured Excel export. "
            "Use --engine baidu or --engine smart."
        )

    if file_path.is_dir():
        if not excel_path:
            raise click.ClickException(
                "When --input is a directory, --excel <output.xlsx> is required."
            )
    else:
        suffix = file_path.suffix.lower()
        if suffix not in SUPPORTED_SUFFIXES:
            raise click.ClickException(
                f"Unsupported file type: {suffix}. "
                f"Supported: {', '.join(sorted(SUPPORTED_SUFFIXES))}"
            )

    # Build engine
    engine_kwargs: dict = {}
    if engine_type == "api":
        if api_url:
            engine_kwargs["api_url"] = api_url
        if access_token:
            engine_kwargs["access_token"] = access_token
    if engine_type in ("baidu", "smart"):
        if baidu_api_key:
            engine_kwargs["api_key"] = baidu_api_key
        if baidu_secret_key:
            engine_kwargs["secret_key"] = baidu_secret_key

    try:
        ocr_engine = create_engine(engine_type, **engine_kwargs)
    except ValueError as e:
        raise click.ClickException(str(e))

    # --- Directory + Excel batch mode ---
    if file_path.is_dir():
        _run_batch_excel(file_path, excel_path, ocr_engine, engine_type)
        return

    # --- Single file mode ---
    image_processor = ImageProcessor()

    # Load images (PDF → multi-page, image → single)
    if suffix in PDF_SUFFIXES:
        images = image_processor.load_images_from_pdf(str(file_path))
        click.echo(f"PDF loaded: {len(images)} page(s)")
    else:
        images = [image_processor.load_image(str(file_path))]

    # If --excel is specified for a single file, use structured mode
    if excel_path:
        _run_single_excel(file_path, images, excel_path, ocr_engine, image_processor)
        return

    # OCR each page (text mode)
    all_texts: list[str] = []
    for i, img in enumerate(images):
        processed = image_processor.preprocess_image(img)
        page_text = ocr_engine.recognize_text(processed)
        if len(images) > 1:
            all_texts.append(f"--- Page {i + 1} ---")
        all_texts.append(page_text)

    text = "\n".join(all_texts)

    if output_path:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(text, encoding="utf-8")

    click.echo(f"OCR result: {text}")


def _run_single_excel(
    file_path: Path,
    images: list,
    excel_path: str,
    ocr_engine,
    image_processor: ImageProcessor,
):
    """Process a single file and export to Excel."""
    from .excel_exporter import extract_invoice_record, export_to_excel

    records = []
    for i, img in enumerate(images):
        processed = image_processor.preprocess_image(img)
        mode, data = ocr_engine.recognize_structured(processed)
        if mode == "general":
            click.echo(f"⚠️  Page {i + 1} is not a supported invoice/ticket, skipping Excel row")
            continue

        rec = extract_invoice_record(
            mode=mode,
            raw_data=data,
            source_file=file_path.name,
            seq=i + 1,
        )
        records.append(rec)

    if records:
        out = export_to_excel(records, excel_path)
        click.echo(f"✅ Excel 已生成: {out} ({len(records)} 条记录)")
    else:
        click.echo("⚠️  无有效发票记录可导出")


def _run_batch_excel(
    input_dir: Path,
    excel_path: str,
    ocr_engine,
    engine_type: str,
):
    """Scan a directory for all supported files, OCR each, and write one Excel."""
    from .excel_exporter import extract_invoice_record, export_to_excel

    image_processor = ImageProcessor()
    records = []
    seq = 0

    # Collect all supported files, sorted by name
    all_files = sorted(
        f for f in input_dir.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_SUFFIXES
    )

    if not all_files:
        click.echo(f"⚠️  目录中未找到支持的文件: {input_dir}")
        click.echo(f"   支持格式: {', '.join(sorted(SUPPORTED_SUFFIXES))}")
        return

    click.echo(f"🚀 批量识别模式 — 引擎: {engine_type}")
    click.echo(f"📂 输入目录: {input_dir}")
    click.echo(f"📊 找到 {len(all_files)} 个文件")
    click.echo("=" * 50)

    success = 0
    fail = 0

    for file_path in all_files:
        suffix = file_path.suffix.lower()
        click.echo(f"\n--- [{file_path.name}] ---")

        try:
            # Load images
            if suffix in PDF_SUFFIXES:
                images = image_processor.load_images_from_pdf(str(file_path))
                click.echo(f"  PDF: {len(images)} page(s)")
            else:
                images = [image_processor.load_image(str(file_path))]

            # OCR each page
            for i, img in enumerate(images):
                processed = image_processor.preprocess_image(img)
                mode, data = ocr_engine.recognize_structured(processed)
                if mode == "general":
                    click.echo("  ⚠️  Not a supported invoice/ticket, skipping Excel row")
                    continue

                seq += 1
                rec = extract_invoice_record(
                    mode=mode,
                    raw_data=data,
                    source_file=file_path.name,
                    seq=seq,
                )
                records.append(rec)
                click.echo(f"  ✅ {rec.票种} | {rec.金额} | {rec.开票日期}")

            success += 1

        except Exception as e:
            fail += 1
            click.echo(f"  ❌ 识别失败: {e}")

    click.echo("\n" + "=" * 50)
    click.echo(f"📊 处理结果: 共 {len(all_files)} 个文件, ✅ {success} 成功, ❌ {fail} 失败")

    if records:
        out = export_to_excel(records, excel_path)
        click.echo(f"📄 Excel 已生成: {out} ({len(records)} 条记录)")
    else:
        click.echo("⚠️  无有效发票记录可导出")


if __name__ == '__main__':
    main()