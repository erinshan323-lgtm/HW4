from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from pydantic_ai import RunContext

try:
    from .models import InventoryLookup, InventoryRecord, ProductLookup
except ImportError:
    from models import InventoryLookup, InventoryRecord, ProductLookup


@dataclass
class ShopDeps:
    database_path: Path
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    current_product_id: Optional[str] = None
    current_path: Optional[str] = None


def _connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def _image_url(image_file_path: str) -> str:
    return f"/product-images/{Path(image_file_path).name}"


def _product_from_row(row: sqlite3.Row) -> ProductLookup:
    item = dict(row)
    item["colors"] = json.loads(item["colors"])
    item["search_tags"] = json.loads(item["search_tags"])
    item["image_url"] = _image_url(item.pop("image_file_path"))
    return ProductLookup.model_validate(item)


def search_products(
    ctx: RunContext[ShopDeps],
    query: str,
    max_price: Optional[float] = None,
    garment_type: Optional[str] = None,
    limit: int = 6,
) -> List[ProductLookup]:
    """Search real catalogue rows by shopper language, price, and garment type."""
    terms = [term for term in query.lower().split() if len(term) > 1][:8]
    clauses = []
    parameters: List[object] = []
    for term in terms:
        pattern = f"%{term}%"
        clauses.append(
            "(LOWER(product_id) LIKE ? OR LOWER(name) LIKE ? OR LOWER(description) LIKE ? OR "
            "LOWER(search_tags) LIKE ? OR LOWER(colors) LIKE ?)"
        )
        parameters.extend([pattern] * 5)
    if max_price is not None:
        clauses.append("price <= ?")
        parameters.append(max_price)
    if garment_type:
        clauses.append("LOWER(garment_type) LIKE ?")
        parameters.append(f"%{garment_type.lower()}%")

    where = " AND ".join(clauses) if clauses else "1 = 1"
    parameters.append(min(max(limit, 1), 8))
    sql = f"""
        SELECT product_id, name, garment_type, description, colors,
               search_tags, image_file_path, price
        FROM catalogue
        WHERE {where}
        ORDER BY name
        LIMIT ?
    """
    with closing(_connect(ctx.deps.database_path)) as connection:
        rows = connection.execute(sql, parameters).fetchall()

    return [_product_from_row(row) for row in rows]


def get_product_details(
    ctx: RunContext[ShopDeps], product_id: str
) -> Optional[ProductLookup]:
    """Fetch one exact catalogue product for page-context and follow-up questions."""
    with closing(_connect(ctx.deps.database_path)) as connection:
        row = connection.execute(
            "SELECT product_id, name, garment_type, description, colors, "
            "search_tags, image_file_path, price FROM catalogue WHERE product_id = ?",
            (product_id,),
        ).fetchone()
    return _product_from_row(row) if row else None


def check_inventory(
    ctx: RunContext[ShopDeps], product_id: str, size: Optional[str] = None
) -> InventoryLookup:
    """Return authoritative size and quantity data for one catalogue product."""
    with closing(_connect(ctx.deps.database_path)) as connection:
        product = connection.execute(
            "SELECT name FROM catalogue WHERE product_id = ?", (product_id,)
        ).fetchone()
        if product is None:
            return InventoryLookup(
                product_id=product_id,
                product_name="Unknown product",
                requested_size=size,
                found=False,
            )
        if size:
            rows = connection.execute(
                "SELECT size, quantity FROM inventory "
                "WHERE product_id = ? AND LOWER(size) = LOWER(?) ORDER BY id",
                (product_id, size),
            ).fetchall()
            if not rows:
                return InventoryLookup(
                    product_id=product_id,
                    product_name=product["name"],
                    requested_size=size,
                    sizes=[InventoryRecord(size=size, quantity=0, in_stock=False)],
                )
        else:
            rows = connection.execute(
                "SELECT size, quantity FROM inventory WHERE product_id = ? ORDER BY id",
                (product_id,),
            ).fetchall()
    return InventoryLookup(
        product_id=product_id,
        product_name=product["name"],
        requested_size=size,
        sizes=[
            InventoryRecord(
                size=row["size"],
                quantity=row["quantity"],
                in_stock=row["quantity"] > 0,
            )
            for row in rows
        ],
    )


def find_in_stock_alternatives(
    ctx: RunContext[ShopDeps], product_id: str, size: str, limit: int = 3
) -> List[ProductLookup]:
    """Find similar products with positive stock in the shopper's requested size."""
    with closing(_connect(ctx.deps.database_path)) as connection:
        product = connection.execute(
            "SELECT garment_type FROM catalogue WHERE product_id = ?", (product_id,)
        ).fetchone()
        if product is None:
            return []
        rows = connection.execute(
            "SELECT c.product_id, c.name, c.garment_type, c.description, c.colors, "
            "c.search_tags, c.image_file_path, c.price "
            "FROM catalogue c JOIN inventory i ON i.product_id = c.product_id "
            "WHERE c.product_id <> ? AND c.garment_type = ? "
            "AND LOWER(i.size) = LOWER(?) AND i.quantity > 0 "
            "ORDER BY i.quantity DESC, c.name LIMIT ?",
            (product_id, product["garment_type"], size, min(max(limit, 1), 4)),
        ).fetchall()
    return [_product_from_row(row) for row in rows]
