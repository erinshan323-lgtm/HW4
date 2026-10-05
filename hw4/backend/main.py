from __future__ import annotations

import json
import base64
import hashlib
import hmac
import os
import secrets
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

try:
    from .agent import answer_shopper
    from .models import ChatReply, ChatRequest, LoginReply, LoginRequest, PublicUser, StoredChatMessage
except ImportError:  # Supports `uvicorn main:app` from backend/.
    from agent import answer_shopper
    from models import ChatReply, ChatRequest, LoginReply, LoginRequest, PublicUser, StoredChatMessage


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.getenv("CAMPUS_DATA_DIR", ROOT / "data")).resolve()
DB_PATH = DATA_DIR / "campus_customs.db"
SESSIONS: dict[str, int] = {}
bearer = HTTPBearer(auto_error=False)

app = FastAPI(title="Campus Customs API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if (DATA_DIR / "products").exists():
    app.mount("/product-images", StaticFiles(directory=DATA_DIR / "products"), name="products")


def connect() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise HTTPException(status_code=503, detail=f"Database not found at {DB_PATH}")
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def product_dict(row: sqlite3.Row) -> dict:
    item = dict(row)
    item["colors"] = json.loads(item["colors"])
    item["search_tags"] = json.loads(item["search_tags"])
    item["image_url"] = f"/product-images/{Path(item['image_file_path']).name}"
    return item


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt, expected = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt.encode(), int(iterations)
        )
        actual = base64.b64encode(digest).decode().strip()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> Optional[sqlite3.Row]:
    if credentials is None:
        return None
    user_id = SESSIONS.get(credentials.credentials)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    with closing(connect()) as connection:
        user = connection.execute(
            "SELECT id, name, email, first_name, last_name FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    if user is None:
        raise HTTPException(status_code=401, detail="User account no longer exists")
    return user


def decode_products(value: Optional[str]) -> list[dict]:
    if not value:
        return []
    try:
        products = json.loads(value)
        return products if isinstance(products, list) else []
    except json.JSONDecodeError:
        return []


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "database": DB_PATH.exists()}


@app.post("/api/auth/login", response_model=LoginReply)
def login(request: LoginRequest) -> LoginReply:
    with closing(connect()) as connection:
        user = connection.execute(
            "SELECT id, name, email, password_hash, first_name, last_name "
            "FROM users WHERE LOWER(email) = LOWER(?)",
            (request.email.strip(),),
        ).fetchone()
    if user is None or not verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    token = secrets.token_urlsafe(32)
    SESSIONS[token] = user["id"]
    return LoginReply(
        token=token,
        user=PublicUser(**{key: user[key] for key in ("id", "name", "email", "first_name", "last_name")}),
    )


@app.post("/api/auth/logout")
def logout(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> dict:
    if credentials:
        SESSIONS.pop(credentials.credentials, None)
    return {"status": "ok"}


@app.get("/api/chat/history", response_model=list[StoredChatMessage])
def chat_history(user: Optional[sqlite3.Row] = Depends(optional_user)) -> list[StoredChatMessage]:
    if user is None:
        return []
    with closing(connect()) as connection:
        rows = connection.execute(
            "SELECT role, content, products_json, created_at FROM chat_messages "
            "WHERE user_id = ? ORDER BY id DESC LIMIT 30",
            (user["id"],),
        ).fetchall()
    return [
        StoredChatMessage(
            role=row["role"],
            content=row["content"],
            products=decode_products(row["products_json"]),
            created_at=row["created_at"],
        )
        for row in reversed(rows)
    ]


@app.get("/api/products")
def list_products(limit: int = 102) -> list[dict]:
    safe_limit = min(max(limit, 1), 102)
    with closing(connect()) as connection:
        rows = connection.execute(
            "SELECT * FROM catalogue ORDER BY name LIMIT ?", (safe_limit,)
        ).fetchall()
    return [product_dict(row) for row in rows]


@app.get("/api/products/{product_id}")
def get_product(product_id: str) -> dict:
    with closing(connect()) as connection:
        row = connection.execute(
            "SELECT * FROM catalogue WHERE product_id = ?", (product_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Product not found")
        inventory = connection.execute(
            "SELECT size, quantity FROM inventory WHERE product_id = ? ORDER BY id",
            (product_id,),
        ).fetchall()
    item = product_dict(row)
    item["inventory"] = [dict(stock) for stock in inventory]
    return item


@app.post("/api/chat", response_model=ChatReply)
async def chat(
    request: ChatRequest, user: Optional[sqlite3.Row] = Depends(optional_user)
) -> ChatReply:
    history: list[str] = []
    if user is not None:
        with closing(connect()) as connection:
            rows = connection.execute(
                "SELECT role, content FROM chat_messages WHERE user_id = ? "
                "ORDER BY id DESC LIMIT 12",
                (user["id"],),
            ).fetchall()
        history = [f"{row['role']}: {row['content']}" for row in reversed(rows)]
    try:
        reply = await answer_shopper(
            request.message,
            DB_PATH,
            user_name=user["name"] if user else None,
            user_email=user["email"] if user else None,
            current_product_id=request.page_context.current_product_id if request.page_context else None,
            current_path=request.page_context.path if request.page_context else None,
            history=history,
        )
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    if user is not None:
        products_json = json.dumps(
            [product.model_dump() for product in reply.products], ensure_ascii=True
        )
        with closing(connect()) as connection:
            connection.execute(
                "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, 'user', ?, NULL)",
                (user["id"], request.message),
            )
            connection.execute(
                "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, 'assistant', ?, ?)",
                (user["id"], reply.answer, products_json),
            )
            connection.commit()
    return reply
