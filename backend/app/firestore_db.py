from datetime import datetime, timezone
from uuid import uuid4

from firebase_admin import firestore

from app.auth import initialize_firebase


initialize_firebase()

db = firestore.client()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def user_ref(user_id: str):
    return db.collection("users").document(user_id)


def videos_ref(user_id: str):
    return user_ref(user_id).collection("videos")


def sessions_ref(user_id: str):
    return user_ref(user_id).collection("chat_sessions")


def create_or_update_video(
    user_id: str,
    video_id: str,
    youtube_url: str,
    chunks_count: int,
    title: str | None = None,
    processing_status: str = "completed",
) -> dict:
    ref = videos_ref(user_id).document(video_id)

    existing = ref.get()
    timestamp = now_iso()

    data = {
        "video_id": video_id,
        "youtube_url": youtube_url,
        "title": title or video_id,
        "chunks_count": chunks_count,
        "processing_status": processing_status,
        "updated_at": timestamp,
    }

    if not existing.exists:
        data["created_at"] = timestamp

    ref.set(data, merge=True)

    saved = ref.get().to_dict()
    return saved


def get_video(user_id: str, video_id: str) -> dict | None:
    doc = videos_ref(user_id).document(video_id).get()

    if not doc.exists:
        return None

    return doc.to_dict()


def list_videos(user_id: str) -> list[dict]:
    docs = (
        videos_ref(user_id)
        .order_by("updated_at", direction=firestore.Query.DESCENDING)
        .stream()
    )

    return [doc.to_dict() for doc in docs]


def create_chat_session(
    user_id: str,
    video_id: str,
    youtube_url: str,
    chunks_count: int,
    video_title: str | None = None,
    title: str = "New Chat",
) -> dict:
    session_id = str(uuid4())
    timestamp = now_iso()

    data = {
        "id": session_id,
        "video_id": video_id,
        "video_title": video_title,
        "youtube_url": youtube_url,
        "title": title,
        "chunks_count": chunks_count,
        "created_at": timestamp,
        "updated_at": timestamp,
    }

    sessions_ref(user_id).document(session_id).set(data)

    return data


def get_chat_session(user_id: str, session_id: str) -> dict | None:
    doc = sessions_ref(user_id).document(session_id).get()

    if not doc.exists:
        return None

    return doc.to_dict()


def list_chat_sessions(user_id: str) -> list[dict]:
    docs = (
        sessions_ref(user_id)
        .order_by("updated_at", direction=firestore.Query.DESCENDING)
        .stream()
    )

    return [doc.to_dict() for doc in docs]


def update_chat_session_title(
    user_id: str,
    session_id: str,
    title: str,
) -> None:
    sessions_ref(user_id).document(session_id).set(
        {
            "title": title,
            "updated_at": now_iso(),
        },
        merge=True,
    )


def touch_chat_session(user_id: str, session_id: str) -> None:
    sessions_ref(user_id).document(session_id).set(
        {
            "updated_at": now_iso(),
        },
        merge=True,
    )


def delete_chat_session(user_id: str, session_id: str) -> bool:
    session_doc = sessions_ref(user_id).document(session_id)
    snapshot = session_doc.get()

    if not snapshot.exists:
        return False

    # Delete messages subcollection
    messages = session_doc.collection("messages").stream()
    for message in messages:
        message.reference.delete()

    session_doc.delete()

    return True


def save_chat_message(
    user_id: str,
    session_id: str,
    video_id: str,
    role: str,
    content: str,
) -> dict:
    session = get_chat_session(user_id, session_id)

    if not session:
        raise ValueError("Chat session not found")

    message_id = str(uuid4())
    timestamp = now_iso()

    data = {
        "id": message_id,
        "session_id": session_id,
        "video_id": video_id,
        "role": role,
        "content": content,
        "created_at": timestamp,
    }

    session_doc = sessions_ref(user_id).document(session_id)
    session_doc.collection("messages").document(message_id).set(data)

    update_data = {
        "updated_at": timestamp,
    }

    if session.get("title") == "New Chat" and role == "user":
        update_data["title"] = content[:50]

    session_doc.set(update_data, merge=True)

    return data


def get_chat_messages(
    user_id: str,
    session_id: str,
    limit: int = 100,
) -> list[dict]:
    session = get_chat_session(user_id, session_id)

    if not session:
        return []

    docs = (
        sessions_ref(user_id)
        .document(session_id)
        .collection("messages")
        .order_by("created_at")
        .limit(limit)
        .stream()
    )

    return [doc.to_dict() for doc in docs]