from fastapi import APIRouter
from adapters import list_adapters, get_adapter

router = APIRouter()

@router.get("/tools")
async def list_tools():
    return {"tools": list_adapters()}

@router.get("/tools/{tool_name}")
async def get_tool(tool_name: str):
    adapter = get_adapter(tool_name)
    if not adapter:
        return {"error": "Tool not found"}
    return adapter.get_metadata()

@router.post("/tools/{tool_name}/run")
async def run_tool(tool_name: str, target: str):
    adapter = get_adapter(tool_name)
    if not adapter:
        return {"error": "Tool not found"}
    if not adapter.validate_target(target):
        return {"error": "Invalid target"}
    result = await adapter.run(target)
    return result