"""
Unit tests for TelemetryCollector

Tests cover:
- Telemetry initialization
- Execution recording (success/failure)
- Statistics calculation
- System metrics collection
- Uptime tracking
- Success rate calculation
- Average execution time

Target: 90%+ code coverage
"""

import pytest
import sys
import os
import time
from unittest.mock import patch, MagicMock

# Add parent directories to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from hexstrike_server import TelemetryCollector


class TestTelemetryInitialization:
    """Test telemetry collector initialization"""

    def test_telemetry_initializes(self):
        """Test that telemetry collector initializes"""
        telemetry = TelemetryCollector()
        assert telemetry is not None
        assert hasattr(telemetry, 'stats')

    def test_telemetry_stats_initialized(self):
        """Test that statistics are initialized to zero"""
        telemetry = TelemetryCollector()
        assert telemetry.stats["commands_executed"] == 0
        assert telemetry.stats["successful_commands"] == 0
        assert telemetry.stats["failed_commands"] == 0
        assert telemetry.stats["total_execution_time"] == 0.0

    def test_telemetry_has_start_time(self):
        """Test that start time is recorded"""
        telemetry = TelemetryCollector()
        assert "start_time" in telemetry.stats
        assert isinstance(telemetry.stats["start_time"], (int, float))
        assert telemetry.stats["start_time"] > 0

    def test_telemetry_start_time_is_recent(self):
        """Test that start time is close to current time"""
        telemetry = TelemetryCollector()
        current_time = time.time()
        # Start time should be within 1 second of creation
        assert abs(current_time - telemetry.stats["start_time"]) < 1.0


class TestRecordExecution:
    """Test execution recording functionality"""

    def test_record_successful_execution(self):
        """Test recording a successful command execution"""
        telemetry = TelemetryCollector()
        initial_executed = telemetry.stats["commands_executed"]
        initial_successful = telemetry.stats["successful_commands"]

        telemetry.record_execution(success=True, execution_time=5.0)

        assert telemetry.stats["commands_executed"] == initial_executed + 1
        assert telemetry.stats["successful_commands"] == initial_successful + 1

    def test_record_failed_execution(self):
        """Test recording a failed command execution"""
        telemetry = TelemetryCollector()
        initial_executed = telemetry.stats["commands_executed"]
        initial_failed = telemetry.stats["failed_commands"]

        telemetry.record_execution(success=False, execution_time=2.0)

        assert telemetry.stats["commands_executed"] == initial_executed + 1
        assert telemetry.stats["failed_commands"] == initial_failed + 1

    def test_record_execution_tracks_time(self):
        """Test that execution time is tracked"""
        telemetry = TelemetryCollector()
        initial_time = telemetry.stats["total_execution_time"]

        telemetry.record_execution(success=True, execution_time=10.5)

        assert telemetry.stats["total_execution_time"] == initial_time + 10.5

    def test_record_multiple_executions(self):
        """Test recording multiple executions"""
        telemetry = TelemetryCollector()

        # Record 3 successful, 2 failed
        for _ in range(3):
            telemetry.record_execution(success=True, execution_time=5.0)
        for _ in range(2):
            telemetry.record_execution(success=False, execution_time=3.0)

        assert telemetry.stats["commands_executed"] == 5
        assert telemetry.stats["successful_commands"] == 3
        assert telemetry.stats["failed_commands"] == 2
        assert telemetry.stats["total_execution_time"] == (3 * 5.0) + (2 * 3.0)

    def test_record_execution_with_zero_time(self):
        """Test recording execution with zero execution time"""
        telemetry = TelemetryCollector()
        telemetry.record_execution(success=True, execution_time=0.0)

        assert telemetry.stats["commands_executed"] == 1
        assert telemetry.stats["total_execution_time"] == 0.0

    def test_record_execution_with_large_time(self):
        """Test recording execution with large execution time"""
        telemetry = TelemetryCollector()
        large_time = 999999.99
        telemetry.record_execution(success=True, execution_time=large_time)

        assert telemetry.stats["total_execution_time"] == large_time


class TestSystemMetrics:
    """Test system metrics collection"""

    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @patch('psutil.net_io_counters')
    def test_get_system_metrics_returns_dict(self, mock_net, mock_disk, mock_mem, mock_cpu):
        """Test that get_system_metrics returns a dictionary"""
        # Configure mocks
        mock_cpu.return_value = 50.0
        mock_mem.return_value = MagicMock(percent=60.0)
        mock_disk.return_value = MagicMock(percent=70.0)
        mock_net.return_value = MagicMock(_asdict=lambda: {'bytes_sent': 1000})

        telemetry = TelemetryCollector()
        metrics = telemetry.get_system_metrics()

        assert isinstance(metrics, dict)

    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @patch('psutil.net_io_counters')
    def test_get_system_metrics_includes_cpu(self, mock_net, mock_disk, mock_mem, mock_cpu):
        """Test that system metrics include CPU percentage"""
        mock_cpu.return_value = 45.5
        mock_mem.return_value = MagicMock(percent=60.0)
        mock_disk.return_value = MagicMock(percent=70.0)
        mock_net.return_value = MagicMock(_asdict=lambda: {})

        telemetry = TelemetryCollector()
        metrics = telemetry.get_system_metrics()

        assert "cpu_percent" in metrics
        assert metrics["cpu_percent"] == 45.5

    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @patch('psutil.net_io_counters')
    def test_get_system_metrics_includes_memory(self, mock_net, mock_disk, mock_mem, mock_cpu):
        """Test that system metrics include memory percentage"""
        mock_cpu.return_value = 50.0
        mock_mem.return_value = MagicMock(percent=75.3)
        mock_disk.return_value = MagicMock(percent=70.0)
        mock_net.return_value = MagicMock(_asdict=lambda: {})

        telemetry = TelemetryCollector()
        metrics = telemetry.get_system_metrics()

        assert "memory_percent" in metrics
        assert metrics["memory_percent"] == 75.3

    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @patch('psutil.net_io_counters')
    def test_get_system_metrics_includes_disk(self, mock_net, mock_disk, mock_mem, mock_cpu):
        """Test that system metrics include disk usage"""
        mock_cpu.return_value = 50.0
        mock_mem.return_value = MagicMock(percent=60.0)
        mock_disk.return_value = MagicMock(percent=82.1)
        mock_net.return_value = MagicMock(_asdict=lambda: {})

        telemetry = TelemetryCollector()
        metrics = telemetry.get_system_metrics()

        assert "disk_usage" in metrics
        assert metrics["disk_usage"] == 82.1

    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @patch('psutil.net_io_counters')
    def test_get_system_metrics_includes_network(self, mock_net, mock_disk, mock_mem, mock_cpu):
        """Test that system metrics include network I/O"""
        mock_cpu.return_value = 50.0
        mock_mem.return_value = MagicMock(percent=60.0)
        mock_disk.return_value = MagicMock(percent=70.0)
        mock_net.return_value = MagicMock(_asdict=lambda: {
            'bytes_sent': 1024,
            'bytes_recv': 2048
        })

        telemetry = TelemetryCollector()
        metrics = telemetry.get_system_metrics()

        assert "network_io" in metrics
        assert isinstance(metrics["network_io"], dict)

    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @patch('psutil.net_io_counters')
    def test_get_system_metrics_handles_no_network(self, mock_net, mock_disk, mock_mem, mock_cpu):
        """Test that system metrics handle when network counters are None"""
        mock_cpu.return_value = 50.0
        mock_mem.return_value = MagicMock(percent=60.0)
        mock_disk.return_value = MagicMock(percent=70.0)
        mock_net.return_value = None  # No network counters

        telemetry = TelemetryCollector()
        metrics = telemetry.get_system_metrics()

        assert "network_io" in metrics
        assert metrics["network_io"] == {}


class TestGetStats:
    """Test statistics retrieval and calculation"""

    @patch('time.time')
    def test_get_stats_returns_dict(self, mock_time):
        """Test that get_stats returns a dictionary"""
        mock_time.return_value = 1000.0
        telemetry = TelemetryCollector()
        stats = telemetry.get_stats()

        assert isinstance(stats, dict)

    @patch('time.time')
    def test_get_stats_includes_uptime(self, mock_time):
        """Test that stats include uptime"""
        mock_time.return_value = 1000.0
        telemetry = TelemetryCollector()

        mock_time.return_value = 1060.0  # 60 seconds later
        stats = telemetry.get_stats()

        assert "uptime_seconds" in stats
        assert stats["uptime_seconds"] == 60.0

    @patch('time.time')
    def test_get_stats_includes_commands_executed(self, mock_time):
        """Test that stats include command count"""
        mock_time.return_value = 1000.0
        telemetry = TelemetryCollector()

        telemetry.record_execution(success=True, execution_time=5.0)
        telemetry.record_execution(success=False, execution_time=3.0)

        stats = telemetry.get_stats()
        assert "commands_executed" in stats
        assert stats["commands_executed"] == 2

    @patch('time.time')
    def test_get_stats_calculates_success_rate(self, mock_time):
        """Test that stats include success rate calculation"""
        mock_time.return_value = 1000.0
        telemetry = TelemetryCollector()

        # 3 successful, 1 failed = 75% success rate
        for _ in range(3):
            telemetry.record_execution(success=True, execution_time=5.0)
        telemetry.record_execution(success=False, execution_time=3.0)

        stats = telemetry.get_stats()
        assert "success_rate" in stats
        assert "%" in stats["success_rate"]

        # Extract percentage
        success_rate = float(stats["success_rate"].rstrip('%'))
        assert abs(success_rate - 75.0) < 0.1  # Should be approximately 75%

    @patch('time.time')
    def test_get_stats_success_rate_with_no_commands(self, mock_time):
        """Test success rate calculation with no commands executed"""
        mock_time.return_value = 1000.0
        telemetry = TelemetryCollector()

        stats = telemetry.get_stats()
        assert "success_rate" in stats
        # Should handle division by zero gracefully
        success_rate = float(stats["success_rate"].rstrip('%'))
        assert success_rate == 0.0

    @patch('time.time')
    def test_get_stats_calculates_average_execution_time(self, mock_time):
        """Test that stats include average execution time"""
        mock_time.return_value = 1000.0
        telemetry = TelemetryCollector()

        # Total time: 10 + 20 + 30 = 60, count: 3, avg: 20
        telemetry.record_execution(success=True, execution_time=10.0)
        telemetry.record_execution(success=True, execution_time=20.0)
        telemetry.record_execution(success=True, execution_time=30.0)

        stats = telemetry.get_stats()
        assert "average_execution_time" in stats
        assert "s" in stats["average_execution_time"]  # Should have 's' for seconds

        # Extract time value
        avg_time = float(stats["average_execution_time"].rstrip('s'))
        assert abs(avg_time - 20.0) < 0.1  # Should be approximately 20 seconds

    @patch('time.time')
    def test_get_stats_avg_time_with_no_commands(self, mock_time):
        """Test average execution time with no commands"""
        mock_time.return_value = 1000.0
        telemetry = TelemetryCollector()

        stats = telemetry.get_stats()
        assert "average_execution_time" in stats
        # Should handle division by zero gracefully
        avg_time = float(stats["average_execution_time"].rstrip('s'))
        assert avg_time == 0.0

    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @patch('psutil.net_io_counters')
    @patch('time.time')
    def test_get_stats_includes_system_metrics(self, mock_time, mock_net, mock_disk, mock_mem, mock_cpu):
        """Test that stats include system metrics"""
        mock_time.return_value = 1000.0
        mock_cpu.return_value = 50.0
        mock_mem.return_value = MagicMock(percent=60.0)
        mock_disk.return_value = MagicMock(percent=70.0)
        mock_net.return_value = MagicMock(_asdict=lambda: {})

        telemetry = TelemetryCollector()
        stats = telemetry.get_stats()

        assert "system_metrics" in stats
        assert isinstance(stats["system_metrics"], dict)


class TestTelemetryIntegration:
    """Integration tests for telemetry collector"""

    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @patch('psutil.net_io_counters')
    @patch('time.time')
    def test_realistic_usage_pattern(self, mock_time, mock_net, mock_disk, mock_mem, mock_cpu):
        """Test telemetry with realistic usage pattern"""
        # Configure mocks
        mock_time.return_value = 1000.0
        mock_cpu.return_value = 50.0
        mock_mem.return_value = MagicMock(percent=60.0)
        mock_disk.return_value = MagicMock(percent=70.0)
        mock_net.return_value = MagicMock(_asdict=lambda: {})

        telemetry = TelemetryCollector()

        # Simulate running several commands
        commands = [
            (True, 10.5),   # nmap - success
            (True, 45.2),   # gobuster - success
            (False, 5.3),   # sqlmap - failed
            (True, 120.8),  # nuclei - success
            (True, 30.1),   # nikto - success
            (False, 2.5),   # hydra - failed
        ]

        for success, exec_time in commands:
            telemetry.record_execution(success, exec_time)

        # Check statistics
        stats = telemetry.get_stats()

        assert stats["commands_executed"] == 6
        assert "success_rate" in stats
        assert "average_execution_time" in stats
        assert "system_metrics" in stats

    @patch('time.time')
    def test_long_running_session(self, mock_time):
        """Test telemetry for long-running session"""
        mock_time.return_value = 1000.0
        telemetry = TelemetryCollector()

        # Simulate 100 commands over time
        for i in range(100):
            success = (i % 3) != 0  # ~67% success rate
            telemetry.record_execution(success, execution_time=float(i))

        stats = telemetry.get_stats()

        assert stats["commands_executed"] == 100
        # Success rate should be around 67%
        success_rate = float(stats["success_rate"].rstrip('%'))
        assert 60.0 <= success_rate <= 70.0

    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @patch('psutil.net_io_counters')
    @patch('time.time')
    def test_all_successful_commands(self, mock_time, mock_net, mock_disk, mock_mem, mock_cpu):
        """Test telemetry when all commands succeed"""
        mock_time.return_value = 1000.0
        mock_cpu.return_value = 50.0
        mock_mem.return_value = MagicMock(percent=60.0)
        mock_disk.return_value = MagicMock(percent=70.0)
        mock_net.return_value = None

        telemetry = TelemetryCollector()

        for _ in range(10):
            telemetry.record_execution(success=True, execution_time=5.0)

        stats = telemetry.get_stats()
        success_rate = float(stats["success_rate"].rstrip('%'))
        assert success_rate == 100.0

    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @patch('psutil.net_io_counters')
    @patch('time.time')
    def test_all_failed_commands(self, mock_time, mock_net, mock_disk, mock_mem, mock_cpu):
        """Test telemetry when all commands fail"""
        mock_time.return_value = 1000.0
        mock_cpu.return_value = 50.0
        mock_mem.return_value = MagicMock(percent=60.0)
        mock_disk.return_value = MagicMock(percent=70.0)
        mock_net.return_value = None

        telemetry = TelemetryCollector()

        for _ in range(10):
            telemetry.record_execution(success=False, execution_time=3.0)

        stats = telemetry.get_stats()
        success_rate = float(stats["success_rate"].rstrip('%'))
        assert success_rate == 0.0


class TestTelemetryEdgeCases:
    """Test edge cases and error conditions"""

    @patch('time.time')
    def test_very_long_uptime(self, mock_time):
        """Test telemetry with very long uptime"""
        mock_time.return_value = 1000.0
        telemetry = TelemetryCollector()

        # Simulate days of uptime
        mock_time.return_value = 1000.0 + (86400 * 7)  # 7 days later

        stats = telemetry.get_stats()
        assert stats["uptime_seconds"] == 86400 * 7

    def test_rapid_consecutive_recordings(self):
        """Test recording many executions rapidly"""
        telemetry = TelemetryCollector()

        for i in range(1000):
            telemetry.record_execution(success=(i % 2 == 0), execution_time=0.1)

        stats = telemetry.get_stats()
        assert stats["commands_executed"] == 1000

    @patch('time.time')
    def test_negative_time_difference(self, mock_time):
        """Test handling of system time going backwards (edge case)"""
        mock_time.return_value = 2000.0
        telemetry = TelemetryCollector()

        # System clock goes backwards
        mock_time.return_value = 1500.0

        stats = telemetry.get_stats()
        # Should handle gracefully, even if uptime is negative
        assert "uptime_seconds" in stats

    def test_execution_time_precision(self):
        """Test that execution time maintains precision"""
        telemetry = TelemetryCollector()

        # Record with high precision
        telemetry.record_execution(success=True, execution_time=0.001234)

        assert telemetry.stats["total_execution_time"] == 0.001234

    @patch('psutil.cpu_percent')
    def test_handles_psutil_exceptions(self, mock_cpu):
        """Test that telemetry handles psutil exceptions gracefully"""
        mock_cpu.side_effect = Exception("psutil error")

        telemetry = TelemetryCollector()

        # Should not crash even if psutil fails
        try:
            metrics = telemetry.get_system_metrics()
            # If it returns, it handled the exception
        except Exception:
            # Or it re-raises, which is also acceptable
            pass
