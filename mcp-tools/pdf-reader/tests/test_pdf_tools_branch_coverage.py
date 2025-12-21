import asyncio

import pytest

from pdf_reader import safety, tools


def test_validate_helpers_more_error_cases(tmp_path):
    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(b"x")

    with pytest.raises(ValueError):
        tools.validate_extract_pdf_content_params({"file_path": str(pdf), "include_tables": "no"})

    with pytest.raises(ValueError):
        tools.validate_extract_pdf_content_params({"file_path": str(pdf), "use_ocr": "no"})

    with pytest.raises(ValueError):
        tools.validate_metadata_params({})

    with pytest.raises(ValueError):
        tools.validate_list_pages_params({})

    with pytest.raises(ValueError):
        tools.validate_list_pages_params({"file_path": str(pdf), "end_page": 0})

    with pytest.raises(ValueError):
        tools.validate_list_pages_params({"file_path": str(pdf), "preview_length": 10})


def test_tool_extract_pdf_content_validation_and_passthrough(monkeypatch):
    # Validation error
    r = asyncio.run(tools.tool_extract_pdf_content({}))
    assert r["code"] == "UserInput"

    # Passthrough error dict from run_with_timeout
    async def fake_timeout(*args, **kwargs):
        return {"ok": False, "code": "Timeout", "message": "x", "correlation_id": "c"}

    monkeypatch.setattr(tools, "run_with_timeout", fake_timeout)

    async def ok(*args, **kwargs):
        return {"any": "thing"}

    monkeypatch.setattr(tools.pdf_processor, "extract_full_content", ok)
    r = asyncio.run(tools.tool_extract_pdf_content({"file_path": "/tmp/x.pdf"}))
    assert r["ok"] is False
    assert r["code"] == "Timeout"


def test_tool_extract_pdf_content_exception_mapping(monkeypatch):
    async def run_direct(coro_or_factory, timeout_seconds=1.0):
        coro = coro_or_factory() if callable(coro_or_factory) else coro_or_factory
        return await coro

    monkeypatch.setattr(tools, "run_with_timeout", run_direct)

    async def boom(*args, **kwargs):
        raise safety.PathTraversalError("escape")

    monkeypatch.setattr(tools.pdf_processor, "extract_full_content", boom)
    r = asyncio.run(tools.tool_extract_pdf_content({"file_path": "/tmp/x.pdf"}))
    assert r["code"] == "Forbidden"

    async def boom2(*args, **kwargs):
        raise safety.FileSizeError("big")

    monkeypatch.setattr(tools.pdf_processor, "extract_full_content", boom2)
    r = asyncio.run(tools.tool_extract_pdf_content({"file_path": "/tmp/x.pdf"}))
    assert r["code"] == "UserInput"

    async def boom3(*args, **kwargs):
        raise safety.UnsupportedFileError("bad")

    monkeypatch.setattr(tools.pdf_processor, "extract_full_content", boom3)
    r = asyncio.run(tools.tool_extract_pdf_content({"file_path": "/tmp/x.pdf"}))
    assert r["code"] == "UserInput"

    async def boom4(*args, **kwargs):
        raise safety.PDFSafetyError("other")

    monkeypatch.setattr(tools.pdf_processor, "extract_full_content", boom4)
    r = asyncio.run(tools.tool_extract_pdf_content({"file_path": "/tmp/x.pdf"}))
    assert r["code"] == "Forbidden"

    async def missing(*args, **kwargs):
        raise FileNotFoundError("missing")

    monkeypatch.setattr(tools.pdf_processor, "extract_full_content", missing)
    r = asyncio.run(tools.tool_extract_pdf_content({"file_path": "/tmp/x.pdf"}))
    assert r["code"] == "NotFound"

    async def explode(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(tools.pdf_processor, "extract_full_content", explode)
    r = asyncio.run(tools.tool_extract_pdf_content({"file_path": "/tmp/x.pdf"}))
    assert r["code"] == "Internal"


def test_tool_list_pdf_pages_exception_mapping(monkeypatch):
    async def run_direct(coro_or_factory, timeout_seconds=1.0):
        coro = coro_or_factory() if callable(coro_or_factory) else coro_or_factory
        return await coro

    monkeypatch.setattr(tools, "run_with_timeout", run_direct)

    async def boom(*args, **kwargs):
        raise safety.FileSizeError("big")

    monkeypatch.setattr(tools.pdf_processor, "extract_page_text_preview", boom)
    r = asyncio.run(tools.tool_list_pdf_pages({"file_path": "/tmp/x.pdf"}))
    assert r["code"] == "UserInput"

    async def missing(*args, **kwargs):
        raise FileNotFoundError("missing")

    monkeypatch.setattr(tools.pdf_processor, "extract_page_text_preview", missing)
    r = asyncio.run(tools.tool_list_pdf_pages({"file_path": "/tmp/x.pdf"}))
    assert r["code"] == "NotFound"


def test_tool_get_pdf_metadata_validation_and_more_safety_mapping(monkeypatch):
    # Validation error
    r = asyncio.run(tools.tool_get_pdf_metadata({}))
    assert r["code"] == "UserInput"

    async def run_direct(coro_or_factory, timeout_seconds=1.0):
        coro = coro_or_factory() if callable(coro_or_factory) else coro_or_factory
        return await coro

    monkeypatch.setattr(tools, "run_with_timeout", run_direct)

    async def too_big(*args, **kwargs):
        raise safety.FileSizeError("big")

    monkeypatch.setattr(tools.pdf_processor, "extract_metadata", too_big)
    r = asyncio.run(tools.tool_get_pdf_metadata({"file_path": "/tmp/x.pdf"}))
    assert r["code"] == "UserInput"

    async def other(*args, **kwargs):
        raise safety.PDFSafetyError("nope")

    monkeypatch.setattr(tools.pdf_processor, "extract_metadata", other)
    r = asyncio.run(tools.tool_get_pdf_metadata({"file_path": "/tmp/x.pdf"}))
    assert r["code"] == "Forbidden"


def test_tool_list_pdf_pages_validation_passthrough_and_more_safety(monkeypatch):
    # Validation error
    r = asyncio.run(tools.tool_list_pdf_pages({}))
    assert r["code"] == "UserInput"

    # Passthrough error dict from run_with_timeout
    async def fake_timeout(*args, **kwargs):
        return {"ok": False, "code": "Timeout", "message": "x", "correlation_id": "c"}

    monkeypatch.setattr(tools, "run_with_timeout", fake_timeout)

    async def ok(*args, **kwargs):
        return []

    monkeypatch.setattr(tools.pdf_processor, "extract_page_text_preview", ok)
    r = asyncio.run(tools.tool_list_pdf_pages({"file_path": "/tmp/x.pdf"}))
    assert r["code"] == "Timeout"

    async def run_direct(coro_or_factory, timeout_seconds=1.0):
        coro = coro_or_factory() if callable(coro_or_factory) else coro_or_factory
        return await coro

    monkeypatch.setattr(tools, "run_with_timeout", run_direct)

    async def escape(*args, **kwargs):
        raise safety.PathTraversalError("escape")

    monkeypatch.setattr(tools.pdf_processor, "extract_page_text_preview", escape)
    r = asyncio.run(tools.tool_list_pdf_pages({"file_path": "/tmp/x.pdf"}))
    assert r["code"] == "Forbidden"

    async def bad(*args, **kwargs):
        raise safety.UnsupportedFileError("bad")

    monkeypatch.setattr(tools.pdf_processor, "extract_page_text_preview", bad)
    r = asyncio.run(tools.tool_list_pdf_pages({"file_path": "/tmp/x.pdf"}))
    assert r["code"] == "UserInput"

    async def other(*args, **kwargs):
        raise safety.PDFSafetyError("nope")

    monkeypatch.setattr(tools.pdf_processor, "extract_page_text_preview", other)
    r = asyncio.run(tools.tool_list_pdf_pages({"file_path": "/tmp/x.pdf"}))
    assert r["code"] == "Forbidden"


def test_tool_stream_pdf_extraction_success_and_other_errors(monkeypatch):
    events = []

    async def send_event(evt):
        events.append(evt)

    async def ok(*args, **kwargs):
        return {"success": True}

    monkeypatch.setattr(tools.pdf_processor, "stream_content_extraction", ok)
    r = asyncio.run(tools.tool_stream_pdf_extraction({"file_path": "/tmp/x.pdf"}, send_event))
    assert r["ok"] is True

    # Validation error
    r = asyncio.run(tools.tool_stream_pdf_extraction({}, send_event))
    assert r["code"] == "UserInput"

    async def missing(*args, **kwargs):
        raise FileNotFoundError("missing")

    monkeypatch.setattr(tools.pdf_processor, "stream_content_extraction", missing)
    r = asyncio.run(tools.tool_stream_pdf_extraction({"file_path": "/tmp/x.pdf"}, send_event))
    assert r["code"] == "NotFound"
    assert any(e.get("type") == "error" for e in events)

    async def other(*args, **kwargs):
        raise safety.PDFSafetyError("other")

    monkeypatch.setattr(tools.pdf_processor, "stream_content_extraction", other)
    r = asyncio.run(tools.tool_stream_pdf_extraction({"file_path": "/tmp/x.pdf"}, send_event))
    assert r["code"] == "Forbidden"

    async def too_big(*args, **kwargs):
        raise safety.FileSizeError("big")

    monkeypatch.setattr(tools.pdf_processor, "stream_content_extraction", too_big)
    r = asyncio.run(tools.tool_stream_pdf_extraction({"file_path": "/tmp/x.pdf"}, send_event))
    assert r["code"] == "UserInput"

    async def bad(*args, **kwargs):
        raise safety.UnsupportedFileError("bad")

    monkeypatch.setattr(tools.pdf_processor, "stream_content_extraction", bad)
    r = asyncio.run(tools.tool_stream_pdf_extraction({"file_path": "/tmp/x.pdf"}, send_event))
    assert r["code"] == "UserInput"

    async def explode(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(tools.pdf_processor, "stream_content_extraction", explode)
    r = asyncio.run(tools.tool_stream_pdf_extraction({"file_path": "/tmp/x.pdf"}, send_event))
    assert r["code"] == "Internal"
