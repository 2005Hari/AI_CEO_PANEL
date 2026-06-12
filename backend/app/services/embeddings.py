# backend/app/services/embeddings.py
import asyncio
import math
import json
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.core.config import settings
from app.db.models import Memory

class EmbeddingsService:
    def __init__(self):
        self._embeddings = None

    def get_embeddings_client(self) -> GoogleGenerativeAIEmbeddings:
        """Dynamically instantiate the embeddings client only when needed."""
        if self._embeddings is None:
            # We use gemini-embedding-2 with 768 dimensions
            self._embeddings = GoogleGenerativeAIEmbeddings(
                model="models/gemini-embedding-2",
                output_dimensionality=768,
                google_api_key=settings.GEMINI_API_KEY
            )
        return self._embeddings

    async def embed_query(self, text: str) -> List[float]:
        """Embed a single search query."""
        client = self.get_embeddings_client()
        return await client.aembed_query(text)

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of document chunks in parallel using client.aembed_query."""
        client = self.get_embeddings_client()
        tasks = [client.aembed_query(t) for t in texts]
        return await asyncio.gather(*tasks)

# Global service instance
embeddings_service = EmbeddingsService()

def parse_sqlite_vector(vector_val: Any) -> List[float]:
    """Parse SQLite vector representation into a list of floats."""
    if isinstance(vector_val, list):
        return [float(x) for x in vector_val]
    if isinstance(vector_val, str):
        try:
            return [float(x) for x in json.loads(vector_val)]
        except Exception:
            # Clean brackets and split
            cleaned = vector_val.replace("[", "").replace("]", "").replace(" ", "")
            if not cleaned:
                return []
            return [float(x) for x in cleaned.split(",") if x]
    return []

def calculate_cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Compute cosine similarity between two float vectors."""
    if not v1 or not v2:
        return 0.0
    dot_product = sum(x * y for x, y in zip(v1, v2))
    norm_v1 = math.sqrt(sum(x * x for x in v1))
    norm_v2 = math.sqrt(sum(x * x for x in v2))
    if not norm_v1 or not norm_v2:
        return 0.0
    return dot_product / (norm_v1 * norm_v2)

async def similarity_search(
    db: AsyncSession,
    project_id: str,
    query: str,
    limit: int = 3
) -> List[Memory]:
    """
    Performs vector similarity search on startup memories.
    Uses SQLite-compatible Python math fallback or PostgreSQL pgvector native search.
    """
    # 1. Generate query embedding
    query_vector = await embeddings_service.embed_query(query)

    # 2. Check dialect to route queries
    bind = db.bind
    is_sqlite = bind is not None and "sqlite" in str(bind.url).lower()

    if is_sqlite:
        # Load all memories for this project and calculate similarity in Python
        result = await db.execute(select(Memory).where(Memory.project_id == project_id))
        all_memories = result.scalars().all()
        
        scored_memories = []
        for mem in all_memories:
            try:
                mem_vector = parse_sqlite_vector(mem.embedding)
                if mem_vector:
                    score = calculate_cosine_similarity(query_vector, mem_vector)
                    scored_memories.append((mem, score))
            except Exception as e:
                # Log warning or skip malformed vector row
                print(f"Skipping vector parse error: {e}")
                continue

        # Sort descending and return top matches
        scored_memories.sort(key=lambda item: item[1], reverse=True)
        return [item[0] for item in scored_memories[:limit]]

    else:
        # Native pgvector SQL cosine distance query
        # pgvector order_by is cosine_distance (distance = 1 - similarity)
        result = await db.execute(
            select(Memory)
            .where(Memory.project_id == project_id)
            .order_by(Memory.embedding.cosine_distance(query_vector))
            .limit(limit)
        )
        return result.scalars().all()
