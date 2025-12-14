# Excel Reader MCP Server - Usage Examples

This document provides practical examples of using the Excel Reader MCP server for various Excel workbook operations.

## Running the Server

This server is part of the maruti monorepo workspace. Install and run from the project structure:

```bash
# From maruti project root, install xlsx-reader
cd xlsx-reader
uv pip install -e .

# Run the server
python -m xlsx_reader
```

Or run directly without installation:

```bash
# From maruti project root
cd xlsx-reader
uvx --from . python -m xlsx_reader
```

With debug logging:

```bash
python -m xlsx_reader --debug
```

## Basic Usage Examples

### 1. Reading Workbook Information

Get metadata about an Excel file:

```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "tools/call", 
  "params": {
    "name": "read_workbook_info",
    "arguments": {
      "file_path": "./sample_data.xlsx",
      "read_only": true
    }
  }
}
```

Expected response:
```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "result": [
    {
      "type": "text",
      "text": "{\"ok\": true, \"data\": {\"sheet_count\": 3, \"sheet_names\": [\"Sales\", \"Products\", \"Summary\"], \"active_sheet\": \"Sales\"}}"
    }
  ]
}
```

### 2. Reading Worksheet Data

Read data from a specific worksheet:

```json
{
  "jsonrpc": "2.0",
  "id": "2", 
  "method": "tools/call",
  "params": {
    "name": "read_worksheet_data",
    "arguments": {
      "file_path": "./sample_data.xlsx",
      "sheet_name": "Sales",
      "include_formulas": false,
      "cell_range": "A1:D10"
    }
  }
}
```

### 3. Updating Cell Values

Update a single cell:

```json
{
  "jsonrpc": "2.0",
  "id": "3",
  "method": "tools/call",
  "params": {
    "name": "update_cell_value", 
    "arguments": {
      "file_path": "./sample_data.xlsx",
      "sheet_name": "Sales",
      "cell_ref": "B5",
      "value": 1500.75
    }
  }
}
```

Update with a formula:

```json
{
  "jsonrpc": "2.0",
  "id": "4",
  "method": "tools/call",
  "params": {
    "name": "update_cell_value",
    "arguments": {
      "file_path": "./sample_data.xlsx", 
      "sheet_name": "Sales",
      "cell_ref": "D5",
      "formula": "=B5*C5"
    }
  }
}
```

### 4. Batch Cell Updates

Update multiple cells at once:

```json
{
  "jsonrpc": "2.0",
  "id": "5",
  "method": "tools/call",
  "params": {
    "name": "update_cell_range",
    "arguments": {
      "file_path": "./sample_data.xlsx",
      "sheet_name": "Sales", 
      "cell_range": "A1:C2",
      "values": [
        ["Product", "Quantity", "Price"],
        ["Widget A", 100, 25.99]
      ]
    }
  }
}
```

### 5. Worksheet Management

Add a new worksheet:

```json
{
  "jsonrpc": "2.0",
  "id": "6",
  "method": "tools/call",
  "params": {
    "name": "add_worksheet",
    "arguments": {
      "file_path": "./sample_data.xlsx",
      "sheet_name": "New Analysis",
      "index": 1
    }
  }
}
```

Delete a worksheet:

```json
{
  "jsonrpc": "2.0", 
  "id": "7",
  "method": "tools/call",
  "params": {
    "name": "delete_worksheet",
    "arguments": {
      "file_path": "./sample_data.xlsx",
      "sheet_name": "Old Data"
    }
  }
}
```

### 6. Export Operations

Export worksheet to CSV:

```json
{
  "jsonrpc": "2.0",
  "id": "8", 
  "method": "tools/call",
  "params": {
    "name": "export_to_csv",
    "arguments": {
      "file_path": "./sample_data.xlsx",
      "sheet_name": "Sales",
      "output_path": "./sales_export.csv",
      "include_headers": true
    }
  }
}
```

### 7. Saving Changes

Save changes to the workbook:

```json
{
  "jsonrpc": "2.0",
  "id": "9",
  "method": "tools/call", 
  "params": {
    "name": "save_workbook",
    "arguments": {
      "file_path": "./sample_data.xlsx"
    }
  }
}
```

Save as a new file:

```json
{
  "jsonrpc": "2.0",
  "id": "10",
  "method": "tools/call",
  "params": {
    "name": "save_workbook",
    "arguments": {
      "file_path": "./sample_data.xlsx",
      "save_as_path": "./sample_data_modified.xlsx" 
    }
  }
}
```

## Advanced Examples

### Working with Large Files

For large Excel files, the server automatically handles:

- File size validation (up to 200MB by default)
- Automatic backup creation before modifications
- File locking to prevent concurrent access conflicts
- Memory-efficient processing

### Error Handling

The server provides structured error responses:

```json
{
  "ok": false,
  "code": "UserInput",
  "message": "Parameter 'file_path' is required",
  "hint": "Provide the path to the Excel file"
}
```

Error codes include:
- **UserInput**: Invalid parameters with correction hints
- **Forbidden**: File access or operation not allowed
- **NotFound**: File or worksheet not found
- **Timeout**: Operation exceeded time limit
- **Internal**: Unexpected server errors
- **Cancelled**: Operation was cancelled

### Resource Access

Access server resources for information:

Get supported formats:
```json
{
  "jsonrpc": "2.0",
  "id": "11",
  "method": "resources/read",
  "params": {
    "uri": "xlsx://supported-formats"
  }
}
```

Get server status:
```json
{
  "jsonrpc": "2.0", 
  "id": "12",
  "method": "resources/read",
  "params": {
    "uri": "xlsx://server-status"
  }
}
```

## Best Practices

1. **File Paths**: Use absolute paths or paths relative to the server's working directory
2. **Backup**: The server automatically creates backups before modifications
3. **Memory**: Close large workbooks when done to free memory
4. **Concurrent Access**: The server handles file locking automatically
5. **Error Handling**: Always check the `ok` field in responses
6. **Validation**: Invalid cell references or sheet names will return helpful error messages

## Common Use Cases

### Data Import Pipeline
1. Read workbook info to discover sheets
2. Read worksheet data from each relevant sheet
3. Process and validate the data
4. Export cleaned data to CSV/JSON

### Report Generation
1. Create new worksheets for reports
2. Update cells with calculated values
3. Apply formatting (future feature)
4. Save the updated workbook

### Data Transformation
1. Read source data from multiple sheets
2. Update cells with transformed values
3. Create summary sheets
4. Export final results

## Limitations

Current limitations of the MCP server:

1. **Chart Operations**: Chart creation/modification has limited support due to openpyxl constraints
2. **Pivot Tables**: Pivot table operations have limited support - extraction works but creation/modification requires Excel
3. **Advanced Formatting**: Complex cell formatting features may not be fully supported
4. **Macros**: VBA macros are not supported
5. **External Links**: External workbook references are not supported

## Performance Notes

- **File Size**: Optimal performance with files under 50MB
- **Memory Usage**: Large workbooks are processed efficiently but may require significant memory
- **Streaming**: Future versions will include streaming support for very large datasets
- **Concurrency**: Single-threaded processing, one workbook operation at a time

## Troubleshooting

### Common Issues

1. **File Access Errors**: Ensure the file exists and is not open in Excel
2. **Permission Errors**: Check file system permissions
3. **Large File Timeout**: Increase timeout for very large files
4. **Memory Errors**: Close other applications when processing large workbooks

### Debug Mode

Run with `--debug` flag for detailed logging:

```bash
uvx python -m xlsx_reader --debug
```

This provides:
- Detailed operation logging
- File access information  
- Error stack traces
- Performance metrics