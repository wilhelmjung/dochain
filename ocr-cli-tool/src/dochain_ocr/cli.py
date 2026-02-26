from pathlib import Path

import click

from .ocr.base import create_engine
from .ocr.processors import ImageProcessor, SUPPORTED_SUFFIXES, PDF_SUFFIXES


@click.command()
@click.option("--input", "input_path", required=True, help="Path to an image or PDF file to process")
@click.option("--output", "output_path", required=False, help="Path to save OCR text result")
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
    engine_type: str,
    api_url: str | None,
    access_token: str | None,
    baidu_api_key: str | None,
    baidu_secret_key: str | None,
):
    file_path = Path(input_path)
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
    image_processor = ImageProcessor()

    # Load images (PDF → multi-page, image → single)
    if suffix in PDF_SUFFIXES:
        images = image_processor.load_images_from_pdf(str(file_path))
        click.echo(f"PDF loaded: {len(images)} page(s)")
    else:
        images = [image_processor.load_image(str(file_path))]

    # OCR each page
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


if __name__ == '__main__':
    main()