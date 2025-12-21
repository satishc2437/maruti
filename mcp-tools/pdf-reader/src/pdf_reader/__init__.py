"""PDF Reader MCP Server.

A Model Context Protocol server that provides comprehensive PDF reading capabilities
including text extraction, image extraction, table detection, document structure
analysis, and OCR support for scanned PDFs.

Features:
- Advanced PDF content extraction (text, images, tables)
- OCR support for scanned documents
- Streaming support for large document processing
- Document metadata retrieval
- Page-by-page content access
- Safety constraints and file validation

Run with: uvx python -m pdf_reader
"""

__version__ = "1.0.0"
__author__ = "MCP Generator"
