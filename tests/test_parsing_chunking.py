"""
tests/test_parsing_chunking.py
==============================
Tests for document parsing and text chunking logic.
"""
import os
import tempfile
from pathlib import Path

import pymupdf
import pytest

from backend.app.services.parsing_service import ParsingService
from backend.app.services.chunking_service import ChunkingService

@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)

def test_parse_text(temp_dir: Path):
    file_path = temp_dir / "test.txt"
    file_path.write_text("Hello World! This is a simple text file.", encoding="utf-8")
    
    text = ParsingService.extract_text(file_path, "text/plain")
    assert text == "Hello World! This is a simple text file."

def test_parse_csv(temp_dir: Path):
    file_path = temp_dir / "test.csv"
    file_path.write_text("Name,Age,City\nAlice,30,New York\nBob, 25 , Los Angeles ", encoding="utf-8")
    
    text = ParsingService.extract_text(file_path, "text/csv")
    assert "Name | Age | City" in text
    assert "Alice | 30 | New York" in text
    assert "Bob | 25 | Los Angeles" in text

def test_parse_pdf(temp_dir: Path):
    file_path = temp_dir / "test.pdf"
    
    # Generate a dummy PDF
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 50), "This is a dummy PDF file.\nIt has multiple lines.")
    doc.save(file_path)
    doc.close()
    
    text = ParsingService.extract_text(file_path, "application/pdf")
    assert "This is a dummy PDF file." in text
    assert "It has multiple lines." in text

def test_parse_missing_file():
    with pytest.raises(FileNotFoundError):
        ParsingService.extract_text(Path("does_not_exist.txt"), "text/plain")

def test_chunking_service_empty():
    chunks = ChunkingService.chunk_text("")
    assert chunks == []
    
    chunks = ChunkingService.chunk_text("   \n  ")
    assert chunks == []

def test_chunking_service_size():
    # Generate a large string
    sentence = "This is a sample sentence that we will repeat to create a large text block. "
    text = sentence * 100  # 7600 characters
    
    chunks = ChunkingService.chunk_text(text, chunk_size=1000, chunk_overlap=200)
    
    # Check that we got multiple chunks
    assert len(chunks) > 1
    
    # Check that no chunk exceeds the max size
    for chunk in chunks:
        assert len(chunk) <= 1000
        
    # Check that the overlap is working (the first sentence of the second chunk should be in the first chunk)
    assert chunks[0][-100:] in chunks[1] or chunks[1][:100] in chunks[0]
