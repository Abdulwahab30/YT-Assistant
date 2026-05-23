import os
from dotenv import load_dotenv
from openai import OpenAI

from .retry_utils import retry_external_call
from .cache import load_cached_embedding, save_cached_embedding

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not OPENROUTER_API_KEY:
    raise RuntimeError(
        "OPENROUTER_API_KEY is missing. Add it to your .env file."
    )

client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
    default_headers={
        "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "http://localhost:8000"),
        "X-Title": os.getenv("OPENROUTER_APP_NAME", "YouTube Video Chatbot"),
    },
)

EMBEDDING_MODEL = os.getenv(
    "OPENROUTER_EMBEDDING_MODEL",
    "openai/text-embedding-3-small"
)


@retry_external_call()
def _create_embedding_uncached(text: str) -> list[float]:
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
    )

    return response.data[0].embedding


def create_embedding(text: str) -> list[float]:
    cached = load_cached_embedding(text, EMBEDDING_MODEL)

    if cached is not None:
        return cached

    embedding = _create_embedding_uncached(text)

    save_cached_embedding(text, EMBEDDING_MODEL, embedding)

    return embedding


def create_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Creates embeddings with per-text cache.

    This avoids re-embedding chunks that were already processed.
    """
    embeddings = []

    missing_texts = []
    missing_indices = []

    for index, text in enumerate(texts):
        cached = load_cached_embedding(text, EMBEDDING_MODEL)

        if cached is not None:
            embeddings.append(cached)
        else:
            embeddings.append(None)
            missing_texts.append(text)
            missing_indices.append(index)

    if missing_texts:
        new_embeddings = _create_embeddings_uncached(missing_texts)

        for original_index, text, embedding in zip(
            missing_indices,
            missing_texts,
            new_embeddings
        ):
            save_cached_embedding(text, EMBEDDING_MODEL, embedding)
            embeddings[original_index] = embedding

    return embeddings


@retry_external_call()
def _create_embeddings_uncached(texts: list[str]) -> list[list[float]]:
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts,
    )

    return [item.embedding for item in response.data]