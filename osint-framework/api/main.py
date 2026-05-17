from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import uuid
from datetime import datetime
import os

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

# Web static files
web_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web')
app.mount("/static", StaticFiles(directory=os.path.join(web_dir, 'static')), name="static")
templates = Jinja2Templates(directory=os.path.join(web_dir, 'templates'))

@app.get("/", include_in_schema=False)
async def root():
    return FileResponse(os.path.join(web_dir, 'templates', 'index.html'))

@app.get("/health")
async def health():
    return {"status": "healthy"}