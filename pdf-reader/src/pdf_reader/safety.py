"""
Safety validation and file guards for PDF Reader MCP Server.

Implements file size limits, path validation, and security constraints
to ensure safe PDF processing operations.
"""

import os
from pathlib import Path
from typing import Union


# Configuration constants
MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024  # 100MB
ALLOWED_EXTENSIONS = {'.pdf'}
# Optional root restriction.
# If ALLOW_ANY_PATH is True (default), absolute paths anywhere on the filesystem are permitted.
# If set to False, paths must remain inside ALLOWED_ROOT.
ALLOWED_ROOT = Path.cwd()  # Base root used only when ALLOW_ANY_PATH is False
ALLOW_ANY_PATH = bool(int(os.environ.get("PDF_READER_ALLOW_ANY_PATH", "1")))


class PDFSafetyError(Exception):
    """Base exception for PDF safety violations."""
    pass


class FileSizeError(PDFSafetyError):
    """Raised when file exceeds size limit."""
    pass


class PathTraversalError(PDFSafetyError):
    """Raised when path attempts to escape allowed root."""
    pass


class UnsupportedFileError(PDFSafetyError):
    """Raised when file type is not supported."""
    pass


def validate_pdf_path(file_path: Union[str, Path]) -> Path:
    """
    Validate PDF file path for safety constraints.
    
    Args:
        file_path: Path to PDF file (string or Path object)
        
    Returns:
        Resolved Path object if valid
        
    Raises:
        PathTraversalError: If path escapes allowed root
        UnsupportedFileError: If file extension not supported
        FileNotFoundError: If file doesn't exist
        FileSizeError: If file exceeds size limit
    """
    # Convert to Path and resolve (expand user and env vars)
    path = Path(os.path.expandvars(os.path.expanduser(str(file_path)))).resolve()

    # Enforce root constraint only if unrestricted access disabled
    if not ALLOW_ANY_PATH and ALLOWED_ROOT is not None:
        try:
            path.relative_to(ALLOWED_ROOT.resolve())
        except ValueError:
            raise PathTraversalError(
                f"Path '{file_path}' is outside allowed root directory (root={ALLOWED_ROOT})"
            )
    # Check file extension
    if path.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise UnsupportedFileError(f"File type '{path.suffix}' not supported. Only PDF files allowed.")
    
    # Check if file exists
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")
    
    # Check if it's actually a file (not directory)
    if not path.is_file():
        raise UnsupportedFileError(f"Path is not a file: {file_path}")
    
    # Check file size
    file_size = path.stat().st_size
    if file_size > MAX_FILE_SIZE_BYTES:
        size_mb = file_size / (1024 * 1024)
        limit_mb = MAX_FILE_SIZE_BYTES / (1024 * 1024)
        raise FileSizeError(f"File size {size_mb:.1f}MB exceeds limit of {limit_mb:.1f}MB")
    
    return path


def check_ocr_available() -> bool:
    """
    OCR functionality has been removed from this server.
    
    Returns:
        Always False as OCR is not supported
    """
    return False


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe usage in responses.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename with dangerous characters removed
    """
    # Remove path separators and other dangerous characters
    dangerous_chars = ['/', '\\', '..', '<', '>', ':', '"', '|', '?', '*']
    sanitized = filename
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, '_')
    
    # Limit length
    if len(sanitized) > 255:
        sanitized = sanitized[:255]
    
    return sanitized


def get_safe_file_info(file_path: Path) -> dict:
    """
    Get safe file information without exposing sensitive paths.
    
    Args:
        file_path: Validated Path object
        
    Returns:
        Dictionary with safe file information
    """
    stat = file_path.stat()
    return {
        "filename": sanitize_filename(file_path.name),
        "size_bytes": stat.st_size,
        "size_mb": round(stat.st_size / (1024 * 1024), 2),
        "modified_time": stat.st_mtime,
        "extension": file_path.suffix.lower()
    }