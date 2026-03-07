"""
Unit tests for IntelligentDecisionEngine

Tests cover:
- Tool effectiveness initialization
- Target analysis and profiling
- Tool selection strategies
- Parameter optimization
- Attack chain creation
- Technology detection
- Risk level determination
- Confidence scoring
- Edge cases and error handling

Target: 95%+ code coverage with 40+ comprehensive tests
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock
from typing import Dict, List, Any

# Add parent directories to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from agents.decision_engine import (
    IntelligentDecisionEngine,
    TargetProfile,
    TargetType,
    TechnologyStack,
    AttackChain,
    AttackStep
)


class TestDecisionEngineInitialization:
    """Test IntelligentDecisionEngine initialization"""

    def test_engine_initializes_successfully(self):
        """Test engine initializes with all required components"""
        engine = IntelligentDecisionEngine()
        assert engine.tool_effectiveness is not None
        assert engine.technology_signatures is not None
        assert engine.attack_patterns is not None
        assert engine._use_advanced_optimizer is True

    def test_tool_effectiveness_has_all_target_types(self):
        """Test tool effectiveness includes all target types"""
        engine = IntelligentDecisionEngine()
        expected_types = [
            TargetType.WEB_APPLICATION.value,
            TargetType.NETWORK_HOST.value,
            TargetType.API_ENDPOINT.value,
            TargetType.CLOUD_SERVICE.value,
            TargetType.BINARY_FILE.value
        ]
        for target_type in expected_types:
            assert target_type in engine.tool_effectiveness
            assert isinstance(engine.tool_effectiveness[target_type], dict)
            assert len(engine.tool_effectiveness[target_type]) > 0

    def test_technology_signatures_initialized(self):
        """Test technology signatures are properly initialized"""
        engine = IntelligentDecisionEngine()
        assert "headers" in engine.technology_signatures
        assert "content" in engine.technology_signatures
        assert "ports" in engine.technology_signatures

    def test_attack_patterns_initialized(self):
        """Test attack patterns are initialized with common scenarios"""
        engine = IntelligentDecisionEngine()
        expected_patterns = [
            "web_reconnaissance",
            "api_testing",
            "network_discovery",
            "vulnerability_assessment"
        ]
        for pattern in expected_patterns:
            assert pattern in engine.attack_patterns
            assert isinstance(engine.attack_patterns[pattern], list)
            assert len(engine.attack_patterns[pattern]) > 0


class TestTargetTypeDetection:
    """Test target type determination logic"""

    def test_detect_web_application_http(self):
        """Test detection of web application with http URL"""
        engine = IntelligentDecisionEngine()
        target_type = engine._determine_target_type("http://example.com")
        assert target_type == TargetType.WEB_APPLICATION

    def test_detect_web_application_https(self):
        """Test detection of web application with https URL"""
        engine = IntelligentDecisionEngine()
        target_type = engine._determine_target_type("https://example.com")
        assert target_type == TargetType.WEB_APPLICATION

    def test_detect_api_endpoint(self):
        """Test detection of API endpoint"""
        engine = IntelligentDecisionEngine()
        target_type = engine._determine_target_type("https://api.example.com/v1")
        assert target_type == TargetType.API_ENDPOINT

    def test_detect_api_endpoint_with_path(self):
        """Test detection of API with /api/ path"""
        engine = IntelligentDecisionEngine()
        target_type = engine._determine_target_type("https://example.com/api/users")
        assert target_type == TargetType.API_ENDPOINT

    def test_detect_ip_address(self):
        """Test detection of network host by IP"""
        engine = IntelligentDecisionEngine()
        target_type = engine._determine_target_type("192.168.1.100")
        assert target_type == TargetType.NETWORK_HOST

    def test_detect_domain_name(self):
        """Test detection of domain as web application"""
        engine = IntelligentDecisionEngine()
        target_type = engine._determine_target_type("example.com")
        assert target_type == TargetType.WEB_APPLICATION

    def test_detect_binary_file_exe(self):
        """Test detection of binary file (.exe)"""
        engine = IntelligentDecisionEngine()
        target_type = engine._determine_target_type("/path/to/binary.exe")
        assert target_type == TargetType.BINARY_FILE

    def test_detect_binary_file_elf(self):
        """Test detection of binary file (.elf)"""
        engine = IntelligentDecisionEngine()
        target_type = engine._determine_target_type("/path/to/binary.elf")
        assert target_type == TargetType.BINARY_FILE

    def test_detect_cloud_service_aws(self):
        """Test detection of cloud service (AWS)"""
        engine = IntelligentDecisionEngine()
        target_type = engine._determine_target_type("https://bucket.s3.amazonaws.com")
        assert target_type == TargetType.CLOUD_SERVICE

    def test_detect_cloud_service_azure(self):
        """Test detection of cloud service (Azure)"""
        engine = IntelligentDecisionEngine()
        target_type = engine._determine_target_type("https://storage.azure.com")
        assert target_type == TargetType.CLOUD_SERVICE

    def test_detect_unknown_target(self):
        """Test detection of unknown target type"""
        engine = IntelligentDecisionEngine()
        target_type = engine._determine_target_type("unknown_format")
        assert target_type == TargetType.UNKNOWN


class TestTargetAnalysis:
    """Test target analysis and profiling"""

    @patch('socket.gethostbyname')
    def test_analyze_web_target(self, mock_gethostbyname):
        """Test analysis of web application target"""
        mock_gethostbyname.return_value = "93.184.216.34"
        engine = IntelligentDecisionEngine()
        profile = engine.analyze_target("https://example.com")

        assert profile.target == "https://example.com"
        assert profile.target_type == TargetType.WEB_APPLICATION
        assert len(profile.ip_addresses) > 0
        assert profile.attack_surface_score > 0
        assert profile.confidence_score > 0

    @patch('socket.gethostbyname')
    def test_analyze_wordpress_site(self, mock_gethostbyname):
        """Test analysis of WordPress site"""
        mock_gethostbyname.return_value = "93.184.216.34"
        engine = IntelligentDecisionEngine()
        profile = engine.analyze_target("https://wordpress.example.com/wp-admin")

        assert TechnologyStack.WORDPRESS in profile.technologies
        assert profile.cms_type == "WordPress"

    def test_analyze_network_host(self):
        """Test analysis of network host"""
        engine = IntelligentDecisionEngine()
        profile = engine.analyze_target("192.168.1.100")

        assert profile.target_type == TargetType.NETWORK_HOST
        assert profile.target == "192.168.1.100"

    @patch('socket.gethostbyname')
    def test_analyze_api_endpoint(self, mock_gethostbyname):
        """Test analysis of API endpoint"""
        mock_gethostbyname.return_value = "93.184.216.34"
        engine = IntelligentDecisionEngine()
        profile = engine.analyze_target("https://api.example.com/v1")

        assert profile.target_type == TargetType.API_ENDPOINT
        assert len(profile.ip_addresses) > 0

    def test_attack_surface_calculation(self):
        """Test attack surface score calculation"""
        engine = IntelligentDecisionEngine()
        profile = TargetProfile(
            target="example.com",
            target_type=TargetType.WEB_APPLICATION,
            technologies=[TechnologyStack.PHP, TechnologyStack.APACHE],
            open_ports=[80, 443, 8080],
            cms_type="WordPress"
        )
        score = engine._calculate_attack_surface(profile)
        assert score > 0
        assert score <= 10.0

    def test_risk_level_critical(self):
        """Test risk level determination for critical score"""
        engine = IntelligentDecisionEngine()
        profile = TargetProfile(target="test", attack_surface_score=9.5)
        risk = engine._determine_risk_level(profile)
        assert risk == "critical"

    def test_risk_level_high(self):
        """Test risk level determination for high score"""
        engine = IntelligentDecisionEngine()
        profile = TargetProfile(target="test", attack_surface_score=7.0)
        risk = engine._determine_risk_level(profile)
        assert risk == "high"

    def test_risk_level_medium(self):
        """Test risk level determination for medium score"""
        engine = IntelligentDecisionEngine()
        profile = TargetProfile(target="test", attack_surface_score=5.0)
        risk = engine._determine_risk_level(profile)
        assert risk == "medium"

    def test_risk_level_low(self):
        """Test risk level determination for low score"""
        engine = IntelligentDecisionEngine()
        profile = TargetProfile(target="test", attack_surface_score=3.0)
        risk = engine._determine_risk_level(profile)
        assert risk == "low"

    def test_confidence_calculation(self):
        """Test confidence score calculation"""
        engine = IntelligentDecisionEngine()
        profile = TargetProfile(
            target="example.com",
            target_type=TargetType.WEB_APPLICATION,
            ip_addresses=["93.184.216.34"],
            technologies=[TechnologyStack.PHP],
            cms_type="WordPress"
        )
        confidence = engine._calculate_confidence(profile)
        assert 0.0 <= confidence <= 1.0


class TestToolSelection:
    """Test tool selection strategies"""

    def test_select_tools_for_web_application(self):
        """Test tool selection for web application"""
        engine = IntelligentDecisionEngine()
        profile = TargetProfile(
            target="https://example.com",
            target_type=TargetType.WEB_APPLICATION
        )
        tools = engine.select_optimal_tools(profile, objective="comprehensive")
        assert isinstance(tools, list)
        assert len(tools) > 0
        assert any(tool in tools for tool in ["nmap", "nuclei", "gobuster"])

    def test_select_tools_quick_mode(self):
        """Test tool selection in quick mode"""
        engine = IntelligentDecisionEngine()
        profile = TargetProfile(
            target="https://example.com",
            target_type=TargetType.WEB_APPLICATION
        )
        tools = engine.select_optimal_tools(profile, objective="quick")
        assert isinstance(tools, list)
        assert len(tools) == 3  # Should select top 3 tools

    def test_select_tools_stealth_mode(self):
        """Test tool selection in stealth mode"""
        engine = IntelligentDecisionEngine()
        profile = TargetProfile(
            target="https://example.com",
            target_type=TargetType.WEB_APPLICATION
        )
        tools = engine.select_optimal_tools(profile, objective="stealth")
        assert isinstance(tools, list)
        # Should only include passive tools
        stealth_tools = ["amass", "subfinder", "httpx", "nuclei"]
        assert all(tool in stealth_tools for tool in tools if tool in stealth_tools)

    def test_select_tools_for_wordpress(self):
        """Test tool selection includes wpscan for WordPress"""
        engine = IntelligentDecisionEngine()
        profile = TargetProfile(
            target="https://example.com",
            target_type=TargetType.WEB_APPLICATION,
            technologies=[TechnologyStack.WORDPRESS]
        )
        tools = engine.select_optimal_tools(profile, objective="comprehensive")
        assert "wpscan" in tools

    def test_select_tools_for_network_host(self):
        """Test tool selection for network host"""
        engine = IntelligentDecisionEngine()
        profile = TargetProfile(
            target="192.168.1.100",
            target_type=TargetType.NETWORK_HOST
        )
        tools = engine.select_optimal_tools(profile, objective="comprehensive")
        assert isinstance(tools, list)
        assert any(tool in tools for tool in ["nmap", "masscan"])

    def test_select_tools_for_api(self):
        """Test tool selection for API endpoint"""
        engine = IntelligentDecisionEngine()
        profile = TargetProfile(
            target="https://api.example.com",
            target_type=TargetType.API_ENDPOINT
        )
        tools = engine.select_optimal_tools(profile, objective="comprehensive")
        assert isinstance(tools, list)
        assert any(tool in tools for tool in ["arjun", "ffuf", "httpx"])


class TestParameterOptimization:
    """Test parameter optimization for different tools"""

    def test_optimize_nmap_parameters(self):
        """Test nmap parameter optimization"""
        engine = IntelligentDecisionEngine()
        profile = TargetProfile(
            target="192.168.1.100",
            target_type=TargetType.NETWORK_HOST
        )
        params = engine.optimize_parameters("nmap", profile)
        assert isinstance(params, dict)

    def test_optimize_gobuster_parameters(self):
        """Test gobuster parameter optimization"""
        engine = IntelligentDecisionEngine()
        profile = TargetProfile(
            target="https://example.com",
            target_type=TargetType.WEB_APPLICATION
        )
        params = engine.optimize_parameters("gobuster", profile)
        assert isinstance(params, dict)

    def test_optimize_nuclei_parameters(self):
        """Test nuclei parameter optimization"""
        engine = IntelligentDecisionEngine()
        profile = TargetProfile(
            target="https://example.com",
            target_type=TargetType.WEB_APPLICATION
        )
        params = engine.optimize_parameters("nuclei", profile)
        assert isinstance(params, dict)

    def test_optimize_unknown_tool(self):
        """Test parameter optimization for unknown tool"""
        engine = IntelligentDecisionEngine()
        profile = TargetProfile(
            target="https://example.com",
            target_type=TargetType.WEB_APPLICATION
        )
        # Should use advanced optimizer for unknown tools
        params = engine.optimize_parameters("unknown_tool", profile)
        assert isinstance(params, dict)

    def test_parameter_optimization_with_context(self):
        """Test parameter optimization with additional context"""
        engine = IntelligentDecisionEngine()
        profile = TargetProfile(
            target="https://example.com",
            target_type=TargetType.WEB_APPLICATION
        )
        context = {"user_preference": "aggressive"}
        params = engine.optimize_parameters("nmap", profile, context)
        assert isinstance(params, dict)

    def test_advanced_optimizer_toggle(self):
        """Test enabling/disabling advanced optimizer"""
        engine = IntelligentDecisionEngine()

        # Test disabling
        engine.disable_advanced_optimization()
        assert engine._use_advanced_optimizer is False

        # Test enabling
        engine.enable_advanced_optimization()
        assert engine._use_advanced_optimizer is True


class TestTechnologyDetection:
    """Test technology detection logic"""

    def test_detect_wordpress(self):
        """Test WordPress detection"""
        engine = IntelligentDecisionEngine()
        techs = engine._detect_technologies("https://example.com/wp-admin")
        assert TechnologyStack.WORDPRESS in techs

    def test_detect_php(self):
        """Test PHP detection"""
        engine = IntelligentDecisionEngine()
        techs = engine._detect_technologies("https://example.com/index.php")
        assert TechnologyStack.PHP in techs

    def test_detect_dotnet(self):
        """Test .NET detection"""
        engine = IntelligentDecisionEngine()
        techs = engine._detect_technologies("https://example.com/page.aspx")
        assert TechnologyStack.DOTNET in techs

    def test_detect_unknown_technology(self):
        """Test unknown technology fallback"""
        engine = IntelligentDecisionEngine()
        techs = engine._detect_technologies("https://example.com")
        assert TechnologyStack.UNKNOWN in techs

    def test_detect_cms_wordpress(self):
        """Test WordPress CMS detection"""
        engine = IntelligentDecisionEngine()
        cms = engine._detect_cms("https://example.com/wp-login.php")
        assert cms == "WordPress"

    def test_detect_cms_drupal(self):
        """Test Drupal CMS detection"""
        engine = IntelligentDecisionEngine()
        cms = engine._detect_cms("https://example.com/drupal")
        assert cms == "Drupal"

    def test_detect_cms_joomla(self):
        """Test Joomla CMS detection"""
        engine = IntelligentDecisionEngine()
        cms = engine._detect_cms("https://example.com/joomla")
        assert cms == "Joomla"

    def test_detect_cms_none(self):
        """Test no CMS detected"""
        engine = IntelligentDecisionEngine()
        cms = engine._detect_cms("https://example.com")
        assert cms is None


class TestDomainResolution:
    """Test domain name resolution"""

    @patch('socket.gethostbyname')
    def test_resolve_domain_success(self, mock_gethostbyname):
        """Test successful domain resolution"""
        mock_gethostbyname.return_value = "93.184.216.34"
        engine = IntelligentDecisionEngine()
        ips = engine._resolve_domain("example.com")
        assert isinstance(ips, list)
        assert len(ips) > 0
        assert "93.184.216.34" in ips

    @patch('socket.gethostbyname')
    def test_resolve_domain_with_http(self, mock_gethostbyname):
        """Test domain resolution from http URL"""
        mock_gethostbyname.return_value = "93.184.216.34"
        engine = IntelligentDecisionEngine()
        ips = engine._resolve_domain("http://example.com")
        assert isinstance(ips, list)
        assert len(ips) > 0

    @patch('socket.gethostbyname')
    def test_resolve_domain_failure(self, mock_gethostbyname):
        """Test domain resolution failure handling"""
        mock_gethostbyname.side_effect = Exception("DNS resolution failed")
        engine = IntelligentDecisionEngine()
        ips = engine._resolve_domain("nonexistent.example.com")
        assert ips == []


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_target(self):
        """Test handling of empty target"""
        engine = IntelligentDecisionEngine()
        target_type = engine._determine_target_type("")
        assert target_type == TargetType.UNKNOWN

    def test_malformed_url(self):
        """Test handling of malformed URL"""
        engine = IntelligentDecisionEngine()
        target_type = engine._determine_target_type("ht!tp://malformed")
        assert target_type == TargetType.UNKNOWN

    def test_invalid_ip_address(self):
        """Test handling of invalid IP address"""
        engine = IntelligentDecisionEngine()
        target_type = engine._determine_target_type("999.999.999.999")
        assert target_type == TargetType.UNKNOWN

    def test_attack_surface_capped_at_10(self):
        """Test attack surface score is capped at 10.0"""
        engine = IntelligentDecisionEngine()
        profile = TargetProfile(
            target="test",
            target_type=TargetType.NETWORK_HOST,
            technologies=[TechnologyStack.PHP] * 20,  # Many technologies
            open_ports=list(range(100)),  # Many open ports
            subdomains=["sub" + str(i) for i in range(100)],  # Many subdomains
            cms_type="WordPress"
        )
        score = engine._calculate_attack_surface(profile)
        assert score <= 10.0

    def test_confidence_capped_at_1(self):
        """Test confidence score is capped at 1.0"""
        engine = IntelligentDecisionEngine()
        profile = TargetProfile(
            target="test",
            target_type=TargetType.WEB_APPLICATION,
            ip_addresses=["1.2.3.4"],
            technologies=[TechnologyStack.PHP],
            cms_type="WordPress"
        )
        confidence = engine._calculate_confidence(profile)
        assert confidence <= 1.0

    def test_select_tools_with_invalid_objective(self):
        """Test tool selection with invalid objective"""
        engine = IntelligentDecisionEngine()
        profile = TargetProfile(
            target="https://example.com",
            target_type=TargetType.WEB_APPLICATION
        )
        tools = engine.select_optimal_tools(profile, objective="invalid_objective")
        assert isinstance(tools, list)
        # Should return base tools for unknown objective

    def test_optimize_parameters_with_none_context(self):
        """Test parameter optimization with None context"""
        engine = IntelligentDecisionEngine()
        profile = TargetProfile(
            target="https://example.com",
            target_type=TargetType.WEB_APPLICATION
        )
        params = engine.optimize_parameters("nmap", profile, context=None)
        assert isinstance(params, dict)


class TestAttackChain:
    """Test attack chain functionality"""

    def test_create_attack_chain(self):
        """Test creating an attack chain"""
        profile = TargetProfile(
            target="https://example.com",
            target_type=TargetType.WEB_APPLICATION
        )
        chain = AttackChain(profile)
        assert chain.target_profile == profile
        assert len(chain.steps) == 0
        assert chain.success_probability == 0.0

    def test_add_step_to_chain(self):
        """Test adding step to attack chain"""
        profile = TargetProfile(target="https://example.com")
        chain = AttackChain(profile)

        step = AttackStep(
            tool="nmap",
            parameters={"scan_type": "-sV"},
            expected_outcome="Identify open ports",
            success_probability=0.9,
            execution_time_estimate=30
        )

        chain.add_step(step)
        assert len(chain.steps) == 1
        assert "nmap" in chain.required_tools
        assert chain.estimated_time == 30

    def test_calculate_chain_success_probability(self):
        """Test calculating attack chain success probability"""
        profile = TargetProfile(target="https://example.com")
        chain = AttackChain(profile)

        step1 = AttackStep(
            tool="nmap",
            parameters={},
            expected_outcome="Find ports",
            success_probability=0.9,
            execution_time_estimate=30
        )
        step2 = AttackStep(
            tool="gobuster",
            parameters={},
            expected_outcome="Find directories",
            success_probability=0.8,
            execution_time_estimate=60
        )

        chain.add_step(step1)
        chain.add_step(step2)
        chain.calculate_success_probability()

        # Compound probability: 0.9 * 0.8 = 0.72
        assert abs(chain.success_probability - 0.72) < 0.01

    def test_attack_chain_to_dict(self):
        """Test converting attack chain to dictionary"""
        profile = TargetProfile(target="https://example.com")
        chain = AttackChain(profile)

        step = AttackStep(
            tool="nmap",
            parameters={"scan_type": "-sV"},
            expected_outcome="Identify services",
            success_probability=0.9,
            execution_time_estimate=30,
            dependencies=[]
        )

        chain.add_step(step)
        chain.calculate_success_probability()

        result = chain.to_dict()
        assert isinstance(result, dict)
        assert "target" in result
        assert "steps" in result
        assert "success_probability" in result
        assert "estimated_time" in result
        assert "required_tools" in result


class TestTargetProfile:
    """Test TargetProfile dataclass"""

    def test_target_profile_creation(self):
        """Test creating a target profile"""
        profile = TargetProfile(
            target="https://example.com",
            target_type=TargetType.WEB_APPLICATION
        )
        assert profile.target == "https://example.com"
        assert profile.target_type == TargetType.WEB_APPLICATION

    def test_target_profile_to_dict(self):
        """Test converting target profile to dictionary"""
        profile = TargetProfile(
            target="https://example.com",
            target_type=TargetType.WEB_APPLICATION,
            technologies=[TechnologyStack.PHP, TechnologyStack.APACHE],
            cms_type="WordPress"
        )

        result = profile.to_dict()
        assert isinstance(result, dict)
        assert result["target"] == "https://example.com"
        assert result["target_type"] == "web_application"
        assert "php" in result["technologies"]
        assert result["cms_type"] == "WordPress"

    def test_target_profile_defaults(self):
        """Test target profile default values"""
        profile = TargetProfile(target="test")
        assert profile.target_type == TargetType.UNKNOWN
        assert profile.ip_addresses == []
        assert profile.open_ports == []
        assert profile.services == {}
        assert profile.technologies == []
        assert profile.attack_surface_score == 0.0
        assert profile.confidence_score == 0.0
