import os
from pathlib import Path

class Config:
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.data_dir = self.base_dir / "data"
        self.data_dir.mkdir(exist_ok=True)
        
        self.db_url = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{self.data_dir}/osint.db")
        self.api_host = os.getenv("API_HOST", "0.0.0.0")
        self.api_port = int(os.getenv("API_PORT", "8000"))
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        
        # Auth
        self.api_keys_enabled = os.getenv("API_KEYS_ENABLED", "true").lower() == "true"
        self.local_auth_enabled = os.getenv("LOCAL_AUTH_ENABLED", "true").lower() == "true"
        
        # Tools
        self.tools_dir = self.base_dir.parent / "osint-tools" / "tools"
        
        # Workflow
        self.max_parallel = int(os.getenv("MAX_PARALLEL", "3"))
        self.timeout = int(os.getenv("TIMEOUT", "300"))

config = Config()