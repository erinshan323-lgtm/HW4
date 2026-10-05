from __future__ import annotations

import os
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

from pydantic_ai import Agent
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

try:
    from .models import AuditEntry, ChatReply, ProductCard
    from .tools import ShopDeps, check_inventory, find_in_stock_alternatives, get_product_details, search_products
except ImportError:  # Supports running from inside backend/.
    from models import AuditEntry, ChatReply, ProductCard
    from tools import ShopDeps, check_inventory, find_in_stock_alternatives, get_product_details, search_products


PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "prompt.md"
AUDIT_PATH = Path(__file__).resolve().parents[1] / "output" / "audit_trail.json"


def _append_audit(entry: AuditEntry) -> None:
    """Append one validated JSON object without reading or truncating prior records."""
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_PATH.open("a", encoding="utf-8") as audit_file:
        audit_file.write(json.dumps(entry.model_dump(mode="json"), ensure_ascii=True) + "\n")


def _offline_database_reply(message: str, database_path: Path, current_product_id: Optional[str]) -> ChatReply:
    """Provide honest catalogue help when a model key is unavailable."""
    text = message.lower()
    size_match = re.search(r"\b(xxl|xl|xs|s|m|l)\b", text, re.IGNORECASE)
    requested_size = size_match.group(1).upper() if size_match else None
    search_terms = {
        "hoodie": "hood",
        "hoodies": "hood",
        "crewneck": "crewneck",
        "crewnecks": "crewneck",
        "t-shirt": "t shirt",
        "t-shirts": "t shirt",
        "shirt": "shirt",
        "shirts": "shirt",
        "jacket": "jacket",
        "jackets": "jacket",
        "fleece": "fleece",
    }
    term = next((value for key, value in search_terms.items() if key in text), None)
    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        if current_product_id and any(word in text for word in ("this", "item", "stock", "price", "cost")):
            row = connection.execute(
                "SELECT * FROM catalogue WHERE product_id = ?", (current_product_id,)
            ).fetchone()
            if row:
                stock_text = ""
                if requested_size:
                    stock = connection.execute(
                        "SELECT quantity FROM inventory WHERE product_id = ? AND UPPER(size) = ?",
                        (current_product_id, requested_size),
                    ).fetchone()
                    quantity = stock["quantity"] if stock else 0
                    stock_text = f" Size {requested_size} has {quantity} in stock."
                return ChatReply(
                    answer=f"{row['name']} is ${row['price']:.2f}.{stock_text}",
                    products=[],
                )
        if term:
            rows = connection.execute(
                "SELECT * FROM catalogue WHERE LOWER(name) LIKE ? OR LOWER(garment_type) LIKE ? ORDER BY name LIMIT 6",
                (f"%{term}%", f"%{term}%"),
            ).fetchall()
            products = [
                ProductCard(
                    product_id=row["product_id"], name=row["name"], price=row["price"],
                    image_url=f"/product-images/{Path(row['image_file_path']).name}",
                    description=row["description"],
                )
                for row in rows
            ]
            return ChatReply(
                answer=f"I found {len(products)} matching items in the Campus Customs catalogue.",
                products=products,
            )
    return ChatReply(
        answer="I can search the catalogue by item type, or check price and size inventory from a product page.",
        products=[],
    )


def _configured_model() -> Model:
    api_key = os.getenv("PORTKEY_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Set PORTKEY_API_KEY or OPENAI_API_KEY to enable chat.")
    model_name = os.getenv("AI_MODEL", "gpt-5.6-luna")
    base_url = os.getenv("AI_BASE_URL")
    if not base_url and os.getenv("PORTKEY_API_KEY"):
        base_url = "https://api.portkey.ai/v1"
    provider = OpenAIProvider(base_url=base_url, api_key=api_key)
    return OpenAIModel(model_name, provider=provider)


def build_agent(model: Optional[Model] = None) -> Agent[ShopDeps, ChatReply]:
    instructions = PROMPT_PATH.read_text(encoding="utf-8")
    agent = Agent(
        model or _configured_model(),
        deps_type=ShopDeps,
        output_type=ChatReply,
        instructions=instructions,
        tools=[search_products, get_product_details, check_inventory, find_in_stock_alternatives],
        retries=2,
    )
    @agent.instructions
    def customer_and_page_context(ctx) -> str:
        identity = (
            f"The signed-in shopper is {ctx.deps.user_name} ({ctx.deps.user_email})."
            if ctx.deps.user_name and ctx.deps.user_email
            else "The shopper is a guest. Do not claim to know their identity or history."
        )
        page = f"Current page path: {ctx.deps.current_path or '/'}"
        if ctx.deps.current_product_id:
            page += f". The product currently visible is {ctx.deps.current_product_id}."
        return f"{identity}\n{page}"
    return agent


async def answer_shopper(
    message: str,
    database_path: Path,
    user_name: Optional[str] = None,
    user_email: Optional[str] = None,
    current_product_id: Optional[str] = None,
    current_path: Optional[str] = None,
    history: Optional[List[str]] = None,
) -> ChatReply:
    run_id = uuid4().hex
    common_args = {
        "message_length": str(len(message)),
        "has_page_product": str(bool(current_product_id)).lower(),
        "history_items": str(min(len(history or []), 12)),
    }
    if not (os.getenv("PORTKEY_API_KEY") or os.getenv("OPENAI_API_KEY")):
        reply = _offline_database_reply(message, database_path, current_product_id)
        tool_name = "database_product_lookup" if current_product_id else "database_catalogue_search"
        _append_audit(AuditEntry(
            timestamp=datetime.now(timezone.utc), run_id=run_id, iteration=1,
            mode="offline_database", tool_name=tool_name, arguments=common_args,
            result_summary=f"answer_chars={len(reply.answer)}; products={len(reply.products)}",
            stop_reason="completed",
        ))
        return reply
    agent = build_agent()
    prior = ""
    if history:
        prior = "Recent conversation for context:\n" + "\n".join(history[-12:]) + "\n\n"
    try:
        result = await agent.run(
            prior + "Current shopper message:\n" + message,
            deps=ShopDeps(
                database_path=database_path,
                user_name=user_name,
                user_email=user_email,
                current_product_id=current_product_id,
                current_path=current_path,
            ),
        )
        reply = result.output
        _append_audit(AuditEntry(
            timestamp=datetime.now(timezone.utc), run_id=run_id, iteration=1,
            mode="pydantic_ai", tool_name="agent_tool_loop", arguments=common_args,
            result_summary=f"answer_chars={len(reply.answer)}; products={len(reply.products)}",
            stop_reason="completed",
        ))
        return reply
    except Exception:
        _append_audit(AuditEntry(
            timestamp=datetime.now(timezone.utc), run_id=run_id, iteration=1,
            mode="pydantic_ai", tool_name="agent_tool_loop", arguments=common_args,
            result_summary="run failed; exception details omitted from audit",
            stop_reason="error",
        ))
        raise
