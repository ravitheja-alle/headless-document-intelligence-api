from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Depends,
    HTTPException
)

from app.core.database import get_db

from app.schemas.extraction import ExtractionRequest
from app.schemas.search import QueryRequest

from app.services.parser import DocumentParser
from app.services.embeddings import generate_embeddings
from app.services.extractor import extract_data
from app.services.search import retrieve_relevant_chunks
from app.services.rag import rag_streamer

from app.models.domain import Document, DocumentChunk

import uuid
import logging


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/documents",
    tags=["documents"]
)

parser = DocumentParser()


# ==========================================
# DOCUMENT UPLOAD + VECTORIZATION
# ==========================================

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):

    # Validate extension
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Strictly PDF files are supported."
        )

    file_bytes = await file.read()

    # ==========================================
    # PARSE + CHUNK DOCUMENT
    # ==========================================

    try:
        chunks = parser.process_document(file_bytes)

    # Allow parser validation errors to bubble upward
    except ValueError as ve:
        raise ve

    # Unexpected failures
    except Exception as e:
        logger.error(f"Extraction failed: {str(e)}")

        raise HTTPException(
            status_code=500,
            detail="Failed to extract text from document."
        )

    if not chunks:
        raise HTTPException(
            status_code=400,
            detail="Document contains no extractable text."
        )

    # ==========================================
    # CREATE DOCUMENT RECORD
    # ==========================================

    doc_id = uuid.uuid4()

    new_doc = Document(
        id=doc_id,
        filename=file.filename,
        status="Processing"
    )

    db.add(new_doc)

    # Lock ID before commit
    await db.flush()

    # ==========================================
    # GENERATE EMBEDDINGS
    # ==========================================

    chunk_texts = [c["text_content"] for c in chunks]

    embeddings = []

    batch_size = 100

    try:
        for i in range(0, len(chunk_texts), batch_size):

            batch_texts = chunk_texts[i:i + batch_size]

            batch_embeds = await generate_embeddings(batch_texts)

            embeddings.extend(batch_embeds)

    except Exception as e:

        logger.error(f"Embedding generation failed: {str(e)}")

        new_doc.status = "Failed"

        await db.commit()

        raise HTTPException(
            status_code=502,
            detail="Embedding generation failed at upstream provider."
        )

    # ==========================================
    # STORE CHUNKS
    # ==========================================

    db_chunks = []

    for chunk_data, emb in zip(chunks, embeddings):

        db_chunks.append(
            DocumentChunk(
                document_id=doc_id,
                chunk_index=chunk_data["chunk_index"],
                page_number=chunk_data["page_number"],
                text_content=chunk_data["text_content"],
                embedding=emb
            )
        )

    db.add_all(db_chunks)

    new_doc.status = "Completed"

    # ==========================================
    # COMMIT TRANSACTION
    # ==========================================

    try:
        await db.commit()

    except Exception as e:

        await db.rollback()

        logger.error(f"Database write failed: {str(e)}")

        raise HTTPException(
            status_code=500,
            detail="Database persistence failed."
        )

    return {
        "document_id": str(doc_id),
        "status": "processed",
        "chunks_stored": len(db_chunks)
    }


# ==========================================
# STRUCTURED EXTRACTION
# ==========================================

@router.post("/{document_id}/extract")
async def extract_document_data(
    document_id: uuid.UUID,
    request: ExtractionRequest,
    db: AsyncSession = Depends(get_db)
):

    # Retrieve document chunks
    result = await db.execute(
        select(DocumentChunk.text_content)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
    )

    chunks = result.scalars().all()

    if not chunks:
        raise HTTPException(
            status_code=404,
            detail="Document not found or contains no text."
        )

    # Reconstruct document
    full_text = "\n".join(chunks)

    # Execute extraction
    try:

        extracted_data = await extract_data(
            full_text,
            request.fields,
            request.mock
        )

        return extracted_data

    except Exception as e:

        logger.error(f"Extraction failed: {str(e)}")

        raise HTTPException(
            status_code=502,
            detail="Upstream extraction processing failed."
        )


# ==========================================
# RAG QUERY ENDPOINT
# ==========================================

@router.post("/query")
async def query_documents(
    request: QueryRequest,
    db: AsyncSession = Depends(get_db)
):

    # Execute semantic vector search
    try:

        chunks = await retrieve_relevant_chunks(
            db=db,
            query_text=request.query,
            top_k=request.top_k,
            document_ids=request.document_ids
        )

    except Exception as e:

        logger.error(f"Vector search failed: {str(e)}")

        raise HTTPException(
            status_code=500,
            detail="Vector search execution failed."
        )

    if not chunks:
        raise HTTPException(
            status_code=404,
            detail="No relevant context found in database."
        )

    # Stream RAG response
    return StreamingResponse(
        rag_streamer(request.query, chunks),
        media_type="text/plain"
    )