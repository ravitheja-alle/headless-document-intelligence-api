from typing import List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.domain import DocumentChunk
from app.services.embeddings import generate_embeddings

async def retrieve_relevant_chunks(
    db: AsyncSession, 
    query_text: str, 
    top_k: int, 
    document_ids: Optional[List[UUID]] = None
) -> List[DocumentChunk]:
    
    # 1. Embed the search query using the identical model
    query_vector = (await generate_embeddings([query_text]))[0]

    # 2. Build the vector search statement (Cosine Distance)
    stmt = select(DocumentChunk).order_by(
        DocumentChunk.embedding.cosine_distance(query_vector)
    ).limit(top_k)

    # 3. Apply optional document filtering
    if document_ids:
        stmt = stmt.where(DocumentChunk.document_id.in_(document_ids))

    result = await db.execute(stmt)
    return result.scalars().all()