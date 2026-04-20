# TEMPLATE: example
"""`items` API router.

Every DB-touching endpoint here uses `DbSession` (the `get_db_with_claims`
dependency). If you add a new endpoint, use the same dependency. The CI test
`tests/test_dependency_graph.py` will fail your PR if you don't.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession, get_current_user
from app.features.items.model import Item
from app.features.items.schema import ItemCreate, ItemOut

router = APIRouter(prefix="/items", tags=["items"])


@router.get("", response_model=list[ItemOut])
async def list_items(db: DbSession, user: CurrentUser) -> list[Item]:
    # RLS scopes this to the authenticated user; no explicit filter needed.
    # The filter is still added as defense-in-depth against a bad RLS policy.
    user_id = uuid.UUID(user["sub"])
    result = await db.execute(select(Item).where(Item.user_id == user_id))
    return list(result.scalars())


@router.post("", response_model=ItemOut, status_code=status.HTTP_201_CREATED)
async def create_item(payload: ItemCreate, db: DbSession, user: CurrentUser) -> Item:
    item = Item(
        user_id=uuid.UUID(user["sub"]),
        name=payload.name,
        description=payload.description,
    )
    db.add(item)
    # Flush so we get the server-generated id/created_at before returning.
    await db.flush()
    return item


@router.get("/{item_id}", response_model=ItemOut, dependencies=[Depends(get_current_user)])
async def get_item(item_id: uuid.UUID, db: DbSession) -> Item:
    # Auth runs via the route-level `dependencies` above; handler doesn't need
    # to bind the claims dict because RLS scopes the query automatically.
    item = await db.get(Item, item_id)
    # RLS blocks cross-user reads; `db.get` returning None is either
    # "doesn't exist" or "exists and belongs to another user" — surface one
    # answer so we don't leak existence.
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item
