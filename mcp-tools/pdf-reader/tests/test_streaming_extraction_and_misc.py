import asyncio
from pathlib import Path

import pytest
from pypdf import PdfWriter

from pdf_reader import errors
from pdf_reader import pdf_processor as pdf_processor_module
from pdf_reader import safety, tools


def _create_minimal_pdf(path: Path) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with path.open("wb") as f:
        writer.write(f)


def test_errors_helpers_cover_branches():
    e = errors.user_input_error("m", hint="h", correlation_id="abcd1234")
    assert e["ok"] is False
    assert e["code"] == "UserInput"
    assert e["hint"] == "h"
    assert e["correlation_id"] == "abcd1234"

    assert errors.forbidden_error("m", correlation_id="c")["code"] == "Forbidden"
    assert errors.not_found_error("m", correlation_id="c")["code"] == "NotFound"
    assert errors.timeout_error("m", correlation_id="c")["code"] == "Timeout"
    assert errors.cancellation_error("m", correlation_id="c")["code"] == "Cancelled"

    internal = errors.internal_error("boom", detail="x" * 1000, correlation_id="c")
    assert internal["code"] == "Internal"
    assert len(internal.get("detail", "")) == 200

    internal2 = errors.internal_error("boom", detail=None, correlation_id="c")
    assert internal2["code"] == "Internal"
    assert "detail" not in internal2


def test_safety_validate_pdf_path_error_branches(tmp_path, monkeypatch):
    # Unsupported extension
    bad = tmp_path / "x.txt"
    bad.write_text("x", encoding="utf-8")
    with pytest.raises(safety.UnsupportedFileError):
        safety.validate_pdf_path(bad)

    # Missing
    missing = tmp_path / "missing.pdf"
    with pytest.raises(FileNotFoundError):
        safety.validate_pdf_path(missing)

    # Directory
    d = tmp_path / "dir.pdf"
    d.mkdir()
    with pytest.raises(safety.UnsupportedFileError):
        safety.validate_pdf_path(d)

    # File size too large (monkeypatch Path.stat)
    real_pdf = tmp_path / "big.pdf"
    _create_minimal_pdf(real_pdf)

    class FakeStat:
        st_size = safety.MAX_FILE_SIZE_BYTES + 1
        st_mtime = 0.0

    monkeypatch.setattr(Path, "stat", lambda self: FakeStat())
    with pytest.raises(safety.FileSizeError):
        safety.validate_pdf_path(real_pdf)


def test_safety_check_ocr_and_sanitize_filename_limits():
    assert safety.check_ocr_available() is False

    long_name = ("a" * 300) + "/.."
    out = safety.sanitize_filename(long_name)
    assert len(out) == 255
    assert "/" not in out


def test_tools_validation_helpers_cover_branches(tmp_path):
    pdf = tmp_path / "a.pdf"
    _create_minimal_pdf(pdf)

    v = tools.validate_extract_pdf_content_params({"file_path": str(pdf), "use_ocr": True})
    assert v["use_ocr"] is False

    with pytest.raises(ValueError):
        tools.validate_extract_pdf_content_params({"file_path": str(pdf), "pages": [0]})

    with pytest.raises(ValueError):
        tools.validate_extract_pdf_content_params({"file_path": str(pdf), "include_images": "no"})

    with pytest.raises(ValueError):
        tools.validate_list_pages_params({"file_path": str(pdf), "start_page": 0})


def test_tools_error_mapping_and_passthrough(monkeypatch, tmp_path):
    pdf = tmp_path / "a.pdf"
    _create_minimal_pdf(pdf)

    # Passthrough error dict from run_with_timeout
    async def fake_timeout(*args, **kwargs):
        return {"ok": False, "code": "Timeout", "message": "x", "correlation_id": "c"}

    monkeypatch.setattr(tools, "run_with_timeout", fake_timeout)
    r = asyncio.run(tools.tool_get_pdf_metadata({"file_path": str(pdf)}))
    assert r["ok"] is False
    assert r["code"] == "Timeout"

    # Tool-level exception mapping
    async def run_direct(coro_or_factory, timeout_seconds=1.0):
        coro = coro_or_factory() if callable(coro_or_factory) else coro_or_factory
        return await coro

    monkeypatch.setattr(tools, "run_with_timeout", run_direct)

    async def boom(*args, **kwargs):
        raise safety.PathTraversalError("escape")

    monkeypatch.setattr(tools.pdf_processor, "extract_metadata", boom)
    r = asyncio.run(tools.tool_get_pdf_metadata({"file_path": str(pdf)}))
    assert r["code"] == "Forbidden"

    async def boom2(*args, **kwargs):
        raise safety.UnsupportedFileError("bad")

    monkeypatch.setattr(tools.pdf_processor, "extract_metadata", boom2)
    r = asyncio.run(tools.tool_get_pdf_metadata({"file_path": str(pdf)}))
    assert r["code"] == "UserInput"

    async def boom3(*args, **kwargs):
        raise FileNotFoundError("missing")

    monkeypatch.setattr(tools.pdf_processor, "extract_metadata", boom3)
    r = asyncio.run(tools.tool_get_pdf_metadata({"file_path": str(pdf)}))
    assert r["code"] == "NotFound"

    async def boom4(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(tools.pdf_processor, "extract_metadata", boom4)
    r = asyncio.run(tools.tool_get_pdf_metadata({"file_path": str(pdf)}))
    assert r["code"] == "Internal"


def test_tools_extract_and_list_error_branches(monkeypatch, tmp_path):
    pdf = tmp_path / "a.pdf"
    _create_minimal_pdf(pdf)

    async def run_direct(coro_or_factory, timeout_seconds=1.0):
        coro = coro_or_factory() if callable(coro_or_factory) else coro_or_factory
        return await coro

    monkeypatch.setattr(tools, "run_with_timeout", run_direct)

    async def bad_size(*args, **kwargs):
        raise safety.FileSizeError("too big")

    monkeypatch.setattr(tools.pdf_processor, "extract_full_content", bad_size)
    r = asyncio.run(tools.tool_extract_pdf_content({"file_path": str(pdf)}))
    assert r["code"] == "UserInput"

    async def bad_path(*args, **kwargs):
        raise safety.PathTraversalError("escape")

    monkeypatch.setattr(tools.pdf_processor, "extract_full_content", bad_path)
    r = asyncio.run(tools.tool_extract_pdf_content({"file_path": str(pdf)}))
    assert r["code"] == "Forbidden"

    async def missing(*args, **kwargs):
        raise FileNotFoundError("missing")

    monkeypatch.setattr(tools.pdf_processor, "extract_page_text_preview", missing)
    r = asyncio.run(tools.tool_list_pdf_pages({"file_path": str(pdf)}))
    assert r["code"] == "NotFound"

    async def explode(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(tools.pdf_processor, "extract_page_text_preview", explode)
    r = asyncio.run(tools.tool_list_pdf_pages({"file_path": str(pdf)}))
    assert r["code"] == "Internal"


def test_tool_stream_pdf_extraction_error_events(monkeypatch, tmp_path):
    pdf = tmp_path / "a.pdf"
    _create_minimal_pdf(pdf)

    events = []

    async def send_event(evt):
        events.append(evt)

    async def boom(*args, **kwargs):
        raise safety.PathTraversalError("escape")

    monkeypatch.setattr(tools.pdf_processor, "stream_content_extraction", boom)
    r = asyncio.run(tools.tool_stream_pdf_extraction({"file_path": str(pdf)}, send_event))
    assert r["code"] == "Forbidden"
    assert any(e.get("type") == "error" for e in events)


def test_pdf_processor_preview_and_table_error_branches(monkeypatch, tmp_path):
    pdf = tmp_path / "a.pdf"
    _create_minimal_pdf(pdf)

    class FakePage:
        bbox = (0, 0, 10, 10)
        rotation = 0

        def extract_text(self):
            return "a" * 300

        def extract_tables(self):
            raise RuntimeError("no tables")

    class FakePDF:
        pages = [FakePage()]

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(pdf_processor_module, "pdfplumber", type("X", (), {"open": lambda *_args, **_kwargs: FakePDF()})())

    proc = pdf_processor_module.PDFProcessor()

    previews = asyncio.run(proc.extract_page_text_preview(str(pdf), start_page=2, end_page=None, preview_length=50))
    assert previews[0]["has_more"] is True
    assert previews[0]["text_preview"].endswith("...")

    full = asyncio.run(proc.extract_full_content(str(pdf), pages=[0, 1, 99], include_images=False, include_tables=True, use_ocr=True))
    assert full["processing_info"]["ocr_used"] is False
    assert full["pages"][0]["tables_count"] == 0


def test_pdf_processor_preview_exception_branch(monkeypatch, tmp_path):
    pdf = tmp_path / "a.pdf"
    _create_minimal_pdf(pdf)

    class BrokenPDF:
        def __enter__(self):
            raise RuntimeError("boom")

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(pdf_processor_module, "pdfplumber", type("X", (), {"open": lambda *_a, **_k: BrokenPDF()})())
    proc = pdf_processor_module.PDFProcessor()
    with pytest.raises(RuntimeError):
        asyncio.run(proc.extract_page_text_preview(str(pdf)))


def test_pdf_processor_image_extraction_branches(monkeypatch, tmp_path):
    pdf = tmp_path / "a.pdf"
    _create_minimal_pdf(pdf)

    class ImgObj(dict):
        def __init__(self, subtype, flt=None, data=b"img"):
            super().__init__({"/Subtype": subtype})
            if flt is not None:
                self["/Filter"] = flt
            self._data = data

        def get(self, key, default=None):
            return super().get(key, default)

    class XObj(dict):
        def get_object(self):
            return self

    class FakePage(dict):
        def __init__(self):
            super().__init__({"/Resources": {"/XObject": XObj({"/Im0": ImgObj("/Image", "/DCTDecode"), "/Im1": ImgObj("/Image", "/DCTDecode")})}})

        def get(self, key, default=None):
            return super().get(key, default)

    class FakeReader:
        def __init__(self, _file):
            self.pages = [FakePage()]
            self.is_encrypted = False
            self.metadata = {"/Title": "t"}

    monkeypatch.setattr(pdf_processor_module.pypdf, "PdfReader", FakeReader)

    class FakePDFPage:
        bbox = (0, 0, 10, 10)
        rotation = 0

        def extract_text(self):
            return "hi"

        def extract_tables(self):
            return []

    class FakePDF:
        pages = [FakePDFPage()]

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(pdf_processor_module, "pdfplumber", type("X", (), {"open": lambda *_args, **_kwargs: FakePDF()})())

    proc = pdf_processor_module.PDFProcessor()
    out = asyncio.run(proc.extract_full_content(str(pdf), pages=[1], include_images=True, include_tables=False))
    assert out["metadata"]["title"] == "t"
    assert out["images"] is not None


def test_pdf_processor_extract_metadata_exception_branch(monkeypatch, tmp_path):
    pdf = tmp_path / "a.pdf"
    _create_minimal_pdf(pdf)

    class BoomReader:
        def __init__(self, _file):
            raise RuntimeError("boom")

    monkeypatch.setattr(pdf_processor_module.pypdf, "PdfReader", BoomReader)
    proc = pdf_processor_module.PDFProcessor()
    with pytest.raises(RuntimeError):
        asyncio.run(proc.extract_metadata(str(pdf)))


def test_pdf_processor_extract_full_content_exception_branch(monkeypatch, tmp_path):
    pdf = tmp_path / "a.pdf"
    _create_minimal_pdf(pdf)

    class BrokenPDF:
        def __enter__(self):
            raise RuntimeError("boom")

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(pdf_processor_module, "pdfplumber", type("X", (), {"open": lambda *_a, **_k: BrokenPDF()})())
    proc = pdf_processor_module.PDFProcessor()
    with pytest.raises(RuntimeError):
        asyncio.run(proc.extract_full_content(str(pdf), include_images=False, include_tables=False))


def test_pdf_processor_extract_images_inner_and_outer_errors(monkeypatch, tmp_path):
    pdf = tmp_path / "a.pdf"
    _create_minimal_pdf(pdf)

    class BadObj(dict):
        def __init__(self):
            super().__init__({"/Subtype": "/Image", "/Filter": "/DCTDecode"})

        @property
        def _data(self):  # type: ignore[override]
            raise RuntimeError("no data")

        def get(self, key, default=None):
            return super().get(key, default)

    class XObj(dict):
        def get_object(self):
            return self

    class FakePage(dict):
        def __init__(self):
            super().__init__({"/Resources": {"/XObject": XObj({"/Im0": BadObj()})}})

    class FakeReader:
        def __init__(self, _file):
            self.pages = [FakePage()]

    monkeypatch.setattr(pdf_processor_module.pypdf, "PdfReader", FakeReader)

    proc = pdf_processor_module.PDFProcessor()
    result = {"images": []}
    asyncio.run(proc._extract_images(Path(pdf), result, pages_to_process=[1]))
    assert result["images"] == []

    # Outer error branch
    def boom_open(*args, **kwargs):
        raise OSError("boom")

    monkeypatch.setattr("builtins.open", boom_open)
    asyncio.run(proc._extract_images(Path(pdf), result, pages_to_process=[1]))


def test_stream_content_extraction_include_images_and_tables(monkeypatch, tmp_path):
    pdf = tmp_path / "a.pdf"
    _create_minimal_pdf(pdf)

    class FakePage:
        def extract_text(self):
            return "hi"

        def extract_tables(self):
            return [[["a"]]]

    class FakePDF:
        pages = [FakePage()]

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class ImgObj(dict):
        def __init__(self):
            super().__init__({"/Subtype": "/Image"})

        def get(self, key, default=None):
            return super().get(key, default)

    class XObj(dict):
        def get_object(self):
            return self

    class ReaderPage(dict):
        def __init__(self):
            super().__init__({"/Resources": {"/XObject": XObj({"/Im0": ImgObj()})}})

        def get(self, key, default=None):
            return super().get(key, default)

    class FakeReader:
        def __init__(self, _file):
            self.pages = [ReaderPage()]
            self.is_encrypted = False
            self.metadata = None

    monkeypatch.setattr(pdf_processor_module, "pdfplumber", type("X", (), {"open": lambda *_a, **_k: FakePDF()})())
    monkeypatch.setattr(pdf_processor_module.pypdf, "PdfReader", FakeReader)

    events = []

    async def send_event(evt):
        events.append(evt)

    proc = pdf_processor_module.PDFProcessor()
    out = asyncio.run(proc.stream_content_extraction(str(pdf), send_event, pages=[1], include_images=True, include_tables=True))
    assert out["success"] is True
    assert any(e.get("type") == "status" for e in events)


def test_stream_content_extraction_error_path(monkeypatch, tmp_path):
    pdf = tmp_path / "a.pdf"
    _create_minimal_pdf(pdf)

    class BrokenPDF:
        def __enter__(self):
            raise RuntimeError("boom")

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(pdf_processor_module, "pdfplumber", type("X", (), {"open": lambda *_args, **_kwargs: BrokenPDF()})())

    events = []

    async def send_event(evt):
        events.append(evt)

    proc = pdf_processor_module.PDFProcessor()

    with pytest.raises(RuntimeError):
        asyncio.run(proc.stream_content_extraction(str(pdf), send_event, pages=[1], include_images=False, include_tables=False))

    assert any(e.get("type") == "error" for e in events)
