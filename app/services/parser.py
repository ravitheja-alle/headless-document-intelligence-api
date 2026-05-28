import io
import logging
from typing import List, Dict, Any

import fitz  # PyMuPDF
import pdfplumber
import pytesseract
import tiktoken
from PIL import Image

# Explicit Windows path for Tesseract OCR
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

logger = logging.getLogger(__name__)


class DocumentParser:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # Tokenizer for OpenAI embedding + GPT models
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def clean_text(self, text: str) -> str:
        """
        Basic text cleanup for extracted/OCR content.
        Removes excessive whitespace and line breaks.
        """
        return " ".join(text.split())

    def extract_text(self, file_bytes: bytes) -> List[Dict[str, Any]]:
        extracted_pages = []
        
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")

        except Exception as e:
            logger.error(f"PDF parsing failed: {str(e)}")

            raise ValueError(
                "The provided file is not a valid or readable PDF."
            )

        if doc.needs_pass:
            doc.close()
            logger.error("Encrypted PDF rejected.")
            raise ValueError("Encrypted PDFs are not supported. Please remove the password protection.")

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text").strip()
            
            if len(text) < 50:
                logger.warning(f"Page {page_num + 1} has insufficient text. Triggering OCR fallback.")
                text = self._extract_ocr(file_bytes, page_num)
            
            extracted_pages.append({
                "page_number": page_num + 1,
                "text": text
            })
            
        doc.close()
        return extracted_pages

    def _extract_ocr(self, file_bytes: bytes, page_index: int) -> str:
        """
        Convert PDF page to image and run OCR using Tesseract.
        """
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                page = pdf.pages[page_index]

                # Render page as image
                image = page.to_image(resolution=300)

                # OCR extraction
                text = pytesseract.image_to_string(image.original)

                return self.clean_text(text)

        except Exception as e:
            logger.error(
                f"OCR failed on page {page_index + 1}: {str(e)}"
            )
            return ""

    def chunk_document(
        self, pages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Split extracted text into overlapping token-aware chunks.
        """
        chunks = []
        chunk_index = 0

        for page in pages:
            page_num = page["page_number"]
            text = page["text"]

            if not text:
                continue

            # Encode text into tokens
            tokens = self.tokenizer.encode(text)
            total_tokens = len(tokens)

            start = 0

            while start < total_tokens:
                end = min(start + self.chunk_size, total_tokens)

                # Slice token window
                chunk_tokens = tokens[start:end]

                # Decode back to text
                chunk_text = self.tokenizer.decode(chunk_tokens)

                chunks.append(
                    {
                        "chunk_index": chunk_index,
                        "page_number": page_num,
                        "text_content": chunk_text,
                        "token_count": len(chunk_tokens),
                    }
                )

                chunk_index += 1

                # Move forward with overlap
                start += (self.chunk_size - self.chunk_overlap)

                # Prevent tiny trailing chunks
                if start >= total_tokens:
                    break

        return chunks

    def process_document(self, file_bytes: bytes) -> List[Dict[str, Any]]:
        """
        Full parsing pipeline:
        PDF -> Extraction -> OCR fallback -> Cleaning -> Chunking
        """
        pages = self.extract_text(file_bytes)

        logger.info(f"Extracted {len(pages)} pages successfully.")

        chunks = self.chunk_document(pages)

        logger.info(f"Generated {len(chunks)} chunks successfully.")

        return chunks