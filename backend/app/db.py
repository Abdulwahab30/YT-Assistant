import os
from datetime import datetime

from dotenv import load_dotenv
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    DateTime,
)
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./chat_history.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
    if DATABASE_URL.startswith("sqlite")
    else {}
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    video_id = Column(String, index=True, nullable=False)
    video_title = Column(String, nullable=True)
    youtube_url = Column(Text, nullable=True)
    title = Column(String, nullable=False, default="New Chat")
    chunks_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, index=True, nullable=False)
    user_id = Column(String, index=True, nullable=False)
    video_id = Column(String, index=True, nullable=False)
    role = Column(String, nullable=False)  # user / assistant
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def create_chat_session(
    user_id: str,
    video_id: str,
    video_title: str | None = None,
    youtube_url: str | None = None,
    title: str = "New Chat",
    chunks_count: int = 0
) -> ChatSession:
    db = SessionLocal()

    try:
        session = ChatSession(
            user_id=user_id,
            video_id=video_id,
            video_title=video_title,
            youtube_url=youtube_url,
            title=title,
            chunks_count=chunks_count,
        )

        db.add(session)
        db.commit()
        db.refresh(session)

        return session

    finally:
        db.close()


def get_chat_session(
    user_id: str,
    session_id: int
) -> ChatSession | None:
    db = SessionLocal()

    try:
        return (
            db.query(ChatSession)
            .filter(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id
            )
            .first()
        )

    finally:
        db.close()


def list_chat_sessions(user_id: str) -> list[dict]:
    db = SessionLocal()

    try:
        sessions = (
            db.query(ChatSession)
            .filter(ChatSession.user_id == user_id)
            .order_by(ChatSession.updated_at.desc())
            .all()
        )

        return [
            {
                "id": session.id,
                "video_id": session.video_id,
                "video_title": session.video_title,
                "youtube_url": session.youtube_url,
                "title": session.title,
                "chunks_count": session.chunks_count,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
            }
            for session in sessions
        ]

    finally:
        db.close()


def update_chat_session_title(
    user_id: str,
    session_id: int,
    title: str
) -> None:
    db = SessionLocal()

    try:
        session = (
            db.query(ChatSession)
            .filter(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id
            )
            .first()
        )

        if session:
            session.title = title
            session.updated_at = datetime.utcnow()
            db.commit()

    finally:
        db.close()


def touch_chat_session(
    user_id: str,
    session_id: int
) -> None:
    db = SessionLocal()

    try:
        session = (
            db.query(ChatSession)
            .filter(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id
            )
            .first()
        )

        if session:
            session.updated_at = datetime.utcnow()
            db.commit()

    finally:
        db.close()


def delete_chat_session(
    user_id: str,
    session_id: int
) -> bool:
    db = SessionLocal()

    try:
        session = (
            db.query(ChatSession)
            .filter(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id
            )
            .first()
        )

        if not session:
            return False

        db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id,
            ChatMessage.user_id == user_id
        ).delete()

        db.delete(session)
        db.commit()

        return True

    finally:
        db.close()


def save_chat_message(
    user_id: str,
    session_id: int,
    video_id: str,
    role: str,
    content: str
) -> ChatMessage:
    db = SessionLocal()

    try:
        message = ChatMessage(
            user_id=user_id,
            session_id=session_id,
            video_id=video_id,
            role=role,
            content=content
        )

        db.add(message)

        session = (
            db.query(ChatSession)
            .filter(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id
            )
            .first()
        )

        if session:
            session.updated_at = datetime.utcnow()

            if session.title == "New Chat" and role == "user":
                session.title = content[:50]

        db.commit()
        db.refresh(message)

        return message

    finally:
        db.close()


def get_chat_messages(
    user_id: str,
    session_id: int,
    limit: int = 100
) -> list[dict]:
    db = SessionLocal()

    try:
        rows = (
            db.query(ChatMessage)
            .filter(
                ChatMessage.user_id == user_id,
                ChatMessage.session_id == session_id
            )
            .order_by(ChatMessage.created_at.asc())
            .limit(limit)
            .all()
        )

        return [
            {
                "id": row.id,
                "session_id": row.session_id,
                "video_id": row.video_id,
                "role": row.role,
                "content": row.content,
                "created_at": row.created_at.isoformat()
            }
            for row in rows
        ]

    finally:
        db.close()