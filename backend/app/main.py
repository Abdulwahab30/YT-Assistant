from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os 

from .transcript import get_transcript, extract_video_id, get_youtube_title
from .chunking import chunk_transcript
from .rag import answer_question
from .embeddings import create_embedding, create_embeddings
from .vector_store import (
    store_chunks,
    get_video_chunks,
    retrieve_chunks,
    video_exists,
)
from .reranker import rerank_chunks
from .semantic_cache import clear_answer_cache

from fastapi import FastAPI, HTTPException, Depends
from .auth import get_current_user


from .firestore_db import (
    create_or_update_video,
    get_video,
    list_videos,
    create_chat_session,
    get_chat_session,
    list_chat_sessions,
    update_chat_session_title,
    delete_chat_session,
    save_chat_message,
    get_chat_messages,
)



app = FastAPI(title="YouTube Video Chatbot")




app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development, allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class IngestRequest(BaseModel):
    youtube_url: str
    force: bool = False


class IngestResponse(BaseModel):
    video_id: str
    chunks_created: int
    message: str


class AskRequest(BaseModel):
    session_id: str
    question: str


class CreateSessionRequest(BaseModel):
    youtube_url: str
    force: bool = False


class UpdateSessionTitleRequest(BaseModel):
    title: str


class RetrieveRequest(BaseModel):
    video_id: str
    question: str
    top_k: int = 5

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "message": "YouTube Video Chatbot API is running"
    }


@app.post("/ingest", response_model=IngestResponse)
def ingest_video(
    request: IngestRequest,
    current_user: dict = Depends(get_current_user)
):
    try:
        user_id = current_user["uid"]
        video_id = extract_video_id(request.youtube_url)

        if video_exists(user_id, video_id) and not request.force:
            chunks = get_video_chunks(user_id, video_id)

            return {
                "video_id": video_id,
                "chunks_created": len(chunks),
                "message": "Video already ingested for this user. Using cached chunks."
            }

        transcript = get_transcript(request.youtube_url)

        chunks = chunk_transcript(
            transcript=transcript,
            chunk_size=700,
            chunk_overlap=120
        )

        texts = [chunk["text"] for chunk in chunks]
        embeddings = create_embeddings(texts)

        store_chunks(
            user_id=user_id,
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
def ask_question_route(
    request: AskRequest,
    current_user: dict = Depends(get_current_user)
):
    try:
        user_id = current_user["uid"]

        session = get_chat_session(
            user_id=user_id,
            session_id=request.session_id
        )

        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")

        save_chat_message(
            user_id=user_id,
            session_id=session["id"],
            video_id=session["video_id"],
            role="user",
            content=request.question
        )

        result = answer_question(
            user_id=user_id,
            video_id=session["video_id"],
            question=request.question
        )

        save_chat_message(
            user_id=user_id,
            session_id=session["id"],
            video_id=session["video_id"],
            role="assistant",
            content=result["answer"]
        )

        return {
            **result,
            "session_id": session["id"]
        }

    except HTTPException:
        raise

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/videos/{video_id}/chunks")
def list_video_chunks(
    video_id: str,
    current_user: dict = Depends(get_current_user)
):
    try:
        chunks = get_video_chunks(
            user_id=current_user["uid"],
            video_id=video_id
        )

        return {
            "video_id": video_id,
            "chunks_count": len(chunks),
            "chunks": chunks
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/retrieve")
def retrieve_only(
    request: RetrieveRequest,
    current_user: dict = Depends(get_current_user)
):
    try:
        question_embedding = create_embedding(request.question)

        chunks = retrieve_chunks(
            user_id=current_user["uid"],
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


@app.delete("/cache/answers")
def clear_all_answer_cache():
    try:
        deleted_count = clear_answer_cache()

        return {
            "deleted_count": deleted_count,
            "message": "Semantic answer cache cleared."
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/cache/answers/{video_id}")
def clear_video_answer_cache(video_id: str):
    try:
        deleted_count = clear_answer_cache(video_id)

        return {
            "video_id": video_id,
            "deleted_count": deleted_count,
            "message": "Semantic answer cache cleared for video."
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/retrieve-reranked")
def retrieve_reranked(
    request: RetrieveRequest,
    current_user: dict = Depends(get_current_user)
):
    try:
        question_embedding = create_embedding(request.question)

        initial_chunks = retrieve_chunks(
            user_id=current_user["uid"],
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

@app.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    return {
        "user": current_user
    }


# @app.get("/chat/history/{video_id}")
# def read_chat_history(
#     video_id: str,
#     current_user: dict = Depends(get_current_user)
# ):
#     try:
#         history = get_chat_history(
#             user_id=current_user["uid"],
#             video_id=video_id
#         )

#         return {
#             "video_id": video_id,
#             "messages": history
#         }

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/sessions")
def create_session(
    request: CreateSessionRequest,
    current_user: dict = Depends(get_current_user)
):
    try:
        user_id = current_user["uid"]
        video_id = extract_video_id(request.youtube_url)

        if video_exists(user_id, video_id) and not request.force:
            chunks = get_video_chunks(user_id, video_id)
        else:
            transcript = get_transcript(request.youtube_url)

            chunks = chunk_transcript(
                transcript=transcript,
                chunk_size=700,
                chunk_overlap=120
            )

            texts = [chunk["text"] for chunk in chunks]
            embeddings = create_embeddings(texts)

            store_chunks(
                user_id=user_id,
                video_id=video_id,
                chunks=chunks,
                embeddings=embeddings
            )

        video_title = get_youtube_title(video_id)

        create_or_update_video(
            user_id=user_id,
            video_id=video_id,
            youtube_url=request.youtube_url,
            chunks_count=len(chunks),
            title=video_title,
            processing_status="completed",
        ) 

        session = create_chat_session(
            user_id=user_id,
            video_id=video_id,
            youtube_url=request.youtube_url,
            video_title=video_title,
            title="New Chat",
            chunks_count=len(chunks),
        )

        return {
            "session": session,
            "message": "Chat session created successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chat/sessions")
def get_sessions(
    current_user: dict = Depends(get_current_user)
):
    try:
        sessions = list_chat_sessions(
            user_id=current_user["uid"]
        )

        return {
            "sessions": sessions
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chat/sessions/{session_id}/messages")
def get_session_messages(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    try:
        user_id = current_user["uid"]

        session = get_chat_session(
            user_id=user_id,
            session_id=session_id
        )

        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")

        messages = get_chat_messages(
            user_id=user_id,
            session_id=session_id
        )

        return {
            "session": session,
            "messages": messages
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/chat/sessions/{session_id}")
def rename_session(
    session_id: str,
    request: UpdateSessionTitleRequest,
    current_user: dict = Depends(get_current_user)
):
    try:
        user_id = current_user["uid"]

        session = get_chat_session(
            user_id=user_id,
            session_id=session_id
        )

        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")

        update_chat_session_title(
            user_id=user_id,
            session_id=session_id,
            title=request.title
        )

        return {
            "message": "Session title updated"
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/chat/sessions/{session_id}")
def remove_session(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    try:
        deleted = delete_chat_session(
            user_id=current_user["uid"],
            session_id=session_id
        )

        if not deleted:
            raise HTTPException(status_code=404, detail="Chat session not found")

        return {
            "message": "Session deleted"
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/videos")
def get_user_videos(
    current_user: dict = Depends(get_current_user)
):
    try:
        videos = list_videos(current_user["uid"])

        return {
            "videos": videos
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/videos/{video_id}")
def get_user_video(
    video_id: str,
    current_user: dict = Depends(get_current_user)
):
    try:
        video = get_video(
            user_id=current_user["uid"],
            video_id=video_id
        )

        if not video:
            raise HTTPException(status_code=404, detail="Video not found")

        return {
            "video": video
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend"))
app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
