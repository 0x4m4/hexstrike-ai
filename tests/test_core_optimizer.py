"""
Tests for core.optimizer module

Tests for ParameterOptimizer and related classes:
- TechnologyDetector
- RateLimitDetector
- FailureRecoverySystem
- PerformanceMonitor
- ParameterOptimizer
"""

import pytest
from unittest.mock import Mock, patch
from core.optimizer import (
    TechnologyDetector,
    RateLimitDetector,
    FailureRecoverySystem,
    PerformanceMonitor,
    ParameterOptimizer
)


class TestTechnologyDetector:
    """Tests for TechnologyDetector class"""

    def test_detector_initialization(self):
        """Test TechnologyDetector initializes correctly"""
        detector = TechnologyDetector()
        assert detector.detection_patterns is not None
        assert "web_servers" in detector.detection_patterns
        assert "frameworks" in detector.detection_patterns
        assert "cms" in detector.detection_patterns
        assert detector.port_services is not None
        assert 80 in detector.port_services
        assert detector.port_services[80] == "http"

    def test_detect_apache_from_headers(self):
        """Test detecting Apache web server from headers"""
        detector = TechnologyDetector()
        headers = {"Server": "Apache/2.4.41"}

        result = detector.detect_technologies(
            target="example.com",
            headers=headers
        )

        assert "apache" in result["web_servers"]

    def test_detect_nginx_from_headers(self):
        """Test detecting nginx from headers"""
        detector = TechnologyDetector()
        headers = {"Server": "nginx/1.18.0"}

        result = detector.detect_technologies(
            target="example.com",
            headers=headers
        )

        assert "nginx" in result["web_servers"]

    def test_detect_wordpress_from_content(self):
        """Test detecting WordPress from page content"""
        detector = TechnologyDetector()
        content = "<html><head><link rel='stylesheet' href='/wp-content/themes/theme.css'></head></html>"

        result = detector.detect_technologies(
            target="example.com",
            content=content
        )

        assert "wordpress" in result["cms"]

    def test_detect_php_from_headers(self):
        """Test detecting PHP from headers"""
        detector = TechnologyDetector()
        headers = {"X-Powered-By": "PHP/7.4.3"}

        result = detector.detect_technologies(
            target="example.com",
            headers=headers
        )

        assert "php" in result["languages"]

    def test_detect_services_from_ports(self):
        """Test detecting services from open ports"""
        detector = TechnologyDetector()
        ports = [22, 80, 443, 3306]

        result = detector.detect_technologies(
            target="example.com",
            ports=ports
        )

        assert "ssh" in result["services"]
        assert "http" in result["services"]
        assert "https" in result["services"]
        assert "mysql" in result["services"]

    def test_detect_cloudflare_waf(self):
        """Test detecting Cloudflare WAF"""
        detector = TechnologyDetector()
        headers = {"CF-RAY": "12345-SJC", "Server": "cloudflare"}

        result = detector.detect_technologies(
            target="example.com",
            headers=headers
        )

        assert "cloudflare" in result["security"] or len(result["security"]) > 0


class TestRateLimitDetector:
    """Tests for RateLimitDetector class"""

    def test_detector_initialization(self):
        """Test RateLimitDetector initializes correctly"""
        detector = RateLimitDetector()
        assert detector.rate_limit_indicators is not None
        assert detector.timing_profiles is not None
        assert "stealth" in detector.timing_profiles
        assert "normal" in detector.timing_profiles

    def test_detect_rate_limit_from_status_code(self):
        """Test detecting rate limiting from HTTP 429 status"""
        detector = RateLimitDetector()

        result = detector.detect_rate_limiting(
            response_text="Rate limit exceeded",
            status_code=429
        )

        assert result["detected"] is True
        assert result["confidence"] >= 0.8
        assert "HTTP 429 status" in result["indicators"]
        assert result["recommended_profile"] == "stealth"

    def test_detect_rate_limit_from_text(self):
        """Test detecting rate limiting from response text"""
        detector = RateLimitDetector()

        result = detector.detect_rate_limiting(
            response_text="Too many requests, please slow down",
            status_code=200
        )

        assert result["detected"] is True
        assert result["confidence"] > 0

    def test_detect_rate_limit_from_headers(self):
        """Test detecting rate limiting from headers"""
        detector = RateLimitDetector()
        headers = {"X-RateLimit-Remaining": "0", "Retry-After": "60"}

        result = detector.detect_rate_limiting(
            response_text="",
            status_code=200,
            headers=headers
        )

        assert result["detected"] is True
        assert result["confidence"] > 0

    def test_adjust_timing_to_stealth(self):
        """Test adjusting timing parameters to stealth profile"""
        detector = RateLimitDetector()
        params = {"threads": 50, "delay": 0, "timeout": 5}

        result = detector.adjust_timing(params, "stealth")

        assert result["threads"] == 5  # stealth profile
        assert result["delay"] == 2.0
        assert result["timeout"] == 30

    def test_timing_profile_recommendation(self):
        """Test timing profile recommendation based on confidence"""
        detector = RateLimitDetector()

        # High confidence should recommend stealth
        assert detector._recommend_timing_profile(0.9) == "stealth"

        # Medium confidence should recommend conservative
        assert detector._recommend_timing_profile(0.6) == "conservative"

        # Low confidence should recommend normal
        assert detector._recommend_timing_profile(0.3) == "normal"

        # Very low should recommend aggressive
        assert detector._recommend_timing_profile(0.1) == "aggressive"


class TestFailureRecoverySystem:
    """Tests for FailureRecoverySystem class"""

    def test_system_initialization(self):
        """Test FailureRecoverySystem initializes correctly"""
        system = FailureRecoverySystem()
        assert system.tool_alternatives is not None
        assert system.failure_patterns is not None
        assert "nmap" in system.tool_alternatives
        assert "timeout" in system.failure_patterns

    def test_analyze_timeout_failure(self):
        """Test analyzing timeout failure"""
        system = FailureRecoverySystem()

        result = system.analyze_failure(
            error_output="Connection timed out after 30 seconds",
            exit_code=124
        )

        assert result["failure_type"] == "timeout"
        assert result["confidence"] > 0.5
        assert "Increase timeout values" in result["recovery_strategies"]

    def test_analyze_permission_denied(self):
        """Test analyzing permission denied failure"""
        system = FailureRecoverySystem()

        result = system.analyze_failure(
            error_output="Permission denied: cannot access file",
            exit_code=126
        )

        assert result["failure_type"] == "permission_denied"
        assert result["confidence"] > 0.5
        assert any("privilege" in s.lower() for s in result["recovery_strategies"])

    def test_analyze_rate_limited_failure(self):
        """Test analyzing rate limited failure"""
        system = FailureRecoverySystem()

        result = system.analyze_failure(
            error_output="Rate limit exceeded, too many requests",
            exit_code=1
        )

        assert result["failure_type"] == "rate_limited"
        assert "Use stealth timing profile" in result["recovery_strategies"]

    def test_suggest_alternative_tools_for_nmap(self):
        """Test suggesting alternative tools for nmap"""
        system = FailureRecoverySystem()

        result = system.analyze_failure(
            error_output="nmap failed with timeout",
            exit_code=1
        )

        assert "rustscan" in result["alternative_tools"] or "masscan" in result["alternative_tools"]

    def test_extract_tool_name_from_error(self):
        """Test extracting tool name from error output"""
        system = FailureRecoverySystem()

        assert system._extract_tool_name("nmap failed") == "nmap"
        assert system._extract_tool_name("gobuster error occurred") == "gobuster"
        assert system._extract_tool_name("unknown error") == "unknown"


class TestPerformanceMonitor:
    """Tests for PerformanceMonitor class"""

    def test_monitor_initialization(self):
        """Test PerformanceMonitor initializes correctly"""
        monitor = PerformanceMonitor()
        assert monitor.resource_thresholds is not None
        assert monitor.optimization_rules is not None
        assert "cpu_high" in monitor.resource_thresholds
        assert "high_cpu" in monitor.optimization_rules

    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @patch('psutil.net_io_counters')
    def test_monitor_system_resources(self, mock_net, mock_disk, mock_mem, mock_cpu):
        """Test monitoring system resources"""
        # Mock psutil functions
        mock_cpu.return_value = 50.0
        mock_mem.return_value = Mock(percent=60.0)
        mock_disk.return_value = Mock(percent=70.0)
        mock_net.return_value = Mock(bytes_sent=1000, bytes_recv=2000)

        monitor = PerformanceMonitor()
        result = monitor.monitor_system_resources()

        assert result["cpu_percent"] == 50.0
        assert result["memory_percent"] == 60.0
        assert result["disk_percent"] == 70.0
        assert result["network_bytes_sent"] == 1000

    def test_optimize_with_high_cpu(self):
        """Test optimization with high CPU usage"""
        monitor = PerformanceMonitor()
        params = {"threads": 50, "delay": 0.5}
        resource_usage = {"cpu_percent": 90.0, "memory_percent": 50.0}

        result = monitor.optimize_based_on_resources(params, resource_usage)

        # Should reduce threads when CPU is high
        assert result["threads"] < params["threads"]
        assert len(result["_optimizations_applied"]) > 0

    def test_optimize_with_high_memory(self):
        """Test optimization with high memory usage"""
        monitor = PerformanceMonitor()
        params = {"batch_size": 100}
        resource_usage = {"cpu_percent": 50.0, "memory_percent": 90.0}

        result = monitor.optimize_based_on_resources(params, resource_usage)

        # Should reduce batch size when memory is high
        assert result["batch_size"] < params["batch_size"]

    def test_no_optimization_with_normal_resources(self):
        """Test no optimization when resources are normal"""
        monitor = PerformanceMonitor()
        params = {"threads": 20, "delay": 0.5}
        resource_usage = {"cpu_percent": 40.0, "memory_percent": 50.0}

        result = monitor.optimize_based_on_resources(params, resource_usage)

        # Should not change parameters significantly
        assert result["threads"] == params["threads"]
        assert len(result.get("_optimizations_applied", [])) == 0


class TestParameterOptimizer:
    """Tests for ParameterOptimizer class"""

    def test_optimizer_initialization(self):
        """Test ParameterOptimizer initializes correctly"""
        optimizer = ParameterOptimizer()
        assert optimizer.tech_detector is not None
        assert optimizer.rate_limiter is not None
        assert optimizer.failure_recovery is not None
        assert optimizer.performance_monitor is not None
        assert optimizer.optimization_profiles is not None
        assert "nmap" in optimizer.optimization_profiles

    def test_get_base_parameters_for_nmap(self):
        """Test getting base parameters for nmap"""
        optimizer = ParameterOptimizer()
        profile = Mock(target="192.168.1.1", open_ports=[80, 443])

        params = optimizer._get_base_parameters("nmap", profile)

        assert params["target"] == "192.168.1.1"
        assert "scan_type" in params
        assert "timing" in params

    def test_get_base_parameters_for_gobuster(self):
        """Test getting base parameters for gobuster"""
        optimizer = ParameterOptimizer()
        profile = Mock(target="https://example.com", open_ports=[443])

        params = optimizer._get_base_parameters("gobuster", profile)

        assert params["target"] == "https://example.com"
        assert params["mode"] == "dir"
        assert "threads" in params

    def test_apply_technology_optimizations_for_wordpress(self):
        """Test applying optimizations for WordPress site"""
        optimizer = ParameterOptimizer()
        params = {"target": "example.com", "threads": 20}
        detected_tech = {
            "web_servers": ["apache"],
            "cms": ["wordpress"],
            "languages": ["php"],
            "frameworks": [],
            "databases": [],
            "security": [],
            "services": []
        }

        result = optimizer._apply_technology_optimizations("gobuster", params, detected_tech)

        # Should add WordPress-specific extensions
        assert "extensions" in result
        assert "php" in result["extensions"]

    def test_apply_technology_optimizations_with_waf(self):
        """Test applying optimizations when WAF detected"""
        optimizer = ParameterOptimizer()
        params = {"target": "example.com", "threads": 50}
        detected_tech = {
            "web_servers": [],
            "cms": [],
            "languages": [],
            "frameworks": [],
            "databases": [],
            "security": ["cloudflare"],
            "services": []
        }

        result = optimizer._apply_technology_optimizations("gobuster", params, detected_tech)

        # Should enable stealth mode and reduce threads
        assert result.get("_stealth_mode") is True
        assert result["threads"] <= 5

    def test_apply_profile_optimizations_stealth(self):
        """Test applying stealth profile optimizations"""
        optimizer = ParameterOptimizer()
        params = {"target": "example.com"}

        result = optimizer._apply_profile_optimizations("nmap", params, "stealth")

        assert result["timing"] == "-T2"
        assert "max-retries 1" in result["additional_args"]

    def test_apply_profile_optimizations_aggressive(self):
        """Test applying aggressive profile optimizations"""
        optimizer = ParameterOptimizer()
        params = {"target": "example.com"}

        result = optimizer._apply_profile_optimizations("nmap", params, "aggressive")

        assert result["timing"] == "-T5"
        assert "min-rate 1000" in result["additional_args"]

    def test_handle_timeout_failure(self):
        """Test handling timeout failure"""
        optimizer = ParameterOptimizer()
        params = {"timeout": 30, "threads": 50}

        recovery = optimizer.handle_tool_failure(
            tool="nmap",
            error_output="Connection timeout",
            exit_code=124,
            current_params=params
        )

        assert recovery["original_tool"] == "nmap"
        assert recovery["adjusted_parameters"]["timeout"] == 60  # doubled
        assert recovery["adjusted_parameters"]["threads"] == 25  # halved
        assert len(recovery["recovery_actions"]) > 0

    def test_handle_rate_limited_failure(self):
        """Test handling rate limited failure"""
        optimizer = ParameterOptimizer()
        params = {"threads": 50, "delay": 0}

        recovery = optimizer.handle_tool_failure(
            tool="gobuster",
            error_output="Rate limit exceeded",
            exit_code=1,
            current_params=params
        )

        # Should apply stealth timing
        assert recovery["adjusted_parameters"]["threads"] <= params["threads"]
        assert "stealth" in recovery["recovery_actions"][0].lower()

    @patch.object(PerformanceMonitor, 'monitor_system_resources')
    def test_optimize_parameters_advanced(self, mock_monitor):
        """Test advanced parameter optimization"""
        mock_monitor.return_value = {
            "cpu_percent": 50.0,
            "memory_percent": 60.0,
            "disk_percent": 70.0,
            "network_bytes_sent": 1000,
            "network_bytes_recv": 2000,
            "timestamp": 1234567890
        }

        optimizer = ParameterOptimizer()
        profile = Mock(target="192.168.1.1", open_ports=[80, 443])
        context = {"optimization_profile": "normal"}

        result = optimizer.optimize_parameters_advanced("nmap", profile, context)

        assert result["target"] == "192.168.1.1"
        assert "_optimization_metadata" in result
        assert "detected_technologies" in result["_optimization_metadata"]
        assert "resource_usage" in result["_optimization_metadata"]


def test_full_optimization_workflow():
    """Integration test for full optimization workflow"""
    optimizer = ParameterOptimizer()
    profile = Mock(target="https://example.com", open_ports=[80, 443, 3306])

    # Simulate context with headers and content
    context = {
        "headers": {"Server": "Apache/2.4", "X-Powered-By": "PHP/7.4"},
        "content": "<html>wp-content</html>",
        "optimization_profile": "normal"
    }

    with patch.object(PerformanceMonitor, 'monitor_system_resources') as mock_monitor:
        mock_monitor.return_value = {
            "cpu_percent": 50.0,
            "memory_percent": 60.0,
            "disk_percent": 70.0,
            "network_bytes_sent": 1000,
            "network_bytes_recv": 2000,
            "timestamp": 1234567890
        }

        result = optimizer.optimize_parameters_advanced("gobuster", profile, context)

        # Should have detected WordPress + Apache + PHP
        metadata = result["_optimization_metadata"]
        assert "apache" in metadata["detected_technologies"]["web_servers"] or \
               "wordpress" in metadata["detected_technologies"]["cms"] or \
               "php" in metadata["detected_technologies"]["languages"]

        # Should have optimization metadata
        assert "resource_usage" in metadata
        assert metadata["optimization_profile"] == "normal"
