import chromadb

CHROMA_PATH = "chroma_db"
COLLECTION_NAME = "youtube_video_chunks"

client = chromadb.PersistentClient(path=CHROMA_PATH)

collection = client.get_or_create_collection(name=COLLECTION_NAME)


def delete_video_chunks(video_id: str) -> None:
    """
    Deletes existing chunks for a video.
    Useful before re-ingesting the same video.
    """

    existing = collection.get(
        where={"video_id": video_id},
        include=[]
    )

    if existing and existing.get("ids"):
        collection.delete(
            ids=existing["ids"]
        )

        
def video_exists(video_id: str) -> bool:
    """
    Checks whether chunks already exist for a video.
    """
    results = collection.get(
        where={"video_id": video_id},
        include=[],
        limit=1
    )

    return bool(results.get("ids"))

def store_chunks(video_id: str, chunks: list[dict], embeddings: list[list[float]]) -> None:
    """
    Stores transcript chunks in Chroma.

    If the same video is ingested again, old chunks are removed first.
    """

    delete_video_chunks(video_id)

    ids = []
    documents = []
    metadatas = []

    for chunk, embedding in zip(chunks, embeddings):
        chunk_id = f"{video_id}_{chunk['chunk_index']}"

        ids.append(chunk_id)
        documents.append(chunk["text"])
        metadatas.append({
            "video_id": video_id,
            "chunk_index": chunk["chunk_index"],
            "start_time": chunk["start_time"],
            "end_time": chunk["end_time"]
        })

    collection.add(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas
    )


def retrieve_chunks(
    question_embedding: list[float],
    video_id: str,
    top_k: int = 5
) -> list[dict]:
    """
    Retrieves the most relevant chunks for a question.
    """

    results = collection.query(
        query_embeddings=[question_embedding],
        n_results=top_k,
        where={"video_id": video_id}
    )

    retrieved = []

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    for doc, metadata, distance in zip(documents, metadatas, distances):
        retrieved.append({
            "text": doc,
            "metadata": metadata,
            "distance": distance
        })

    return retrieved


def get_video_chunks(video_id: str) -> list[dict]:
    """
    Returns all stored chunks for a video.
    Useful for debugging chunk quality.
    """

    results = collection.get(
        where={"video_id": video_id},
        include=["documents", "metadatas"]
    )

    chunks = []

    documents = results.get("documents", [])
    metadatas = results.get("metadatas", [])

    for doc, metadata in zip(documents, metadatas):
        chunks.append({
            "text": doc,
            "metadata": metadata
        })

    chunks.sort(key=lambda item: item["metadata"]["chunk_index"])

    return chunks