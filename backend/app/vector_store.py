import chromadb

CHROMA_PATH = "chroma_db"
COLLECTION_NAME = "youtube_video_chunks"

client = chromadb.PersistentClient(path=CHROMA_PATH)

collection = client.get_or_create_collection(name=COLLECTION_NAME)


def user_video_filter(user_id: str, video_id: str) -> dict:
    return {
        "$and": [
            {"user_id": user_id},
            {"video_id": video_id}
        ]
    }


def delete_video_chunks(user_id: str, video_id: str) -> None:
    existing = collection.get(
        where=user_video_filter(user_id, video_id),
        include=[]
    )

    if existing and existing.get("ids"):
        collection.delete(ids=existing["ids"])


def store_chunks(
    user_id: str,
    video_id: str,
    chunks: list[dict],
    embeddings: list[list[float]]
) -> None:
    delete_video_chunks(user_id, video_id)

    ids = []
    documents = []
    metadatas = []

    for chunk, embedding in zip(chunks, embeddings):
        chunk_id = f"{user_id}_{video_id}_{chunk['chunk_index']}"

        ids.append(chunk_id)
        documents.append(chunk["text"])
        metadatas.append({
            "user_id": user_id,
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
    user_id: str,
    question_embedding: list[float],
    video_id: str,
    top_k: int = 5
) -> list[dict]:
    results = collection.query(
        query_embeddings=[question_embedding],
        n_results=top_k,
        where=user_video_filter(user_id, video_id)
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


def get_video_chunks(user_id: str, video_id: str) -> list[dict]:
    results = collection.get(
        where=user_video_filter(user_id, video_id),
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


def video_exists(user_id: str, video_id: str) -> bool:
    results = collection.get(
        where=user_video_filter(user_id, video_id),
        include=[],
        limit=1
    )

    return bool(results.get("ids"))