"""
CLI entry point for Local AI Studio.

Usage:
    python -m local_ai_studio                 # Launch GUI (default)
    python -m local_ai_studio gui             # Launch GUI
    python -m local_ai_studio gui --port 8080 # GUI on custom port
    python -m local_ai_studio mcp             # Run MCP server
    python -m local_ai_studio chat            # Interactive CLI chat
    python -m local_ai_studio scan            # Scan for models
    python -m local_ai_studio info            # Show hardware info
    python -m local_ai_studio config          # Show current config
"""

import argparse
import json
import logging
import sys
from pathlib import Path

from local_ai_studio.config import StudioConfig, INFERENCE_PRESETS, SYSTEM_PROMPT_TEMPLATES


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def cmd_gui(args, config: StudioConfig) -> None:
    """Launch the Gradio web GUI."""
    from local_ai_studio.gui.app import StudioApp
    app = StudioApp(config)
    app.launch(
        host=args.host,
        port=args.port,
        share=args.share,
        inbrowser=not args.no_browser,
    )


def cmd_mcp(args, config: StudioConfig) -> None:
    """Run the MCP server."""
    from local_ai_studio.mcp.server import MCPServer
    from local_ai_studio.models.manager import ModelLoader
    from local_ai_studio.chat.engine import ChatEngine
    from local_ai_studio.tools.executor import ToolExecutor
    from local_ai_studio.tools.python_sandbox import create_python_tool, create_pip_install_tool
    from local_ai_studio.tools.filesystem import register_filesystem_tools
    from local_ai_studio.tools.web import register_web_tools
    from local_ai_studio.tools.database import register_database_tools
    from local_ai_studio.tools.git_tools import register_git_tools

    loader = ModelLoader(config)
    chat = ChatEngine(config, loader)
    chat.set_system_prompt(config.get_system_prompt())

    executor = ToolExecutor(config)
    executor.register(create_python_tool(config))
    executor.register(create_pip_install_tool(config))
    register_filesystem_tools(config, executor)
    register_web_tools(config, executor)
    register_database_tools(config, executor)
    register_git_tools(config, executor)

    server = MCPServer(config)
    server.set_model_loader(loader)
    server.set_chat_engine(chat)
    server.set_tool_executor(executor)

    print("Starting MCP server...")
    server.run()


def cmd_chat(args, config: StudioConfig) -> None:
    """Interactive CLI chat session."""
    from local_ai_studio.models.manager import ModelLoader, ModelRegistry
    from local_ai_studio.chat.engine import ChatEngine
    from local_ai_studio.chat.history import ConversationStore

    loader = ModelLoader(config)

    # Load model if specified
    if args.model:
        registry = ModelRegistry(config)
        registry.scan()
        card = registry.get_model(args.model)
        if card is None and Path(args.model).exists():
            from local_ai_studio.models.manager import ModelCard
            card = ModelCard(name=Path(args.model).stem, path=args.model, format="gguf")
        if card is None:
            print(f"Model not found: {args.model}")
            sys.exit(1)
        print(f"Loading {card.name}...")
        loader.load_gguf(
            card,
            gpu_layers=args.gpu_layers,
            context_length=args.context_length,
        )
        print(f"Model loaded: {card.name}")
    else:
        print("No model specified. Use --model <name_or_path> to load one.")
        print("Available models:")
        registry = ModelRegistry(config)
        for m in registry.scan():
            print(f"  - {m.name} ({m.quantization or m.format}, {m.size_bytes // 1048576} MB)")
        sys.exit(0)

    # Apply preset if specified
    if args.preset:
        config.apply_preset(args.preset)

    chat = ChatEngine(config, loader)
    prompt = args.system_prompt or config.get_system_prompt()
    chat.set_system_prompt(prompt)

    conv_store = ConversationStore(config.get("conversations_dir"))

    print(f"\nLocal AI Studio - CLI Chat")
    print(f"Model: {loader.current_model.card.name}")
    print(f"Preset: {config.get('inference.preset', 'balanced')}")
    print(f"Type /help for commands, /quit to exit\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            if _handle_cli_command(user_input, chat, conv_store, config, loader):
                continue
            if user_input == "/quit":
                break
            continue

        print("AI: ", end="", flush=True)
        try:
            for token in chat.send(user_input, stream=True):
                print(token, end="", flush=True)
            print()
        except Exception as e:
            print(f"\n[Error] {e}")


def _handle_cli_command(
    command: str, chat, conv_store, config, loader
) -> bool:
    """Handle CLI slash-commands. Returns True if command was handled."""
    parts = command.split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    if cmd == "/help":
        print("""
Commands:
  /help              Show this help
  /quit              Exit the chat
  /clear             Clear conversation history
  /save [tags]       Save conversation (comma-separated tags)
  /preset <name>     Switch inference preset (code/research/creative/roleplay/balanced)
  /system <prompt>   Change system prompt
  /template <name>   Apply a system prompt template
  /temp <value>      Set temperature
  /info              Show model and settings info
""")
        return True

    if cmd == "/clear":
        chat.clear()
        print("Conversation cleared.")
        return True

    if cmd == "/save":
        tags = [t.strip() for t in arg.split(",") if t.strip()] if arg else []
        model_name = loader.current_model.card.name if loader.current_model else ""
        conv_id = conv_store.save(
            messages=chat.get_messages(),
            tags=tags,
            model_name=model_name,
            system_prompt=config.get_system_prompt(),
            inference_preset=config.get("inference.preset", ""),
        )
        print(f"Saved as: {conv_id}")
        return True

    if cmd == "/preset":
        if config.apply_preset(arg):
            print(f"Applied preset: {arg}")
        else:
            print(f"Unknown preset. Available: {', '.join(INFERENCE_PRESETS.keys())}")
        return True

    if cmd == "/system":
        chat.set_system_prompt(arg)
        config.set("system_prompt.custom", arg)
        print("System prompt updated.")
        return True

    if cmd == "/template":
        if arg in SYSTEM_PROMPT_TEMPLATES:
            prompt = SYSTEM_PROMPT_TEMPLATES[arg]
            chat.set_system_prompt(prompt)
            config.set("system_prompt.template", arg)
            print(f"Applied template: {arg}")
        else:
            print(f"Unknown template. Available: {', '.join(SYSTEM_PROMPT_TEMPLATES.keys())}")
        return True

    if cmd == "/temp":
        try:
            temp = float(arg)
            config.set("inference.temperature", temp)
            print(f"Temperature set to {temp}")
        except ValueError:
            print("Usage: /temp <float>")
        return True

    if cmd == "/info":
        m = loader.current_model
        if m:
            print(f"Model: {m.card.name}")
            print(f"Backend: {m.backend}")
            print(f"GPU Layers: {m.gpu_layers}")
            print(f"Context: {m.context_length}")
        print(f"Preset: {config.get('inference.preset')}")
        print(f"Temperature: {config.get('inference.temperature')}")
        print(f"Messages: {len(chat.get_messages())}")
        return True

    if cmd == "/quit":
        print("Goodbye!")
        return False  # Signal to break the main loop

    print(f"Unknown command: {cmd}. Type /help for available commands.")
    return True


def cmd_scan(args, config: StudioConfig) -> None:
    """Scan for local models."""
    from local_ai_studio.models.manager import ModelRegistry
    registry = ModelRegistry(config)
    models = registry.scan()
    if not models:
        print(f"No models found in {config.get('models_dir')}")
        print("Place GGUF model files there, or use the GUI to download from HuggingFace.")
        return
    print(f"Found {len(models)} model(s):\n")
    for m in models:
        size_mb = m.size_bytes / 1048576
        print(f"  {m.name}")
        print(f"    Format: {m.format} | Quant: {m.quantization or 'N/A'} | Params: {m.parameter_count or 'N/A'}")
        print(f"    Size: {size_mb:.0f} MB | Architecture: {m.architecture or 'N/A'}")
        print(f"    Path: {m.path}")
        print()


def cmd_info(args, config: StudioConfig) -> None:
    """Show hardware information."""
    from local_ai_studio.hardware import build_hardware_profile, get_vram_usage, get_ram_usage

    profile = build_hardware_profile()
    vram = get_vram_usage()
    ram = get_ram_usage()

    print("=== Hardware Profile ===\n")
    print(f"GPU:  {profile.gpu.name}")
    if profile.gpu.cuda_available:
        print(f"  CUDA: {profile.gpu.cuda_version} (Driver: {profile.gpu.driver_version})")
        print(f"  VRAM: {vram['used_mb']} / {vram['total_mb']} MB ({vram['free_mb']} MB free)")
        if vram.get("temperature_c") is not None:
            print(f"  Temp: {vram['temperature_c']} C | Util: {vram.get('utilization_pct', 'N/A')}%")
    else:
        print("  CUDA: Not available")

    print(f"\nCPU:  {profile.cpu.name}")
    print(f"  Cores: {profile.cpu.cores_physical} physical / {profile.cpu.cores_logical} logical")
    print(f"  Architecture: {profile.cpu.architecture}")
    print(f"  ARM: {profile.cpu.is_arm}")

    print(f"\nRAM:  {ram['used_mb']} / {ram['total_mb']} MB ({ram['percent']}% used)")

    print(f"\n=== Recommendations ===")
    print(f"  Quantization: {profile.recommended_quant}")
    print(f"  Context Length: {profile.recommended_context_length}")
    print(f"  Batch Size: {profile.recommended_batch_size}")
    print(f"  Threads: {profile.recommended_threads}")
    print(f"  GPU Layers: {profile.recommended_gpu_layers} (-1 = auto)")


def cmd_config(args, config: StudioConfig) -> None:
    """Show or modify configuration."""
    if args.key and args.value:
        # Try to parse value as JSON, fall back to string
        try:
            value = json.loads(args.value)
        except json.JSONDecodeError:
            value = args.value
        config.set(args.key, value)
        print(f"Set {args.key} = {value}")
    elif args.key:
        val = config.get(args.key)
        print(f"{args.key} = {json.dumps(val, indent=2, default=str)}")
    else:
        print(json.dumps(config.data, indent=2, default=str))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Local AI Studio - Local AI Development Environment",
        prog="local_ai_studio",
    )
    parser.add_argument(
        "--config", type=str, default=None,
        help="Path to config.json file",
    )
    parser.add_argument(
        "--log-level", type=str, default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )

    subparsers = parser.add_subparsers(dest="command")

    # GUI subcommand
    gui_parser = subparsers.add_parser("gui", help="Launch the web GUI")
    gui_parser.add_argument("--host", type=str, default="127.0.0.1")
    gui_parser.add_argument("--port", type=int, default=7860)
    gui_parser.add_argument("--share", action="store_true", help="Create public Gradio link")
    gui_parser.add_argument("--no-browser", action="store_true", help="Don't open browser")

    # MCP subcommand
    subparsers.add_parser("mcp", help="Run MCP server")

    # Chat subcommand
    chat_parser = subparsers.add_parser("chat", help="Interactive CLI chat")
    chat_parser.add_argument("--model", type=str, help="Model name or path to load")
    chat_parser.add_argument("--preset", type=str, choices=list(INFERENCE_PRESETS.keys()))
    chat_parser.add_argument("--system-prompt", type=str, help="System prompt to use")
    chat_parser.add_argument("--gpu-layers", type=int, default=-1)
    chat_parser.add_argument("--context-length", type=int, default=8192)

    # Scan subcommand
    subparsers.add_parser("scan", help="Scan for local models")

    # Info subcommand
    subparsers.add_parser("info", help="Show hardware information")

    # Config subcommand
    config_parser = subparsers.add_parser("config", help="View/edit configuration")
    config_parser.add_argument("key", nargs="?", help="Config key (dot notation)")
    config_parser.add_argument("value", nargs="?", help="Value to set")

    args = parser.parse_args()
    setup_logging(args.log_level)
    config = StudioConfig(args.config)

    command_map = {
        "gui": cmd_gui,
        "mcp": cmd_mcp,
        "chat": cmd_chat,
        "scan": cmd_scan,
        "info": cmd_info,
        "config": cmd_config,
        None: cmd_gui,  # Default to GUI
    }

    handler = command_map.get(args.command, cmd_gui)
    handler(args, config)


if __name__ == "__main__":
    main()
