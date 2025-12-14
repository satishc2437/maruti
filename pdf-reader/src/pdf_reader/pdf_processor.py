"""
Core PDF processing logic with streaming support.

Handles PDF content extraction including text, images, tables, metadata,
and OCR functionality for scanned documents.
"""

import asyncio
import base64
import io
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Iterator, Tuple
import logging

# PDF processing imports
try:
    import PyPDF2
    import pdfplumber
    from PIL import Image
except ImportError as e:
    raise ImportError(f"Required PDF processing library not installed: {e}")

# Optional pandas import for table processing
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    pd = None

from .safety import validate_pdf_path, check_ocr_available, get_safe_file_info


logger = logging.getLogger(__name__)


class PDFProcessor:
    """Core PDF processing functionality with streaming support."""
    
    def __init__(self):
        self.ocr_available = False  # OCR functionality removed
    
    async def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Extract PDF metadata without processing content.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Dictionary containing PDF metadata
        """
        validated_path = validate_pdf_path(file_path)
        file_info = get_safe_file_info(validated_path)
        
        try:
            # Use PyPDF2 for basic metadata
            with open(validated_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                metadata = {
                    "file_info": file_info,
                    "page_count": len(pdf_reader.pages),
                    "title": None,
                    "author": None,
                    "creator": None,
                    "creation_date": None,
                    "modification_date": None,
                    "encrypted": pdf_reader.is_encrypted
                }
                
                # Extract document info if available
                if pdf_reader.metadata:
                    doc_info = pdf_reader.metadata
                    metadata.update({
                        "title": doc_info.get('/Title'),
                        "author": doc_info.get('/Author'),
                        "creator": doc_info.get('/Creator'),
                        "creation_date": str(doc_info.get('/CreationDate')),
                        "modification_date": str(doc_info.get('/ModDate'))
                    })
                
                return metadata
                
        except Exception as e:
            logger.error(f"Error extracting metadata from {file_path}: {e}")
            raise
    
    async def extract_page_text_preview(self, file_path: str, start_page: int = 1, 
                                       end_page: Optional[int] = None, 
                                       preview_length: int = 200) -> List[Dict[str, Any]]:
        """
        Extract text preview from specific pages.
        
        Args:
            file_path: Path to PDF file
            start_page: Starting page (1-indexed)
            end_page: Ending page (1-indexed), None for all pages
            preview_length: Maximum characters per page preview
            
        Returns:
            List of page previews with page numbers and text
        """
        validated_path = validate_pdf_path(file_path)
        
        try:
            with pdfplumber.open(validated_path) as pdf:
                total_pages = len(pdf.pages)
                
                if end_page is None:
                    end_page = total_pages
                
                # Validate page ranges
                start_page = max(1, min(start_page, total_pages))
                end_page = max(start_page, min(end_page, total_pages))
                
                pages_preview = []
                
                for page_num in range(start_page - 1, end_page):  # Convert to 0-indexed
                    page = pdf.pages[page_num]
                    text = page.extract_text() or ""
                    
                    # Create preview
                    preview = text[:preview_length]
                    if len(text) > preview_length:
                        preview += "..."
                    
                    pages_preview.append({
                        "page_number": page_num + 1,
                        "text_preview": preview,
                        "full_text_length": len(text),
                        "has_more": len(text) > preview_length
                    })
                
                return pages_preview
                
        except Exception as e:
            logger.error(f"Error extracting page previews from {file_path}: {e}")
            raise
    
    async def extract_full_content(self, file_path: str, pages: Optional[List[int]] = None,
                                  include_images: bool = True, include_tables: bool = True,
                                  use_ocr: bool = False) -> Dict[str, Any]:
        """
        Extract complete PDF content including text, images, and tables.
        
        Args:
            file_path: Path to PDF file
            pages: Specific pages to extract (1-indexed), None for all
            include_images: Whether to extract images
            include_tables: Whether to extract tables
            use_ocr: Not supported (parameter ignored)
            
        Returns:
            Complete content extraction results
        """
        validated_path = validate_pdf_path(file_path)
        
        if use_ocr:
            logger.warning("OCR functionality not available in this server")
            use_ocr = False
        
        try:
            result = {
                "metadata": await self.extract_metadata(file_path),
                "pages": [],
                "images": [] if include_images else None,
                "tables": [] if include_tables else None,
                "processing_info": {
                    "ocr_used": use_ocr,
                    "images_extracted": include_images,
                    "tables_extracted": include_tables
                }
            }
            
            with pdfplumber.open(validated_path) as pdf:
                total_pages = len(pdf.pages)
                
                # Determine pages to process
                if pages is None:
                    pages_to_process = list(range(1, total_pages + 1))
                else:
                    pages_to_process = [p for p in pages if 1 <= p <= total_pages]
                
                for page_num in pages_to_process:
                    page = pdf.pages[page_num - 1]  # Convert to 0-indexed
                    
                    # Extract text
                    text = page.extract_text() or ""
                    
                    page_data = {
                        "page_number": page_num,
                        "text": text,
                        "bbox": page.bbox,  # Page dimensions
                        "rotation": getattr(page, 'rotation', 0)
                    }
                    
                    # Extract tables from this page
                    if include_tables:
                        try:
                            tables = page.extract_tables()
                            page_tables = []
                            for i, table in enumerate(tables):
                                if table:  # Skip empty tables
                                    table_data = {
                                        "page_number": page_num,
                                        "table_index": i,
                                        "data": table,
                                        "rows": len(table),
                                        "columns": len(table[0]) if table else 0
                                    }
                                    page_tables.append(table_data)
                                    result["tables"].append(table_data)
                            
                            page_data["tables_count"] = len(page_tables)
                        except Exception as e:
                            logger.warning(f"Table extraction failed for page {page_num}: {e}")
                            page_data["tables_count"] = 0
                    
                    result["pages"].append(page_data)
                
                # Extract images using PyPDF2
                if include_images:
                    await self._extract_images(validated_path, result, pages_to_process)
            
            return result
            
        except Exception as e:
            logger.error(f"Error extracting content from {file_path}: {e}")
            raise
    
    async def _extract_images(self, file_path: Path, result: Dict[str, Any], 
                             pages_to_process: List[int]) -> None:
        """Extract images from PDF and add to result."""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page_num in pages_to_process:
                    if page_num - 1 >= len(pdf_reader.pages):
                        continue
                        
                    page = pdf_reader.pages[page_num - 1]
                    
                    if '/XObject' in page['/Resources']:
                        xObject = page['/Resources']['/XObject'].get_object()
                        
                        for obj_name in xObject:
                            obj = xObject[obj_name]
                            
                            if obj['/Subtype'] == '/Image':
                                try:
                                    # Extract image data
                                    if '/Filter' in obj:
                                        if obj['/Filter'] == '/DCTDecode':
                                            # JPEG image
                                            img_data = obj._data
                                            img_base64 = base64.b64encode(img_data).decode()
                                            
                                            image_info = {
                                                "page_number": page_num,
                                                "object_name": obj_name,
                                                "format": "JPEG",
                                                "width": obj.get('/Width'),
                                                "height": obj.get('/Height'),
                                                "data": img_base64,
                                                "size_bytes": len(img_data)
                                            }
                                            
                                            result["images"].append(image_info)
                                            
                                except Exception as e:
                                    logger.warning(f"Failed to extract image {obj_name} from page {page_num}: {e}")
                                    
        except Exception as e:
            logger.warning(f"Image extraction failed: {e}")
    
    async def stream_content_extraction(self, file_path: str, 
                                       send_event: callable,
                                       pages: Optional[List[int]] = None,
                                       include_images: bool = True,
                                       include_tables: bool = True,
                                       use_ocr: bool = False) -> Dict[str, Any]:
        """
        Stream PDF content extraction with progress updates.
        
        Args:
            file_path: Path to PDF file
            send_event: Async function to send streaming events
            pages: Specific pages to extract
            include_images: Whether to extract images
            include_tables: Whether to extract tables
            use_ocr: Whether to use OCR
            
        Returns:
            Final extraction summary
        """
        validated_path = validate_pdf_path(file_path)
        
        # Send start event
        metadata = await self.extract_metadata(file_path)
        total_pages = metadata["page_count"]
        
        if pages is None:
            pages_to_process = list(range(1, total_pages + 1))
        else:
            pages_to_process = [p for p in pages if 1 <= p <= total_pages]
        
        await send_event({
            "type": "start",
            "total_pages": len(pages_to_process),
            "file_info": metadata["file_info"],
            "processing_options": {
                "include_images": include_images,
                "include_tables": include_tables,
                "use_ocr": use_ocr and self.ocr_available
            }
        })
        
        # Process pages with streaming
        processed_pages = []
        extracted_tables = []
        extracted_images = []
        
        try:
            with pdfplumber.open(validated_path) as pdf:
                for i, page_num in enumerate(pages_to_process):
                    # Cooperative yield
                    await asyncio.sleep(0)
                    
                    page = pdf.pages[page_num - 1]
                    
                    # Extract page content
                    text = page.extract_text() or ""
                    
                    page_data = {
                        "page_number": page_num,
                        "text": text,
                        "text_length": len(text)
                    }
                    
                    # Extract tables
                    if include_tables:
                        try:
                            tables = page.extract_tables()
                            page_table_count = 0
                            for table_idx, table in enumerate(tables):
                                if table:
                                    table_data = {
                                        "page_number": page_num,
                                        "table_index": table_idx,
                                        "rows": len(table),
                                        "columns": len(table[0]) if table else 0,
                                        "data": table[:5]  # Preview only in stream
                                    }
                                    extracted_tables.append(table_data)
                                    page_table_count += 1
                            
                            page_data["tables_count"] = page_table_count
                        except Exception:
                            page_data["tables_count"] = 0
                    
                    processed_pages.append(page_data)
                    
                    # Send progress event
                    await send_event({
                        "type": "progress",
                        "page_completed": page_num,
                        "pages_processed": i + 1,
                        "total_pages": len(pages_to_process),
                        "page_data": page_data
                    })
            
            # Extract images if requested (separate pass)
            if include_images:
                await send_event({"type": "status", "message": "Extracting images..."})
                # Simplified image extraction for streaming
                with open(validated_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    image_count = 0
                    
                    for page_num in pages_to_process:
                        if page_num - 1 < len(pdf_reader.pages):
                            page = pdf_reader.pages[page_num - 1]
                            if '/XObject' in page.get('/Resources', {}):
                                xObject = page['/Resources']['/XObject'].get_object()
                                for obj_name in xObject:
                                    obj = xObject[obj_name]
                                    if obj.get('/Subtype') == '/Image':
                                        image_count += 1
                    
                    extracted_images = [{"total_images_found": image_count}]
            
            # Send completion event
            summary = {
                "pages_processed": len(processed_pages),
                "tables_found": len(extracted_tables),
                "images_found": len(extracted_images),
                "total_text_length": sum(len(p.get("text", "")) for p in processed_pages)
            }
            
            await send_event({
                "type": "complete",
                "summary": summary
            })
            
            return {
                "success": True,
                "summary": summary,
                "metadata": metadata
            }
            
        except Exception as e:
            await send_event({
                "type": "error",
                "message": str(e)
            })
            raise