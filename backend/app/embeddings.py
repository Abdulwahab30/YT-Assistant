import os
from dotenv import load_dotenv
from openai import OpenAI

# Load .env from the backend folder (one level up from this file)
dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv(dotenv_path=dotenv_path)

client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
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


def create_embedding(text: str) -> list[float]:
    """
    Converts one text string into an embedding vector using OpenRouter.
    """
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
    )

    return response.data[0].embedding


def create_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Converts a list of texts into embedding vectors using OpenRouter.
    """
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts,
    )

    return [item.embedding for item in response.data]