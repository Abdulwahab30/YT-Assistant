import os

import firebase_admin
from firebase_admin import credentials, auth
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from dotenv import load_dotenv

load_dotenv()

security = HTTPBearer()


def initialize_firebase() -> None:
    """
    Initializes Firebase Admin SDK once.
    """
    if firebase_admin._apps:
        return

    service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")

    if not service_account_path:
        raise RuntimeError(
            "FIREBASE_SERVICE_ACCOUNT_PATH is missing in .env"
        )

    cred = credentials.Certificate(service_account_path)
    firebase_admin.initialize_app(cred)


initialize_firebase()


def get_current_user(
    credentials_data: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    FastAPI dependency that verifies Firebase ID token.

    Frontend must send:
    Authorization: Bearer <firebase_id_token>
    """
    token = credentials_data.credentials

    try:
        decoded_token = auth.verify_id_token(token)

        return {
            "uid": decoded_token["uid"],
            "email": decoded_token.get("email"),
            "name": decoded_token.get("name")
        }

    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired Firebase token"
        )