"""
Gradio web GUI for Local AI Studio.

Provides a full-featured browser interface with:
- Chat interface with streaming responses
- Model management (load, download, configure)
- Inference settings with presets
- Hardware monitoring (VRAM, RAM, GPU utilization)
- Tool configuration and execution log
- Conversation history management
- System prompt templates
"""

import json
import logging
import time
from pathlib import Path
from typing import Any, Optional

from local_ai_studio.config import (
    INFERENCE_PRESETS,
    SYSTEM_PROMPT_TEMPLATES,
    StudioConfig,
)
from local_ai_studio.hardware import (
    build_hardware_profile,
    get_ram_usage,
    get_vram_usage,
)
from local_ai_studio.models.manager import ModelLoader, ModelRegistry, OllamaManager
from local_ai_studio.models.quantization import (
    QUANT_FORMATS,
    estimate_model_size_mb,
    estimate_vram_mb,
    recommend_quantization,
)
from local_ai_studio.models.lora import LoRAManager
from local_ai_studio.chat.engine import ChatEngine
from local_ai_studio.chat.history import ConversationStore
from local_ai_studio.tools.executor import ToolExecutor
from local_ai_studio.tools.python_sandbox import create_python_tool, create_pip_install_tool
from local_ai_studio.tools.filesystem import register_filesystem_tools
from local_ai_studio.tools.web import register_web_tools
from local_ai_studio.tools.database import register_database_tools
from local_ai_studio.tools.git_tools import register_git_tools

logger = logging.getLogger(__name__)


class StudioApp:
    """Main application class that wires everything together and creates the Gradio UI."""

    def __init__(self, config: StudioConfig):
        self.config = config

        # Core components
        self.registry = ModelRegistry(config)
        self.loader = ModelLoader(config)
        self.lora_manager = LoRAManager(config)
        self.chat_engine = ChatEngine(config, self.loader)
        self.conv_store = ConversationStore(config.get("conversations_dir"))
        self.tool_executor = ToolExecutor(config)
        self._current_conv_id: Optional[str] = None

        # Register tools
        self._register_tools()

        # Set system prompt
        self.chat_engine.set_system_prompt(config.get_system_prompt())

    def _register_tools(self) -> None:
        self.tool_executor.register(create_python_tool(self.config))
        self.tool_executor.register(create_pip_install_tool(self.config))
        register_filesystem_tools(self.config, self.tool_executor)
        register_web_tools(self.config, self.tool_executor)
        register_database_tools(self.config, self.tool_executor)
        register_git_tools(self.config, self.tool_executor)
        self.chat_engine.set_tool_executor(self.tool_executor)

    def build_ui(self):
        """Build and return the Gradio Blocks interface."""
        try:
            import gradio as gr
        except ImportError:
            raise RuntimeError(
                "Gradio is required for the GUI. Install with: pip install gradio"
            )

        theme = gr.themes.Soft(
            primary_hue="blue",
            secondary_hue="slate",
            neutral_hue="slate",
        )

        with gr.Blocks(
            title="Local AI Studio",
            theme=theme,
            css=_CUSTOM_CSS,
        ) as app:
            gr.Markdown("# Local AI Studio", elem_classes=["studio-header"])
            gr.Markdown(
                "Fully local AI development environment | "
                "Optimized for RTX 5060 + Snapdragon X Plus",
                elem_classes=["studio-subtitle"],
            )

            with gr.Tabs() as tabs:
                # ============================================================
                # TAB 1: Chat
                # ============================================================
                with gr.Tab("Chat", id="chat"):
                    self._build_chat_tab(gr)

                # ============================================================
                # TAB 2: Models
                # ============================================================
                with gr.Tab("Models", id="models"):
                    self._build_models_tab(gr)

                # ============================================================
                # TAB 3: Settings
                # ============================================================
                with gr.Tab("Settings", id="settings"):
                    self._build_settings_tab(gr)

                # ============================================================
                # TAB 4: Tools
                # ============================================================
                with gr.Tab("Tools", id="tools"):
                    self._build_tools_tab(gr)

                # ============================================================
                # TAB 5: Hardware Monitor
                # ============================================================
                with gr.Tab("Hardware", id="hardware"):
                    self._build_hardware_tab(gr)

                # ============================================================
                # TAB 6: Conversations
                # ============================================================
                with gr.Tab("History", id="history"):
                    self._build_history_tab(gr)

        return app

    # ================================================================
    # Chat Tab
    # ================================================================
    def _build_chat_tab(self, gr) -> None:
        with gr.Row():
            with gr.Column(scale=4):
                chatbot = gr.Chatbot(
                    label="Conversation",
                    height=550,
                    type="messages",
                    show_copy_button=True,
                )
                with gr.Row():
                    msg_input = gr.Textbox(
                        placeholder="Type your message...",
                        show_label=False,
                        scale=8,
                        lines=2,
                        max_lines=10,
                    )
                    send_btn = gr.Button("Send", variant="primary", scale=1)
                    stop_btn = gr.Button("Stop", variant="stop", scale=1)

                with gr.Row():
                    clear_btn = gr.Button("Clear Chat")
                    save_btn = gr.Button("Save Conversation")
                    mode_dropdown = gr.Dropdown(
                        choices=list(INFERENCE_PRESETS.keys()),
                        value=self.config.get("inference.preset", "balanced"),
                        label="Mode",
                        scale=1,
                    )

            with gr.Column(scale=1):
                gr.Markdown("### Quick Settings")
                temperature = gr.Slider(0, 2, value=self.config.get("inference.temperature", 0.7), step=0.05, label="Temperature")
                max_tokens = gr.Slider(128, 8192, value=self.config.get("inference.max_tokens", 4096), step=128, label="Max Tokens")
                system_template = gr.Dropdown(
                    choices=["(custom)"] + list(SYSTEM_PROMPT_TEMPLATES.keys()),
                    value=self.config.get("system_prompt.template", "general"),
                    label="System Prompt Template",
                )
                system_prompt = gr.Textbox(
                    value=self.config.get_system_prompt(),
                    label="System Prompt",
                    lines=4,
                    max_lines=8,
                )
                model_status = gr.Textbox(
                    value=self._get_model_status(),
                    label="Active Model",
                    interactive=False,
                )
                save_tags = gr.Textbox(
                    placeholder="coding, project-x",
                    label="Tags (for save)",
                )

        # -- Event handlers --
        def user_send(message, history, temp, max_tok):
            if not message.strip():
                return "", history
            history = history or []
            history.append({"role": "user", "content": message})
            return "", history

        def bot_respond(history, temp, max_tok):
            if not history:
                return history
            if self.loader.current_model is None:
                history.append({"role": "assistant", "content": "[No model loaded. Go to the Models tab to load one.]"})
                yield history
                return

            user_msg = history[-1]["content"]
            self.config.set("inference.temperature", temp)
            self.config.set("inference.max_tokens", int(max_tok))

            try:
                response_gen = self.chat_engine.send(user_msg, stream=True)
                partial = ""
                history.append({"role": "assistant", "content": ""})
                for token in response_gen:
                    partial += token
                    history[-1]["content"] = partial
                    yield history
            except Exception as e:
                history.append({"role": "assistant", "content": f"[Error] {e}"})
                yield history

        def apply_mode(mode):
            self.config.apply_preset(mode)
            preset = INFERENCE_PRESETS.get(mode, {})
            return (
                preset.get("temperature", 0.7),
                preset.get("max_tokens", 4096),
            )

        def apply_template(template):
            if template == "(custom)":
                return ""
            prompt = SYSTEM_PROMPT_TEMPLATES.get(template, "")
            self.config.set("system_prompt.template", template)
            self.config.set("system_prompt.custom", "")
            self.chat_engine.set_system_prompt(prompt)
            return prompt

        def update_system_prompt(prompt):
            self.config.set("system_prompt.custom", prompt)
            self.chat_engine.set_system_prompt(prompt)

        def clear_chat():
            self.chat_engine.clear()
            return []

        def save_conversation(history, tags):
            if not history:
                return "Nothing to save"
            tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
            model_name = ""
            if self.loader.current_model:
                model_name = self.loader.current_model.card.name
            conv_id = self.conv_store.save(
                messages=self.chat_engine.get_messages(),
                tags=tag_list,
                mode=self.config.get("inference.preset", "general"),
                model_name=model_name,
                system_prompt=self.config.get_system_prompt(),
                inference_preset=self.config.get("inference.preset", ""),
                conversation_id=self._current_conv_id,
            )
            self._current_conv_id = conv_id
            return f"Saved as {conv_id}"

        send_event = send_btn.click(
            user_send, [msg_input, chatbot, temperature, max_tokens], [msg_input, chatbot],
        ).then(
            bot_respond, [chatbot, temperature, max_tokens], chatbot,
        )
        msg_input.submit(
            user_send, [msg_input, chatbot, temperature, max_tokens], [msg_input, chatbot],
        ).then(
            bot_respond, [chatbot, temperature, max_tokens], chatbot,
        )
        stop_btn.click(fn=None, cancels=[send_event])
        clear_btn.click(clear_chat, outputs=chatbot)
        save_btn.click(save_conversation, [chatbot, save_tags], model_status)
        mode_dropdown.change(apply_mode, mode_dropdown, [temperature, max_tokens])
        system_template.change(apply_template, system_template, system_prompt)
        system_prompt.blur(update_system_prompt, system_prompt)

    # ================================================================
    # Models Tab
    # ================================================================
    def _build_models_tab(self, gr) -> None:
        with gr.Row():
            with gr.Column(scale=2):
                gr.Markdown("### Local Models")
                model_list = gr.Dataframe(
                    value=self._get_model_table(),
                    headers=["Name", "Format", "Size (MB)", "Quant", "Params", "Architecture"],
                    label="Available Models",
                    interactive=False,
                )
                with gr.Row():
                    scan_btn = gr.Button("Scan Models Directory")
                    refresh_btn = gr.Button("Refresh")

                gr.Markdown("### Load Model")
                load_model_name = gr.Textbox(label="Model Name or Path", placeholder="e.g., mistral-7b-instruct-v0.2.Q4_K_M")
                with gr.Row():
                    gpu_layers = gr.Slider(-1, 100, value=-1, step=1, label="GPU Layers (-1=auto)")
                    ctx_length = gr.Slider(512, 32768, value=8192, step=512, label="Context Length")
                load_btn = gr.Button("Load Model", variant="primary")
                unload_btn = gr.Button("Unload Model")
                load_status = gr.Textbox(label="Status", interactive=False)

            with gr.Column(scale=1):
                gr.Markdown("### Download from HuggingFace")
                hf_search = gr.Textbox(label="Search HuggingFace", placeholder="e.g., TheBloke/Mistral-7B-GGUF")
                hf_search_btn = gr.Button("Search")
                hf_results = gr.Dataframe(
                    headers=["Repository", "Downloads"],
                    label="Search Results",
                    interactive=False,
                )
                hf_repo = gr.Textbox(label="Repository ID", placeholder="TheBloke/Mistral-7B-Instruct-v0.2-GGUF")
                hf_list_btn = gr.Button("List GGUF Files")
                hf_files = gr.Dropdown(label="Select File", choices=[])
                hf_download_btn = gr.Button("Download", variant="primary")
                download_status = gr.Textbox(label="Download Status", interactive=False)

                gr.Markdown("### Ollama Models")
                ollama_status = gr.Textbox(
                    value="Available" if OllamaManager.is_available() else "Not installed",
                    label="Ollama Status",
                    interactive=False,
                )
                ollama_list = gr.Dataframe(
                    value=self._get_ollama_models(),
                    headers=["Name", "Size"],
                    label="Ollama Models",
                    interactive=False,
                )

        # -- Quantization Info --
        with gr.Accordion("Quantization Reference", open=False):
            quant_data = [
                [name, f"{qf.bits_per_weight:.1f}", qf.description, qf.recommended_min_vram_mb, qf.quality_rating]
                for name, qf in QUANT_FORMATS.items()
            ]
            gr.Dataframe(
                value=quant_data,
                headers=["Format", "Bits/Weight", "Description", "Min VRAM (7B)", "Quality"],
                interactive=False,
            )

        # -- Events --
        def scan_models():
            models = self.registry.scan()
            return self._get_model_table()

        def load_model(name, layers, ctx):
            card = self.registry.get_model(name)
            if card is None:
                # Try as direct path
                if Path(name).exists():
                    from local_ai_studio.models.manager import ModelCard
                    card = ModelCard(name=Path(name).stem, path=name, format="gguf")
                else:
                    return f"Model not found: {name}"
            try:
                self.loader.load_gguf(card, gpu_layers=int(layers), context_length=int(ctx))
                return f"Loaded: {card.name} (GPU layers: {layers}, ctx: {ctx})"
            except Exception as e:
                return f"Load failed: {e}"

        def unload_model():
            self.loader.unload()
            return "Model unloaded"

        def search_hf(query):
            try:
                from local_ai_studio.models.manager import ModelDownloader
                results = ModelDownloader.search_hf_models(query)
                return [[r["id"], r.get("downloads", 0)] for r in results]
            except Exception as e:
                return [[f"Error: {e}", ""]]

        def list_hf_files(repo):
            try:
                from local_ai_studio.models.manager import ModelDownloader
                files = ModelDownloader.list_repo_files(repo)
                return gr.update(choices=files, value=files[0] if files else None)
            except Exception as e:
                return gr.update(choices=[f"Error: {e}"])

        def download_hf(repo, filename):
            if not repo or not filename:
                return "Please select a repository and file"
            try:
                from local_ai_studio.models.manager import ModelDownloader
                path = ModelDownloader.download_from_hf(
                    repo, filename, self.config.get("models_dir")
                )
                self.registry.scan()
                return f"Downloaded to: {path}"
            except Exception as e:
                return f"Download failed: {e}"

        scan_btn.click(scan_models, outputs=model_list)
        refresh_btn.click(lambda: self._get_model_table(), outputs=model_list)
        load_btn.click(load_model, [load_model_name, gpu_layers, ctx_length], load_status)
        unload_btn.click(unload_model, outputs=load_status)
        hf_search_btn.click(search_hf, hf_search, hf_results)
        hf_list_btn.click(list_hf_files, hf_repo, hf_files)
        hf_download_btn.click(download_hf, [hf_repo, hf_files], download_status)

    # ================================================================
    # Settings Tab
    # ================================================================
    def _build_settings_tab(self, gr) -> None:
        with gr.Row():
            with gr.Column():
                gr.Markdown("### Inference Parameters")
                preset_dropdown = gr.Dropdown(
                    choices=list(INFERENCE_PRESETS.keys()),
                    value=self.config.get("inference.preset", "balanced"),
                    label="Preset",
                )
                temperature = gr.Slider(0, 2, value=self.config.get("inference.temperature", 0.7), step=0.05, label="Temperature")
                top_p = gr.Slider(0, 1, value=self.config.get("inference.top_p", 0.9), step=0.01, label="Top-P")
                top_k = gr.Slider(1, 200, value=self.config.get("inference.top_k", 50), step=1, label="Top-K")
                rep_penalty = gr.Slider(1.0, 2.0, value=self.config.get("inference.repetition_penalty", 1.1), step=0.01, label="Repetition Penalty")
                max_tokens = gr.Slider(128, 8192, value=self.config.get("inference.max_tokens", 4096), step=128, label="Max Tokens")
                ctx_length = gr.Slider(512, 32768, value=self.config.get("inference.context_length", 8192), step=512, label="Context Length")

                save_settings_btn = gr.Button("Save Inference Settings", variant="primary")
                settings_status = gr.Textbox(label="Status", interactive=False)

            with gr.Column():
                gr.Markdown("### Hardware Configuration")
                gpu_layers = gr.Slider(-1, 100, value=self.config.get("hardware.gpu_layers", -1), step=1, label="GPU Layers (-1=auto)")
                cpu_threads = gr.Slider(0, 32, value=self.config.get("hardware.cpu_threads", 0), step=1, label="CPU Threads (0=auto)")
                batch_size = gr.Slider(32, 2048, value=self.config.get("hardware.batch_size", 512), step=32, label="Batch Size")
                use_mmap = gr.Checkbox(value=self.config.get("hardware.use_mmap", True), label="Use Memory-Mapped Files")
                cpu_fallback = gr.Checkbox(value=self.config.get("hardware.cpu_fallback", True), label="CPU Fallback")

                save_hw_btn = gr.Button("Save Hardware Settings", variant="primary")
                hw_status = gr.Textbox(label="Status", interactive=False)

                gr.Markdown("### Profile Management")
                profile_name = gr.Textbox(label="Profile Name", placeholder="e.g., coding_session")
                export_btn = gr.Button("Export Profile")
                import_file = gr.File(label="Import Profile (.json)")
                import_btn = gr.Button("Import Profile")
                profile_status = gr.Textbox(label="Status", interactive=False)

        # -- Events --
        def apply_preset(preset):
            self.config.apply_preset(preset)
            p = INFERENCE_PRESETS.get(preset, {})
            return (
                p.get("temperature", 0.7),
                p.get("top_p", 0.9),
                p.get("top_k", 50),
                p.get("repetition_penalty", 1.1),
                p.get("max_tokens", 4096),
            )

        def save_inference(temp, tp, tk, rp, mt, cl):
            self.config.set("inference.temperature", temp)
            self.config.set("inference.top_p", tp)
            self.config.set("inference.top_k", int(tk))
            self.config.set("inference.repetition_penalty", rp)
            self.config.set("inference.max_tokens", int(mt))
            self.config.set("inference.context_length", int(cl))
            return "Inference settings saved"

        def save_hw(gl, ct, bs, mm, cf):
            self.config.set("hardware.gpu_layers", int(gl))
            self.config.set("hardware.cpu_threads", int(ct))
            self.config.set("hardware.batch_size", int(bs))
            self.config.set("hardware.use_mmap", mm)
            self.config.set("hardware.cpu_fallback", cf)
            return "Hardware settings saved"

        def export_profile(name):
            if not name.strip():
                return "Please enter a profile name"
            path = self.config.export_profile(name.strip())
            return f"Profile exported to: {path}"

        def import_profile(file):
            if file is None:
                return "No file selected"
            self.config.import_profile(file.name)
            return "Profile imported successfully"

        preset_dropdown.change(apply_preset, preset_dropdown, [temperature, top_p, top_k, rep_penalty, max_tokens])
        save_settings_btn.click(save_inference, [temperature, top_p, top_k, rep_penalty, max_tokens, ctx_length], settings_status)
        save_hw_btn.click(save_hw, [gpu_layers, cpu_threads, batch_size, use_mmap, cpu_fallback], hw_status)
        export_btn.click(export_profile, profile_name, profile_status)
        import_btn.click(import_profile, import_file, profile_status)

    # ================================================================
    # Tools Tab
    # ================================================================
    def _build_tools_tab(self, gr) -> None:
        with gr.Row():
            with gr.Column():
                gr.Markdown("### Tool Configuration")
                tools_data = []
                for tool in self.tool_executor.list_tools():
                    tools_data.append([tool.name, tool.category, tool.description[:80]])
                gr.Dataframe(
                    value=tools_data,
                    headers=["Name", "Category", "Description"],
                    label="Registered Tools",
                    interactive=False,
                )

                gr.Markdown("### Tool Permissions")
                python_enabled = gr.Checkbox(value=self.config.get("tools.python_sandbox.enabled", True), label="Python Sandbox")
                fs_enabled = gr.Checkbox(value=self.config.get("tools.filesystem.enabled", True), label="Filesystem Access")
                web_enabled = gr.Checkbox(value=self.config.get("tools.web.enabled", True), label="Web/API Access")
                db_enabled = gr.Checkbox(value=self.config.get("tools.database.enabled", True), label="Database Access")
                git_enabled = gr.Checkbox(value=self.config.get("tools.git.enabled", True), label="Git Operations")
                shell_enabled = gr.Checkbox(value=self.config.get("tools.shell.enabled", False), label="Shell Commands (Advanced)")
                save_tools_btn = gr.Button("Save Tool Permissions", variant="primary")
                tools_status = gr.Textbox(label="Status", interactive=False)

            with gr.Column():
                gr.Markdown("### Test Tool Execution")
                tool_name = gr.Dropdown(
                    choices=[t.name for t in self.tool_executor.list_tools()],
                    label="Tool",
                )
                tool_input = gr.Code(label="Input (JSON)", language="json", value="{}")
                run_tool_btn = gr.Button("Execute Tool", variant="primary")
                tool_output = gr.Textbox(label="Output", lines=10, interactive=False)

                gr.Markdown("### Recent Tool Calls")
                tool_history = gr.Dataframe(
                    headers=["Tool", "Success", "Duration (ms)", "Error"],
                    label="Execution Log",
                    interactive=False,
                )
                refresh_history_btn = gr.Button("Refresh Log")

        def save_tool_perms(py, fs, web, db, git, shell):
            self.config.set("tools.python_sandbox.enabled", py)
            self.config.set("tools.filesystem.enabled", fs)
            self.config.set("tools.web.enabled", web)
            self.config.set("tools.database.enabled", db)
            self.config.set("tools.git.enabled", git)
            self.config.set("tools.shell.enabled", shell)
            return "Tool permissions saved"

        def execute_tool(name, inp):
            try:
                inputs = json.loads(inp)
            except json.JSONDecodeError:
                return "Invalid JSON input"
            result = self.tool_executor.execute(name, inputs)
            if result.success:
                return result.output
            return f"Error: {result.error}"

        def get_tool_history():
            history = self.tool_executor.get_history(50)
            return [
                [h.name, str(h.success), f"{h.duration_ms:.0f}", h.error[:50]]
                for h in history
            ]

        save_tools_btn.click(
            save_tool_perms,
            [python_enabled, fs_enabled, web_enabled, db_enabled, git_enabled, shell_enabled],
            tools_status,
        )
        run_tool_btn.click(execute_tool, [tool_name, tool_input], tool_output)
        refresh_history_btn.click(get_tool_history, outputs=tool_history)

    # ================================================================
    # Hardware Monitor Tab
    # ================================================================
    def _build_hardware_tab(self, gr) -> None:
        with gr.Row():
            with gr.Column():
                gr.Markdown("### GPU Status")
                gpu_name = gr.Textbox(label="GPU", interactive=False)
                vram_bar = gr.Slider(0, 100, label="VRAM Usage (%)", interactive=False)
                vram_detail = gr.Textbox(label="VRAM Detail", interactive=False)
                gpu_temp = gr.Textbox(label="Temperature", interactive=False)
                gpu_util = gr.Textbox(label="GPU Utilization", interactive=False)
                gpu_power = gr.Textbox(label="Power Draw", interactive=False)

            with gr.Column():
                gr.Markdown("### CPU / RAM Status")
                cpu_name = gr.Textbox(label="CPU", interactive=False)
                ram_bar = gr.Slider(0, 100, label="RAM Usage (%)", interactive=False)
                ram_detail = gr.Textbox(label="RAM Detail", interactive=False)
                cpu_cores = gr.Textbox(label="CPU Cores", interactive=False)
                cpu_arch = gr.Textbox(label="Architecture", interactive=False)

            with gr.Column():
                gr.Markdown("### Recommendations")
                rec_quant = gr.Textbox(label="Recommended Quantization", interactive=False)
                rec_ctx = gr.Textbox(label="Recommended Context Length", interactive=False)
                rec_batch = gr.Textbox(label="Recommended Batch Size", interactive=False)
                rec_threads = gr.Textbox(label="Recommended Threads", interactive=False)

        refresh_hw_btn = gr.Button("Refresh Hardware Info", variant="primary")

        def refresh_hardware():
            profile = build_hardware_profile()
            vram = get_vram_usage()
            ram = get_ram_usage()
            vram_pct = (vram["used_mb"] / vram["total_mb"] * 100) if vram["total_mb"] > 0 else 0
            return (
                profile.gpu.name,
                vram_pct,
                f"{vram['used_mb']} / {vram['total_mb']} MB ({vram['free_mb']} MB free)",
                f"{vram.get('temperature_c', 'N/A')} C",
                f"{vram.get('utilization_pct', 'N/A')} %",
                f"{vram.get('power_draw_w', 'N/A')} W",
                profile.cpu.name,
                ram["percent"],
                f"{ram['used_mb']} / {ram['total_mb']} MB ({ram['available_mb']} MB available)",
                f"{profile.cpu.cores_physical} physical / {profile.cpu.cores_logical} logical",
                profile.cpu.architecture,
                profile.recommended_quant,
                str(profile.recommended_context_length),
                str(profile.recommended_batch_size),
                str(profile.recommended_threads),
            )

        refresh_hw_btn.click(
            refresh_hardware,
            outputs=[
                gpu_name, vram_bar, vram_detail, gpu_temp, gpu_util, gpu_power,
                cpu_name, ram_bar, ram_detail, cpu_cores, cpu_arch,
                rec_quant, rec_ctx, rec_batch, rec_threads,
            ],
        )


    # ================================================================
    # History Tab
    # ================================================================
    def _build_history_tab(self, gr) -> None:
        with gr.Row():
            with gr.Column(scale=2):
                gr.Markdown("### Saved Conversations")
                with gr.Row():
                    search_input = gr.Textbox(placeholder="Search conversations...", label="Search", scale=3)
                    tag_filter = gr.Dropdown(
                        choices=["(all)"] + self.conv_store.get_all_tags(),
                        value="(all)",
                        label="Tag Filter",
                        scale=1,
                    )
                    mode_filter = gr.Dropdown(
                        choices=["(all)", "code", "research", "creative", "roleplay", "general"],
                        value="(all)",
                        label="Mode Filter",
                        scale=1,
                    )
                    search_btn = gr.Button("Search", scale=1)

                conv_table = gr.Dataframe(
                    value=self._get_conversation_table(),
                    headers=["ID", "Title", "Mode", "Tags", "Messages", "Updated"],
                    label="Conversations",
                    interactive=False,
                )

            with gr.Column(scale=1):
                gr.Markdown("### Actions")
                conv_id_input = gr.Textbox(label="Conversation ID")
                load_conv_btn = gr.Button("Load Conversation")
                delete_conv_btn = gr.Button("Delete Conversation", variant="stop")
                export_json_btn = gr.Button("Export as JSON")
                export_md_btn = gr.Button("Export as Markdown")
                action_status = gr.Textbox(label="Status", interactive=False)
                export_output = gr.Code(label="Export Output", language="json")

        def search_conversations(search, tag, mode):
            tag_val = None if tag == "(all)" else tag
            mode_val = None if mode == "(all)" else mode
            convs = self.conv_store.list_conversations(
                tag=tag_val, mode=mode_val, search=search or None,
            )
            return [
                [c.id, c.title[:50], c.mode, ", ".join(c.tags), c.message_count,
                 time.strftime("%Y-%m-%d %H:%M", time.localtime(c.updated_at))]
                for c in convs
            ]

        def load_conversation(conv_id):
            conv = self.conv_store.load(conv_id)
            if conv is None:
                return "Conversation not found"
            self.chat_engine.set_messages(conv.messages)
            self._current_conv_id = conv_id
            if conv.meta.system_prompt:
                self.chat_engine.set_system_prompt(conv.meta.system_prompt)
            if conv.meta.inference_preset:
                self.config.apply_preset(conv.meta.inference_preset)
            return f"Loaded conversation: {conv.meta.title}"

        def delete_conversation(conv_id):
            if self.conv_store.delete(conv_id):
                return "Deleted"
            return "Not found"

        def export_json(conv_id):
            result = self.conv_store.export_conversation(conv_id, "json")
            return result or "Not found", self._get_conversation_table()

        def export_md(conv_id):
            result = self.conv_store.export_conversation(conv_id, "markdown")
            return result or "Not found", self._get_conversation_table()

        search_btn.click(search_conversations, [search_input, tag_filter, mode_filter], conv_table)
        load_conv_btn.click(load_conversation, conv_id_input, action_status)
        delete_conv_btn.click(delete_conversation, conv_id_input, action_status)
        export_json_btn.click(export_json, conv_id_input, [export_output, conv_table])
        export_md_btn.click(export_md, conv_id_input, [export_output, conv_table])

    # ================================================================
    # Helpers
    # ================================================================
    def _get_model_status(self) -> str:
        if self.loader.current_model:
            m = self.loader.current_model
            return f"{m.card.name} ({m.card.quantization or m.card.format})"
        return "No model loaded"

    def _get_model_table(self) -> list[list]:
        models = self.registry.list_models()
        if not models:
            self.registry.scan()
            models = self.registry.list_models()
        return [
            [m.name, m.format, f"{m.size_bytes / 1048576:.0f}", m.quantization, m.parameter_count, m.architecture]
            for m in models
        ]

    def _get_ollama_models(self) -> list[list]:
        models = OllamaManager.list_models()
        return [[m["name"], m.get("size", "")] for m in models]

    def _get_conversation_table(self) -> list[list]:
        convs = self.conv_store.list_conversations()
        return [
            [c.id, c.title[:50], c.mode, ", ".join(c.tags), c.message_count,
             time.strftime("%Y-%m-%d %H:%M", time.localtime(c.updated_at))]
            for c in convs
        ]

    def launch(self, **kwargs) -> None:
        """Build and launch the Gradio app."""
        gui_cfg = self.config.get("gui", {})
        app = self.build_ui()
        app.launch(
            server_name=kwargs.get("host", gui_cfg.get("host", "127.0.0.1")),
            server_port=kwargs.get("port", gui_cfg.get("port", 7860)),
            share=kwargs.get("share", gui_cfg.get("share", False)),
            inbrowser=kwargs.get("inbrowser", True),
        )


# ================================================================
# Custom CSS for dark theme
# ================================================================
_CUSTOM_CSS = """
.studio-header {
    text-align: center;
    margin-bottom: 0 !important;
}
.studio-subtitle {
    text-align: center;
    opacity: 0.7;
    margin-top: 0 !important;
    margin-bottom: 1rem !important;
}
.dark .gradio-container {
    background-color: #1a1a2e;
}
"""
