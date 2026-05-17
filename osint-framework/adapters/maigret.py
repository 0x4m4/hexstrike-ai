import subprocess
import json
from typing import Dict, Any, Optional
from .base import ToolAdapter

class MaigretAdapter(ToolAdapter):
    def __init__(self):
        super().__init__("maigret", "username", "Deep username profiling across thousands of sites")
    
    def validate_target(self, target: str) -> bool:
        return len(target) > 0
    
    async def run(self, target: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            result = subprocess.run(
                ["python3", "-m", "maigret", target, "--json"],
                capture_output=True, text=True, timeout=300
            )
            return {"status": "success", "data": json.loads(result.stdout) if result.stdout else {}}
        except Exception as e:
            return {"status": "error", "error": str(e)}