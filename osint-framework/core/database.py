from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, String, Integer, DateTime, Text, JSON
from datetime import datetime
import os

Base = declarative_base()

class Search(Base):
    __tablename__ = "searches"
    id = Column(String, primary_key=True)
    target = Column(String, nullable=False)
    tools = Column(JSON, nullable=False)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

class Result(Base):
    __tablename__ = "results"
    id = Column(String, primary_key=True)
    search_id = Column(String, nullable=False)
    tool = Column(String, nullable=False)
    data = Column(JSON, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

class Workflow(Base):
    __tablename__ = "workflows"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    steps = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="user")

class APIKey(Base):
    __tablename__ = "api_keys"
    id = Column(String, primary_key=True)
    key = Column(String, unique=True, nullable=False)
    user_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Database:
    def __init__(self, db_url: str = None):
        if db_url is None:
            # Default to data/osint.db
            data_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(data_dir, 'data', 'osint.db')
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            db_url = f"sqlite+aiosqlite:///{db_path}"
        
        self.engine = create_async_engine(db_url, echo=False)
        self.session_maker = sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
    
    async def init_db(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def create_session(self):
        return self.session_maker()

db = Database()