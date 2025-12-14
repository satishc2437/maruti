# PDF Reader MCP Server

A comprehensive Model Context Protocol (MCP) server that provides advanced PDF reading capabilities for LLM agents. This server enables efficient extraction and processing of PDF content including text, images, tables, document structure, and OCR support for scanned documents.

## Features

### Core Capabilities
- **Advanced Text Extraction**: Extract text from PDF pages with high fidelity
- **Image Extraction**: Extract embedded images as base64-encoded data
- **Table Detection**: Identify and extract table structures and data
- **Document Metadata**: Retrieve PDF properties, author, creation date, etc.
- **Streaming Processing**: Handle large documents with real-time progress updates

### Safety & Security
- File size limits (100MB max)
- Path traversal protection
- File type validation (PDF only)
- Timeout protection for long operations
- Comprehensive error handling and logging

## Installation

### Prerequisites
```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies using uv
uv sync

# Or install core dependencies from PyPI
uv add mcp PyPDF2 pdfplumber Pillow

# Optional: Add table extraction support (may fail on some systems)
uv add --optional tables pandas
```

### Dependencies

**Core Dependencies:**
- `mcp>=1.0.0` - MCP server framework
- `PyPDF2>=3.0.0` - Basic PDF processing
- `pdfplumber>=0.10.0` - Advanced text and table extraction
- `Pillow>=9.0.0` - Image processing

**Optional Dependencies:**
- `pandas>=1.5.0` - Table data processing (install with `uv add --optional tables pandas`)

## Usage

### Running the Server
```bash
# Using uv (recommended)
uv run python -m pdf_reader

# Using uvx for one-time execution
uvx --from . python -m pdf_reader

# Standard execution (if dependencies installed globally)
python -m pdf_reader

# Test mode (development)
uv run python -m pdf_reader --test
```

## MCP Server Configuration

### Using with Claude Desktop

1. **Install the server:**
   ```bash
   cd pdf-reader
   uv sync
   ```

2. **Add to Claude Desktop configuration:**
   
   Edit your Claude Desktop configuration file:
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Linux**: `~/.config/claude/claude_desktop_config.json`

   Add the PDF Reader server:
   ```json
   {
     "mcpServers": {
       "pdf-reader": {
         "command": "uv",
         "args": ["run", "python", "-m", "pdf_reader"],
         "cwd": "/path/to/your/pdf-reader"
       }
     }
   }
   ```

3. **Restart Claude Desktop** to load the new server.

### Using with Other MCP Clients

For other MCP-compatible clients, run the server in stdio mode:
```bash
cd pdf-reader
uv run python -m pdf_reader
```

The server communicates via JSON-RPC over stdin/stdout as per MCP specification.

### Using with uvx (Alternative)

For one-time usage without installation:
```bash
uvx --from /path/to/pdf-reader python -m pdf_reader
```

### Available Tools

#### 1. `extract_pdf_content`
Comprehensive PDF content extraction with all features.

**Parameters:**
- `file_path` (string, required): Path to PDF file
- `pages` (array of integers, optional): Specific pages to extract (1-indexed)
- `include_images` (boolean, default: true): Extract images
- `include_tables` (boolean, default: true): Extract table structures
- `use_ocr` (boolean, default: false): OCR functionality not supported (parameter ignored)

**Example:**
```json
{
  "file_path": "./documents/report.pdf",
  "pages": [1, 2, 3],
  "include_images": true,
  "include_tables": true,
  "use_ocr": false
}
```

#### 2. `get_pdf_metadata`
Extract PDF metadata and document properties without processing content.

**Parameters:**
- `file_path` (string, required): Path to PDF file

**Example:**
```json
{
  "file_path": "./documents/report.pdf"
}
```

#### 3. `list_pdf_pages`
Get a preview of PDF pages with text snippets for content overview.

**Parameters:**
- `file_path` (string, required): Path to PDF file
- `start_page` (integer, default: 1): Starting page number
- `end_page` (integer, optional): Ending page number
- `preview_length` (integer, default: 200): Max characters per preview

**Example:**
```json
{
  "file_path": "./documents/report.pdf",
  "start_page": 1,
  "end_page": 5,
  "preview_length": 300
}
```

#### 4. `stream_pdf_extraction`
Stream PDF content extraction with real-time progress updates (for MCP clients with streaming support).

**Parameters:** Same as `extract_pdf_content`

### Available Resources

#### `pdf://supported-features`
Information about supported PDF processing capabilities and limitations.

#### `pdf://server-status`
Current server status, configuration, and available tools.

## Example Usage

### Basic Text Extraction
```python
# Extract all text from a PDF
{
  "tool": "extract_pdf_content",
  "arguments": {
    "file_path": "./document.pdf",
    "include_images": false,
    "include_tables": false
  }
}
```

### Advanced Content Extraction
```python
# Extract everything including images and tables
{
  "tool": "extract_pdf_content",
  "arguments": {
    "file_path": "./document.pdf",
    "include_images": true,
    "include_tables": true
  }
}
```

### Quick Document Overview
```python
# Get metadata and page previews
{
  "tool": "get_pdf_metadata",
  "arguments": {
    "file_path": "./document.pdf"
  }
}

{
  "tool": "list_pdf_pages",
  "arguments": {
    "file_path": "./document.pdf",
    "preview_length": 150
  }
}
```

## Response Format

### Success Response
```json
{
  "ok": true,
  "data": {
    "metadata": {...},
    "pages": [...],
    "images": [...],
    "tables": [...]
  }
}
```

### Error Response
```json
{
  "ok": false,
  "code": "UserInput|Forbidden|NotFound|Timeout|Internal",
  "message": "Error description",
  "hint": "Suggested resolution",
  "correlation_id": "abc123"
}
```

## Error Codes

- **UserInput**: Invalid parameters or file format
- **Forbidden**: Security violation (path traversal, etc.)
- **NotFound**: File doesn't exist
- **Timeout**: Operation exceeded time limit
- **Internal**: Unexpected server error

## Limitations

- Maximum file size: 100MB
- Password-protected PDFs not supported
- OCR functionality not available
- Complex table layouts may not extract perfectly
- Very large files may timeout during processing

## Development

### Project Structure
```
pdf-reader/
├── __init__.py           # Package initialization
├── __main__.py           # Entry point
├── server.py            # MCP server setup
├── tools.py             # Tool implementations
├── pdf_processor.py     # Core PDF processing
├── safety.py            # Security validation
├── errors.py            # Error handling
├── pyproject.toml       # Project configuration and dependencies
└── README.md           # Documentation
```

### Testing
```bash
# Run server tests
uv run python server.py --test

# Test specific functionality with uv
uv run python -c "
import asyncio
from pdf_reader.tools import tool_get_pdf_metadata
result = asyncio.run(tool_get_pdf_metadata({'file_path': 'test.pdf'}))
print(result)
"

# Run pytest (if dev dependencies installed)
uv run pytest
```

## License

This MCP server is provided as-is for educational and development purposes.