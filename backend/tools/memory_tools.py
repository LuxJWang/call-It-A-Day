from typing import List, Dict, Any
from embeddings import embedding_store


def search_memories(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Search for relevant memories based on a query.

    Args:
        query: The search query
        limit: Maximum number of results to return

    Returns:
        List of matching memories with content and metadata
    """
    results = embedding_store.search_similar(query, n_results=limit)
    return results


def add_memory(content: str, metadata: Dict[str, Any] = None) -> str:
    """
    Add a new memory to the vector store.

    Args:
        content: The content to remember
        metadata: Optional metadata about the memory

    Returns:
        The ID of the stored memory
    """
    from datetime import datetime
    import uuid

    memory_id = str(uuid.uuid4())
    meta = metadata or {}
    meta["created_at"] = datetime.utcnow().isoformat()

    embedding_store.add_entry(memory_id, content, meta)
    return memory_id
