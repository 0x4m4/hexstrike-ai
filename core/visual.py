"""
ModernVisualEngine - Beautiful, modern output formatting with animations and colors

This module provides visual formatting capabilities for the HexStrike framework,
including banners, progress bars, vulnerability cards, error messages, and more.
"""

import os
from typing import Dict, Any


# API Configuration - imported from environment variables
API_PORT = int(os.environ.get('HEXSTRIKE_PORT', 8888))
API_HOST = os.environ.get('HEXSTRIKE_HOST', '127.0.0.1')


class ModernVisualEngine:
    """Beautiful, modern output formatting with animations and colors"""

    # Enhanced color palette with reddish tones and better highlighting
    COLORS = {
        'MATRIX_GREEN': '\033[38;5;46m',
        'NEON_BLUE': '\033[38;5;51m',
        'ELECTRIC_PURPLE': '\033[38;5;129m',
        'CYBER_ORANGE': '\033[38;5;208m',
        'HACKER_RED': '\033[38;5;196m',
        'TERMINAL_GRAY': '\033[38;5;240m',
        'BRIGHT_WHITE': '\033[97m',
        'RESET': '\033[0m',
        'BOLD': '\033[1m',
        'DIM': '\033[2m',
        # New reddish tones and highlighting colors
        'BLOOD_RED': '\033[38;5;124m',
        'CRIMSON': '\033[38;5;160m',
        'DARK_RED': '\033[38;5;88m',
        'FIRE_RED': '\033[38;5;202m',
        'ROSE_RED': '\033[38;5;167m',
        'BURGUNDY': '\033[38;5;52m',
        'SCARLET': '\033[38;5;197m',
        'RUBY': '\033[38;5;161m',
    # Unified theme primary/secondary (used going forward instead of legacy blue/green accents)
    'PRIMARY_BORDER': '\033[38;5;160m',  # CRIMSON
    'ACCENT_LINE': '\033[38;5;196m',      # HACKER_RED
    'ACCENT_GRADIENT': '\033[38;5;124m',  # BLOOD_RED (for subtle alternation)
        # Highlighting colors
        'HIGHLIGHT_RED': '\033[48;5;196m\033[38;5;15m',  # Red background, white text
        'HIGHLIGHT_YELLOW': '\033[48;5;226m\033[38;5;16m',  # Yellow background, black text
        'HIGHLIGHT_GREEN': '\033[48;5;46m\033[38;5;16m',  # Green background, black text
        'HIGHLIGHT_BLUE': '\033[48;5;51m\033[38;5;16m',  # Blue background, black text
        'HIGHLIGHT_PURPLE': '\033[48;5;129m\033[38;5;15m',  # Purple background, white text
        # Status colors with reddish tones
        'SUCCESS': '\033[38;5;46m',  # Bright green
        'WARNING': '\033[38;5;208m',  # Orange
        'ERROR': '\033[38;5;196m',  # Bright red
        'CRITICAL': '\033[48;5;196m\033[38;5;15m\033[1m',  # Red background, white bold text
        'INFO': '\033[38;5;51m',  # Cyan
        'DEBUG': '\033[38;5;240m',  # Gray
        # Vulnerability severity colors
        'VULN_CRITICAL': '\033[48;5;124m\033[38;5;15m\033[1m',  # Dark red background
        'VULN_HIGH': '\033[38;5;196m\033[1m',  # Bright red bold
        'VULN_MEDIUM': '\033[38;5;208m\033[1m',  # Orange bold
        'VULN_LOW': '\033[38;5;226m',  # Yellow
        'VULN_INFO': '\033[38;5;51m',  # Cyan
        # Tool status colors
        'TOOL_RUNNING': '\033[38;5;46m\033[5m',  # Blinking green
        'TOOL_SUCCESS': '\033[38;5;46m\033[1m',  # Bold green
        'TOOL_FAILED': '\033[38;5;196m\033[1m',  # Bold red
        'TOOL_TIMEOUT': '\033[38;5;208m\033[1m',  # Bold orange
        'TOOL_RECOVERY': '\033[38;5;129m\033[1m',  # Bold purple
        # Progress and animation colors
        'PROGRESS_BAR': '\033[38;5;46m',  # Green
        'PROGRESS_EMPTY': '\033[38;5;240m',  # Gray
        'SPINNER': '\033[38;5;51m',  # Cyan
        'PULSE': '\033[38;5;196m\033[5m'  # Blinking red
    }

    # Progress animation styles
    PROGRESS_STYLES = {
        'dots': ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'],
        'bars': ['▁', '▂', '▃', '▄', '▅', '▆', '▇', '█'],
        'arrows': ['←', '↖', '↑', '↗', '→', '↘', '↓', '↙'],
        'pulse': ['●', '◐', '◑', '◒', '◓', '◔', '◕', '◖', '◗', '◘']
    }

    @staticmethod
    def create_banner() -> str:
        """Create the enhanced HexStrike banner"""
        # Build a blood-red themed border using primary/gradient alternation
        border_color = ModernVisualEngine.COLORS['PRIMARY_BORDER']
        accent = ModernVisualEngine.COLORS['ACCENT_LINE']
        gradient = ModernVisualEngine.COLORS['ACCENT_GRADIENT']
        RESET = ModernVisualEngine.COLORS['RESET']
        BOLD = ModernVisualEngine.COLORS['BOLD']
        title_block = f"{accent}{BOLD}"
        banner = f"""
{title_block}
██╗  ██╗███████╗██╗  ██╗███████╗████████╗██████╗ ██╗██╗  ██╗███████╗
██║  ██║██╔════╝╚██╗██╔╝██╔════╝╚══██╔══╝██╔══██╗██║██║ ██╔╝██╔════╝
███████║█████╗   ╚███╔╝ ███████╗   ██║   ██████╔╝██║█████╔╝ █████╗
██╔══██║██╔══╝   ██╔██╗ ╚════██║   ██║   ██╔══██╗██║██╔═██╗ ██╔══╝
██║  ██║███████╗██╔╝ ██╗███████║   ██║   ██║  ██║██║██║  ██╗███████╗
╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝╚═╝  ╚═╝╚══════╝
{RESET}
{border_color}┌─────────────────────────────────────────────────────────────────────┐
│  {ModernVisualEngine.COLORS['BRIGHT_WHITE']}🚀 HexStrike AI - Blood-Red Offensive Intelligence Core{border_color}        │
│  {accent}⚡ AI-Automated Recon | Exploitation | Analysis Pipeline{border_color}          │
│  {gradient}🎯 Bug Bounty | CTF | Red Team | Zero-Day Research{border_color}              │
└─────────────────────────────────────────────────────────────────────┘{RESET}

{ModernVisualEngine.COLORS['TERMINAL_GRAY']}[INFO] Server starting on {API_HOST}:{API_PORT}
[INFO] 150+ integrated modules | Adaptive AI decision engine active
[INFO] Blood-red theme engaged – unified offensive operations UI{RESET}
"""
        return banner

    @staticmethod
    def create_progress_bar(current: int, total: int, width: int = 50, tool: str = "") -> str:
        """Create a beautiful progress bar with cyberpunk styling"""
        if total == 0:
            percentage = 0
        else:
            percentage = min(100, (current / total) * 100)

        filled = int(width * percentage / 100)
        bar = '█' * filled + '░' * (width - filled)

        border = ModernVisualEngine.COLORS['PRIMARY_BORDER']
        fill_col = ModernVisualEngine.COLORS['ACCENT_LINE']
        return f"""
{border}┌─ {tool} ─{'─' * (width - len(tool) - 4)}┐
│ {fill_col}{bar}{border} │ {percentage:6.1f}%
└─{'─' * (width + 10)}┘{ModernVisualEngine.COLORS['RESET']}"""

    @staticmethod
    def render_progress_bar(progress: float, width: int = 40, style: str = 'cyber',
                          label: str = "", eta: float = 0, speed: str = "") -> str:
        """Render a beautiful progress bar with multiple styles"""

        # Clamp progress between 0 and 1
        progress = max(0.0, min(1.0, progress))

        # Calculate filled and empty portions
        filled_width = int(width * progress)
        empty_width = width - filled_width

        # Style-specific rendering
        if style == 'cyber':
            filled_char = '█'
            empty_char = '░'
            bar_color = ModernVisualEngine.COLORS['ACCENT_LINE']
            progress_color = ModernVisualEngine.COLORS['PRIMARY_BORDER']
        elif style == 'matrix':
            filled_char = '▓'
            empty_char = '▒'
            bar_color = ModernVisualEngine.COLORS['ACCENT_LINE']
            progress_color = ModernVisualEngine.COLORS['ACCENT_GRADIENT']
        elif style == 'neon':
            filled_char = '━'
            empty_char = '─'
            bar_color = ModernVisualEngine.COLORS['PRIMARY_BORDER']
            progress_color = ModernVisualEngine.COLORS['CYBER_ORANGE']
        else:  # default
            filled_char = '█'
            empty_char = '░'
            bar_color = ModernVisualEngine.COLORS['ACCENT_LINE']
            progress_color = ModernVisualEngine.COLORS['PRIMARY_BORDER']

        # Build the progress bar
        filled_part = bar_color + filled_char * filled_width
        empty_part = ModernVisualEngine.COLORS['TERMINAL_GRAY'] + empty_char * empty_width
        percentage = f"{progress * 100:.1f}%"

        # Add ETA and speed if provided
        extra_info = ""
        if eta > 0:
            extra_info += f" ETA: {eta:.1f}s"
        if speed:
            extra_info += f" Speed: {speed}"

        # Build final progress bar
        bar_display = f"[{filled_part}{empty_part}{ModernVisualEngine.COLORS['RESET']}] {progress_color}{percentage}{ModernVisualEngine.COLORS['RESET']}"

        if label:
            return f"{label}: {bar_display}{extra_info}"
        else:
            return f"{bar_display}{extra_info}"

    @staticmethod
    def create_live_dashboard(processes: Dict[int, Dict[str, Any]]) -> str:
        """Create a live dashboard showing all active processes"""

        if not processes:
            return f"""
{ModernVisualEngine.COLORS['PRIMARY_BORDER']}╭─────────────────────────────────────────────────────────────────────────────╮
│ {ModernVisualEngine.COLORS['ACCENT_LINE']}📊 HEXSTRIKE LIVE DASHBOARD{ModernVisualEngine.COLORS['PRIMARY_BORDER']}                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│ {ModernVisualEngine.COLORS['TERMINAL_GRAY']}No active processes currently running{ModernVisualEngine.COLORS['PRIMARY_BORDER']}                                    │
╰─────────────────────────────────────────────────────────────────────────────╯{ModernVisualEngine.COLORS['RESET']}
"""

        dashboard_lines = [
            f"{ModernVisualEngine.COLORS['PRIMARY_BORDER']}╭─────────────────────────────────────────────────────────────────────────────╮",
            f"│ {ModernVisualEngine.COLORS['ACCENT_LINE']}📊 HEXSTRIKE LIVE DASHBOARD{ModernVisualEngine.COLORS['PRIMARY_BORDER']}                                           │",
            f"├─────────────────────────────────────────────────────────────────────────────┤"
        ]

        for pid, proc_info in processes.items():
            status = proc_info.get('status', 'unknown')
            command = proc_info.get('command', 'unknown')[:50] + "..." if len(proc_info.get('command', '')) > 50 else proc_info.get('command', 'unknown')
            duration = proc_info.get('duration', 0)

            status_color = ModernVisualEngine.COLORS['ACCENT_LINE'] if status == 'running' else ModernVisualEngine.COLORS['HACKER_RED']

            dashboard_lines.append(
                f"│ {ModernVisualEngine.COLORS['CYBER_ORANGE']}PID {pid}{ModernVisualEngine.COLORS['PRIMARY_BORDER']} | {status_color}{status}{ModernVisualEngine.COLORS['PRIMARY_BORDER']} | {ModernVisualEngine.COLORS['BRIGHT_WHITE']}{command}{ModernVisualEngine.COLORS['PRIMARY_BORDER']} │"
            )

        dashboard_lines.append(f"╰─────────────────────────────────────────────────────────────────────────────╯{ModernVisualEngine.COLORS['RESET']}")

        return "\n".join(dashboard_lines)

    @staticmethod
    def format_vulnerability_card(vuln_data: Dict[str, Any]) -> str:
        """Format vulnerability as a beautiful card"""
        severity = vuln_data.get('severity', 'unknown').upper()
        name = vuln_data.get('name', 'Unknown Vulnerability')
        description = vuln_data.get('description', 'No description available')

        # Severity color mapping
        severity_colors = {
            'CRITICAL': ModernVisualEngine.COLORS['VULN_CRITICAL'],
            'HIGH': ModernVisualEngine.COLORS['HACKER_RED'],
            'MEDIUM': ModernVisualEngine.COLORS['ACCENT_GRADIENT'],
            'LOW': ModernVisualEngine.COLORS['CYBER_ORANGE'],
            'INFO': ModernVisualEngine.COLORS['TERMINAL_GRAY']
        }

        color = severity_colors.get(severity, ModernVisualEngine.COLORS['TERMINAL_GRAY'])

        return f"""
{color}┌─ 🚨 VULNERABILITY DETECTED ─────────────────────────────────────┐
│ {ModernVisualEngine.COLORS['BRIGHT_WHITE']}{name:<60}{color} │
│ {ModernVisualEngine.COLORS['TERMINAL_GRAY']}Severity: {color}{severity:<52}{color} │
│ {ModernVisualEngine.COLORS['TERMINAL_GRAY']}{description[:58]:<58}{color} │
└─────────────────────────────────────────────────────────────────┘{ModernVisualEngine.COLORS['RESET']}"""

    @staticmethod
    def format_error_card(error_type: str, tool_name: str, error_message: str, recovery_action: str = "") -> str:
        """Format error information as a highlighted card with reddish tones"""
        error_colors = {
            'CRITICAL': ModernVisualEngine.COLORS['VULN_CRITICAL'],
            'ERROR': ModernVisualEngine.COLORS['TOOL_FAILED'],
            'TIMEOUT': ModernVisualEngine.COLORS['TOOL_TIMEOUT'],
            'RECOVERY': ModernVisualEngine.COLORS['TOOL_RECOVERY'],
            'WARNING': ModernVisualEngine.COLORS['WARNING']
        }

        color = error_colors.get(error_type.upper(), ModernVisualEngine.COLORS['ERROR'])

        card = f"""
{color}┌─ 🔥 ERROR DETECTED ─────────────────────────────────────────────┐{ModernVisualEngine.COLORS['RESET']}
{color}│ {ModernVisualEngine.COLORS['BRIGHT_WHITE']}Tool: {tool_name:<55}{color} │{ModernVisualEngine.COLORS['RESET']}
{color}│ {ModernVisualEngine.COLORS['BRIGHT_WHITE']}Type: {error_type:<55}{color} │{ModernVisualEngine.COLORS['RESET']}
{color}│ {ModernVisualEngine.COLORS['BRIGHT_WHITE']}Error: {error_message[:53]:<53}{color} │{ModernVisualEngine.COLORS['RESET']}"""

        if recovery_action:
            card += f"""
{color}│ {ModernVisualEngine.COLORS['TOOL_RECOVERY']}Recovery: {recovery_action[:50]:<50}{color} │{ModernVisualEngine.COLORS['RESET']}"""

        card += f"""
{color}└─────────────────────────────────────────────────────────────────┘{ModernVisualEngine.COLORS['RESET']}"""

        return card

    @staticmethod
    def format_tool_status(tool_name: str, status: str, target: str = "", progress: float = 0.0) -> str:
        """Format tool execution status with enhanced highlighting"""
        status_colors = {
            'RUNNING': ModernVisualEngine.COLORS['TOOL_RUNNING'],
            'SUCCESS': ModernVisualEngine.COLORS['TOOL_SUCCESS'],
            'FAILED': ModernVisualEngine.COLORS['TOOL_FAILED'],
            'TIMEOUT': ModernVisualEngine.COLORS['TOOL_TIMEOUT'],
            'RECOVERY': ModernVisualEngine.COLORS['TOOL_RECOVERY']
        }

        color = status_colors.get(status.upper(), ModernVisualEngine.COLORS['INFO'])

        # Create progress bar if progress > 0
        progress_bar = ""
        if progress > 0:
            filled = int(20 * progress)
            empty = 20 - filled
            progress_bar = f" [{ModernVisualEngine.COLORS['PROGRESS_BAR']}{'█' * filled}{ModernVisualEngine.COLORS['PROGRESS_EMPTY']}{'░' * empty}{ModernVisualEngine.COLORS['RESET']}] {progress*100:.1f}%"

        return f"{color}🔧 {tool_name.upper()}{ModernVisualEngine.COLORS['RESET']} | {color}{status}{ModernVisualEngine.COLORS['RESET']} | {ModernVisualEngine.COLORS['BRIGHT_WHITE']}{target}{ModernVisualEngine.COLORS['RESET']}{progress_bar}"

    @staticmethod
    def format_highlighted_text(text: str, highlight_type: str = "RED") -> str:
        """Format text with highlighting background"""
        highlight_colors = {
            'RED': ModernVisualEngine.COLORS['HIGHLIGHT_RED'],
            'YELLOW': ModernVisualEngine.COLORS['HIGHLIGHT_YELLOW'],
            'GREEN': ModernVisualEngine.COLORS['HIGHLIGHT_GREEN'],
            'BLUE': ModernVisualEngine.COLORS['HIGHLIGHT_BLUE'],
            'PURPLE': ModernVisualEngine.COLORS['HIGHLIGHT_PURPLE']
        }

        color = highlight_colors.get(highlight_type.upper(), ModernVisualEngine.COLORS['HIGHLIGHT_RED'])
        return f"{color} {text} {ModernVisualEngine.COLORS['RESET']}"

    @staticmethod
    def format_vulnerability_severity(severity: str, count: int = 0) -> str:
        """Format vulnerability severity with appropriate colors"""
        severity_colors = {
            'CRITICAL': ModernVisualEngine.COLORS['VULN_CRITICAL'],
            'HIGH': ModernVisualEngine.COLORS['VULN_HIGH'],
            'MEDIUM': ModernVisualEngine.COLORS['VULN_MEDIUM'],
            'LOW': ModernVisualEngine.COLORS['VULN_LOW'],
            'INFO': ModernVisualEngine.COLORS['VULN_INFO']
        }

        color = severity_colors.get(severity.upper(), ModernVisualEngine.COLORS['INFO'])
        count_text = f" ({count})" if count > 0 else ""

        return f"{color}{severity.upper()}{count_text}{ModernVisualEngine.COLORS['RESET']}"

    @staticmethod
    def create_section_header(title: str, icon: str = "🔥", color: str = "FIRE_RED") -> str:
        """Create a section header with reddish styling"""
        header_color = ModernVisualEngine.COLORS.get(color, ModernVisualEngine.COLORS['FIRE_RED'])

        return f"""
{header_color}{'═' * 70}{ModernVisualEngine.COLORS['RESET']}
{header_color}{icon} {title.upper()}{ModernVisualEngine.COLORS['RESET']}
{header_color}{'═' * 70}{ModernVisualEngine.COLORS['RESET']}"""

    @staticmethod
    def format_command_execution(command: str, status: str, duration: float = 0.0) -> str:
        """Format command execution with enhanced styling"""
        status_colors = {
            'STARTING': ModernVisualEngine.COLORS['INFO'],
            'RUNNING': ModernVisualEngine.COLORS['TOOL_RUNNING'],
            'SUCCESS': ModernVisualEngine.COLORS['TOOL_SUCCESS'],
            'FAILED': ModernVisualEngine.COLORS['TOOL_FAILED'],
            'TIMEOUT': ModernVisualEngine.COLORS['TOOL_TIMEOUT']
        }

        color = status_colors.get(status.upper(), ModernVisualEngine.COLORS['INFO'])
        duration_text = f" ({duration:.2f}s)" if duration > 0 else ""

        return f"{color}▶ {command[:60]}{'...' if len(command) > 60 else ''} | {status.upper()}{duration_text}{ModernVisualEngine.COLORS['RESET']}"
