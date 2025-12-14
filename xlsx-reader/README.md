# Excel Reader MCP Server

A comprehensive Model Context Protocol (MCP) server for reading, editing, and processing Microsoft Excel (.xlsx) workbooks.

## Features

### Reading Capabilities
- Extract workbook metadata (sheet names, dimensions, file info)
- Read worksheet data with cell values, formulas, and formatting
- Stream large workbook data in chunks
- Extract chart definitions and metadata
- Extract pivot table structures and calculations

### Editing Capabilities
- Update individual cells or cell ranges
- Modify cell formatting (fonts, colors, borders, alignment)
- Merge and unmerge cells
- Add data validation rules
- Insert/delete rows and columns
- Add/delete/rename worksheets
- Apply conditional formatting
- Create and modify charts
- Create and modify pivot tables

### Export & Save
- Export worksheets to CSV format
- Export complete workbooks to JSON
- Save changes to existing files
- Save workbooks with new filenames

### Safety Features
- Automatic file backup before modifications
- File locking for concurrent access protection
- Streaming support for large files
- Comprehensive error handling

## Installation

This server is part of the maruti monorepo workspace. Install from the project root:

```bash
# From the maruti project root directory
cd xlsx-reader
uv pip install -e .

# Or run directly without installation
uvx --from . python -m xlsx_reader
```

## Dependencies

- **openpyxl**: Primary Excel file manipulation
- **xlsxwriter**: Enhanced writing capabilities  
- **pandas**: Data analysis and CSV export
- **python-dateutil**: Date/time handling
- **filelock**: Concurrent access protection

## Usage

The server provides tools for comprehensive Excel workbook manipulation:

### Reading Tools
- `read_workbook_info`: Get workbook metadata
- `read_worksheet_data`: Read specific worksheet data
- `stream_workbook_data`: Stream large workbooks in chunks
- `extract_charts_metadata`: Get chart information
- `extract_pivot_tables`: Get pivot table structure

### Editing Tools
- `update_cell_value`: Modify cell values/formulas
- `update_cell_range`: Batch update multiple cells
- `update_cell_formatting`: Apply formatting
- `merge_cells`: Merge/unmerge cell ranges
- `add_data_validation`: Add input constraints
- `add_worksheet`: Create new worksheets
- `delete_worksheet`: Remove worksheets
- `rename_worksheet`: Change worksheet names
- `insert_rows`/`delete_rows`: Modify row structure
- `insert_columns`/`delete_columns`: Modify column structure
- `add_conditional_formatting`: Rules-based formatting
- `modify_chart`/`create_chart`: Chart manipulation
- `modify_pivot_table`/`create_pivot_table`: Pivot table operations

### Export Tools
- `export_to_csv`: Convert sheets to CSV
- `export_workbook_json`: Full JSON serialization
- `save_workbook`: Persist changes
- `save_workbook_as`: Save with new name

## Safety

The server operates with full filesystem access and includes:
- Automatic backup creation before modifications
- File locking to prevent concurrent access conflicts
- Maximum file size limits (200MB for editing operations)
- Comprehensive error classification and handling

## Error Handling

The server uses a structured error taxonomy:
- **UserInput**: Invalid parameters with correction hints
- **Forbidden**: Policy violations
- **NotFound**: Missing files or resources
- **Timeout**: Operations exceeding time limits
- **Internal**: Unexpected system errors
- **Cancelled**: User-cancelled operations

## Development

Development setup from the maruti project root:

```bash
# Install in development mode (from maruti root)
cd xlsx-reader
uv pip install -e ".[dev]"

# Run the server
python -m xlsx_reader

# Run tests
pytest

# Format code
black src/ && isort src/

# Type checking
mypy src/
```

## License

MIT License