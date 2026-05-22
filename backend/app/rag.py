from importlib import metadata
import os
from dotenv import load_dotenv
from openai import OpenAI

from .embeddings import create_embedding
from .vector_store import retrieve_chunks
from .reranker import rerank_chunks


load_dotenv(dotenv_path=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env")))

client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
    default_headers={
        "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "http://localhost:8000"),
        "X-Title": os.getenv("OPENROUTER_APP_NAME", "YouTube Video Chatbot"),
    },
)

CHAT_MODEL = os.getenv("OPENROUTER_CHAT_MODEL", "openai/gpt-4o-mini")


def format_timestamp(seconds: float) -> str:
    """
    Converts seconds into mm:ss format.
    """
    minutes = int(seconds // 60)
    remaining_seconds = int(seconds % 60)
    return f"{minutes:02d}:{remaining_seconds:02d}"


def build_context(chunks: list[dict]) -> str:
    """
    Formats retrieved chunks into context for the LLM.
    """

    context_parts = []

    for chunk in chunks:
        metadata = chunk["metadata"]

        start = format_timestamp(metadata["start_time"])
        end = format_timestamp(metadata["end_time"])

        context_parts.append(
            f"[{start} - {end}]\n{chunk['text']}"
        )

    return "\n\n".join(context_parts)


def answer_question(video_id: str, question: str) -> dict:
    """
    Full RAG question-answering pipeline.
    """

    question_embedding = create_embedding(question)

    initial_chunks = retrieve_chunks(
    question_embedding=question_embedding,
    video_id=video_id,
    top_k=15
)

    retrieved_chunks = rerank_chunks(
        question=question,
        chunks=initial_chunks,
        top_n=5
    )

    context = build_context(retrieved_chunks)

    prompt = f"""
    You are a YouTube video question-answering assistant.

    You must answer using ONLY the transcript context provided below.

    Rules:
    1. If the answer is present in the context, answer clearly and concisely.
    2. Mention only 1–2 timestamps in the answer, and only when they directly support the answer.
    3. If the answer is not present in the context, say:
    "I could not find that in the video."
    4. Do not use outside knowledge.
    5. Do not guess.
    6. Do not mention information that is not supported by the transcript context.

    Transcript context:
    {context}

    User question:
    {question}
    """

    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You answer questions using only the provided YouTube transcript context."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2
    )

    answer = response.choices[0].message.content

    MAX_VISIBLE_SOURCES = 3

    sources = []

    for chunk in retrieved_chunks[:MAX_VISIBLE_SOURCES]:
        metadata = chunk["metadata"]
        start_seconds = int(metadata["start_time"])

        sources.append({
            "start_time": metadata["start_time"],
            "end_time": metadata["end_time"],
            "start": format_timestamp(metadata["start_time"]),
            "end": format_timestamp(metadata["end_time"]),
            "youtube_url": f"https://www.youtube.com/watch?v={video_id}&t={start_seconds}s",
            "rerank_score": chunk.get("rerank_score"),
            "text_preview": chunk["text"][:300] + "..."
        })

    return {
    "video_id": video_id,
    "question": question,
    "answer": answer,
    "sources": sources,
    "initial_retrieved_chunks_count": len(initial_chunks),
    "reranked_chunks_count": len(retrieved_chunks)
}