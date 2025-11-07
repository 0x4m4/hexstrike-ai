#!/usr/bin/env python3
"""
Notification System for MindSync Oracle

Sends proactive notifications when goals complete, critical findings emerge,
or important events occur.
"""

import logging
import subprocess
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class NotificationLevel(Enum):
    """Notification priority levels."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    CRITICAL = "critical"


class NotificationSystem:
    """
    Multi-channel notification system.

    Supports:
    - Desktop notifications (Linux/Mac/Windows)
    - Terminal output
    - Log file
    - Future: Email, Slack, etc.
    """

    def __init__(self, enabled_methods: Optional[List[str]] = None):
        """
        Initialize notification system.

        Args:
            enabled_methods: List of notification methods to enable
                           ('desktop', 'terminal', 'log')
        """
        self.enabled_methods = enabled_methods or ['terminal', 'log']
        self.notification_history = []
        logger.info(f"Notification system initialized: {self.enabled_methods}")

    def notify(self, title: str, message: str,
               level: NotificationLevel = NotificationLevel.INFO,
               metadata: Optional[Dict[str, Any]] = None):
        """
        Send a notification through all enabled channels.

        Args:
            title: Notification title
            message: Notification message
            level: Priority level
            metadata: Optional additional data
        """
        notification = {
            'title': title,
            'message': message,
            'level': level.value,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }

        # Store in history
        self.notification_history.append(notification)

        # Send via each enabled method
        if 'desktop' in self.enabled_methods:
            self._send_desktop(title, message, level)

        if 'terminal' in self.enabled_methods:
            self._send_terminal(title, message, level)

        if 'log' in self.enabled_methods:
            self._send_log(title, message, level)

    def _send_desktop(self, title: str, message: str, level: NotificationLevel):
        """Send desktop notification."""
        try:
            # Detect OS and use appropriate notification system
            import platform
            system = platform.system()

            if system == "Linux":
                self._send_linux_notification(title, message, level)
            elif system == "Darwin":  # macOS
                self._send_macos_notification(title, message, level)
            elif system == "Windows":
                self._send_windows_notification(title, message, level)

        except Exception as e:
            logger.error(f"Error sending desktop notification: {e}")

    def _send_linux_notification(self, title: str, message: str, level: NotificationLevel):
        """Send notification via notify-send (Linux)."""
        try:
            urgency = {
                NotificationLevel.INFO: "normal",
                NotificationLevel.SUCCESS: "normal",
                NotificationLevel.WARNING: "normal",
                NotificationLevel.CRITICAL: "critical"
            }.get(level, "normal")

            icon = {
                NotificationLevel.INFO: "dialog-information",
                NotificationLevel.SUCCESS: "dialog-ok",
                NotificationLevel.WARNING: "dialog-warning",
                NotificationLevel.CRITICAL: "dialog-error"
            }.get(level, "dialog-information")

            subprocess.run([
                'notify-send',
                '-u', urgency,
                '-i', icon,
                '-a', 'MindSync Oracle',
                title,
                message
            ], check=False, capture_output=True)

        except FileNotFoundError:
            logger.debug("notify-send not found - desktop notifications disabled")
        except Exception as e:
            logger.error(f"Error with notify-send: {e}")

    def _send_macos_notification(self, title: str, message: str, level: NotificationLevel):
        """Send notification via osascript (macOS)."""
        try:
            script = f'''
            display notification "{message}" with title "MindSync Oracle" subtitle "{title}"
            '''
            subprocess.run(['osascript', '-e', script], check=False, capture_output=True)

        except Exception as e:
            logger.error(f"Error with osascript: {e}")

    def _send_windows_notification(self, title: str, message: str, level: NotificationLevel):
        """Send notification via Windows toast (Windows 10+)."""
        try:
            # Use Windows 10 toast notifications
            from win10toast import ToastNotifier
            toaster = ToastNotifier()
            toaster.show_toast(
                f"MindSync Oracle - {title}",
                message,
                duration=10,
                threaded=True
            )

        except ImportError:
            logger.debug("win10toast not installed - desktop notifications disabled")
        except Exception as e:
            logger.error(f"Error with Windows toast: {e}")

    def _send_terminal(self, title: str, message: str, level: NotificationLevel):
        """Send notification to terminal with colors."""
        colors = {
            NotificationLevel.INFO: '\033[94m',      # Blue
            NotificationLevel.SUCCESS: '\033[92m',   # Green
            NotificationLevel.WARNING: '\033[93m',   # Yellow
            NotificationLevel.CRITICAL: '\033[91m'   # Red
        }
        reset = '\033[0m'
        bold = '\033[1m'

        color = colors.get(level, colors[NotificationLevel.INFO])

        print(f"\n{color}{bold}{'='*60}")
        print(f"🔔 {title}")
        print(f"{'='*60}{reset}")
        print(f"{color}{message}{reset}")
        print(f"{color}{'='*60}{reset}\n")

    def _send_log(self, title: str, message: str, level: NotificationLevel):
        """Send notification to log file."""
        log_methods = {
            NotificationLevel.INFO: logger.info,
            NotificationLevel.SUCCESS: logger.info,
            NotificationLevel.WARNING: logger.warning,
            NotificationLevel.CRITICAL: logger.critical
        }

        log_method = log_methods.get(level, logger.info)
        log_method(f"[NOTIFICATION] {title}: {message}")

    # Convenience methods for common notifications

    def goal_completed(self, goal_text: str, results_summary: str):
        """Notify that a goal has been completed."""
        self.notify(
            "Goal Completed ✅",
            f"'{goal_text}'\n\nResults: {results_summary}",
            NotificationLevel.SUCCESS,
            metadata={'type': 'goal_completed', 'goal': goal_text}
        )

    def goal_failed(self, goal_text: str, error: str):
        """Notify that a goal has failed."""
        self.notify(
            "Goal Failed ❌",
            f"'{goal_text}'\n\nError: {error}",
            NotificationLevel.WARNING,
            metadata={'type': 'goal_failed', 'goal': goal_text, 'error': error}
        )

    def critical_finding(self, finding_type: str, details: str):
        """Notify about a critical security finding."""
        self.notify(
            f"Critical Finding: {finding_type} 🚨",
            details,
            NotificationLevel.CRITICAL,
            metadata={'type': 'critical_finding', 'finding_type': finding_type}
        )

    def pattern_detected(self, pattern_type: str, description: str):
        """Notify about a detected user pattern."""
        self.notify(
            f"Pattern Detected: {pattern_type}",
            description,
            NotificationLevel.INFO,
            metadata={'type': 'pattern_detected', 'pattern_type': pattern_type}
        )

    def cve_alert(self, cve_id: str, severity: str, affected_project: str):
        """Notify about a new CVE affecting user's project."""
        self.notify(
            f"New CVE Alert: {cve_id}",
            f"Severity: {severity}\nAffected: {affected_project}",
            NotificationLevel.CRITICAL,
            metadata={'type': 'cve_alert', 'cve_id': cve_id, 'severity': severity}
        )

    def get_recent_notifications(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent notifications."""
        return self.notification_history[-limit:]


# Global instance
_notifier: Optional[NotificationSystem] = None


def get_notifier(enabled_methods: Optional[List[str]] = None) -> NotificationSystem:
    """Get or create global notifier instance."""
    global _notifier
    if _notifier is None:
        _notifier = NotificationSystem(enabled_methods)
    return _notifier


if __name__ == "__main__":
    # Test notifications
    logging.basicConfig(level=logging.INFO)

    notifier = NotificationSystem(enabled_methods=['desktop', 'terminal', 'log'])

    print("Testing notification system...\n")

    # Test different notification types
    notifier.notify(
        "Test Info Notification",
        "This is an info notification test",
        NotificationLevel.INFO
    )

    notifier.goal_completed(
        "Research CVE-2024-1234",
        "Found exploit code and tested successfully"
    )

    notifier.critical_finding(
        "SQL Injection",
        "Found SQLi vulnerability in example.com/search?q="
    )

    notifier.cve_alert(
        "CVE-2024-XXXX",
        "CRITICAL",
        "WordPress 6.2 on acme.com"
    )

    print("\nNotification test complete!")
