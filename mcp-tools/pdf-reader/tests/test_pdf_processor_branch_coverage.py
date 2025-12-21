import asyncio
import builtins
import importlib.util
from pathlib import Path

import pytest
from pypdf import PdfWriter

from pdf_reader import pdf_processor as pdf_processor_module


def _create_minimal_pdf(path: Path) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with path.open("wb") as f:
        writer.write(f)


def test_pdf_processor_import_error_branches(tmp_path):
    processor_path = Path(pdf_processor_module.__file__)

    # 1) Cover the required-imports ImportError branch (pypdf/pdfplumber/PIL)
    spec = importlib.util.spec_from_file_location("pdf_reader._pdf_processor_blocked", processor_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)

    orig_import = builtins.__import__

    def block_core_imports(name, globals=None, locals=None, fromlist=(), level=0):
        if name in {"pypdf", "pdfplumber", "PIL"} or name.startswith("PIL"):
            raise ImportError("blocked")
        return orig_import(name, globals, locals, fromlist, level)

    builtins.__import__ = block_core_imports
    try:
        with pytest.raises(ImportError):
            spec.loader.exec_module(module)
    finally:
        builtins.__import__ = orig_import

    # 2) Cover the optional pandas ImportError branch
    spec2 = importlib.util.spec_from_file_location("pdf_reader._pdf_processor_no_pandas", processor_path)
    assert spec2 and spec2.loader
    module2 = importlib.util.module_from_spec(spec2)

    def block_pandas(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "pandas":
            raise ImportError("blocked")
        return orig_import(name, globals, locals, fromlist, level)

    builtins.__import__ = block_pandas
    try:
        spec2.loader.exec_module(module2)
        assert getattr(module2, "PANDAS_AVAILABLE") is False
    finally:
        builtins.__import__ = orig_import


def test_extract_full_content_pages_none_and_table_truthy(monkeypatch, tmp_path):
    pdf = tmp_path / "a.pdf"
    _create_minimal_pdf(pdf)

    class FakePage:
        bbox = (0, 0, 10, 10)
        rotation = 0

        def extract_text(self):
            return "hi"

        def extract_tables(self):
            return [None, [["a", "b"], ["c", "d"]]]

    class FakePDF:
        pages = [FakePage()]

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        pdf_processor_module,
        "pdfplumber",
        type("X", (), {"open": lambda *_args, **_kwargs: FakePDF()})(),
    )

    proc = pdf_processor_module.PDFProcessor()
    out = asyncio.run(proc.extract_full_content(str(pdf), pages=None, include_images=False, include_tables=True))
    assert out["pages"][0]["tables_count"] == 1
    assert out["tables"][0]["rows"] == 2


def test_extract_images_continue_and_filter_fallthroughs(monkeypatch, tmp_path):
    pdf = tmp_path / "a.pdf"
    _create_minimal_pdf(pdf)

    class ImgObj(dict):
        def __init__(self, subtype: str, flt: str | None = None, data: bytes = b"img"):
            super().__init__({"/Subtype": subtype})
            if flt is not None:
                self["/Filter"] = flt
            self._data = data

        def get(self, key, default=None):
            return super().get(key, default)

    class XObj(dict):
        def get_object(self):
            return self

    class Page(dict):
        def __init__(self):
            super().__init__(
                {
                    "/Resources": {
                        "/XObject": XObj(
                            {
                                "/NotImg": ImgObj("/Form"),
                                "/NoFilter": ImgObj("/Image", None),
                                "/BadFilter": ImgObj("/Image", "/FlateDecode"),
                                "/Good": ImgObj("/Image", "/DCTDecode", b"jpgdata"),
                            }
                        )
                    }
                }
            )

        def get(self, key, default=None):
            return super().get(key, default)

    class FakeReader:
        def __init__(self, _file):
            self.pages = [Page()]

    monkeypatch.setattr(pdf_processor_module.pypdf, "PdfReader", FakeReader)

    proc = pdf_processor_module.PDFProcessor()
    result = {"images": []}

    # Include an out-of-range page to trigger the 'continue' branch
    asyncio.run(proc._extract_images(Path(pdf), result, pages_to_process=[1, 2]))
    assert any(img.get("format") == "JPEG" for img in result["images"])


def test_stream_content_extraction_table_exception_branch(monkeypatch, tmp_path):
    pdf = tmp_path / "a.pdf"
    _create_minimal_pdf(pdf)

    class FakePage:
        def extract_text(self):
            return "hi"

        def extract_tables(self):
            raise RuntimeError("no tables")

    class FakePDF:
        pages = [FakePage()]

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(pdf_processor_module, "pdfplumber", type("X", (), {"open": lambda *_a, **_k: FakePDF()})())

    proc = pdf_processor_module.PDFProcessor()

    async def fake_meta(_file_path: str):
        return {"page_count": 1, "file_info": {"path": str(pdf)}, "encrypted": False}

    monkeypatch.setattr(proc, "extract_metadata", fake_meta)

    events = []

    async def send_event(evt):
        events.append(evt)

    out = asyncio.run(proc.stream_content_extraction(str(pdf), send_event, pages=[1], include_images=False, include_tables=True))
    assert out["success"] is True
    progress = [e for e in events if e.get("type") == "progress"]
    assert progress[0]["page_data"]["tables_count"] == 0


def test_stream_content_extraction_image_counting_missing_xobject(monkeypatch, tmp_path):
    pdf = tmp_path / "a.pdf"
    _create_minimal_pdf(pdf)

    class FakePage:
        def extract_text(self):
            return "hi"

        def extract_tables(self):
            return []

    class FakePDF:
        pages = [FakePage(), FakePage()]

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class ReaderPage(dict):
        def __init__(self):
            super().__init__({"/Resources": {}})

        def get(self, key, default=None):
            return super().get(key, default)

    class FakeReader:
        def __init__(self, _file):
            # Only 1 page, but we'll claim 2 in metadata to hit out-of-range branch
            self.pages = [ReaderPage()]

    monkeypatch.setattr(pdf_processor_module, "pdfplumber", type("X", (), {"open": lambda *_a, **_k: FakePDF()})())
    monkeypatch.setattr(pdf_processor_module.pypdf, "PdfReader", FakeReader)

    proc = pdf_processor_module.PDFProcessor()

    async def fake_meta(_file_path: str):
        return {"page_count": 2, "file_info": {"path": str(pdf)}, "encrypted": False}

    monkeypatch.setattr(proc, "extract_metadata", fake_meta)

    events = []

    async def send_event(evt):
        events.append(evt)

    out = asyncio.run(proc.stream_content_extraction(str(pdf), send_event, pages=None, include_images=True, include_tables=False))
    assert out["success"] is True


def test_stream_content_extraction_image_counting_non_image_subtype(monkeypatch, tmp_path):
    pdf = tmp_path / "a.pdf"
    _create_minimal_pdf(pdf)

    class FakePage:
        def extract_text(self):
            return "hi"

        def extract_tables(self):
            return []

    class FakePDF:
        pages = [FakePage()]

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class Obj(dict):
        def get(self, key, default=None):
            return super().get(key, default)

    class XObj(dict):
        def get_object(self):
            return self

    class ReaderPage(dict):
        def __init__(self):
            super().__init__({"/Resources": {"/XObject": XObj({"/X0": Obj({"/Subtype": "/Form"})})}})

        def get(self, key, default=None):
            return super().get(key, default)

    class FakeReader:
        def __init__(self, _file):
            self.pages = [ReaderPage()]

    monkeypatch.setattr(pdf_processor_module, "pdfplumber", type("X", (), {"open": lambda *_a, **_k: FakePDF()})())
    monkeypatch.setattr(pdf_processor_module.pypdf, "PdfReader", FakeReader)

    proc = pdf_processor_module.PDFProcessor()

    async def fake_meta(_file_path: str):
        return {"page_count": 1, "file_info": {"path": str(pdf)}, "encrypted": False}

    monkeypatch.setattr(proc, "extract_metadata", fake_meta)

    async def send_event(_evt):
        return None

    out = asyncio.run(proc.stream_content_extraction(str(pdf), send_event, pages=[1], include_images=True, include_tables=False))
    assert out["success"] is True
