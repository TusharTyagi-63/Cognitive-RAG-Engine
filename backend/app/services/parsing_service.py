"""
backend/app/services/parsing_service.py
=======================================
Extracts plain text from raw files stored on disk.
"""
import csv
from pathlib import Path
from typing import Optional

import pymupdf

from backend.app.utils.exceptions import BadRequestException

class ParsingService:
    @staticmethod
    def extract_text(file_path: Path, content_type: str) -> str:
        """
        Routes the file to the correct parser based on MIME type or extension.
        Returns the extracted plain text as a single string.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Fallback to extension if content type is generic or missing
        ext = file_path.suffix.lower()

        try:
            if content_type == "application/pdf" or ext == ".pdf":
                return ParsingService._parse_pdf(file_path)
            elif content_type in ["text/csv", "application/csv"] or ext == ".csv":
                return ParsingService._parse_csv(file_path)
            elif content_type == "text/markdown" or ext == ".md":
                return ParsingService._parse_text(file_path)
            elif content_type == "text/plain" or ext == ".txt":
                return ParsingService._parse_text(file_path)
            else:
                # Attempt standard text decoding for unknown formats
                return ParsingService._parse_text(file_path)
        except Exception as e:
            raise BadRequestException(f"Failed to parse file: {str(e)}")

    @staticmethod
    def _parse_pdf(file_path: Path) -> str:
        """Extracts text from a PDF file using PyMuPDF."""
        text_blocks = []
        with pymupdf.open(file_path) as doc:
            for page in doc:
                text_blocks.append(page.get_text())
        return "\n\n".join(text_blocks)

    @staticmethod
    def _parse_csv(file_path: Path) -> str:
        """Extracts text from a CSV file, formatting it cleanly."""
        lines = []
        with open(file_path, mode='r', encoding='utf-8', errors='replace') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                # Join non-empty cells with a tab or comma for readable text
                lines.append(" | ".join([cell.strip() for cell in row if cell.strip()]))
        return "\n".join(lines)

    @staticmethod
    def _parse_text(file_path: Path) -> str:
        """Reads plain text, markdown, or code files."""
        with open(file_path, mode='r', encoding='utf-8', errors='replace') as f:
            return f.read()
