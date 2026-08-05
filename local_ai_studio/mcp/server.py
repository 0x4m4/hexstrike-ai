"""
MCP (Model Context Protocol) server implementation.

Provides a standards-compliant MCP server that exposes the local AI studio's
capabilities (chat, tools, model management) to external clients such as
IDEs, productivity apps, and other MCP-compatible tools.

Uses the fastmcp library for protocol handling.
"""

import json
import logging
from typing import Any, Optional

from local_ai_studio.config import StudioConfig

logger = logging.getLogger(__name__)


class MCPServer:
    """MCP server that bridges the local AI studio with external clients.

    Exposes resources (models, conversations) and tools (chat, code execution,
    file operations) via the Model Context Protocol.
    """

    def __init__(self, config: StudioConfig):
        self.config = config
        self._app = None
        self._model_loader = None
        self._chat_engine = None
        self._tool_executor = None

    def set_model_loader(self, loader) -> None:
        self._model_loader = loader

    def set_chat_engine(self, engine) -> None:
        self._chat_engine = engine

    def set_tool_executor(self, executor) -> None:
        self._tool_executor = executor

    def create_app(self):
        """Create and configure the MCP FastMCP application."""
        try:
            from mcp.server.fastmcp import FastMCP
        except ImportError:
            raise RuntimeError(
                "fastmcp is required for MCP support. Install with: pip install fastmcp"
            )

        mcp_cfg = self.config.get("mcp", {})
        self._app = FastMCP(
            "Local AI Studio",
            description="Local AI development environment with model management, chat, and tool execution",
        )

        self._register_resources()
        self._register_tools()
        self._register_prompts()

        return self._app

    def run(self) -> None:
        """Run the MCP server."""
        if self._app is None:
            self.create_app()
        self._app.run()

    # -- Resources -----------------------------------------------------------

    def _register_resources(self) -> None:
        app = self._app

        @app.resource("studio://models")
        def list_models() -> str:
            """List all available local models."""
            if self._model_loader is None:
                return json.dumps({"error": "Model loader not initialized"})
            from local_ai_studio.models.manager import ModelRegistry
            registry = ModelRegistry(self.config)
            models = registry.list_models()
            return json.dumps([
                {
                    "name": m.name,
                    "path": m.path,
                    "format": m.format,
                    "size_bytes": m.size_bytes,
                    "quantization": m.quantization,
                    "parameter_count": m.parameter_count,
                    "architecture": m.architecture,
                    "tags": m.tags,
                }
                for m in models
            ], indent=2)

        @app.resource("studio://model/active")
        def active_model() -> str:
            """Get information about the currently loaded model."""
            if self._model_loader is None or self._model_loader.current_model is None:
                return json.dumps({"status": "no model loaded"})
            m = self._model_loader.current_model
            return json.dumps({
                "name": m.card.name,
                "path": m.card.path,
                "backend": m.backend,
                "gpu_layers": m.gpu_layers,
                "context_length": m.context_length,
                "lora_adapters": m.lora_adapters,
            }, indent=2)

        @app.resource("studio://config")
        def get_config() -> str:
            """Get the current studio configuration."""
            return json.dumps(self.config.data, indent=2, default=str)

        @app.resource("studio://hardware")
        def hardware_info() -> str:
            """Get hardware information and status."""
            from local_ai_studio.hardware import build_hardware_profile, get_vram_usage, get_ram_usage
            profile = build_hardware_profile()
            return json.dumps({
                "gpu": {
                    "name": profile.gpu.name,
                    "vram_total_mb": profile.gpu.vram_total_mb,
                    "vram_free_mb": profile.gpu.vram_free_mb,
                    "cuda_available": profile.gpu.cuda_available,
                    "utilization_pct": profile.gpu.utilization_pct,
                    "temperature_c": profile.gpu.temperature_c,
                },
                "cpu": {
                    "name": profile.cpu.name,
                    "cores": profile.cpu.cores_logical,
                    "architecture": profile.cpu.architecture,
                },
                "ram": get_ram_usage(),
                "recommendations": {
                    "gpu_layers": profile.recommended_gpu_layers,
                    "threads": profile.recommended_threads,
                    "batch_size": profile.recommended_batch_size,
                    "context_length": profile.recommended_context_length,
                    "quantization": profile.recommended_quant,
                },
            }, indent=2)

        @app.resource("studio://tools")
        def list_tools() -> str:
            """List available tools and their status."""
            if self._tool_executor is None:
                return json.dumps({"error": "Tool executor not initialized"})
            tools = self._tool_executor.list_tools()
            return json.dumps([
                {
                    "name": t.name,
                    "description": t.description,
                    "category": t.category,
                    "parameters": t.parameters,
                }
                for t in tools
            ], indent=2)

    # -- Tools ---------------------------------------------------------------

    def _register_tools(self) -> None:
        app = self._app

        @app.tool()
        def chat(message: str, system_prompt: str = "", temperature: float = 0.7) -> str:
            """Send a message to the AI and get a response."""
            if self._chat_engine is None:
                return json.dumps({"error": "Chat engine not initialized"})
            if system_prompt:
                self._chat_engine.set_system_prompt(system_prompt)
            try:
                response = self._chat_engine.send(message, stream=False, temperature=temperature)
                return response
            except Exception as e:
                return json.dumps({"error": str(e)})

        @app.tool()
        def execute_tool(tool_name: str, tool_input: str = "{}") -> str:
            """Execute a registered tool by name."""
            if self._tool_executor is None:
                return json.dumps({"error": "Tool executor not initialized"})
            try:
                inputs = json.loads(tool_input)
            except json.JSONDecodeError:
                return json.dumps({"error": "Invalid JSON input"})
            result = self._tool_executor.execute(tool_name, inputs)
            return json.dumps({
                "success": result.success,
                "output": result.output,
                "error": result.error,
                "duration_ms": result.duration_ms,
            }, indent=2)

        @app.tool()
        def run_python(code: str) -> str:
            """Execute Python code in the sandbox."""
            if self._tool_executor is None:
                return json.dumps({"error": "Tool executor not initialized"})
            result = self._tool_executor.execute("python_execute", {"code": code})
            return result.output if result.success else f"Error: {result.error}"

        @app.tool()
        def load_model(model_name: str, gpu_layers: int = -1, context_length: int = 8192) -> str:
            """Load a model by name or path."""
            if self._model_loader is None:
                return json.dumps({"error": "Model loader not initialized"})
            from local_ai_studio.models.manager import ModelRegistry
            registry = ModelRegistry(self.config)
            card = registry.get_model(model_name)
            if card is None:
                return json.dumps({"error": f"Model not found: {model_name}"})
            try:
                self._model_loader.load_gguf(card, gpu_layers=gpu_layers, context_length=context_length)
                return json.dumps({"status": "loaded", "model": card.name})
            except Exception as e:
                return json.dumps({"error": str(e)})

        @app.tool()
        def set_inference_preset(preset: str) -> str:
            """Switch inference settings to a named preset (code, research, creative, roleplay, balanced)."""
            success = self.config.apply_preset(preset)
            if success:
                return json.dumps({"status": "applied", "preset": preset})
            from local_ai_studio.config import INFERENCE_PRESETS
            return json.dumps({
                "error": f"Unknown preset: {preset}",
                "available": list(INFERENCE_PRESETS.keys()),
            })

        @app.tool()
        def get_conversation_history(limit: int = 20) -> str:
            """Get recent conversation messages."""
            if self._chat_engine is None:
                return json.dumps({"error": "Chat engine not initialized"})
            messages = self._chat_engine.get_messages()[-limit:]
            return json.dumps([m.to_dict() for m in messages], indent=2, default=str)

        @app.tool()
        def clear_conversation() -> str:
            """Clear the current conversation history."""
            if self._chat_engine is None:
                return json.dumps({"error": "Chat engine not initialized"})
            self._chat_engine.clear()
            return json.dumps({"status": "cleared"})

    # -- Prompts -------------------------------------------------------------

    def _register_prompts(self) -> None:
        app = self._app

        @app.prompt()
        def code_review(code: str, language: str = "python") -> str:
            """Generate a code review prompt."""
            return (
                f"Please review the following {language} code. Identify bugs, "
                f"performance issues, security concerns, and suggest improvements:\n\n"
                f"```{language}\n{code}\n```"
            )

        @app.prompt()
        def explain_code(code: str, language: str = "python") -> str:
            """Generate a code explanation prompt."""
            return (
                f"Please explain the following {language} code in detail. "
                f"Describe what it does, how it works, and any important patterns used:\n\n"
                f"```{language}\n{code}\n```"
            )

        @app.prompt()
        def research_query(topic: str, depth: str = "thorough") -> str:
            """Generate a structured research prompt."""
            return (
                f"Please provide a {depth} analysis of the following topic. "
                f"Include key concepts, current state, advantages/disadvantages, "
                f"and relevant citations where possible:\n\n"
                f"Topic: {topic}"
            )

        @app.prompt()
        def creative_writing(genre: str, premise: str, style: str = "literary") -> str:
            """Generate a creative writing prompt."""
            return (
                f"Write a {style} {genre} based on the following premise. "
                f"Focus on vivid descriptions, strong character development, "
                f"and engaging narrative flow:\n\n"
                f"Premise: {premise}"
            )
