# OneNote MCP Server (Scaffold Phase)

Status: Scaffold implementation (no live Microsoft Graph calls yet).
Implements MCP server exposing tools to read, write, and list structural children of OneNote pages (simulated).
Future work will replace simulated graph_client with real Graph API + device code auth (memory-only token).

## Features (Current Scaffold)

- MCP stdio server (name: `onenote-reader`)
- Tools:
  - `read_onenote_page`
  - `write_onenote_page`
  - `list_onenote_page_children`
  - `traverse_onenote_notebook` (NEW: hierarchical notebook traversal, simulated)
- Resources:
  - `onenote://server-status`
  - `onenote://capabilities`
- In-memory rate limit placeholder (5 calls / 10s)
- Share link validation (pattern-based)
- HTML length validation (sanitization placeholder)
- In-memory simulated auth token

## Not Yet Implemented (Planned)

| Area | Future Implementation |
|------|------------------------|
| Auth | MSAL device code flow, real access token retrieval |
| Network | HTTP calls to `graph.microsoft.com` (`/v1.0/me/onenote/**`, `/v1.0/shares/**`) |
| HTML Sanitization | Enforce allowed tags/attrs using internal sanitizer |
| Write Modes | Real replace / append / new page creation via Graph endpoints |
| JSON Output | Rich block segmentation (images, tables, outlines, paragraphs) |
| Error Coverage | Mapping of Graph HTTP status codes -> taxonomy |

## Installation

Assumes `uv` and Python 3.14.

From the repository root:

```
cd mcp-tools/onenote-reader
uv sync
```

Local editable install (optional):

```
cd mcp-tools/onenote-reader
uv pip install -e .
```

(Or run directly via `uvx` without editable install:)

```
cd mcp-tools/onenote-reader
uvx --from . python -m onenote_reader --test

# Or fetch directly from GitHub (no checkout)
uvx --from "git+https://github.com/<owner>/<repo>.git@<ref>#subdirectory=mcp-tools/onenote-reader" \
  python -m onenote_reader --test
```

## Run

Start server (stdio JSON-RPC):

```
cd mcp-tools/onenote-reader
uvx --from . python -m onenote_reader

# Or fetch directly from GitHub (no checkout)
uvx --from "git+https://github.com/<owner>/<repo>.git@<ref>#subdirectory=mcp-tools/onenote-reader" \
  python -m onenote_reader
```

Self-test (lists tools/resources then exits):

```
uvx --from . python -m onenote_reader --test
```

## MCP Integration

Client must speak MCP over stdio. Example pseudo JSON-RPC call (tool listing):

```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "tools/list"
}
```

Tool invocation (example read):

```json
{
  "jsonrpc": "2.0",
  "id": "2",
  "method": "tools/call",
  "params": {
    "name": "read_onenote_page",
    "arguments": {
      "share_link": "https://example.onenote.com/someShare",
      "format": "plain"
    }
  }
}
```

Response `content[0].text` will contain JSON string like:

```json
{
  "ok": true,
  "data": {
    "page_id": "...",
    "title": "Placeholder Title",
    "format": "plain",
    "plain_text": "Scaffold placeholder page content...",
    "source_link": "https://example..."
  }
}
```

## Tools (Schemas)

### read_onenote_page

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| share_link | string (required) | — | Must match accepted OneNote patterns |
| format | enum[plain, html, json] | plain | Output representation |
| include_images | boolean | false | Adds placeholder image list (scaffold) |
| max_chars | integer | None | Truncate plain text if provided |

Returns:
```
{ ok, data: { page_id, title, format, plain_text? | html? | json?, images?[], source_link } }
```

### write_onenote_page

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| share_link | string (required) | — | Page (replace/append) or section (new_page) |
| mode | enum[replace, append, new_page] | append | Operation type |
| content_html | string (required) | — | HTML fragment (length checked) |
| title | string | None | Used if provided (replace/new_page) |
| position | enum[top, bottom] | bottom | Append insertion point |

Returns:
```
{ ok, data: { page_id, mode, position?, title, fragment_length, note } }
```

### list_onenote_page_children

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| share_link | string (required) | — | Page or section share link |
| type | enum[images, outlines, all] | all | Filter result set |

Returns:
```
{ ok, data: { share_link, filter, elements:[{id,type,preview}], note } }
```

### traverse_onenote_notebook (NEW)

Traverse a full OneNote hierarchy (sections, pages; simulated — no real Graph calls yet).

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| share_link | string (required) | — | Notebook or section share link |
| content_mode | enum[summary, plain, html] | summary | Per-page content inclusion strategy |
| max_chars_per_page | integer | 2000 | Truncation cap when content_mode != summary (100–10000) |

content_mode behaviors (scaffold):
- summary: metadata only (ids, titles, counts)
- plain: adds truncated plain_text to each page
- html: adds truncated simple HTML wrapper for each page

Returns:
```
{
  "ok": true,
  "data": {
    "share_link": "...",
    "content_mode": "plain",
    "max_chars_per_page": 2000,
    "sections": [
      {
        "id": "sec_0_1234",
        "title": "Section 1",
        "pages": [
          {"id": "pg_0_56789", "title": "Page 1 (Section 1)", "plain_text": "Placeholder content ..."}
        ]
      }
    ],
    "note": "Traversal simulated (no network)"
  }
}
```

## Resources

- `onenote://server-status`
  Runtime status, tool names, auth scaffold status, limits.

- `onenote://capabilities`
  Declared limits, allowed HTML tags, rate limit description.

## Error Taxonomy

| Code | Meaning |
|------|---------|
| UserInput | Invalid params / share link / rate limit exceeded |
| Forbidden | (Reserved for future: disallowed domain / tag) |
| NotFound | (Future: page/section missing) |
| Timeout | (Future: Graph call exceeded timeout) |
| Internal | Unexpected failure (current placeholder network denial) |

## Security / Safety (Scaffold)

- Network calls disabled (no external requests)
- Token is simulated placeholder (not persisted)
- HTML not sanitized yet (do not pass untrusted HTML into final system until sanitization added)
- Strict share link pattern checks prevent arbitrary URL usage
- Rate limiter prevents burst misuse

## Planned Device Code Auth (Future)

Flow (will implement in `auth.py` using MSAL):
1. Initiate device flow with required scopes (`Notes.ReadWrite.All offline_access`).
2. Display user code + verification URL to user (stderr log).
3. Poll until token acquired or timeout.
4. Store token only in memory.
5. Inject `Authorization: Bearer <token>` in Graph requests.

## Development Roadmap

| Step | Action |
|------|--------|
| 1 | Add real HTTP client (httpx) with host/path allowlist |
| 2 | Implement share link resolution |
| 3 | Implement page read (HTML) + format conversions |
| 4 | Add HTML sanitizer + allowed tags enforcement |
| 5 | Implement write modes with Graph PATCH/POST |
| 6 | Enhance children listing via DOM parsing |
| 7 | Add streaming (optional) for large pages |
| 8 | Expand tests (unit + integration) |

## Testing (Current)

Manual:
1. `uvx --from . python -m onenote_reader --test`
2. Use an MCP client to call each tool with sample share link (pattern-valid dummy).

## Limitations

- No real OneNote/Graph access
- No persistence
- Placeholder IDs & content
- No streaming or partial updates

## Extension Ideas

- Add `resolve_share_link` as explicit tool
- Add `search_onenote_pages(query, section_link)`
- Add streaming large page extraction
- Add metrics resource (counts per tool)

## License

See root repository LICENSE file.
