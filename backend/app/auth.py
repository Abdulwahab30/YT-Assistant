import json
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

    # ponytail: HF Spaces secrets are env vars only (no file mounts), so the
    # service account JSON can be passed inline instead of a file path.
    service_account_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")

    if service_account_json:
        cred = credentials.Certificate(json.loads(service_account_json))
    elif service_account_path:
        cred = credentials.Certificate(service_account_path)
    else:
        raise RuntimeError(
            "Set FIREBASE_SERVICE_ACCOUNT_JSON (inline JSON) or "
            "FIREBASE_SERVICE_ACCOUNT_PATH (file path) in the environment."
        )

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