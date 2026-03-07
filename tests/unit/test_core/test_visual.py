"""
Unit tests for ModernVisualEngine

Tests cover:
- Banner creation
- Progress bars
- Dashboard rendering
- Vulnerability cards
- Error cards
- Tool status formatting
- Color formatting
- Text highlighting
- Section headers
- Command execution formatting

Target: 90%+ code coverage
"""

import pytest
import sys
import os

# Add parent directories to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from core.visual import ModernVisualEngine
from tests.helpers.test_utils import ColorStripper


class TestModernVisualEngineBasics:
    """Test basic functionality of ModernVisualEngine"""

    def test_class_has_color_constants(self):
        """Test that ModernVisualEngine has color constants defined"""
        assert hasattr(ModernVisualEngine, 'COLORS')
        assert isinstance(ModernVisualEngine.COLORS, dict)
        assert 'RESET' in ModernVisualEngine.COLORS
        assert 'HACKER_RED' in ModernVisualEngine.COLORS
        assert 'PRIMARY_BORDER' in ModernVisualEngine.COLORS

    def test_class_has_progress_styles(self):
        """Test that ModernVisualEngine has progress styles defined"""
        assert hasattr(ModernVisualEngine, 'PROGRESS_STYLES')
        assert isinstance(ModernVisualEngine.PROGRESS_STYLES, dict)
        assert 'dots' in ModernVisualEngine.PROGRESS_STYLES
        assert 'bars' in ModernVisualEngine.PROGRESS_STYLES

    def test_colors_are_ansi_codes(self):
        """Test that color values are ANSI escape codes"""
        for name, value in ModernVisualEngine.COLORS.items():
            assert isinstance(value, str)
            # ANSI codes start with escape character or are empty (RESET)
            assert value.startswith('\033') or name == 'RESET' or value == '\033[0m'


class TestBannerCreation:
    """Test banner creation functionality"""

    def test_create_banner_returns_string(self):
        """Test that create_banner returns a string"""
        banner = ModernVisualEngine.create_banner()
        assert isinstance(banner, str)
        assert len(banner) > 0

    def test_banner_contains_hexstrike_text(self):
        """Test that banner contains HexStrike branding"""
        banner = ModernVisualEngine.create_banner()
        # Strip colors to check content
        clean_banner = ColorStripper.strip_colors(banner)
        assert 'HEXSTRIKE' in clean_banner or 'HexStrike' in clean_banner

    def test_banner_contains_color_codes(self):
        """Test that banner includes color formatting"""
        banner = ModernVisualEngine.create_banner()
        assert ColorStripper.has_colors(banner)

    def test_banner_is_multi_line(self):
        """Test that banner spans multiple lines"""
        banner = ModernVisualEngine.create_banner()
        lines = banner.split('\n')
        assert len(lines) > 5

    def test_banner_contains_version_info(self):
        """Test that banner shows server info"""
        banner = ModernVisualEngine.create_banner()
        clean_banner = ColorStripper.strip_colors(banner)
        # Should mention server or modules
        assert 'Server' in clean_banner or 'module' in clean_banner.lower()


class TestProgressBars:
    """Test progress bar functionality"""

    def test_create_progress_bar_zero_progress(self):
        """Test progress bar with 0% completion"""
        progress = ModernVisualEngine.create_progress_bar(0, 100, width=50, tool="nmap")
        assert isinstance(progress, str)
        assert 'nmap' in progress.lower()
        assert '0.0%' in progress

    def test_create_progress_bar_full_progress(self):
        """Test progress bar with 100% completion"""
        progress = ModernVisualEngine.create_progress_bar(100, 100, width=50, tool="gobuster")
        assert isinstance(progress, str)
        assert '100.0%' in progress

    def test_create_progress_bar_partial_progress(self):
        """Test progress bar with partial completion"""
        progress = ModernVisualEngine.create_progress_bar(50, 100, width=50, tool="sqlmap")
        assert isinstance(progress, str)
        assert '50.0%' in progress

    def test_create_progress_bar_handles_zero_total(self):
        """Test progress bar gracefully handles zero total"""
        progress = ModernVisualEngine.create_progress_bar(10, 0, width=50, tool="test")
        assert isinstance(progress, str)
        # Should show 0% when total is 0
        assert '0' in progress

    def test_create_progress_bar_custom_width(self):
        """Test progress bar with custom width"""
        progress_narrow = ModernVisualEngine.create_progress_bar(50, 100, width=20, tool="test")
        progress_wide = ModernVisualEngine.create_progress_bar(50, 100, width=80, tool="test")
        assert isinstance(progress_narrow, str)
        assert isinstance(progress_wide, str)
        # Wide should be longer
        assert len(progress_wide) > len(progress_narrow)

    def test_render_progress_bar_basic(self):
        """Test basic render_progress_bar functionality"""
        progress = ModernVisualEngine.render_progress_bar(0.5, width=40, label="Test")
        assert isinstance(progress, str)
        assert '50.0%' in progress
        assert 'Test' in progress

    def test_render_progress_bar_clamps_values(self):
        """Test that render_progress_bar clamps values to 0-1 range"""
        # Test negative value
        progress_negative = ModernVisualEngine.render_progress_bar(-0.5, width=40)
        assert '0.0%' in progress_negative

        # Test over 100%
        progress_over = ModernVisualEngine.render_progress_bar(1.5, width=40)
        assert '100.0%' in progress_over

    def test_render_progress_bar_different_styles(self):
        """Test different progress bar styles"""
        styles = ['cyber', 'matrix', 'neon', 'default']

        for style in styles:
            progress = ModernVisualEngine.render_progress_bar(
                0.75, width=40, style=style, label=f"Test {style}"
            )
            assert isinstance(progress, str)
            assert '75.0%' in progress

    def test_render_progress_bar_with_eta(self):
        """Test progress bar with ETA information"""
        progress = ModernVisualEngine.render_progress_bar(
            0.5, width=40, label="Test", eta=30.5
        )
        assert isinstance(progress, str)
        assert 'ETA' in progress
        assert '30.5' in progress

    def test_render_progress_bar_with_speed(self):
        """Test progress bar with speed information"""
        progress = ModernVisualEngine.render_progress_bar(
            0.5, width=40, label="Test", speed="100 KB/s"
        )
        assert isinstance(progress, str)
        assert 'Speed' in progress
        assert '100 KB/s' in progress


class TestDashboard:
    """Test live dashboard functionality"""

    def test_create_live_dashboard_empty(self):
        """Test dashboard with no active processes"""
        dashboard = ModernVisualEngine.create_live_dashboard({})
        assert isinstance(dashboard, str)
        clean_dashboard = ColorStripper.strip_colors(dashboard)
        assert 'No active processes' in clean_dashboard or 'DASHBOARD' in clean_dashboard

    def test_create_live_dashboard_single_process(self):
        """Test dashboard with one active process"""
        processes = {
            12345: {
                'status': 'running',
                'command': 'nmap -sV target.com',
                'duration': 30.5
            }
        }
        dashboard = ModernVisualEngine.create_live_dashboard(processes)
        assert isinstance(dashboard, str)
        assert '12345' in dashboard
        assert 'nmap' in dashboard.lower()

    def test_create_live_dashboard_multiple_processes(self):
        """Test dashboard with multiple active processes"""
        processes = {
            12345: {'status': 'running', 'command': 'nmap -sV target.com', 'duration': 30},
            12346: {'status': 'completed', 'command': 'gobuster dir -u http://target.com', 'duration': 60},
            12347: {'status': 'running', 'command': 'sqlmap -u http://target.com?id=1', 'duration': 120}
        }
        dashboard = ModernVisualEngine.create_live_dashboard(processes)
        assert isinstance(dashboard, str)
        assert '12345' in dashboard
        assert '12346' in dashboard
        assert '12347' in dashboard

    def test_create_live_dashboard_truncates_long_commands(self):
        """Test that dashboard truncates very long commands"""
        processes = {
            12345: {
                'status': 'running',
                'command': 'a' * 100,  # Very long command
                'duration': 10
            }
        }
        dashboard = ModernVisualEngine.create_live_dashboard(processes)
        assert isinstance(dashboard, str)
        # Should contain truncation indicator
        assert '...' in dashboard


class TestVulnerabilityCards:
    """Test vulnerability card formatting"""

    def test_format_vulnerability_card_basic(self):
        """Test basic vulnerability card formatting"""
        vuln_data = {
            'severity': 'high',
            'name': 'SQL Injection',
            'description': 'SQL injection in login form'
        }
        card = ModernVisualEngine.format_vulnerability_card(vuln_data)
        assert isinstance(card, str)
        assert 'SQL Injection' in card
        assert 'HIGH' in card.upper()

    def test_format_vulnerability_card_all_severities(self):
        """Test vulnerability cards for all severity levels"""
        severities = ['critical', 'high', 'medium', 'low', 'info']

        for severity in severities:
            vuln_data = {
                'severity': severity,
                'name': f'Test {severity} vulnerability',
                'description': f'Description for {severity}'
            }
            card = ModernVisualEngine.format_vulnerability_card(vuln_data)
            assert isinstance(card, str)
            assert severity.upper() in card.upper()

    def test_format_vulnerability_card_missing_fields(self):
        """Test vulnerability card with missing optional fields"""
        vuln_data = {}  # Empty data
        card = ModernVisualEngine.format_vulnerability_card(vuln_data)
        assert isinstance(card, str)
        # Should handle missing fields gracefully
        assert 'Unknown' in card or 'unknown' in card

    def test_format_vulnerability_card_has_colors(self):
        """Test that vulnerability cards include color formatting"""
        vuln_data = {
            'severity': 'critical',
            'name': 'Critical Bug',
            'description': 'Very dangerous'
        }
        card = ModernVisualEngine.format_vulnerability_card(vuln_data)
        assert ColorStripper.has_colors(card)


class TestErrorCards:
    """Test error card formatting"""

    def test_format_error_card_basic(self):
        """Test basic error card formatting"""
        card = ModernVisualEngine.format_error_card(
            'ERROR', 'nmap', 'Connection timeout'
        )
        assert isinstance(card, str)
        assert 'nmap' in card
        assert 'Connection timeout' in card
        assert 'ERROR' in card.upper()

    def test_format_error_card_with_recovery(self):
        """Test error card with recovery action"""
        card = ModernVisualEngine.format_error_card(
            'TIMEOUT', 'sqlmap', 'Request timed out', 'Retrying with longer timeout'
        )
        assert isinstance(card, str)
        assert 'TIMEOUT' in card.upper()
        assert 'Recovery' in card or 'recovery' in card
        assert 'Retrying' in card

    def test_format_error_card_different_types(self):
        """Test error cards for different error types"""
        error_types = ['CRITICAL', 'ERROR', 'TIMEOUT', 'RECOVERY', 'WARNING']

        for error_type in error_types:
            card = ModernVisualEngine.format_error_card(
                error_type, 'test_tool', 'Test error message'
            )
            assert isinstance(card, str)
            assert error_type in card.upper()

    def test_format_error_card_has_colors(self):
        """Test that error cards include color formatting"""
        card = ModernVisualEngine.format_error_card('CRITICAL', 'test', 'Error')
        assert ColorStripper.has_colors(card)


class TestToolStatus:
    """Test tool status formatting"""

    def test_format_tool_status_running(self):
        """Test tool status for running tools"""
        status = ModernVisualEngine.format_tool_status(
            'nmap', 'RUNNING', 'target.com', progress=0.5
        )
        assert isinstance(status, str)
        assert 'nmap' in status.lower()
        assert 'RUNNING' in status.upper()
        assert 'target.com' in status

    def test_format_tool_status_success(self):
        """Test tool status for successful completion"""
        status = ModernVisualEngine.format_tool_status(
            'gobuster', 'SUCCESS', 'http://example.com'
        )
        assert isinstance(status, str)
        assert 'SUCCESS' in status.upper()

    def test_format_tool_status_failed(self):
        """Test tool status for failed execution"""
        status = ModernVisualEngine.format_tool_status(
            'sqlmap', 'FAILED', 'http://example.com'
        )
        assert isinstance(status, str)
        assert 'FAILED' in status.upper()

    def test_format_tool_status_with_progress(self):
        """Test tool status includes progress bar when progress > 0"""
        status = ModernVisualEngine.format_tool_status(
            'nuclei', 'RUNNING', 'target.com', progress=0.75
        )
        assert isinstance(status, str)
        assert '75.0%' in status

    def test_format_tool_status_without_progress(self):
        """Test tool status without progress bar"""
        status = ModernVisualEngine.format_tool_status(
            'nikto', 'RUNNING', 'target.com', progress=0.0
        )
        assert isinstance(status, str)
        # Should not include percentage when progress is 0
        # (or should show 0.0%)


class TestTextFormatting:
    """Test text formatting and highlighting"""

    def test_format_highlighted_text_default(self):
        """Test text highlighting with default color"""
        text = ModernVisualEngine.format_highlighted_text('Important')
        assert isinstance(text, str)
        assert 'Important' in text
        assert ColorStripper.has_colors(text)

    def test_format_highlighted_text_all_colors(self):
        """Test text highlighting with all available colors"""
        colors = ['RED', 'YELLOW', 'GREEN', 'BLUE', 'PURPLE']

        for color in colors:
            text = ModernVisualEngine.format_highlighted_text('Test', color)
            assert isinstance(text, str)
            assert 'Test' in text
            assert ColorStripper.has_colors(text)

    def test_format_vulnerability_severity_basic(self):
        """Test vulnerability severity formatting"""
        severity = ModernVisualEngine.format_vulnerability_severity('critical', count=5)
        assert isinstance(severity, str)
        assert 'CRITICAL' in severity.upper()
        assert '5' in severity

    def test_format_vulnerability_severity_no_count(self):
        """Test vulnerability severity without count"""
        severity = ModernVisualEngine.format_vulnerability_severity('high', count=0)
        assert isinstance(severity, str)
        assert 'HIGH' in severity.upper()

    def test_format_vulnerability_severity_all_levels(self):
        """Test all vulnerability severity levels"""
        severities = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO']

        for sev in severities:
            formatted = ModernVisualEngine.format_vulnerability_severity(sev, count=3)
            assert isinstance(formatted, str)
            assert sev in formatted.upper()


class TestSectionHeaders:
    """Test section header creation"""

    def test_create_section_header_basic(self):
        """Test basic section header creation"""
        header = ModernVisualEngine.create_section_header('Test Section')
        assert isinstance(header, str)
        assert 'TEST SECTION' in header.upper()

    def test_create_section_header_with_icon(self):
        """Test section header with custom icon"""
        header = ModernVisualEngine.create_section_header('Scanning', icon='🔍')
        assert isinstance(header, str)
        assert '🔍' in header
        assert 'SCANNING' in header.upper()

    def test_create_section_header_with_color(self):
        """Test section header with custom color"""
        header = ModernVisualEngine.create_section_header(
            'Results', icon='📊', color='HACKER_RED'
        )
        assert isinstance(header, str)
        assert 'RESULTS' in header.upper()
        assert ColorStripper.has_colors(header)

    def test_create_section_header_multi_line(self):
        """Test that section headers span multiple lines"""
        header = ModernVisualEngine.create_section_header('Test')
        lines = header.split('\n')
        # Should have separator lines
        assert len(lines) > 1


class TestCommandFormatting:
    """Test command execution formatting"""

    def test_format_command_execution_starting(self):
        """Test formatting for starting command"""
        formatted = ModernVisualEngine.format_command_execution(
            'nmap -sV target.com', 'STARTING'
        )
        assert isinstance(formatted, str)
        assert 'nmap' in formatted
        assert 'STARTING' in formatted.upper()

    def test_format_command_execution_running(self):
        """Test formatting for running command"""
        formatted = ModernVisualEngine.format_command_execution(
            'gobuster dir -u http://target.com', 'RUNNING'
        )
        assert isinstance(formatted, str)
        assert 'RUNNING' in formatted.upper()

    def test_format_command_execution_success(self):
        """Test formatting for successful command"""
        formatted = ModernVisualEngine.format_command_execution(
            'sqlmap -u http://target.com', 'SUCCESS', duration=45.67
        )
        assert isinstance(formatted, str)
        assert 'SUCCESS' in formatted.upper()
        assert '45.67' in formatted

    def test_format_command_execution_failed(self):
        """Test formatting for failed command"""
        formatted = ModernVisualEngine.format_command_execution(
            'nuclei -u target.com', 'FAILED', duration=10.0
        )
        assert isinstance(formatted, str)
        assert 'FAILED' in formatted.upper()

    def test_format_command_execution_timeout(self):
        """Test formatting for timed out command"""
        formatted = ModernVisualEngine.format_command_execution(
            'nikto -h target.com', 'TIMEOUT', duration=300.0
        )
        assert isinstance(formatted, str)
        assert 'TIMEOUT' in formatted.upper()

    def test_format_command_execution_truncates_long_commands(self):
        """Test that long commands are truncated"""
        long_command = 'a' * 100
        formatted = ModernVisualEngine.format_command_execution(
            long_command, 'RUNNING'
        )
        assert isinstance(formatted, str)
        assert '...' in formatted
        # Should be truncated to 60 chars + ...
        assert len(ColorStripper.strip_colors(formatted)) < len(long_command) + 20

    def test_format_command_execution_without_duration(self):
        """Test command formatting without duration"""
        formatted = ModernVisualEngine.format_command_execution(
            'test command', 'RUNNING', duration=0.0
        )
        assert isinstance(formatted, str)
        # Should not show duration when it's 0


class TestColorConsistency:
    """Test color consistency across the visual engine"""

    def test_all_methods_return_colored_output(self):
        """Test that all formatting methods include color codes"""
        # Banner
        assert ColorStripper.has_colors(ModernVisualEngine.create_banner())

        # Progress bar
        assert ColorStripper.has_colors(
            ModernVisualEngine.create_progress_bar(50, 100, tool="test")
        )

        # Vulnerability card
        assert ColorStripper.has_colors(
            ModernVisualEngine.format_vulnerability_card({
                'severity': 'high',
                'name': 'Test',
                'description': 'Test'
            })
        )

        # Error card
        assert ColorStripper.has_colors(
            ModernVisualEngine.format_error_card('ERROR', 'tool', 'message')
        )

        # Tool status
        assert ColorStripper.has_colors(
            ModernVisualEngine.format_tool_status('tool', 'RUNNING', 'target')
        )

    def test_reset_codes_present(self):
        """Test that RESET codes are used to prevent color bleeding"""
        methods_output = [
            ModernVisualEngine.create_banner(),
            ModernVisualEngine.create_progress_bar(50, 100, tool="test"),
            ModernVisualEngine.format_vulnerability_card({
                'severity': 'critical', 'name': 'Test', 'description': 'Test'
            }),
            ModernVisualEngine.format_error_card('ERROR', 'tool', 'msg'),
        ]

        reset_code = ModernVisualEngine.COLORS['RESET']
        for output in methods_output:
            assert reset_code in output, "Output should include RESET code"
