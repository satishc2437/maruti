"""
Safety utilities for file operations and validation.
Provides backup, file locking, and size validation functionality.
"""

import os
import shutil
from pathlib import Path
from typing import Optional
import logging
from filelock import FileLock

from .errors import FileAccessError, ValidationError

logger = logging.getLogger(__name__)

# Configuration constants
MAX_FILE_SIZE_BYTES = 200 * 1024 * 1024  # 200MB default
BACKUP_SUFFIX = ".backup"


def validate_file_path(file_path: str) -> Path:
    """
    Validate that a file path exists and is accessible.

    Args:
        file_path: Path to validate

    Returns:
        Resolved Path object

    Raises:
        ValidationError: If path is invalid
        FileAccessError: If file is not accessible
    """
    if not file_path or not isinstance(file_path, str):
        raise ValidationError("File path must be a non-empty string")

    try:
        path = Path(file_path).resolve()
    except Exception as e:
        raise ValidationError(f"Invalid file path: {e}")

    if not path.exists():
        raise FileAccessError(f"File does not exist: {file_path}")

    if not path.is_file():
        raise FileAccessError(f"Path is not a file: {file_path}")

    return path


def validate_file_size(file_path: Path, max_size: Optional[int] = None) -> None:
    """
    Validate that file size is within acceptable limits.

    Args:
        file_path: Path to check
        max_size: Maximum size in bytes (default: MAX_FILE_SIZE_BYTES)

    Raises:
        ValidationError: If file is too large
    """
    max_size = max_size or MAX_FILE_SIZE_BYTES

    try:
        size = file_path.stat().st_size
        if size > max_size:
            raise ValidationError(
                f"File too large: {size} bytes (max: {max_size} bytes)"
            )
    except OSError as e:
        raise FileAccessError(f"Cannot read file size: {e}")


def validate_excel_file(file_path: str) -> Path:
    """
    Validate that a file is a readable Excel file.

    Args:
        file_path: Path to validate

    Returns:
        Validated Path object

    Raises:
        ValidationError: If not a valid Excel file
        FileAccessError: If file is not accessible
    """
    path = validate_file_path(file_path)

    # Check file extension
    valid_extensions = {".xlsx", ".xlsm", ".xltx", ".xltm"}
    if path.suffix.lower() not in valid_extensions:
        raise ValidationError(
            f"Invalid Excel file extension: {path.suffix}. "
            f"Supported: {', '.join(valid_extensions)}"
        )

    validate_file_size(path)

    return path


def create_backup(file_path: Path) -> Path:
    """
    Create a backup copy of a file before modification.

    Args:
        file_path: Path to backup

    Returns:
        Path to backup file

    Raises:
        FileAccessError: If backup creation fails
    """
    backup_path = file_path.with_suffix(file_path.suffix + BACKUP_SUFFIX)

    try:
        shutil.copy2(file_path, backup_path)
        logger.info(f"Created backup: {backup_path}")
        return backup_path
    except Exception as e:
        raise FileAccessError(f"Failed to create backup: {e}")


def restore_backup(original_path: Path, backup_path: Optional[Path] = None) -> None:
    """
    Restore a file from its backup.

    Args:
        original_path: Path to restore to
        backup_path: Backup file path (auto-detected if None)

    Raises:
        FileAccessError: If restore fails
    """
    if backup_path is None:
        backup_path = original_path.with_suffix(original_path.suffix + BACKUP_SUFFIX)

    if not backup_path.exists():
        raise FileAccessError(f"Backup file not found: {backup_path}")

    try:
        shutil.copy2(backup_path, original_path)
        logger.info(f"Restored from backup: {backup_path}")
    except Exception as e:
        raise FileAccessError(f"Failed to restore backup: {e}")


def cleanup_backup(backup_path: Path) -> None:
    """
    Remove a backup file.

    Args:
        backup_path: Path to backup file to remove
    """
    try:
        if backup_path.exists():
            backup_path.unlink()
            logger.debug(f"Removed backup: {backup_path}")
    except Exception as e:
        logger.warning(f"Failed to remove backup {backup_path}: {e}")


class FileOperationContext:
    """
    Context manager for safe file operations with backup and locking.
    """

    def __init__(self, file_path: str, create_backup: bool = True):
        self.file_path = validate_excel_file(file_path)
        self.create_backup = create_backup
        self.backup_path: Optional[Path] = None
        self.lock_path = self.file_path.with_suffix(".lock")
        self.file_lock: Optional[FileLock] = None

    def __enter__(self) -> Path:
        """Enter the context - acquire lock and create backup."""
        try:
            # Acquire file lock
            self.file_lock = FileLock(self.lock_path, timeout=10)
            self.file_lock.acquire()
            logger.debug(f"Acquired lock: {self.lock_path}")

            # Create backup if requested
            if self.create_backup:
                self.backup_path = create_backup(self.file_path)

            return self.file_path

        except Exception as e:
            self._cleanup()
            raise FileAccessError(f"Failed to acquire file access: {e}")

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the context - release lock and cleanup."""
        try:
            # If an exception occurred and we have a backup, restore it
            if exc_type is not None and self.backup_path:
                logger.warning("Operation failed, restoring backup")
                restore_backup(self.file_path, self.backup_path)

            # Clean up backup on success
            elif exc_type is None and self.backup_path:
                cleanup_backup(self.backup_path)

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        finally:
            self._cleanup()

    def _cleanup(self) -> None:
        """Release resources."""
        if self.file_lock:
            try:
                self.file_lock.release()
                logger.debug(f"Released lock: {self.lock_path}")
            except Exception as e:
                logger.error(f"Failed to release lock: {e}")


def validate_sheet_name(sheet_name: str) -> str:
    """
    Validate worksheet name according to Excel rules.

    Args:
        sheet_name: Name to validate

    Returns:
        Validated sheet name

    Raises:
        ValidationError: If name is invalid
    """
    if not sheet_name or not isinstance(sheet_name, str):
        raise ValidationError("Sheet name must be a non-empty string")

    if len(sheet_name) > 31:
        raise ValidationError("Sheet name cannot exceed 31 characters")

    # Excel forbidden characters
    forbidden_chars = ["\\", "/", "?", "*", "[", "]", ":"]
    for char in forbidden_chars:
        if char in sheet_name:
            raise ValidationError(
                f"Sheet name cannot contain '{char}'. "
                f"Forbidden characters: {', '.join(forbidden_chars)}"
            )

    return sheet_name.strip()


def validate_cell_reference(cell_ref: str) -> str:
    """
    Validate Excel cell reference format.

    Args:
        cell_ref: Cell reference (e.g., "A1", "B2:D4")

    Returns:
        Validated cell reference

    Raises:
        ValidationError: If reference is invalid
    """
    if not cell_ref or not isinstance(cell_ref, str):
        raise ValidationError("Cell reference must be a non-empty string")

    # Basic validation - could be enhanced with regex
    cell_ref = cell_ref.strip().upper()

    if ":" in cell_ref:
        # Range reference
        parts = cell_ref.split(":")
        if len(parts) != 2:
            raise ValidationError("Invalid range reference format")
        for part in parts:
            _validate_single_cell(part.strip())
    else:
        # Single cell reference
        _validate_single_cell(cell_ref)

    return cell_ref


def _validate_single_cell(cell_ref: str) -> None:
    """Validate a single cell reference like A1."""
    if not cell_ref:
        raise ValidationError("Empty cell reference")

    # Simple check for basic format (letters followed by numbers)
    import re

    if not re.match(r"^[A-Z]+[0-9]+$", cell_ref):
        raise ValidationError(f"Invalid cell reference format: {cell_ref}")
