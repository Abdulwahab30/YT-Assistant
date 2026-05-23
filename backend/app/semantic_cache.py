import json
import time
import uuid
import chromadb


CHROMA_PATH = "chroma_db"
ANSWER_CACHE_COLLECTION_NAME = "youtube_answer_cache"

client = chromadb.PersistentClient(path=CHROMA_PATH)

answer_cache_collection = client.get_or_create_collection(
    name=ANSWER_CACHE_COLLECTION_NAME
)


SEMANTIC_CACHE_DISTANCE_THRESHOLD = 0.15
SEMANTIC_CACHE_TOP_K = 1
PIPELINE_VERSION = "rag-v1"
PROMPT_VERSION = "prompt-v1"

def get_cached_answer(
    video_id: str,
    question_embedding: list[float],
    distance_threshold: float = SEMANTIC_CACHE_DISTANCE_THRESHOLD
) -> dict | None:
    """
    Finds a semantically similar cached answer for the same video.

    Chroma distance meaning depends on the collection metric.
    Lower distance usually means more similar.
    """

    results = answer_cache_collection.query(
        query_embeddings=[question_embedding],
        n_results=SEMANTIC_CACHE_TOP_K,
        where={
            "$and": [
                {"video_id": video_id},
                {"pipeline_version": PIPELINE_VERSION},
                {"prompt_version": PROMPT_VERSION}
            ]
}
    )

    ids = results.get("ids", [[]])[0]
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    if not ids:
        return None

    best_distance = distances[0]

    if best_distance > distance_threshold:
        return None

    metadata = metadatas[0]

    sources_json = metadata.get("sources_json", "[]")

    try:
        sources = json.loads(sources_json)
    except json.JSONDecodeError:
        sources = []

    return {
        "cache_hit": True,
        "cache_id": ids[0],
        "cached_question": metadata.get("question"),
        "answer": documents[0],
        "sources": sources,
        "cache_distance": best_distance,
        "created_at": metadata.get("created_at")
    }


def save_answer_to_cache(
    video_id: str,
    question: str,
    question_embedding: list[float],
    answer: str,
    sources: list[dict]
) -> None:
    """
    Saves generated answer into semantic cache.
    """

    cache_id = f"{video_id}_{uuid.uuid4()}"

    metadata = {
        "video_id": video_id,
        "question": question,
        "sources_json": json.dumps(sources),
        "created_at": int(time.time()),
        "pipeline_version": PIPELINE_VERSION,
        "prompt_version": PROMPT_VERSION
    }

    answer_cache_collection.add(
        ids=[cache_id],
        embeddings=[question_embedding],
        documents=[answer],
        metadatas=[metadata]
    )

def clear_answer_cache(video_id: str | None = None) -> int:
    """
    Clears semantic answer cache.
    If video_id is provided, clears only that video's cached answers.
    Returns number of deleted cache entries.
    """

    if video_id:
        existing = answer_cache_collection.get(
            where={"video_id": video_id},
            include=[]
        )
    else:
        existing = answer_cache_collection.get(include=[])

    ids = existing.get("ids", [])

    if ids:
        answer_cache_collection.delete(ids=ids)

    return len(ids)