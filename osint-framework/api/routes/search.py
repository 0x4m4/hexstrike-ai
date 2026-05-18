from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from sqlalchemy import select
import uuid

from core.database import db, Search

router = APIRouter()

class SearchRequest(BaseModel):
    target: str
    tools: List[str]
    options: Optional[Dict[str, Any]] = None

class SearchResponse(BaseModel):
    search_id: str
    status: str
    target: str
    tools: List[str]

@router.post("/search", response_model=SearchResponse)
async def create_search(req: SearchRequest):
    search_id = str(uuid.uuid4())
    search = Search(
        id=search_id,
        target=req.target,
        tools=req.tools,
        status="pending",
    )

    async with db.session_maker() as session:
        session.add(search)
        await session.commit()

    return SearchResponse(
        search_id=search.id,
        status=search.status,
        target=search.target,
        tools=search.tools,
    )

@router.get("/search/{search_id}")
async def get_search(search_id: str):
    async with db.session_maker() as session:
        search = await session.get(Search, search_id)

    if search is None:
        raise HTTPException(status_code=404, detail="Search not found")

    return {
        "search_id": search.id,
        "status": search.status,
        "target": search.target,
        "tools": search.tools,
        "results": [],
        "created_at": search.created_at.isoformat() if search.created_at else None,
        "completed_at": search.completed_at.isoformat() if search.completed_at else None,
    }

@router.get("/history")
async def get_history():
    async with db.session_maker() as session:
        result = await session.execute(select(Search).order_by(Search.created_at.desc()))
        searches = result.scalars().all()

    return {
        "searches": [
            {
                "search_id": search.id,
                "status": search.status,
                "target": search.target,
                "tools": search.tools,
                "created_at": search.created_at.isoformat() if search.created_at else None,
                "completed_at": search.completed_at.isoformat() if search.completed_at else None,
            }
            for search in searches
        ]
    }
