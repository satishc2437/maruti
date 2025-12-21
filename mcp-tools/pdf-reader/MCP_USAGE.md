# PDF Reader MCP Server Usage Guide

Updated to support `uvx --from .` usage (ephemeral execution) and clarify why plain `uvx python -m pdf_reader` fails without `--from .` (module not installed in that transient environment).

Also supports a no-checkout workflow using `uvx` directly from GitHub.

---

## 1. Installation (Editable Developer Mode – Recommended for Local Dev)

Creates a persistent editable install using the project’s existing virtual environment (preferred for iterative work):

```bash
cd mcp-tools/pdf-reader
uv pip install -e .
```

Then you can run (persistent environment):
```bash
uv run pdf-reader --test
uv run pdf-reader
```

---

## 2. One‑Shot Execution With `uvx` (No Persistent venv)

Because `uvx` creates a fresh ephemeral environment each run, you must tell it to build/install the current project using `--from .`.

Self‑test (non‑blocking):
```bash
uvx --from . pdf-reader --test
# or explicitly:
uvx --from . python -m pdf_reader --test
```

Start server (blocks, stdio):
```bash
uvx --from . pdf-reader
# or
uvx --from . python -m pdf_reader
```

(Without `--from .`, the module is absent -> “No module named pdf_reader”.)

---

## 3. Minimal Dependency Install (Non-Editable, Ephemeral)

If you only want a throwaway run (tables optional):
```bash
uvx pip install mcp PyPDF2 pdfplumber Pillow
uvx pip install pandas   # optional
```
(This does NOT install your local source; you still need `--from .` to run project code.)

---

## 4. CLI Overview

```
pdf-reader [--test]

(no flag)  Start persistent MCP stdio server
--test     Run internal tool/resource listing diagnostics then exit
```

Run forms:
```
Editable install: uv run pdf-reader --test
Ephemeral build:  uvx --from . pdf-reader --test
```

---

## 5. Integration with MCP Clients

### Claude Desktop

Config file paths:
- Windows: %APPDATA%\Claude\claude_desktop_config.json
- macOS:   ~/Library/Application Support/Claude/claude_desktop_config.json
- Linux:   ~/.config/claude/claude_desktop_config.json

Add server (choose ONE approach):

A) Using local editable install (prefer if you used `uv pip install -e .`):
```json
{
  "mcpServers": {
    "pdf-reader": {
      "command": "uv",
      "args": ["run", "pdf-reader"],
      "cwd": "C:/work/repos/maruti/mcp-tools/pdf-reader"
    }
  }
}
```

B) Using ephemeral `uvx --from .` (builds each launch):
```json
{
  "mcpServers": {
    "pdf-reader": {
      "command": "uvx",
      "args": ["--from", ".", "pdf-reader"],
      "cwd": "C:/work/repos/maruti/mcp-tools/pdf-reader"
    }
  }
}
```

C) Using `uvx` directly from GitHub (no manual checkout):
```json
{
  "mcpServers": {
    "pdf-reader": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/<owner>/<repo>.git@<ref>#subdirectory=mcp-tools/pdf-reader",
        "pdf-reader"
      ]
    }
  }
}
```

Restart Claude Desktop fully; then ask:
```
List available PDF tools
```

### VS Code MCP Extensions (e.g., Cline)

Editable install variant:
```json
{
  "mcp.servers": {
    "pdf-reader": {
      "command": "uv",
      "args": ["run", "pdf-reader"],
      "cwd": "/absolute/path/to/pdf-reader"
    }
  }
}
```

Ephemeral variant:
```json
{
  "mcp.servers": {
    "pdf-reader": {
      "command": "uvx",
      "args": ["--from", ".", "pdf-reader"],
      "cwd": "/absolute/path/to/pdf-reader"
    }
  }
}
```

### Generic MCP Clients

Editable:
```bash
uv run pdf-reader
```

Ephemeral:
```bash
uvx --from . pdf-reader
```

---

## 6. Available Tools

| Tool | Purpose | Key Params | Notes |
|------|---------|------------|-------|
| extract_pdf_content | Full content (pages, images*, tables*, metadata) | file_path, pages?, include_images, include_tables | OCR flag ignored |
| get_pdf_metadata | Lightweight metadata only | file_path | Fast |
| list_pdf_pages | Page text previews | file_path, start_page?, end_page?, preview_length (50–1000) | Truncated |
| stream_pdf_extraction | Incremental extraction w/ progress events | Same as extract_pdf_content | Requires streaming client |

\* Images: JPEG path; Tables: pdfplumber raw structures.

### Streaming Event Sequence
start → progress (per page) → status (images phase optional) → complete OR error.

Non-streaming client invocation returns explanatory error.

---

## 7. Manual Tool Invocation (Debug)

Editable environment:
```bash
uv run python -c "import asyncio,json;from pdf_reader.tools import tool_get_pdf_metadata as m;print(json.dumps(asyncio.run(m({'file_path':'sample.pdf'})),indent=2))"
```

Ephemeral (project code):
```bash
uvx --from . python -c "import asyncio,json;from pdf_reader.tools import tool_list_pdf_pages as lp;print(json.dumps(asyncio.run(lp({'file_path':'sample.pdf','start_page':1,'end_page':3})),indent=2))"
```

---

## 8. Self-Test Mode

Editable:
```bash
uv run pdf-reader --test
```

Ephemeral:
```bash
uvx --from . pdf-reader --test
```

Outputs tool list, resources, server status JSON.

---

## 9. Resources

| URI | Description |
|-----|-------------|
| pdf://supported-features | Feature matrix |
| pdf://server-status | Runtime status & safety features |

---

## 10. Safety / Constraints

- Read-only (no writes)
- Path traversal guarded
- File size limit: 100MB
- No network access
- OCR disabled
- Per-tool timeouts (≈10–60s)

---

## 11. Troubleshooting

| Issue | Cause | Resolution |
|-------|-------|-----------|
| No module named pdf_reader (uvx) | Missing `--from .` | Use `uvx --from . pdf-reader` |
| Streaming tool returns error | Client lacks streaming support | Use `extract_pdf_content` instead |
| Table extraction sparse | Complex layout | Accept limitation or post-process |
| Large PDF slow | Many pages/images | Limit `pages` parameter |

### Common Checks
- File exists & valid PDF
- Page indices 1-based
- Size ≤ 100MB

---

## 12. Example Claude Configs (Ephemeral vs Editable)

Ephemeral:
```json
{
  "mcpServers": {
    "pdf-reader": {
      "command": "uvx",
      "args": ["--from", ".", "pdf-reader"],
      "cwd": "C:\\work\\repos\\maruti\\pdf-reader"
    }
  }
}
```

Editable:
```json
{
  "mcpServers": {
    "pdf-reader": {
      "command": "uv",
      "args": ["run", "pdf-reader"],
      "cwd": "C:\\work\\repos\\maruti\\pdf-reader"
    }
  }
}
```

---

## 13. Maintenance

Editable code changes: no reinstall needed.
Dependency change:
```bash
uv pip install -e .
```
Regression check:
```bash
uv run pdf-reader --test
```

For ephemeral demonstration, always include `--from .`.

---

## 14. Future Enhancements

- Configurable allowed root & size (config + reload tool)
- Invocation metrics tool
- Correlation IDs in streaming events
- Optional OCR integration (tesseract)

---

Document updated to reflect:
- Correct usage of `uvx --from .`
- Dual strategy: editable (`uv`) vs ephemeral (`uvx`)
- Clarified misstep causing “No module named pdf_reader”

End.
