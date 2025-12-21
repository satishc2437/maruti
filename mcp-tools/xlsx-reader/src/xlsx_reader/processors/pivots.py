"""Pivot table processing functionality for Excel workbooks.

Handles pivot table extraction, modification, and creation.
"""

import logging
from typing import Any, Dict, List, Optional

from ..errors import PivotTableError, WorksheetError

logger = logging.getLogger(__name__)


class PivotTableProcessor:
    """Handles Excel pivot table operations."""

    def __init__(self, workbook):
        """Create a pivot table processor for an openpyxl workbook."""
        self.workbook = workbook

    def extract_pivot_tables_from_sheet(self, sheet_name: str) -> List[Dict[str, Any]]:
        """Extract pivot table metadata from a worksheet.

        Args:
            sheet_name: Name of worksheet to analyze

        Returns:
            List of pivot table definitions and properties

        Raises:
            PivotTableError: If pivot table extraction fails
        """
        try:
            if sheet_name not in self.workbook.sheetnames:
                raise PivotTableError(f"Sheet '{sheet_name}' not found")

            sheet = self.workbook[sheet_name]
            pivot_tables = []

            # Extract pivot table objects from worksheet
            if hasattr(sheet, "_pivots") and sheet._pivots:
                for i, pivot in enumerate(sheet._pivots):
                    pivot_info = {
                        "index": i,
                        "name": getattr(pivot, "name", f"PivotTable{i + 1}"),
                        "cache_definition": self._get_cache_definition(pivot),
                        "location": self._get_pivot_location(pivot),
                        "fields": self._extract_pivot_fields(pivot),
                        "data_fields": self._extract_data_fields(pivot),
                        "row_fields": self._extract_row_fields(pivot),
                        "column_fields": self._extract_column_fields(pivot),
                        "filter_fields": self._extract_filter_fields(pivot),
                        "style": self._get_pivot_style(pivot),
                    }
                    pivot_tables.append(pivot_info)

            return pivot_tables

        except Exception as e:
            raise PivotTableError(
                f"Failed to extract pivot tables from sheet '{sheet_name}': {e}"
            )

    def extract_all_pivot_tables(self) -> Dict[str, List[Dict[str, Any]]]:
        """Extract pivot tables from all worksheets in the workbook.

        Returns:
            Dictionary mapping sheet names to their pivot table lists

        Raises:
            PivotTableError: If extraction fails
        """
        try:
            all_pivots = {}

            for sheet_name in self.workbook.sheetnames:
                try:
                    pivots = self.extract_pivot_tables_from_sheet(sheet_name)
                    if pivots:
                        all_pivots[sheet_name] = pivots
                except Exception as e:
                    logger.warning(
                        f"Failed to extract pivot tables from '{sheet_name}': {e}"
                    )
                    all_pivots[sheet_name] = {"error": str(e)}

            return all_pivots

        except Exception as e:
            raise PivotTableError(f"Failed to extract pivot tables from workbook: {e}")

    def create_pivot_table(
        self,
        source_sheet: str,
        source_range: str,
        target_sheet: str,
        target_location: str,
        fields_config: Dict[str, List[str]],
    ) -> Dict[str, Any]:
        """Create a new pivot table.

        Args:
            source_sheet: Name of worksheet containing source data
            source_range: Range of cells containing source data
            target_sheet: Name of worksheet to place pivot table
            target_location: Cell location for pivot table
            fields_config: Configuration for pivot fields

        Returns:
            Information about the created pivot table

        Raises:
            PivotTableError: If pivot table creation fails
        """
        try:
            # Note: openpyxl has limited pivot table creation support
            # This is a placeholder implementation
            logger.warning("Pivot table creation has limited support in openpyxl")

            if source_sheet not in self.workbook.sheetnames:
                raise PivotTableError(f"Source sheet '{source_sheet}' not found")

            if target_sheet not in self.workbook.sheetnames:
                raise PivotTableError(f"Target sheet '{target_sheet}' not found")

            # Basic validation of field configuration
            required_fields = ["row_fields", "column_fields", "data_fields"]
            for field in required_fields:
                if field not in fields_config:
                    fields_config[field] = []

            return {
                "source_sheet": source_sheet,
                "source_range": source_range,
                "target_sheet": target_sheet,
                "target_location": target_location,
                "fields_config": fields_config,
                "created": False,
                "message": "Pivot table creation requires Excel application - openpyxl has limited support",
            }

        except Exception as e:
            raise PivotTableError(f"Failed to create pivot table: {e}")

    def modify_pivot_table(
        self, sheet_name: str, pivot_index: int, modifications: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Modify an existing pivot table.

        Args:
            sheet_name: Name of worksheet containing the pivot table
            pivot_index: Index of pivot table in the worksheet
            modifications: Dictionary of properties to modify

        Returns:
            Information about the modified pivot table

        Raises:
            PivotTableError: If pivot table modification fails
        """
        try:
            if sheet_name not in self.workbook.sheetnames:
                raise PivotTableError(f"Sheet '{sheet_name}' not found")

            sheet = self.workbook[sheet_name]

            if not hasattr(sheet, "_pivots") or not sheet._pivots:
                raise PivotTableError(f"No pivot tables found in sheet '{sheet_name}'")

            if pivot_index >= len(sheet._pivots):
                raise PivotTableError(f"Pivot table index {pivot_index} out of range")

            # Note: openpyxl has very limited pivot table modification support
            logger.warning("Pivot table modification has limited support in openpyxl")

            return {
                "sheet_name": sheet_name,
                "pivot_index": pivot_index,
                "modifications": modifications,
                "modified": False,
                "message": "Pivot table modification requires Excel application - openpyxl has limited support",
            }

        except Exception as e:
            raise PivotTableError(f"Failed to modify pivot table: {e}")

    def delete_pivot_table(self, sheet_name: str, pivot_index: int) -> Dict[str, Any]:
        """Delete a pivot table from the worksheet.

        Args:
            sheet_name: Name of worksheet containing the pivot table
            pivot_index: Index of pivot table to delete

        Returns:
            Information about the deleted pivot table

        Raises:
            PivotTableError: If pivot table deletion fails
        """
        try:
            if sheet_name not in self.workbook.sheetnames:
                raise PivotTableError(f"Sheet '{sheet_name}' not found")

            sheet = self.workbook[sheet_name]

            if not hasattr(sheet, "_pivots") or not sheet._pivots:
                raise PivotTableError(f"No pivot tables found in sheet '{sheet_name}'")

            if pivot_index >= len(sheet._pivots):
                raise PivotTableError(f"Pivot table index {pivot_index} out of range")

            # Remove pivot table (limited support)
            try:
                pivot = sheet._pivots.pop(pivot_index)
                deleted = True
            except Exception:
                deleted = False

            return {
                "sheet_name": sheet_name,
                "pivot_index": pivot_index,
                "remaining_pivots": len(sheet._pivots)
                if hasattr(sheet, "_pivots")
                else 0,
                "deleted": deleted,
                "message": "Pivot table deletion may require manual verification",
            }

        except Exception as e:
            raise PivotTableError(f"Failed to delete pivot table: {e}")

    def get_pivot_data_summary(
        self, sheet_name: str, pivot_index: int
    ) -> Dict[str, Any]:
        """Get summary information about pivot table data.

        Args:
            sheet_name: Name of worksheet containing the pivot table
            pivot_index: Index of pivot table

        Returns:
            Summary of pivot table data and structure

        Raises:
            PivotTableError: If analysis fails
        """
        try:
            if sheet_name not in self.workbook.sheetnames:
                raise PivotTableError(f"Sheet '{sheet_name}' not found")

            sheet = self.workbook[sheet_name]

            if not hasattr(sheet, "_pivots") or not sheet._pivots:
                raise PivotTableError(f"No pivot tables found in sheet '{sheet_name}'")

            if pivot_index >= len(sheet._pivots):
                raise PivotTableError(f"Pivot table index {pivot_index} out of range")

            pivot = sheet._pivots[pivot_index]

            summary = {
                "sheet_name": sheet_name,
                "pivot_index": pivot_index,
                "name": getattr(pivot, "name", f"PivotTable{pivot_index + 1}"),
                "cache_definition": self._get_cache_definition(pivot),
                "field_count": len(self._extract_pivot_fields(pivot)),
                "data_field_count": len(self._extract_data_fields(pivot)),
                "row_field_count": len(self._extract_row_fields(pivot)),
                "column_field_count": len(self._extract_column_fields(pivot)),
                "location": self._get_pivot_location(pivot),
            }

            return summary

        except Exception as e:
            raise PivotTableError(f"Failed to get pivot table summary: {e}")

    # Helper methods

    def _get_cache_definition(self, pivot) -> Dict[str, Any]:
        """Get pivot table cache definition."""
        try:
            if hasattr(pivot, "cache"):
                cache = pivot.cache
                return {
                    "source_range": getattr(cache, "worksheetSource", None),
                    "record_count": getattr(cache, "recordCount", None),
                    "refresh_on_load": getattr(cache, "refreshOnLoad", None),
                }
        except Exception as e:
            logger.warning(f"Failed to extract cache definition: {e}")

        return {}

    def _get_pivot_location(self, pivot) -> Dict[str, Any]:
        """Get pivot table location information."""
        try:
            if hasattr(pivot, "location"):
                location = pivot.location
                return {
                    "ref": getattr(location, "ref", None),
                    "first_header_row": getattr(location, "firstHeaderRow", None),
                    "first_data_row": getattr(location, "firstDataRow", None),
                    "first_data_col": getattr(location, "firstDataCol", None),
                }
        except Exception as e:
            logger.warning(f"Failed to extract pivot location: {e}")

        return {}

    def _extract_pivot_fields(self, pivot) -> List[Dict[str, Any]]:
        """Extract all pivot table fields."""
        fields = []

        try:
            if hasattr(pivot, "pivotFields") and pivot.pivotFields:
                for i, field in enumerate(pivot.pivotFields):
                    field_info = {
                        "index": i,
                        "name": getattr(field, "name", f"Field{i + 1}"),
                        "axis": getattr(field, "axis", None),
                        "data_field": getattr(field, "dataField", False),
                        "items_count": len(getattr(field, "items", [])),
                    }
                    fields.append(field_info)
        except Exception as e:
            logger.warning(f"Failed to extract pivot fields: {e}")

        return fields

    def _extract_data_fields(self, pivot) -> List[Dict[str, Any]]:
        """Extract data fields from pivot table."""
        data_fields = []

        try:
            if hasattr(pivot, "dataFields") and pivot.dataFields:
                for i, field in enumerate(pivot.dataFields):
                    field_info = {
                        "index": i,
                        "name": getattr(field, "name", f"DataField{i + 1}"),
                        "fld": getattr(field, "fld", None),
                        "subtotal": getattr(field, "subtotal", None),
                    }
                    data_fields.append(field_info)
        except Exception as e:
            logger.warning(f"Failed to extract data fields: {e}")

        return data_fields

    def _extract_row_fields(self, pivot) -> List[str]:
        """Extract row fields from pivot table."""
        try:
            if hasattr(pivot, "rowFields") and pivot.rowFields:
                return [
                    getattr(field, "x", i) for i, field in enumerate(pivot.rowFields)
                ]
        except Exception as e:
            logger.warning(f"Failed to extract row fields: {e}")

        return []

    def _extract_column_fields(self, pivot) -> List[str]:
        """Extract column fields from pivot table."""
        try:
            if hasattr(pivot, "colFields") and pivot.colFields:
                return [
                    getattr(field, "x", i) for i, field in enumerate(pivot.colFields)
                ]
        except Exception as e:
            logger.warning(f"Failed to extract column fields: {e}")

        return []

    def _extract_filter_fields(self, pivot) -> List[str]:
        """Extract filter/page fields from pivot table."""
        try:
            if hasattr(pivot, "pageFields") and pivot.pageFields:
                return [
                    getattr(field, "x", i) for i, field in enumerate(pivot.pageFields)
                ]
        except Exception as e:
            logger.warning(f"Failed to extract filter fields: {e}")

        return []

    def _get_pivot_style(self, pivot) -> Dict[str, Any]:
        """Get pivot table styling information."""
        style_info = {}

        try:
            if hasattr(pivot, "pivotTableStyleInfo"):
                style = pivot.pivotTableStyleInfo
                style_info = {
                    "name": getattr(style, "name", None),
                    "show_row_headers": getattr(style, "showRowHeaders", None),
                    "show_col_headers": getattr(style, "showColHeaders", None),
                    "show_row_stripes": getattr(style, "showRowStripes", None),
                    "show_col_stripes": getattr(style, "showColStripes", None),
                }
        except Exception as e:
            logger.warning(f"Failed to extract pivot style: {e}")

        return style_info
