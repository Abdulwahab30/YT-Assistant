import json
from pathlib import Path
from typing import Any
import hashlib

CACHE_DIR = Path("cache")
TRANSCRIPT_CACHE_DIR = CACHE_DIR / "transcripts"

TRANSCRIPT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
EMBEDDING_CACHE_DIR = CACHE_DIR / "embeddings"
EMBEDDING_CACHE_DIR.mkdir(parents=True, exist_ok=True)

def get_transcript_cache_path(video_id: str) -> Path:
    return TRANSCRIPT_CACHE_DIR / f"{video_id}.json"


def load_cached_transcript(video_id: str) -> list[dict] | None:
    """
    Loads cached transcript if available.
    """
    path = get_transcript_cache_path(video_id)

    if not path.exists():
        return None

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_cached_transcript(video_id: str, transcript: list[dict]) -> None:
    """
    Saves transcript to local JSON cache.
    """
    path = get_transcript_cache_path(video_id)

    with path.open("w", encoding="utf-8") as file:
        json.dump(transcript, file, ensure_ascii=False, indent=2)


def cache_exists(video_id: str) -> bool:
    return get_transcript_cache_path(video_id).exists()

def get_text_hash(text: str, model: str) -> str:
    """
    Creates a stable hash for text + model.

    Including the model is important because different embedding models
    produce different vector dimensions/values.
    """
    raw = f"{model}:{text}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def get_embedding_cache_path(text: str, model: str) -> Path:
    text_hash = get_text_hash(text, model)
    return EMBEDDING_CACHE_DIR / f"{text_hash}.json"


def load_cached_embedding(text: str, model: str) -> list[float] | None:
    path = get_embedding_cache_path(text, model)

    if not path.exists():
        return None

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_cached_embedding(text: str, model: str, embedding: list[float]) -> None:
    path = get_embedding_cache_path(text, model)

    with path.open("w", encoding="utf-8") as file:
        json.dump(embedding, file)