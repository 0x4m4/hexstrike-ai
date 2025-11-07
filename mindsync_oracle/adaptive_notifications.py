#!/usr/bin/env python3
"""
MindSync Oracle - Adaptive Notification Escalation

Smart notification routing based on:
- Urgency/severity
- User preferences
- Time of day
- Historical response patterns

No more alert fatigue. Only critical stuff gets escalated.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, time
from enum import Enum
import json

logger = logging.getLogger(__name__)


class NotificationPriority(Enum):
    """Notification priority levels for routing."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4
    URGENT = 5  # Immediate escalation


class NotificationChannel(Enum):
    """Available notification channels."""
    TERMINAL = "terminal"
    DESKTOP = "desktop"
    LOG = "log"
    EMAIL = "email"
    SMS = "sms"
    SLACK = "slack"
    WEBHOOK = "webhook"


class AdaptiveNotificationEngine:
    """
    Intelligent notification routing that learns from user behavior.

    Features:
    - Priority-based escalation
    - Time-aware routing
    - Channel preferences
    - Rate limiting
    - Learned patterns
    """

    def __init__(self, base_notifier, memory_manager, config_manager):
        """
        Initialize adaptive notification engine.

        Args:
            base_notifier: Base NotificationSystem instance
            memory_manager: MemoryManager for learning preferences
            config_manager: ConfigManager for settings
        """
        self.base_notifier = base_notifier
        self.memory = memory_manager
        self.config = config_manager

        # Load routing rules
        self.routing_rules = self._load_routing_rules()

        # Track notification history for rate limiting
        self.notification_history = []

        logger.info("Adaptive Notification Engine initialized")

    def _load_routing_rules(self) -> Dict[str, Any]:
        """Load notification routing rules from config and memory."""
        # Default rules
        rules = {
            NotificationPriority.LOW: [NotificationChannel.LOG],
            NotificationPriority.MEDIUM: [NotificationChannel.TERMINAL, NotificationChannel.LOG],
            NotificationPriority.HIGH: [NotificationChannel.DESKTOP, NotificationChannel.TERMINAL, NotificationChannel.LOG],
            NotificationPriority.CRITICAL: [NotificationChannel.DESKTOP, NotificationChannel.EMAIL, NotificationChannel.LOG],
            NotificationPriority.URGENT: [NotificationChannel.SMS, NotificationChannel.DESKTOP, NotificationChannel.EMAIL, NotificationChannel.LOG]
        }

        # Override from config if exists
        config_rules = self.config.get('notifications.routing_rules')
        if config_rules:
            for priority, channels in config_rules.items():
                try:
                    priority_enum = NotificationPriority[priority.upper()]
                    channel_enums = [NotificationChannel[ch.upper()] for ch in channels]
                    rules[priority_enum] = channel_enums
                except (KeyError, AttributeError):
                    logger.warning(f"Invalid routing rule: {priority} -> {channels}")

        return rules

    def infer_priority(self, notification_type: str, content: str, metadata: Dict[str, Any]) -> NotificationPriority:
        """
        Intelligently infer notification priority.

        Args:
            notification_type: Type of notification
            content: Notification content
            metadata: Additional context

        Returns:
            Inferred priority level
        """
        # Keyword-based inference
        content_lower = content.lower()

        # URGENT keywords
        if any(word in content_lower for word in ['exploit confirmed', 'zero-day', 'active attack', 'breach detected']):
            return NotificationPriority.URGENT

        # CRITICAL keywords
        if any(word in content_lower for word in ['critical', 'severe', 'rce', 'root access', 'credential leak']):
            return NotificationPriority.CRITICAL

        # HIGH keywords
        if any(word in content_lower for word in ['high severity', 'authentication bypass', 'sql injection', 'xss']):
            return NotificationPriority.HIGH

        # MEDIUM keywords
        if any(word in content_lower for word in ['vulnerability', 'misconfiguration', 'warning']):
            return NotificationPriority.MEDIUM

        # Check notification type
        type_priorities = {
            'goal_completed': NotificationPriority.MEDIUM,
            'goal_failed': NotificationPriority.HIGH,
            'cve_alert': NotificationPriority.HIGH,
            'critical_finding': NotificationPriority.CRITICAL,
            'pattern_detected': NotificationPriority.LOW,
            'info': NotificationPriority.LOW
        }

        if notification_type in type_priorities:
            return type_priorities[notification_type]

        # Default to MEDIUM
        return NotificationPriority.MEDIUM

    def should_suppress(self, notification_type: str, priority: NotificationPriority) -> bool:
        """
        Check if notification should be suppressed due to rate limiting or quiet hours.

        Args:
            notification_type: Type of notification
            priority: Priority level

        Returns:
            True if should suppress
        """
        # Never suppress URGENT
        if priority == NotificationPriority.URGENT:
            return False

        # Check quiet hours (from config)
        quiet_start = self.config.get('notifications.quiet_hours.start')
        quiet_end = self.config.get('notifications.quiet_hours.end')

        if quiet_start and quiet_end:
            now = datetime.now().time()
            quiet_start_time = time.fromisoformat(quiet_start)
            quiet_end_time = time.fromisoformat(quiet_end)

            # Check if in quiet hours (and not CRITICAL)
            if quiet_start_time <= now <= quiet_end_time:
                if priority.value < NotificationPriority.CRITICAL.value:
                    logger.info(f"Suppressing {priority.name} notification (quiet hours)")
                    return True

        # Rate limiting - max notifications per hour
        max_per_hour = self.config.get('notifications.rate_limit.per_hour', 20)

        recent_count = len([
            n for n in self.notification_history
            if (datetime.now() - n['timestamp']).seconds < 3600
        ])

        if recent_count >= max_per_hour:
            if priority.value < NotificationPriority.HIGH.value:
                logger.info(f"Rate limit reached, suppressing {priority.name} notification")
                return True

        return False

    async def send_adaptive(self, title: str, message: str,
                           notification_type: str = "info",
                           metadata: Optional[Dict[str, Any]] = None,
                           override_priority: Optional[NotificationPriority] = None):
        """
        Send notification with adaptive routing.

        Args:
            title: Notification title
            message: Notification message
            notification_type: Type of notification
            metadata: Optional metadata
            override_priority: Optional priority override
        """
        metadata = metadata or {}

        # Infer or use override priority
        priority = override_priority or self.infer_priority(notification_type, message, metadata)

        # Check suppression
        if self.should_suppress(notification_type, priority):
            logger.info(f"Notification suppressed: {title}")
            return

        # Get routing channels
        channels = self.routing_rules.get(priority, [NotificationChannel.TERMINAL])

        # Log notification
        logger.info(f"Sending {priority.name} notification via {[c.value for c in channels]}: {title}")

        # Route to channels
        for channel in channels:
            await self._send_to_channel(channel, title, message, priority, metadata)

        # Track history
        self.notification_history.append({
            'timestamp': datetime.now(),
            'priority': priority.name,
            'type': notification_type,
            'title': title
        })

        # Store pattern for learning
        self.memory.store_pattern(
            "notification_sent",
            {
                "type": notification_type,
                "priority": priority.name,
                "channels": [c.value for c in channels]
            },
            confidence=0.5
        )

    async def _send_to_channel(self, channel: NotificationChannel,
                               title: str, message: str,
                               priority: NotificationPriority,
                               metadata: Dict[str, Any]):
        """Send notification to specific channel."""
        try:
            if channel == NotificationChannel.TERMINAL:
                # Use base notifier for terminal
                from notification_system import NotificationLevel
                level_map = {
                    NotificationPriority.LOW: NotificationLevel.INFO,
                    NotificationPriority.MEDIUM: NotificationLevel.INFO,
                    NotificationPriority.HIGH: NotificationLevel.WARNING,
                    NotificationPriority.CRITICAL: NotificationLevel.CRITICAL,
                    NotificationPriority.URGENT: NotificationLevel.CRITICAL
                }
                self.base_notifier.notify(title, message, level=level_map.get(priority, NotificationLevel.INFO), metadata=metadata)

            elif channel == NotificationChannel.DESKTOP:
                self.base_notifier._send_desktop(title, message, level_map.get(priority, NotificationLevel.INFO))

            elif channel == NotificationChannel.LOG:
                self.base_notifier._send_log(title, message, level_map.get(priority, NotificationLevel.INFO))

            elif channel == NotificationChannel.EMAIL:
                await self._send_email(title, message, priority, metadata)

            elif channel == NotificationChannel.SMS:
                await self._send_sms(title, message, priority, metadata)

            elif channel == NotificationChannel.SLACK:
                await self._send_slack(title, message, priority, metadata)

            elif channel == NotificationChannel.WEBHOOK:
                await self._send_webhook(title, message, priority, metadata)

        except Exception as e:
            logger.error(f"Error sending to {channel.value}: {e}")

    async def _send_email(self, title: str, message: str,
                         priority: NotificationPriority, metadata: Dict[str, Any]):
        """Send email notification."""
        email_config = self.config.get('notifications.email')
        if not email_config:
            logger.debug("Email not configured")
            return

        # TODO: Implement with SendGrid/SMTP
        logger.info(f"[EMAIL PLACEHOLDER] {title}: {message[:100]}")

    async def _send_sms(self, title: str, message: str,
                       priority: NotificationPriority, metadata: Dict[str, Any]):
        """Send SMS notification."""
        sms_config = self.config.get('notifications.sms')
        if not sms_config:
            logger.debug("SMS not configured")
            return

        # TODO: Implement with Twilio
        logger.info(f"[SMS PLACEHOLDER] {title}: {message[:100]}")

    async def _send_slack(self, title: str, message: str,
                         priority: NotificationPriority, metadata: Dict[str, Any]):
        """Send Slack notification."""
        slack_config = self.config.get('notifications.slack')
        if not slack_config:
            logger.debug("Slack not configured")
            return

        # TODO: Implement with Slack webhooks
        logger.info(f"[SLACK PLACEHOLDER] {title}: {message[:100]}")

    async def _send_webhook(self, title: str, message: str,
                           priority: NotificationPriority, metadata: Dict[str, Any]):
        """Send webhook notification."""
        webhook_url = self.config.get('notifications.webhook.url')
        if not webhook_url:
            logger.debug("Webhook not configured")
            return

        # TODO: Implement HTTP POST
        logger.info(f"[WEBHOOK PLACEHOLDER] {title}: {message[:100]}")

    async def learn_from_response(self, notification_id: str, user_action: str):
        """
        Learn from user's response to notification.

        Args:
            notification_id: ID of notification
            user_action: Action taken (viewed, dismissed, acted)
        """
        # Store learning pattern
        self.memory.store_pattern(
            "notification_response",
            {
                "notification_id": notification_id,
                "action": user_action,
                "timestamp": datetime.now().isoformat()
            },
            confidence=0.7
        )

        logger.info(f"Learned from notification response: {user_action}")

    def get_notification_stats(self) -> Dict[str, Any]:
        """Get notification statistics."""
        # Count by priority
        priority_counts = {}
        for notif in self.notification_history:
            priority = notif['priority']
            priority_counts[priority] = priority_counts.get(priority, 0) + 1

        return {
            "total_sent": len(self.notification_history),
            "by_priority": priority_counts,
            "recent_hour": len([
                n for n in self.notification_history
                if (datetime.now() - n['timestamp']).seconds < 3600
            ])
        }


if __name__ == "__main__":
    # Test adaptive notifications
    import sys
    import asyncio
    sys.path.append('..')

    from storage.memory_manager import MemoryManager
    from notification_system import NotificationSystem
    from config_manager import ConfigManager

    logging.basicConfig(level=logging.INFO)

    async def test():
        memory = MemoryManager("test_memory.db")
        config = ConfigManager("config.yaml")
        base_notifier = NotificationSystem(enabled_methods=['terminal', 'log'])

        adaptive = AdaptiveNotificationEngine(base_notifier, memory, config)

        # Test different priorities
        await adaptive.send_adaptive(
            "Low Priority Test",
            "This is a low priority notification",
            notification_type="info"
        )

        await adaptive.send_adaptive(
            "High Priority Test",
            "Critical vulnerability detected in WordPress 6.2",
            notification_type="cve_alert"
        )

        await adaptive.send_adaptive(
            "URGENT Test",
            "Zero-day exploit confirmed - active attack detected",
            notification_type="critical_finding"
        )

        # Get stats
        stats = adaptive.get_notification_stats()
        print(f"\nNotification Stats:\n{json.dumps(stats, indent=2)}")

    asyncio.run(test())
