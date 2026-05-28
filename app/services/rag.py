import json
from typing import List
from app.models.domain import DocumentChunk

async def rag_streamer(query: str, chunks: List[DocumentChunk]):

    # Build simple mock answer
    yield f"MOCK RAG RESPONSE\n\n"

    yield f"User Query:\n{query}\n\n"

    yield "Relevant Context Found:\n\n"

    citations = []

    for c in chunks:
        preview = c.text_content[:300]

        yield f"[Page {c.page_number}] {preview}\n\n"

        citations.append({
            "document_id": str(c.document_id),
            "page": c.page_number,
            "chunk_index": c.chunk_index
        })

    yield f"\n__CITATIONS__\n{json.dumps(citations)}"