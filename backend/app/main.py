from fastapi import FastAPI, HTTPException
from pydantic import BaseModel 

from .transcript import get_transcript, extract_video_id
from .chunking import chunk_transcript
from .rag import answer_question
from .embeddings import create_embedding, create_embeddings
from .vector_store import store_chunks, get_video_chunks, retrieve_chunks
from .reranker import rerank_chunks

app = FastAPI(title="YouTube Video Chatbot")


class IngestRequest(BaseModel):
    youtube_url: str


class IngestResponse(BaseModel):
    video_id: str
    chunks_created: int
    message: str


class AskRequest(BaseModel):
    video_id: str
    question: str

class RetrieveRequest(BaseModel):
    video_id: str
    question: str
    top_k: int = 5

@app.get("/")
def health_check():
    return {
        "status": "ok",
        "message": "YouTube Video Chatbot API is running"
    }


@app.post("/ingest", response_model=IngestResponse)
def ingest_video(request: IngestRequest):
    try:
        video_id = extract_video_id(request.youtube_url)

        transcript = get_transcript(request.youtube_url)

        chunks = chunk_transcript(transcript)

        texts = [chunk["text"] for chunk in chunks]

        embeddings = create_embeddings(texts)

        store_chunks(
            video_id=video_id,
            chunks=chunks,
            embeddings=embeddings
        )

        return {
            "video_id": video_id,
            "chunks_created": len(chunks),
            "message": "Video transcript ingested successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ask")
def ask_question(request: AskRequest):
    try:
        result = answer_question(
            video_id=request.video_id,
            question=request.question
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/videos/{video_id}/chunks")
def list_video_chunks(video_id: str):
    try:
        chunks = get_video_chunks(video_id)

        return {
            "video_id": video_id,
            "chunks_count": len(chunks),
            "chunks": chunks
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/retrieve")
def retrieve_only(request: RetrieveRequest):
    try:
        question_embedding = create_embedding(request.question)

        chunks = retrieve_chunks(
            question_embedding=question_embedding,
            video_id=request.video_id,
            top_k=request.top_k
        )

        return {
            "video_id": request.video_id,
            "question": request.question,
            "top_k": request.top_k,
            "chunks": chunks
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/retrieve-reranked")
def retrieve_reranked(request: RetrieveRequest):
    try:
        question_embedding = create_embedding(request.question)

        initial_chunks = retrieve_chunks(
            question_embedding=question_embedding,
            video_id=request.video_id,
            top_k=15
        )

        reranked_chunks = rerank_chunks(
            question=request.question,
            chunks=initial_chunks,
            top_n=request.top_k
        )

        return {
            "video_id": request.video_id,
            "question": request.question,
            "initial_top_k": 15,
            "reranked_top_k": request.top_k,
            "chunks": reranked_chunks
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))