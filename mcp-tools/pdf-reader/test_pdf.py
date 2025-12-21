#!/usr/bin/env python3
"""
Test the PDF Reader MCP Server with a specific PDF file.
"""

import asyncio
import json
from pathlib import Path

from pypdf import PdfWriter

from pdf_reader.tools import tool_extract_pdf_content, tool_get_pdf_metadata, tool_list_pdf_pages


async def run_pdf_file(file_path: str):
    """Run all PDF tools against the specified file and print results."""
    print(f"Testing PDF file: {file_path}")
    print("=" * 80)

    # Test 1: Get metadata
    print("1. Testing get_pdf_metadata...")
    try:
        metadata_result = await tool_get_pdf_metadata({"file_path": file_path})
        print(f"Metadata result: {json.dumps(metadata_result, indent=2, default=str)}")
    except Exception as e:  # pylint: disable=broad-except
        print(f"Metadata test failed: {e}")

    print("\n" + "-" * 80 + "\n")

    # Test 2: List first 3 pages preview
    print("2. Testing list_pdf_pages (first 3 pages)...")
    try:
        pages_result = await tool_list_pdf_pages(
            {
                "file_path": file_path,
                "start_page": 1,
                "end_page": 3,
                "preview_length": 200,
            }
        )
        print(f"Pages preview result: {json.dumps(pages_result, indent=2, default=str)}")
    except Exception as e:  # pylint: disable=broad-except
        print(f"Pages test failed: {e}")

    print("\n" + "-" * 80 + "\n")

    # Test 3: Extract content (first page only to keep output manageable)
    print("3. Testing extract_pdf_content (first page only)...")
    try:
        content_result = await tool_extract_pdf_content(
            {
                "file_path": file_path,
                "pages": [1],
                "include_images": False,  # Skip images for faster test
                "include_tables": True,
                "use_ocr": False,
            }
        )
        print(f"Content extraction result (first page): {json.dumps(content_result, indent=2, default=str)}")
    except Exception as e:  # pylint: disable=broad-except
        print(f"Content extraction test failed: {e}")


def _create_minimal_pdf(path: Path) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with path.open("wb") as f:
        writer.write(f)


def test_pdf_tools_smoke(tmp_path: Path):
    """Smoke-test core PDF tools on a minimal generated PDF."""
    pdf_path = tmp_path / "sample.pdf"
    _create_minimal_pdf(pdf_path)

    metadata_result = asyncio.run(tool_get_pdf_metadata({"file_path": str(pdf_path)}))
    assert metadata_result["ok"] is True
    assert "data" in metadata_result
    assert metadata_result["data"]["page_count"] == 1

    pages_result = asyncio.run(
        tool_list_pdf_pages(
            {
                "file_path": str(pdf_path),
                "start_page": 1,
                "end_page": 1,
                "preview_length": 200,
            }
        )
    )
    assert pages_result["ok"] is True
    assert isinstance(pages_result["data"], list)
    assert pages_result["data"][0]["page_number"] == 1

    content_result = asyncio.run(
        tool_extract_pdf_content(
            {
                "file_path": str(pdf_path),
                "pages": [1],
                "include_images": False,
                "include_tables": False,
                "use_ocr": False,
            }
        )
    )
    assert content_result["ok"] is True
    assert "data" in content_result
    assert "metadata" in content_result["data"]
    assert "pages" in content_result["data"]


async def main():
    """Main test function."""
    # Test file path provided by user (now in pdf-reader directory)
    test_file = "basic-text.pdf"

    print("PDF Reader MCP Server - Functionality Test")
    print("=" * 80)

    # Check if file exists
    if not Path(test_file).exists():
        print(f"ERROR: Test file not found: {test_file}")
        print("Please ensure the file exists and the path is correct.")
        return

    await run_pdf_file(test_file)

    print("\n" + "=" * 80)
    print("Test completed!")


if __name__ == "__main__":
    asyncio.run(main())
