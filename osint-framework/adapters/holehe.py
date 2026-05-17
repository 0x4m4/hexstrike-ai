import subprocess
from typing import Dict, Any, Optional
from .base import ToolAdapter

class HoleheAdapter(ToolAdapter):
    def __init__(self):
        super().__init__("holehe", "email", "Checks where an email is registered")
    
    def validate_target(self, target: str) -> bool:
        return "@" in target and "." in target
    
    async def run(self, target: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            result = subprocess.run(
                ["holehe", target],
                capture_output=True, text=True, timeout=300
            )
            return {"status": "success", "data": {"output": result.stdout}}
        except Exception as e:
            return {"status": "error", "error": str(e)}