"""
backend/app/services/parsing_service.py
=======================================
Extracts plain text from raw files stored on disk.

Supports: PDF, DOCX, PPTX, XLSX, CSV, HTML, XML, JSON, RTF,
          Images (via Gemini Vision AI), Markdown, plain text,
          and all common source code / config formats.
"""
import csv
import json
from pathlib import Path

import pymupdf

from backend.app.utils.exceptions import BadRequestException


# Extensions that can be read as plain text (source code, configs, logs)
_TEXT_EXTENSIONS = {
    ".txt", ".md", ".py", ".js", ".ts", ".java", ".c", ".cpp", ".go",
    ".rs", ".rb", ".php", ".sh", ".sql", ".yaml", ".yml", ".toml",
    ".ini", ".cfg", ".log",
}

# Image extensions — parsed via Gemini Vision AI
_IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff", ".tif", ".svg",
}


class ParsingService:
    @staticmethod
    def extract_text(file_path: Path, content_type: str = "", original_filename: str = None) -> str:
        """
        Routes the file to the correct parser based on MIME type, original filename, or magic bytes.
        Returns the extracted plain text as a single string.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # 1. Determine extension from original filename or file path
        ext = ""
        if original_filename:
            ext = Path(original_filename).suffix.lower()
        if not ext and file_path.suffix:
            ext = file_path.suffix.lower()

        # 2. Magic byte detection for extensionless files on disk
        if not ext:
            try:
                with open(file_path, "rb") as f:
                    header = f.read(16)
                    if header.startswith(b"%PDF-"):
                        ext = ".pdf"
                    elif header.startswith(b"\x89PNG"):
                        ext = ".png"
                    elif header.startswith(b"\xff\xd8\xff"):
                        ext = ".jpg"
                    elif header.startswith(b"PK\x03\x04"):
                        ct = (content_type or "").lower()
                        if "sheet" in ct or "excel" in ct:
                            ext = ".xlsx"
                        elif "presentation" in ct or "powerpoint" in ct:
                            ext = ".pptx"
                        else:
                            ext = ".docx"
            except Exception:
                pass

        ct = (content_type or "").lower()

        try:
            # ── PDF ──────────────────────────────────────────────────────
            if ext == ".pdf" or "pdf" in ct:
                return ParsingService._parse_pdf(file_path)

            # ── Microsoft Office ─────────────────────────────────────────
            if ext == ".docx" or "word" in ct:
                return ParsingService._parse_docx(file_path)

            if ext == ".pptx" or "presentation" in ct or "powerpoint" in ct:
                return ParsingService._parse_pptx(file_path)

            if ext in (".xlsx", ".xls") or "spreadsheet" in ct or "excel" in ct:
                return ParsingService._parse_xlsx(file_path)

            # ── CSV ──────────────────────────────────────────────────────
            if ext == ".csv" or "csv" in ct:
                return ParsingService._parse_csv(file_path)

            # ── HTML ─────────────────────────────────────────────────────
            if ext in (".html", ".htm") or "html" in ct:
                return ParsingService._parse_html(file_path)

            # ── XML ──────────────────────────────────────────────────────
            if ext == ".xml" or "xml" in ct:
                return ParsingService._parse_xml(file_path)

            # ── JSON ─────────────────────────────────────────────────────
            if ext == ".json" or "json" in ct:
                return ParsingService._parse_json(file_path)

            # ── RTF ──────────────────────────────────────────────────────
            if ext == ".rtf" or "rtf" in ct:
                return ParsingService._parse_rtf(file_path)

            # ── Images (Gemini Vision AI) ────────────────────────────────
            if ext in _IMAGE_EXTENSIONS or ct.startswith("image/"):
                return ParsingService._parse_image(file_path)

            # ── Plain text / source code / config ────────────────────────
            if ext in _TEXT_EXTENSIONS or ct.startswith("text/"):
                return ParsingService._parse_text(file_path)

            # ── Fallback: attempt plain text ─────────────────────────────
            return ParsingService._parse_text(file_path)

        except BadRequestException:
            raise
        except Exception as e:
            raise BadRequestException(f"Failed to parse file: {str(e)}")

    # ──────────────────────────────────────────────────────────────────────
    # Individual Parsers
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_pdf(file_path: Path) -> str:
        """Extracts text from a PDF file using PyMuPDF."""
        text_blocks = []
        with pymupdf.open(file_path) as doc:
            for page in doc:
                text_blocks.append(page.get_text())
        return "\n\n".join(text_blocks)

    @staticmethod
    def _parse_docx(file_path: Path) -> str:
        """Extracts text from a Word (.docx) file including paragraphs and tables."""
        from docx import Document

        doc = Document(str(file_path))
        parts = []

        # Extract paragraphs
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                parts.append(text)

        # Extract tables
        for table in doc.tables:
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if cells:
                    parts.append(" | ".join(cells))

        return "\n\n".join(parts)

    @staticmethod
    def _parse_pptx(file_path: Path) -> str:
        """Extracts text from a PowerPoint (.pptx) file, slide by slide."""
        from pptx import Presentation

        prs = Presentation(str(file_path))
        parts = []

        for slide_num, slide in enumerate(prs.slides, 1):
            slide_texts = []
            for shape in slide.shapes:
                if shape.has_text_frame:
                    for paragraph in shape.text_frame.paragraphs:
                        text = paragraph.text.strip()
                        if text:
                            slide_texts.append(text)

                # Extract text from tables inside slides
                if shape.has_table:
                    for row in shape.table.rows:
                        cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                        if cells:
                            slide_texts.append(" | ".join(cells))

            if slide_texts:
                parts.append(f"--- Slide {slide_num} ---\n" + "\n".join(slide_texts))

        return "\n\n".join(parts)

    @staticmethod
    def _parse_xlsx(file_path: Path) -> str:
        """Extracts text from an Excel (.xlsx) file, sheet by sheet."""
        from openpyxl import load_workbook

        wb = load_workbook(str(file_path), read_only=True, data_only=True)
        parts = []

        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            sheet_lines = [f"--- Sheet: {sheet_name} ---"]

            for row in ws.iter_rows(values_only=True):
                cells = [str(cell).strip() for cell in row if cell is not None and str(cell).strip()]
                if cells:
                    sheet_lines.append(" | ".join(cells))

            if len(sheet_lines) > 1:  # More than just the header
                parts.append("\n".join(sheet_lines))

        wb.close()
        return "\n\n".join(parts)

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
    def _parse_html(file_path: Path) -> str:
        """Extracts readable text from an HTML file, stripping tags."""
        from bs4 import BeautifulSoup

        with open(file_path, mode='r', encoding='utf-8', errors='replace') as f:
            soup = BeautifulSoup(f.read(), 'lxml')

        # Remove script and style elements
        for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
            tag.decompose()

        return soup.get_text(separator='\n', strip=True)

    @staticmethod
    def _parse_xml(file_path: Path) -> str:
        """Extracts text content from an XML file."""
        from bs4 import BeautifulSoup

        with open(file_path, mode='r', encoding='utf-8', errors='replace') as f:
            soup = BeautifulSoup(f.read(), 'lxml-xml')

        return soup.get_text(separator='\n', strip=True)

    @staticmethod
    def _parse_json(file_path: Path) -> str:
        """Pretty-prints a JSON file for AI readability."""
        with open(file_path, mode='r', encoding='utf-8', errors='replace') as f:
            data = json.load(f)
        return json.dumps(data, indent=2, ensure_ascii=False)

    @staticmethod
    def _parse_rtf(file_path: Path) -> str:
        """Extracts plain text from an RTF file."""
        from striprtf.striprtf import rtf_to_text

        with open(file_path, mode='r', encoding='utf-8', errors='replace') as f:
            rtf_content = f.read()
        return rtf_to_text(rtf_content)

    @staticmethod
    def _parse_text(file_path: Path) -> str:
        """Reads plain text, markdown, source code, or config files."""
        with open(file_path, mode='r', encoding='utf-8', errors='replace') as f:
            return f.read()

    @staticmethod
    def _parse_image(file_path: Path) -> str:
        """
        Extracts text and descriptions from an image using Google Gemini Vision.
        This handles text extraction (OCR), diagram reading, chart analysis,
        and general image description — far superior to traditional OCR.
        """
        import base64
        import mimetypes
        from openai import OpenAI
        from backend.app.core.config import settings

        if not settings.GEMINI_API_KEY:
            raise BadRequestException("GEMINI_API_KEY is not configured. Cannot process images.")

        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type or not mime_type.startswith("image/"):
            mime_type = "image/jpeg"

        with open(file_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')

        client = OpenAI(
            api_key=settings.GEMINI_API_KEY,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )

        prompt = (
            "Analyze this image thoroughly. Extract ALL text visible in the image exactly as written. "
            "If the image contains diagrams, charts, tables, or figures, describe them in detail "
            "including all data points, labels, and relationships. "
            "If it's a screenshot of code, extract the code exactly. "
            "If it's a photograph, describe what you see in detail. "
            "Format the output as clean, readable text."
        )

        response = client.chat.completions.create(
            model="gemini-3.6-flash",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=2048
        )

        return response.choices[0].message.content
