from .base import ToolAdapter
from .maigret import MaigretAdapter
from .sherlock import SherlockAdapter
from .holehe import HoleheAdapter

# Registry of all available adapters
ADAPTERS = {
    "maigret": MaigretAdapter(),
    "sherlock": SherlockAdapter(),
    "holehe": HoleheAdapter(),
}

def get_adapter(name: str) -> ToolAdapter:
    return ADAPTERS.get(name)

def list_adapters():
    return [adapter.get_metadata() for adapter in ADAPTERS.values()]