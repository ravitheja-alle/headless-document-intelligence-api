import logging
from typing import List
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Load local embedding model once
model = SentenceTransformer("all-MiniLM-L6-v2")

async def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Generate local embeddings using sentence-transformers.
    Returns 384-dimensional vectors.
    """
    if not texts:
        return []

    try:
        embeddings = model.encode(texts, convert_to_numpy=True)
        return [embedding.tolist() for embedding in embeddings]

    except Exception as e:
        logger.error(f"Local embedding error: {str(e)}")
        raise