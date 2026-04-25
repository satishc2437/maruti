# Template internals

This directory is the canonical skeleton for new MCP tools. It is **not**
a runnable tool itself.

`scripts/new_mcp_tool.py <name>` instantiates this template into
`mcp-tools/<name>/`, substituting four placeholders:

| Placeholder           | Meaning                       | Example            |
| --------------------- | ----------------------------- | ------------------ |
| `{{TOOL_HYPHEN}}`     | lowercase-hyphen tool name    | `image-processor`  |
| `{{TOOL_MODULE}}`     | snake-case Python module      | `image_processor`  |
| `{{TOOL_TITLE}}`      | Human Title Case              | `Image Processor`  |
| `{{TOOL_DESCRIPTION}}`| one-line description          | (passed via flag)  |

The `__module__` directory under `src/` is renamed to the actual
`{{TOOL_MODULE}}` value at instantiation time.

Edit the template directly to evolve what new tools look like. Keep the
skeleton minimal — anything domain-specific belongs in the tool itself,
not in the template.
