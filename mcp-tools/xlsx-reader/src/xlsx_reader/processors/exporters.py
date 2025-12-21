"""Data export functionality for Excel workbooks.

Handles conversion to CSV, JSON, and other formats.
"""

import csv
import io
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from ..errors import ValidationError, WorksheetError, success_response
from .workbook import ExcelProcessor

logger = logging.getLogger(__name__)


class DataExporter:
    """Handles exporting Excel data to various formats."""

    def __init__(self, excel_processor: ExcelProcessor):
        """Create an exporter bound to an Excel processor."""
        self.excel_processor = excel_processor

    def export_worksheet_to_csv(
        self,
        sheet_name: str,
        output_path: Optional[str] = None,
        include_headers: bool = True,
        delimiter: str = ",",
    ) -> Dict[str, Any]:
        """Export worksheet data to CSV format.

        Args:
            sheet_name: Name of worksheet to export
            output_path: File path to save CSV (returns string if None)
            include_headers: Include first row as headers
            delimiter: CSV delimiter character

        Returns:
            Export results with CSV data or file info

        Raises:
            WorksheetError: If export fails
        """
        try:
            # Get worksheet data
            worksheet_data = self.excel_processor.get_worksheet_data(sheet_name)

            if not worksheet_data["data"]:
                return success_response(
                    {
                        "sheet_name": sheet_name,
                        "rows_exported": 0,
                        "message": "No data to export",
                    }
                )

            # Convert to CSV
            csv_content = io.StringIO()
            writer = csv.writer(csv_content, delimiter=delimiter)

            rows_exported = 0
            for row_data in worksheet_data["data"]:
                row_values = []
                for cell in row_data:
                    value = cell.get("value")
                    # Handle None values and convert to string
                    if value is None:
                        row_values.append("")
                    else:
                        row_values.append(str(value))

                writer.writerow(row_values)
                rows_exported += 1

            csv_string = csv_content.getvalue()
            csv_content.close()

            result = {
                "sheet_name": sheet_name,
                "rows_exported": rows_exported,
                "format": "CSV",
                "delimiter": delimiter,
            }

            # Save to file or return content
            if output_path:
                output_file = Path(output_path)
                with open(output_file, "w", newline="", encoding="utf-8") as f:
                    f.write(csv_string)

                result.update(
                    {
                        "saved_to": str(output_file),
                        "file_size": output_file.stat().st_size,
                    }
                )
            else:
                result["csv_data"] = csv_string

            return result

        except Exception as e:
            raise WorksheetError(f"Failed to export to CSV: {e}")

    def export_workbook_to_json(
        self,
        include_formulas: bool = False,
        include_formatting: bool = True,
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Export entire workbook to JSON format.

        Args:
            include_formulas: Include formula strings in output
            include_formatting: Include cell formatting information
            output_path: File path to save JSON (returns dict if None)

        Returns:
            Complete workbook data in JSON format

        Raises:
            WorksheetError: If export fails
        """
        try:
            workbook_info = self.excel_processor.get_workbook_info()

            workbook_json = {
                "metadata": {
                    "file_path": workbook_info.get("file_path"),
                    "sheet_count": workbook_info.get("sheet_count"),
                    "sheet_names": workbook_info.get("sheet_names"),
                    "active_sheet": workbook_info.get("active_sheet"),
                    "export_options": {
                        "include_formulas": include_formulas,
                        "include_formatting": include_formatting,
                    },
                },
                "sheets": {},
            }

            # Export each worksheet
            for sheet_name in workbook_info.get("sheet_names", []):
                try:
                    sheet_data = self.excel_processor.get_worksheet_data(
                        sheet_name=sheet_name, include_formulas=include_formulas
                    )

                    # Process sheet data for JSON serialization
                    processed_data = []
                    for row in sheet_data.get("data", []):
                        processed_row = []
                        for cell in row:
                            cell_data = {
                                "coordinate": cell.get("coordinate"),
                                "value": cell.get("value"),
                                "data_type": cell.get("data_type"),
                            }

                            if include_formulas and "formula" in cell:
                                cell_data["formula"] = cell["formula"]

                            if include_formatting:
                                for attr in [
                                    "font",
                                    "fill",
                                    "alignment",
                                    "number_format",
                                ]:
                                    if attr in cell:
                                        cell_data[attr] = cell[attr]

                            processed_row.append(cell_data)
                        processed_data.append(processed_row)

                    workbook_json["sheets"][sheet_name] = {
                        "dimensions": sheet_data.get("range"),
                        "rows": sheet_data.get("rows", 0),
                        "columns": sheet_data.get("columns", 0),
                        "data": processed_data,
                    }

                except Exception as e:
                    logger.warning(f"Failed to export sheet '{sheet_name}': {e}")
                    workbook_json["sheets"][sheet_name] = {"error": str(e)}

            result = {
                "sheets_exported": len(
                    [s for s in workbook_json["sheets"].values() if "error" not in s]
                ),
                "total_sheets": len(workbook_json["sheets"]),
                "format": "JSON",
            }

            # Save to file or return data
            if output_path:
                output_file = Path(output_path)
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(workbook_json, f, indent=2, default=str)

                result.update(
                    {
                        "saved_to": str(output_file),
                        "file_size": output_file.stat().st_size,
                    }
                )
            else:
                result["json_data"] = workbook_json

            return result

        except Exception as e:
            raise WorksheetError(f"Failed to export to JSON: {e}")

    def export_sheet_to_pandas(
        self, sheet_name: str, include_headers: bool = True
    ) -> pd.DataFrame:
        """Export worksheet data to pandas DataFrame.

        Args:
            sheet_name: Name of worksheet to export
            include_headers: Use first row as column headers

        Returns:
            pandas DataFrame with worksheet data

        Raises:
            WorksheetError: If export fails
        """
        try:
            worksheet_data = self.excel_processor.get_worksheet_data(sheet_name)

            if not worksheet_data["data"]:
                return pd.DataFrame()

            # Convert to list of lists
            rows = []
            for row_data in worksheet_data["data"]:
                row_values = [cell.get("value") for cell in row_data]
                rows.append(row_values)

            # Create DataFrame
            if include_headers and rows:
                headers = rows[0]
                data_rows = rows[1:]
                df = pd.DataFrame(data_rows, columns=headers)
            else:
                df = pd.DataFrame(rows)

            return df

        except Exception as e:
            raise WorksheetError(f"Failed to export to pandas: {e}")

    def get_summary_statistics(self, sheet_name: str) -> Dict[str, Any]:
        """Generate summary statistics for worksheet data.

        Args:
            sheet_name: Name of worksheet to analyze

        Returns:
            Dictionary with summary statistics

        Raises:
            WorksheetError: If analysis fails
        """
        try:
            df = self.export_sheet_to_pandas(sheet_name, include_headers=True)

            if df.empty:
                return {
                    "sheet_name": sheet_name,
                    "total_rows": 0,
                    "total_columns": 0,
                    "message": "No data to analyze",
                }

            # Basic statistics
            stats = {
                "sheet_name": sheet_name,
                "total_rows": len(df),
                "total_columns": len(df.columns),
                "column_names": df.columns.tolist(),
                "data_types": df.dtypes.astype(str).to_dict(),
                "null_counts": df.isnull().sum().to_dict(),
                "non_null_counts": df.count().to_dict(),
            }

            # Numeric column statistics
            numeric_columns = df.select_dtypes(include=["number"]).columns
            if len(numeric_columns) > 0:
                numeric_stats = df[numeric_columns].describe().to_dict()
                stats["numeric_statistics"] = numeric_stats

            # String column statistics
            string_columns = df.select_dtypes(include=["object"]).columns
            if len(string_columns) > 0:
                string_stats = {}
                for col in string_columns:
                    string_stats[col] = {
                        "unique_count": df[col].nunique(),
                        "most_frequent": df[col].mode().iloc[0]
                        if not df[col].mode().empty
                        else None,
                    }
                stats["string_statistics"] = string_stats

            return stats

        except Exception as e:
            raise WorksheetError(f"Failed to generate statistics: {e}")
