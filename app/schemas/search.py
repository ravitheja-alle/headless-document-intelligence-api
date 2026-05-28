from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID

class QueryRequest(BaseModel):
    query: str = Field(..., example="What is the liability cap in this contract?")
    document_ids: Optional[List[UUID]] = Field(default=None, description="Limit search to specific documents.")
    top_k: int = Field(5, description="Number of contextual chunks to retrieve.")