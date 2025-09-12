#!/usr/bin/env python3
"""
Test the PDF Reader MCP Server with a specific PDF file.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add the package to Python path
sys.path.insert(0, str(Path(__file__).parent))

from pdf_reader.tools import tool_get_pdf_metadata, tool_list_pdf_pages, tool_extract_pdf_content


async def test_pdf_file(file_path: str):
    """Test all PDF tools with the specified file."""
    print(f"Testing PDF file: {file_path}")
    print("=" * 80)
    
    # Test 1: Get metadata
    print("1. Testing get_pdf_metadata...")
    try:
        metadata_result = await tool_get_pdf_metadata({"file_path": file_path})
        print(f"Metadata result: {json.dumps(metadata_result, indent=2, default=str)}")
    except Exception as e:
        print(f"Metadata test failed: {e}")
    
    print("\n" + "-" * 80 + "\n")
    
    # Test 2: List first 3 pages preview
    print("2. Testing list_pdf_pages (first 3 pages)...")
    try:
        pages_result = await tool_list_pdf_pages({
            "file_path": file_path,
            "start_page": 1,
            "end_page": 3,
            "preview_length": 200
        })
        print(f"Pages preview result: {json.dumps(pages_result, indent=2, default=str)}")
    except Exception as e:
        print(f"Pages test failed: {e}")
    
    print("\n" + "-" * 80 + "\n")
    
    # Test 3: Extract content (first page only to keep output manageable)
    print("3. Testing extract_pdf_content (first page only)...")
    try:
        content_result = await tool_extract_pdf_content({
            "file_path": file_path,
            "pages": [1],
            "include_images": False,  # Skip images for faster test
            "include_tables": True,
            "use_ocr": False
        })
        print(f"Content extraction result (first page): {json.dumps(content_result, indent=2, default=str)}")
    except Exception as e:
        print(f"Content extraction test failed: {e}")


async def main():
    """Main test function."""
    # Test file path provided by user (now in pdf-reader directory)
    test_file = r".\basic-text.pdf"
    
    print("PDF Reader MCP Server - Functionality Test")
    print("=" * 80)
    
    # Check if file exists
    if not Path(test_file).exists():
        print(f"ERROR: Test file not found: {test_file}")
        print("Please ensure the file exists and the path is correct.")
        return
    
    await test_pdf_file(test_file)
    
    print("\n" + "=" * 80)
    print("Test completed!")


if __name__ == "__main__":
    asyncio.run(main())