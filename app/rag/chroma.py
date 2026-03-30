import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import get_settings

settings = get_settings()

_client = None


def get_chroma_client() -> chromadb.Client:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path="./chroma_db",
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _client


def get_or_create_collection(client_id: str) -> chromadb.Collection:
    client = get_chroma_client()
    collection_name = f"client_{client_id}"
    return client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )


def add_chunks(
    client_id: str,
    chunks: list[str],
    embeddings: list[list[float]],
    document_id: str,
    filename: str,
) -> int:
    collection = get_or_create_collection(client_id)
    ids = [f"{document_id}_{i}" for i in range(len(chunks))]
    metadatas = [{"document_id": document_id, "filename": filename, "chunk_index": i} for i in range(len(chunks))]
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas,
    )
    return len(chunks)


def search_chunks(
    client_id: str,
    query_embedding: list[float],
    top_k: int = 5,
) -> list[str]:
    collection = get_or_create_collection(client_id)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
    )
    if not results["documents"]:
        return []
    return results["documents"][0]