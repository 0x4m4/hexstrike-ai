"""
Unit tests for BugBountyWorkflowManager

Tests cover:
- Workflow manager initialization
- Reconnaissance workflow creation
- Vulnerability hunting workflows
- Business logic testing
- OSINT workflow creation
- Test scenario generation
- Tool selection for bug bounties
- Priority vulnerability handling
- Edge cases and error handling

Target: 95%+ code coverage with 30+ comprehensive tests
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock
from typing import Dict, List, Any

# Add parent directories to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from hexstrike_server import (
    BugBountyWorkflowManager,
    BugBountyTarget
)


class TestBugBountyManagerInitialization:
    """Test BugBountyWorkflowManager initialization"""

    def test_manager_initializes_successfully(self):
        """Test manager initializes with all required components"""
        manager = BugBountyWorkflowManager()
        assert manager.high_impact_vulns is not None
        assert manager.reconnaissance_tools is not None
        assert isinstance(manager.high_impact_vulns, dict)
        assert isinstance(manager.reconnaissance_tools, list)

    def test_high_impact_vulns_initialized(self):
        """Test high impact vulnerabilities are properly configured"""
        manager = BugBountyWorkflowManager()
        expected_vulns = ["rce", "sqli", "ssrf", "idor", "xss", "lfi", "xxe", "csrf"]

        for vuln in expected_vulns:
            assert vuln in manager.high_impact_vulns
            assert "priority" in manager.high_impact_vulns[vuln]
            assert "tools" in manager.high_impact_vulns[vuln]
            assert "payloads" in manager.high_impact_vulns[vuln]

    def test_vulnerability_priorities(self):
        """Test vulnerabilities have correct priority ordering"""
        manager = BugBountyWorkflowManager()
        assert manager.high_impact_vulns["rce"]["priority"] == 10  # Highest
        assert manager.high_impact_vulns["sqli"]["priority"] == 9
        assert manager.high_impact_vulns["csrf"]["priority"] == 5  # Lower

    def test_reconnaissance_tools_configured(self):
        """Test reconnaissance tools are properly configured"""
        manager = BugBountyWorkflowManager()
        assert len(manager.reconnaissance_tools) > 0

        for tool_config in manager.reconnaissance_tools:
            assert "tool" in tool_config
            assert "phase" in tool_config
            assert "priority" in tool_config


class TestBugBountyTarget:
    """Test BugBountyTarget dataclass"""

    def test_create_basic_target(self):
        """Test creating a basic bug bounty target"""
        target = BugBountyTarget(domain="example.com")
        assert target.domain == "example.com"
        assert target.scope == []
        assert target.program_type == "web"

    def test_create_target_with_scope(self):
        """Test creating target with scope definition"""
        target = BugBountyTarget(
            domain="example.com",
            scope=["*.example.com", "api.example.com"],
            out_of_scope=["blog.example.com"]
        )
        assert len(target.scope) == 2
        assert len(target.out_of_scope) == 1

    def test_target_default_priority_vulns(self):
        """Test target has default priority vulnerabilities"""
        target = BugBountyTarget(domain="example.com")
        assert "rce" in target.priority_vulns
        assert "sqli" in target.priority_vulns
        assert "xss" in target.priority_vulns

    def test_create_api_target(self):
        """Test creating API program target"""
        target = BugBountyTarget(
            domain="api.example.com",
            program_type="api"
        )
        assert target.program_type == "api"


class TestReconnaissanceWorkflow:
    """Test reconnaissance workflow creation"""

    def test_create_reconnaissance_workflow(self):
        """Test creating basic reconnaissance workflow"""
        manager = BugBountyWorkflowManager()
        target = BugBountyTarget(domain="example.com")

        workflow = manager.create_reconnaissance_workflow(target)

        assert isinstance(workflow, dict)
        assert "target" in workflow
        assert workflow["target"] == "example.com"
        assert "phases" in workflow
        assert len(workflow["phases"]) > 0

    def test_reconnaissance_workflow_has_subdomain_phase(self):
        """Test workflow includes subdomain discovery phase"""
        manager = BugBountyWorkflowManager()
        target = BugBountyTarget(domain="example.com")

        workflow = manager.create_reconnaissance_workflow(target)
        phase_names = [phase["name"] for phase in workflow["phases"]]

        assert "subdomain_discovery" in phase_names

    def test_reconnaissance_workflow_has_http_phase(self):
        """Test workflow includes HTTP service discovery"""
        manager = BugBountyWorkflowManager()
        target = BugBountyTarget(domain="example.com")

        workflow = manager.create_reconnaissance_workflow(target)
        phase_names = [phase["name"] for phase in workflow["phases"]]

        assert "http_service_discovery" in phase_names

    def test_reconnaissance_workflow_has_content_discovery(self):
        """Test workflow includes content discovery phase"""
        manager = BugBountyWorkflowManager()
        target = BugBountyTarget(domain="example.com")

        workflow = manager.create_reconnaissance_workflow(target)
        phase_names = [phase["name"] for phase in workflow["phases"]]

        assert "content_discovery" in phase_names

    def test_reconnaissance_workflow_has_parameter_discovery(self):
        """Test workflow includes parameter discovery phase"""
        manager = BugBountyWorkflowManager()
        target = BugBountyTarget(domain="example.com")

        workflow = manager.create_reconnaissance_workflow(target)
        phase_names = [phase["name"] for phase in workflow["phases"]]

        assert "parameter_discovery" in phase_names

    def test_reconnaissance_workflow_estimated_time(self):
        """Test workflow has estimated time calculation"""
        manager = BugBountyWorkflowManager()
        target = BugBountyTarget(domain="example.com")

        workflow = manager.create_reconnaissance_workflow(target)

        assert "estimated_time" in workflow
        assert workflow["estimated_time"] > 0

    def test_reconnaissance_workflow_tools_count(self):
        """Test workflow includes tools count"""
        manager = BugBountyWorkflowManager()
        target = BugBountyTarget(domain="example.com")

        workflow = manager.create_reconnaissance_workflow(target)

        assert "tools_count" in workflow
        assert workflow["tools_count"] > 0

    def test_subdomain_phase_includes_tools(self):
        """Test subdomain discovery phase includes proper tools"""
        manager = BugBountyWorkflowManager()
        target = BugBountyTarget(domain="example.com")

        workflow = manager.create_reconnaissance_workflow(target)
        subdomain_phase = [p for p in workflow["phases"] if p["name"] == "subdomain_discovery"][0]

        tool_names = [t["tool"] for t in subdomain_phase["tools"]]
        assert "amass" in tool_names or "subfinder" in tool_names


class TestVulnerabilityHuntingWorkflow:
    """Test vulnerability hunting workflow creation"""

    def test_create_vulnerability_hunting_workflow(self):
        """Test creating vulnerability hunting workflow"""
        manager = BugBountyWorkflowManager()
        target = BugBountyTarget(domain="example.com")

        workflow = manager.create_vulnerability_hunting_workflow(target)

        assert isinstance(workflow, dict)
        assert "target" in workflow
        assert "vulnerability_tests" in workflow

    def test_vulnerability_workflow_sorted_by_priority(self):
        """Test vulnerabilities are sorted by priority"""
        manager = BugBountyWorkflowManager()
        target = BugBountyTarget(
            domain="example.com",
            priority_vulns=["xss", "rce", "sqli"]
        )

        workflow = manager.create_vulnerability_hunting_workflow(target)
        tests = workflow["vulnerability_tests"]

        # RCE should come first (priority 10), then SQLI (9), then XSS (7)
        priorities = [test["priority"] for test in tests]
        assert priorities == sorted(priorities, reverse=True)

    def test_vulnerability_workflow_includes_tools(self):
        """Test vulnerability tests include appropriate tools"""
        manager = BugBountyWorkflowManager()
        target = BugBountyTarget(
            domain="example.com",
            priority_vulns=["sqli"]
        )

        workflow = manager.create_vulnerability_hunting_workflow(target)
        sqli_test = workflow["vulnerability_tests"][0]

        assert "tools" in sqli_test
        assert "sqlmap" in sqli_test["tools"]

    def test_vulnerability_workflow_has_test_scenarios(self):
        """Test vulnerability tests include test scenarios"""
        manager = BugBountyWorkflowManager()
        target = BugBountyTarget(
            domain="example.com",
            priority_vulns=["rce"]
        )

        workflow = manager.create_vulnerability_hunting_workflow(target)
        rce_test = workflow["vulnerability_tests"][0]

        assert "test_scenarios" in rce_test
        assert len(rce_test["test_scenarios"]) > 0

    def test_vulnerability_workflow_estimated_time(self):
        """Test workflow has estimated time"""
        manager = BugBountyWorkflowManager()
        target = BugBountyTarget(domain="example.com")

        workflow = manager.create_vulnerability_hunting_workflow(target)

        assert "estimated_time" in workflow
        assert workflow["estimated_time"] > 0

    def test_vulnerability_workflow_priority_score(self):
        """Test workflow has priority score"""
        manager = BugBountyWorkflowManager()
        target = BugBountyTarget(domain="example.com")

        workflow = manager.create_vulnerability_hunting_workflow(target)

        assert "priority_score" in workflow
        assert workflow["priority_score"] > 0


class TestVulnerabilityScenarios:
    """Test vulnerability test scenario generation"""

    def test_rce_test_scenarios(self):
        """Test RCE test scenarios"""
        manager = BugBountyWorkflowManager()
        scenarios = manager._get_test_scenarios("rce")

        assert isinstance(scenarios, list)
        assert len(scenarios) > 0

        scenario_names = [s["name"] for s in scenarios]
        assert any("Command Injection" in name for name in scenario_names)

    def test_sqli_test_scenarios(self):
        """Test SQL injection test scenarios"""
        manager = BugBountyWorkflowManager()
        scenarios = manager._get_test_scenarios("sqli")

        assert isinstance(scenarios, list)
        assert len(scenarios) > 0

        scenario_names = [s["name"] for s in scenarios]
        assert any("Union" in name or "Boolean" in name for name in scenario_names)

    def test_xss_test_scenarios(self):
        """Test XSS test scenarios"""
        manager = BugBountyWorkflowManager()
        scenarios = manager._get_test_scenarios("xss")

        assert isinstance(scenarios, list)
        assert len(scenarios) > 0

        scenario_names = [s["name"] for s in scenarios]
        assert any("XSS" in name for name in scenario_names)

    def test_ssrf_test_scenarios(self):
        """Test SSRF test scenarios"""
        manager = BugBountyWorkflowManager()
        scenarios = manager._get_test_scenarios("ssrf")

        assert isinstance(scenarios, list)
        assert len(scenarios) > 0

    def test_idor_test_scenarios(self):
        """Test IDOR test scenarios"""
        manager = BugBountyWorkflowManager()
        scenarios = manager._get_test_scenarios("idor")

        assert isinstance(scenarios, list)
        assert len(scenarios) > 0

    def test_unknown_vuln_scenarios(self):
        """Test scenarios for unknown vulnerability type"""
        manager = BugBountyWorkflowManager()
        scenarios = manager._get_test_scenarios("unknown_vuln_type")

        assert isinstance(scenarios, list)
        # Should return empty list for unknown types
        assert len(scenarios) == 0


class TestBusinessLogicWorkflow:
    """Test business logic testing workflow"""

    def test_create_business_logic_workflow(self):
        """Test creating business logic testing workflow"""
        manager = BugBountyWorkflowManager()
        target = BugBountyTarget(domain="example.com")

        workflow = manager.create_business_logic_testing_workflow(target)

        assert isinstance(workflow, dict)
        assert "target" in workflow
        assert "business_logic_tests" in workflow

    def test_business_logic_categories(self):
        """Test business logic workflow includes key categories"""
        manager = BugBountyWorkflowManager()
        target = BugBountyTarget(domain="example.com")

        workflow = manager.create_business_logic_testing_workflow(target)
        tests = workflow["business_logic_tests"]

        categories = [test["category"] for test in tests]
        assert "Authentication Bypass" in categories
        assert "Authorization Flaws" in categories

    def test_business_logic_workflow_has_manual_flag(self):
        """Test workflow indicates manual testing required"""
        manager = BugBountyWorkflowManager()
        target = BugBountyTarget(domain="example.com")

        workflow = manager.create_business_logic_testing_workflow(target)

        assert "manual_testing_required" in workflow
        assert workflow["manual_testing_required"] is True

    def test_business_logic_workflow_estimated_time(self):
        """Test business logic workflow has estimated time"""
        manager = BugBountyWorkflowManager()
        target = BugBountyTarget(domain="example.com")

        workflow = manager.create_business_logic_testing_workflow(target)

        assert "estimated_time" in workflow
        assert workflow["estimated_time"] > 0


class TestOSINTWorkflow:
    """Test OSINT gathering workflow"""

    def test_create_osint_workflow(self):
        """Test creating OSINT workflow"""
        manager = BugBountyWorkflowManager()
        target = BugBountyTarget(domain="example.com")

        workflow = manager.create_osint_workflow(target)

        assert isinstance(workflow, dict)
        assert "target" in workflow
        assert "osint_phases" in workflow

    def test_osint_workflow_phases(self):
        """Test OSINT workflow includes all phases"""
        manager = BugBountyWorkflowManager()
        target = BugBountyTarget(domain="example.com")

        workflow = manager.create_osint_workflow(target)
        phases = workflow["osint_phases"]

        phase_names = [phase["name"] for phase in phases]
        assert "Domain Intelligence" in phase_names
        assert "Social Media Intelligence" in phase_names
        assert "Email Intelligence" in phase_names
        assert "Technology Intelligence" in phase_names

    def test_osint_workflow_estimated_time(self):
        """Test OSINT workflow has estimated time"""
        manager = BugBountyWorkflowManager()
        target = BugBountyTarget(domain="example.com")

        workflow = manager.create_osint_workflow(target)

        assert "estimated_time" in workflow
        assert workflow["estimated_time"] > 0

    def test_osint_workflow_intelligence_types(self):
        """Test OSINT workflow includes intelligence types"""
        manager = BugBountyWorkflowManager()
        target = BugBountyTarget(domain="example.com")

        workflow = manager.create_osint_workflow(target)

        assert "intelligence_types" in workflow
        assert isinstance(workflow["intelligence_types"], list)

    def test_domain_intelligence_tools(self):
        """Test domain intelligence phase includes proper tools"""
        manager = BugBountyWorkflowManager()
        target = BugBountyTarget(domain="example.com")

        workflow = manager.create_osint_workflow(target)
        domain_phase = [p for p in workflow["osint_phases"] if p["name"] == "Domain Intelligence"][0]

        tool_names = [t["tool"] for t in domain_phase["tools"]]
        assert "whois" in tool_names


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_create_workflow_empty_priority_vulns(self):
        """Test workflow creation with empty priority vulnerabilities"""
        manager = BugBountyWorkflowManager()
        target = BugBountyTarget(
            domain="example.com",
            priority_vulns=[]
        )

        workflow = manager.create_vulnerability_hunting_workflow(target)

        assert isinstance(workflow, dict)
        assert len(workflow["vulnerability_tests"]) == 0

    def test_create_workflow_unknown_vulns(self):
        """Test workflow creation with unknown vulnerability types"""
        manager = BugBountyWorkflowManager()
        target = BugBountyTarget(
            domain="example.com",
            priority_vulns=["unknown_vuln1", "unknown_vuln2"]
        )

        workflow = manager.create_vulnerability_hunting_workflow(target)

        # Should handle gracefully
        assert isinstance(workflow, dict)

    def test_recon_workflow_with_mobile_target(self):
        """Test reconnaissance workflow with mobile app target"""
        manager = BugBountyWorkflowManager()
        target = BugBountyTarget(
            domain="example.com",
            program_type="mobile"
        )

        workflow = manager.create_reconnaissance_workflow(target)

        assert isinstance(workflow, dict)
        assert "phases" in workflow

    def test_vuln_workflow_single_priority(self):
        """Test vulnerability workflow with single priority vulnerability"""
        manager = BugBountyWorkflowManager()
        target = BugBountyTarget(
            domain="example.com",
            priority_vulns=["rce"]
        )

        workflow = manager.create_vulnerability_hunting_workflow(target)

        assert len(workflow["vulnerability_tests"]) == 1
        assert workflow["vulnerability_tests"][0]["vulnerability_type"] == "rce"

    def test_workflow_with_special_characters_domain(self):
        """Test workflow creation with special characters in domain"""
        manager = BugBountyWorkflowManager()
        target = BugBountyTarget(domain="ex-ample_123.com")

        workflow = manager.create_reconnaissance_workflow(target)

        assert workflow["target"] == "ex-ample_123.com"


class TestWorkflowIntegration:
    """Test integration between different workflows"""

    def test_multiple_workflow_creation(self):
        """Test creating multiple workflows for same target"""
        manager = BugBountyWorkflowManager()
        target = BugBountyTarget(domain="example.com")

        recon_workflow = manager.create_reconnaissance_workflow(target)
        vuln_workflow = manager.create_vulnerability_hunting_workflow(target)
        osint_workflow = manager.create_osint_workflow(target)

        assert recon_workflow["target"] == "example.com"
        assert vuln_workflow["target"] == "example.com"
        assert osint_workflow["target"] == "example.com"

    def test_workflow_phase_completeness(self):
        """Test that workflows have complete phase information"""
        manager = BugBountyWorkflowManager()
        target = BugBountyTarget(domain="example.com")

        workflow = manager.create_reconnaissance_workflow(target)

        for phase in workflow["phases"]:
            assert "name" in phase
            assert "description" in phase
            assert "tools" in phase
            assert "estimated_time" in phase


class TestVulnerabilityPrioritization:
    """Test vulnerability prioritization logic"""

    def test_high_priority_vulns_first(self):
        """Test high priority vulnerabilities are tested first"""
        manager = BugBountyWorkflowManager()
        target = BugBountyTarget(
            domain="example.com",
            priority_vulns=["csrf", "rce", "xss"]  # Mixed priorities
        )

        workflow = manager.create_vulnerability_hunting_workflow(target)
        tests = workflow["vulnerability_tests"]

        # RCE should be first
        assert tests[0]["vulnerability_type"] == "rce"
        assert tests[0]["priority"] == 10

    def test_priority_score_calculation(self):
        """Test overall priority score calculation"""
        manager = BugBountyWorkflowManager()
        target = BugBountyTarget(
            domain="example.com",
            priority_vulns=["rce", "sqli"]
        )

        workflow = manager.create_vulnerability_hunting_workflow(target)

        # Priority score should be sum of individual priorities
        expected_score = 10 + 9  # rce + sqli
        assert workflow["priority_score"] == expected_score

    def test_time_allocation_by_priority(self):
        """Test time allocation based on vulnerability priority"""
        manager = BugBountyWorkflowManager()
        target = BugBountyTarget(
            domain="example.com",
            priority_vulns=["rce"]
        )

        workflow = manager.create_vulnerability_hunting_workflow(target)
        rce_test = workflow["vulnerability_tests"][0]

        # Higher priority should get more time
        assert rce_test["estimated_time"] == rce_test["priority"] * 30


class TestPayloadGeneration:
    """Test payload information in vulnerability tests"""

    def test_rce_payloads(self):
        """Test RCE payloads are included in scenarios"""
        manager = BugBountyWorkflowManager()
        scenarios = manager._get_test_scenarios("rce")

        # Check that payloads exist in scenarios
        assert any("payloads" in scenario for scenario in scenarios)

    def test_sqli_payloads(self):
        """Test SQL injection payloads are included"""
        manager = BugBountyWorkflowManager()
        scenarios = manager._get_test_scenarios("sqli")

        assert any("payloads" in scenario for scenario in scenarios)

    def test_payload_variety(self):
        """Test different payload types for XSS"""
        manager = BugBountyWorkflowManager()
        scenarios = manager._get_test_scenarios("xss")

        # Should have different types: reflected, stored, DOM
        scenario_names = [s["name"] for s in scenarios]
        assert any("Reflected" in name for name in scenario_names)
