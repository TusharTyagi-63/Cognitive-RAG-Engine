"""
backend/app/services/chunking_service.py
========================================
Splits large texts into smaller, overlapping chunks for embedding.
"""
from typing import List

from langchain_text_splitters import RecursiveCharacterTextSplitter

class ChunkingService:
    @staticmethod
    def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
        """
        Splits text into chunks using a Recursive Character Text Splitter.
        It tries to split on paragraphs (\n\n), then sentences (.), then spaces ( ).
        This keeps semantic meaning intact without slicing words in half.
        """
        if not text.strip():
            return []
            
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            is_separator_regex=False,
            separators=[
                "\n\n",
                "\n",
                " ",
                "",
            ]
        )
        
        chunks = splitter.split_text(text)
        return chunks
