from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class ToolAdapter(ABC):
    """Base class for OSINT tool adapters"""
    
    def __init__(self, name: str, category: str, description: str):
        self.name = name
        self.category = category
        self.description = description
    
    @abstractmethod
    async def run(self, target: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Run the tool and return results"""
        pass
    
    @abstractmethod
    def validate_target(self, target: str) -> bool:
        """Validate the target format"""
        pass
    
    def get_metadata(self) -> Dict[str, str]:
        return {
            "name": self.name,
            "category": self.category,
            "description": self.description
        }