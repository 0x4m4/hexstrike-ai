from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uuid
from datetime import datetime

from core.database import db
from core.config import config
from api.routes import search, tools

@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_db()
    yield

app = FastAPI(title="OSINT Automation Framework", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search.router, prefix="/api/v1")
app.include_router(tools.router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "OSINT Automation Framework API", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy"}