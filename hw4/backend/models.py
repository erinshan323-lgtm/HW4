from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ProductCard(BaseModel):
    product_id: str = Field(description="Stable product identifier from the catalogue")
    name: str
    price: float = Field(ge=0)
    image_url: str
    description: str
    stock_summary: Optional[str] = None


class ProductLookup(BaseModel):
    product_id: str
    name: str
    garment_type: str
    description: str
    colors: List[str]
    search_tags: List[str]
    image_url: str
    price: float = Field(ge=0)


class InventoryRecord(BaseModel):
    size: str
    quantity: int = Field(ge=0)
    in_stock: bool


class InventoryLookup(BaseModel):
    product_id: str
    product_name: str
    requested_size: Optional[str] = None
    sizes: List[InventoryRecord] = Field(default_factory=list)
    found: bool = True


class ChatReply(BaseModel):
    answer: str = Field(description="Helpful, concise response for the shopper")
    products: List[ProductCard] = Field(
        default_factory=list,
        description="Zero or more database-backed products relevant to the answer",
    )


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    page_context: Optional["PageContext"] = None


class PageContext(BaseModel):
    path: str = Field(max_length=300)
    current_product_id: Optional[str] = Field(default=None, max_length=120)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=200)


class PublicUser(BaseModel):
    id: int
    name: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class LoginReply(BaseModel):
    token: str
    user: PublicUser


class StoredChatMessage(BaseModel):
    role: str
    content: str
    products: List[ProductCard] = Field(default_factory=list)
    created_at: str


class AuditEntry(BaseModel):
    timestamp: datetime
    run_id: str
    iteration: int = Field(ge=1)
    mode: str
    tool_name: str
    arguments: Dict[str, str] = Field(default_factory=dict)
    result_summary: str
    stop_reason: str
