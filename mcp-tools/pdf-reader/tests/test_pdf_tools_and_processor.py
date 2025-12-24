import asyncio
from pathlib import Path

import pytest
from pypdf import PdfWriter

from pdf_reader import pdf_processor as pdf_processor_module
from pdf_reader import safety, tools


def _create_minimal_pdf(path: Path) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with path.open("wb") as f:
        writer.write(f)


def test_safety_validate_pdf_path_and_filename(tmp_path, monkeypatch):
    pdf_path = tmp_path / "sample.pdf"
    _create_minimal_pdf(pdf_path)

    # Default allows any path.
    assert safety.validate_pdf_path(str(pdf_path)) == pdf_path.resolve()

    assert safety.sanitize_filename("a/b..c")

    info = safety.get_safe_file_info(pdf_path)
    assert info["filename"].endswith(".pdf")

    # Force a root restriction by patching module globals.
    monkeypatch.setattr(safety, "ALLOW_ANY_PATH", False)
    monkeypatch.setattr(safety, "ALLOWED_ROOT", tmp_path)

    # Outside root should error.
    with pytest.raises(safety.PathTraversalError):
        safety.validate_pdf_path("/etc/passwd")


def test_tools_validation_errors():
    with pytest.raises(ValueError):
        tools.validate_extract_pdf_content_params({})

    with pytest.raises(ValueError):
        tools.validate_list_pages_params({"file_path": "x", "preview_length": 10})


def test_run_with_timeout_returns_timeout_error():
    async def slow():
        await asyncio.sleep(0.05)
        return 123

    result = asyncio.run(tools.run_with_timeout(slow(), timeout_seconds=0.001))
    assert result["ok"] is False
    assert result["code"] == "Timeout"


def test_pdf_processor_and_tool_endpoints(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    _create_minimal_pdf(pdf_path)

    # Exercise processor methods directly.
    processor = pdf_processor_module.PDFProcessor()
    meta = asyncio.run(processor.extract_metadata(str(pdf_path)))
    assert meta["page_count"] == 1

    previews = asyncio.run(processor.extract_page_text_preview(str(pdf_path), start_page=1, end_page=1, preview_length=50))
    assert previews[0]["page_number"] == 1

    full = asyncio.run(processor.extract_full_content(str(pdf_path), pages=[1], include_images=True, include_tables=True, use_ocr=True))
    assert full["metadata"]["page_count"] == 1
    assert isinstance(full["pages"], list)

    # Exercise tools facade.
    meta_tool = asyncio.run(tools.tool_get_pdf_metadata({"file_path": str(pdf_path)}))
    assert meta_tool["ok"] is True

    pages_tool = asyncio.run(tools.tool_list_pdf_pages({"file_path": str(pdf_path), "start_page": 1, "end_page": 1, "preview_length": 50}))
    assert pages_tool["ok"] is True

    content_tool = asyncio.run(tools.tool_extract_pdf_content({"file_path": str(pdf_path), "pages": [1], "include_images": False, "include_tables": False}))
    assert content_tool["ok"] is True


def test_streaming_extraction_sends_events(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    _create_minimal_pdf(pdf_path)

    events = []

    async def send_event(evt):
        events.append(evt)

    processor = pdf_processor_module.PDFProcessor()
    summary = asyncio.run(processor.stream_content_extraction(str(pdf_path), send_event, pages=[1], include_images=False, include_tables=False))

    assert summary["success"] is True
    assert any(e.get("type") == "start" for e in events)
    assert any(e.get("type") == "progress" for e in events)
    assert any(e.get("type") == "complete" for e in events)
