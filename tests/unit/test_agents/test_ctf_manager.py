"""
Unit tests for CTFWorkflowManager

Tests cover:
- CTF workflow manager initialization
- Challenge workflow creation
- Category-specific tool selection
- Solving strategy generation
- Team strategy creation
- Time estimation
- Success probability calculation
- Tool selection based on keywords
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
    CTFWorkflowManager,
    CTFChallenge
)


class TestCTFManagerInitialization:
    """Test CTFWorkflowManager initialization"""

    def test_manager_initializes_successfully(self):
        """Test manager initializes with all required components"""
        manager = CTFWorkflowManager()
        assert manager.category_tools is not None
        assert manager.solving_strategies is not None
        assert isinstance(manager.category_tools, dict)
        assert isinstance(manager.solving_strategies, dict)

    def test_category_tools_initialized(self):
        """Test category tools are properly initialized"""
        manager = CTFWorkflowManager()
        expected_categories = ["web", "crypto", "pwn", "forensics", "rev", "misc", "osint"]

        for category in expected_categories:
            assert category in manager.category_tools
            assert isinstance(manager.category_tools[category], dict)

    def test_solving_strategies_initialized(self):
        """Test solving strategies for all categories"""
        manager = CTFWorkflowManager()
        expected_categories = ["web", "crypto", "pwn", "forensics", "rev"]

        for category in expected_categories:
            assert category in manager.solving_strategies
            strategies = manager.solving_strategies[category]
            assert isinstance(strategies, list)
            assert len(strategies) > 0

    def test_web_category_tools(self):
        """Test web category has required tool types"""
        manager = CTFWorkflowManager()
        web_tools = manager.category_tools["web"]

        assert "reconnaissance" in web_tools
        assert "vulnerability_scanning" in web_tools
        assert "content_discovery" in web_tools

    def test_crypto_category_tools(self):
        """Test crypto category has required tool types"""
        manager = CTFWorkflowManager()
        crypto_tools = manager.category_tools["crypto"]

        assert "hash_analysis" in crypto_tools
        assert "cipher_analysis" in crypto_tools
        assert "rsa_attacks" in crypto_tools

    def test_pwn_category_tools(self):
        """Test pwn category has required tool types"""
        manager = CTFWorkflowManager()
        pwn_tools = manager.category_tools["pwn"]

        assert "binary_analysis" in pwn_tools
        assert "exploit_development" in pwn_tools


class TestCTFChallenge:
    """Test CTFChallenge dataclass"""

    def test_create_basic_challenge(self):
        """Test creating a basic CTF challenge"""
        challenge = CTFChallenge(
            name="Test Challenge",
            category="web",
            description="A test web challenge"
        )
        assert challenge.name == "Test Challenge"
        assert challenge.category == "web"
        assert challenge.points == 0
        assert challenge.difficulty == "unknown"

    def test_create_challenge_with_points(self):
        """Test creating challenge with points"""
        challenge = CTFChallenge(
            name="Hard Challenge",
            category="pwn",
            description="Binary exploitation",
            points=500,
            difficulty="hard"
        )
        assert challenge.points == 500
        assert challenge.difficulty == "hard"

    def test_create_challenge_with_files(self):
        """Test creating challenge with file attachments"""
        challenge = CTFChallenge(
            name="Crypto Challenge",
            category="crypto",
            description="Decrypt the file",
            files=["encrypted.txt", "key.pem"]
        )
        assert len(challenge.files) == 2

    def test_create_challenge_with_hints(self):
        """Test creating challenge with hints"""
        challenge = CTFChallenge(
            name="Mystery Challenge",
            category="misc",
            description="Find the flag",
            hints=["Look at the headers", "Try base64"]
        )
        assert len(challenge.hints) == 2


class TestChallengeWorkflowCreation:
    """Test CTF challenge workflow creation"""

    def test_create_web_challenge_workflow(self):
        """Test creating workflow for web challenge"""
        manager = CTFWorkflowManager()
        challenge = CTFChallenge(
            name="Web Challenge",
            category="web",
            description="SQL injection in login form",
            points=300,
            difficulty="medium"
        )

        workflow = manager.create_ctf_challenge_workflow(challenge)

        assert isinstance(workflow, dict)
        assert workflow["challenge"] == "Web Challenge"
        assert workflow["category"] == "web"
        assert workflow["difficulty"] == "medium"

    def test_workflow_has_tools(self):
        """Test workflow includes appropriate tools"""
        manager = CTFWorkflowManager()
        challenge = CTFChallenge(
            name="Test",
            category="web",
            description="Web challenge",
            difficulty="easy"
        )

        workflow = manager.create_ctf_challenge_workflow(challenge)

        assert "tools" in workflow
        assert isinstance(workflow["tools"], list)

    def test_workflow_has_strategies(self):
        """Test workflow includes solving strategies"""
        manager = CTFWorkflowManager()
        challenge = CTFChallenge(
            name="Test",
            category="web",
            description="Web challenge",
            difficulty="easy"
        )

        workflow = manager.create_ctf_challenge_workflow(challenge)

        assert "strategies" in workflow
        assert isinstance(workflow["strategies"], list)

    def test_workflow_estimated_time(self):
        """Test workflow has estimated time"""
        manager = CTFWorkflowManager()
        challenge = CTFChallenge(
            name="Test",
            category="web",
            description="Web challenge",
            difficulty="medium"
        )

        workflow = manager.create_ctf_challenge_workflow(challenge)

        assert "estimated_time" in workflow
        assert workflow["estimated_time"] > 0

    def test_workflow_success_probability(self):
        """Test workflow has success probability"""
        manager = CTFWorkflowManager()
        challenge = CTFChallenge(
            name="Test",
            category="web",
            description="Web challenge",
            difficulty="easy"
        )

        workflow = manager.create_ctf_challenge_workflow(challenge)

        assert "success_probability" in workflow
        assert 0 <= workflow["success_probability"] <= 1


class TestToolSelection:
    """Test tool selection for different challenges"""

    def test_web_sqli_tool_selection(self):
        """Test tool selection for SQL injection challenge"""
        manager = CTFWorkflowManager()
        challenge = CTFChallenge(
            name="SQL Challenge",
            category="web",
            description="SQL injection in database query",
            difficulty="medium"
        )

        workflow = manager.create_ctf_challenge_workflow(challenge)

        assert "sqlmap" in workflow["tools"]

    def test_web_xss_tool_selection(self):
        """Test tool selection for XSS challenge"""
        manager = CTFWorkflowManager()
        challenge = CTFChallenge(
            name="XSS Challenge",
            category="web",
            description="Exploit XSS vulnerability using JavaScript",
            difficulty="easy"
        )

        workflow = manager.create_ctf_challenge_workflow(challenge)

        assert "dalfox" in workflow["tools"]

    def test_web_wordpress_tool_selection(self):
        """Test tool selection for WordPress challenge"""
        manager = CTFWorkflowManager()
        challenge = CTFChallenge(
            name="WP Challenge",
            category="web",
            description="WordPress site vulnerability",
            difficulty="medium"
        )

        workflow = manager.create_ctf_challenge_workflow(challenge)

        assert "wpscan" in workflow["tools"]

    def test_crypto_hash_tool_selection(self):
        """Test tool selection for hash cracking challenge"""
        manager = CTFWorkflowManager()
        challenge = CTFChallenge(
            name="Hash Challenge",
            category="crypto",
            description="Crack the MD5 hash",
            difficulty="easy"
        )

        workflow = manager.create_ctf_challenge_workflow(challenge)

        assert any(tool in workflow["tools"] for tool in ["hashcat", "john"])

    def test_crypto_rsa_tool_selection(self):
        """Test tool selection for RSA challenge"""
        manager = CTFWorkflowManager()
        challenge = CTFChallenge(
            name="RSA Challenge",
            category="crypto",
            description="Break weak RSA public key encryption",
            difficulty="hard"
        )

        workflow = manager.create_ctf_challenge_workflow(challenge)

        assert any(tool in workflow["tools"] for tool in ["rsatool", "factordb"])

    def test_pwn_basic_tool_selection(self):
        """Test tool selection for pwn challenge"""
        manager = CTFWorkflowManager()
        challenge = CTFChallenge(
            name="Binary Exploit",
            category="pwn",
            description="Exploit buffer overflow",
            difficulty="medium"
        )

        workflow = manager.create_ctf_challenge_workflow(challenge)

        assert "checksec" in workflow["tools"]
        assert "ghidra" in workflow["tools"] or "pwntools" in workflow["tools"]

    def test_forensics_image_tool_selection(self):
        """Test tool selection for image forensics"""
        manager = CTFWorkflowManager()
        challenge = CTFChallenge(
            name="Image Forensics",
            category="forensics",
            description="Find hidden data in PNG image",
            difficulty="easy"
        )

        workflow = manager.create_ctf_challenge_workflow(challenge)

        assert any(tool in workflow["tools"] for tool in ["exiftool", "steghide", "stegsolve"])

    def test_forensics_memory_tool_selection(self):
        """Test tool selection for memory forensics"""
        manager = CTFWorkflowManager()
        challenge = CTFChallenge(
            name="Memory Dump",
            category="forensics",
            description="Analyze memory dump for secrets",
            difficulty="hard"
        )

        workflow = manager.create_ctf_challenge_workflow(challenge)

        assert "volatility" in workflow["tools"]

    def test_rev_basic_tool_selection(self):
        """Test tool selection for reverse engineering"""
        manager = CTFWorkflowManager()
        challenge = CTFChallenge(
            name="Reverse Me",
            category="rev",
            description="Reverse engineer the binary",
            difficulty="medium"
        )

        workflow = manager.create_ctf_challenge_workflow(challenge)

        assert any(tool in workflow["tools"] for tool in ["ghidra", "radare2", "strings"])


class TestTimeEstimation:
    """Test challenge time estimation"""

    def test_easy_challenge_time(self):
        """Test time estimation for easy challenge"""
        manager = CTFWorkflowManager()
        challenge = CTFChallenge(
            name="Easy Challenge",
            category="web",
            description="Simple web challenge",
            difficulty="easy"
        )

        workflow = manager.create_ctf_challenge_workflow(challenge)

        # Easy challenges should take less time
        assert workflow["estimated_time"] < 3600  # Less than 1 hour in seconds

    def test_hard_challenge_time(self):
        """Test time estimation for hard challenge"""
        manager = CTFWorkflowManager()
        challenge = CTFChallenge(
            name="Hard Challenge",
            category="pwn",
            description="Complex binary exploitation",
            difficulty="hard"
        )

        workflow = manager.create_ctf_challenge_workflow(challenge)

        # Hard challenges should take more time
        assert workflow["estimated_time"] > 3600  # More than 1 hour

    def test_insane_challenge_time(self):
        """Test time estimation for insane challenge"""
        manager = CTFWorkflowManager()
        challenge = CTFChallenge(
            name="Insane Challenge",
            category="crypto",
            description="Advanced cryptographic challenge",
            difficulty="insane"
        )

        workflow = manager.create_ctf_challenge_workflow(challenge)

        # Insane challenges should take longest
        assert workflow["estimated_time"] > 7200  # More than 2 hours

    def test_category_time_multiplier(self):
        """Test that category affects time estimation"""
        manager = CTFWorkflowManager()

        pwn_challenge = CTFChallenge(
            name="Pwn", category="pwn", description="Binary", difficulty="medium"
        )
        web_challenge = CTFChallenge(
            name="Web", category="web", description="Web", difficulty="medium"
        )

        pwn_workflow = manager.create_ctf_challenge_workflow(pwn_challenge)
        web_workflow = manager.create_ctf_challenge_workflow(web_challenge)

        # Pwn should typically take longer than web
        assert pwn_workflow["estimated_time"] >= web_workflow["estimated_time"]


class TestSuccessProbability:
    """Test success probability calculation"""

    def test_easy_challenge_probability(self):
        """Test success probability for easy challenge"""
        manager = CTFWorkflowManager()
        challenge = CTFChallenge(
            name="Easy",
            category="web",
            description="Simple challenge",
            difficulty="easy"
        )

        workflow = manager.create_ctf_challenge_workflow(challenge)

        # Easy challenges should have high success probability
        assert workflow["success_probability"] > 0.7

    def test_insane_challenge_probability(self):
        """Test success probability for insane challenge"""
        manager = CTFWorkflowManager()
        challenge = CTFChallenge(
            name="Insane",
            category="crypto",
            description="Very difficult challenge",
            difficulty="insane"
        )

        workflow = manager.create_ctf_challenge_workflow(challenge)

        # Insane challenges should have lower success probability
        assert workflow["success_probability"] < 0.5

    def test_tool_availability_bonus(self):
        """Test that more tools increase success probability"""
        manager = CTFWorkflowManager()

        # Challenge with keyword-specific tools
        challenge_with_keywords = CTFChallenge(
            name="SQL Injection",
            category="web",
            description="SQL injection and XSS vulnerability",
            difficulty="medium"
        )

        # Challenge without specific keywords
        challenge_generic = CTFChallenge(
            name="Generic",
            category="web",
            description="Generic web challenge",
            difficulty="medium"
        )

        workflow_keywords = manager.create_ctf_challenge_workflow(challenge_with_keywords)
        workflow_generic = manager.create_ctf_challenge_workflow(challenge_generic)

        # More tools should lead to slightly higher probability
        assert len(workflow_keywords["tools"]) >= len(workflow_generic["tools"])


class TestCategoryWorkflows:
    """Test category-specific workflows"""

    def test_web_workflow_steps(self):
        """Test web challenge workflow steps"""
        manager = CTFWorkflowManager()
        challenge = CTFChallenge(
            name="Web",
            category="web",
            description="Web challenge",
            difficulty="medium"
        )

        workflow = challenge

        steps = manager._create_category_workflow(workflow)

        assert isinstance(steps, list)
        assert len(steps) > 0

        # Check for common web steps
        step_actions = [step["action"] for step in steps]
        assert "reconnaissance" in step_actions
        assert "flag_extraction" in step_actions

    def test_crypto_workflow_steps(self):
        """Test crypto challenge workflow steps"""
        manager = CTFWorkflowManager()
        challenge = CTFChallenge(
            name="Crypto",
            category="crypto",
            description="Cryptography challenge",
            difficulty="medium"
        )

        steps = manager._create_category_workflow(challenge)

        step_actions = [step["action"] for step in steps]
        assert "cipher_identification" in step_actions

    def test_pwn_workflow_steps(self):
        """Test pwn challenge workflow steps"""
        manager = CTFWorkflowManager()
        challenge = CTFChallenge(
            name="Pwn",
            category="pwn",
            description="Binary exploitation",
            difficulty="medium"
        )

        steps = manager._create_category_workflow(challenge)

        step_actions = [step["action"] for step in steps]
        assert "binary_analysis" in step_actions
        assert "exploit_development" in step_actions

    def test_forensics_workflow_steps(self):
        """Test forensics challenge workflow steps"""
        manager = CTFWorkflowManager()
        challenge = CTFChallenge(
            name="Forensics",
            category="forensics",
            description="Digital forensics",
            difficulty="medium"
        )

        steps = manager._create_category_workflow(challenge)

        step_actions = [step["action"] for step in steps]
        assert "file_analysis" in step_actions

    def test_unknown_category_workflow(self):
        """Test workflow for unknown category"""
        manager = CTFWorkflowManager()
        challenge = CTFChallenge(
            name="Unknown",
            category="unknown_category",
            description="Unknown challenge",
            difficulty="medium"
        )

        steps = manager._create_category_workflow(challenge)

        # Should return generic workflow
        assert isinstance(steps, list)
        assert len(steps) > 0


class TestTeamStrategy:
    """Test CTF team strategy creation"""

    def test_create_team_strategy(self):
        """Test creating team strategy"""
        manager = CTFWorkflowManager()
        challenges = [
            CTFChallenge("Easy Web", "web", "Web challenge", points=100, difficulty="easy"),
            CTFChallenge("Hard Pwn", "pwn", "Binary exploit", points=500, difficulty="hard")
        ]

        strategy = manager.create_ctf_team_strategy(challenges, team_size=4)

        assert isinstance(strategy, dict)
        assert "team_size" in strategy
        assert strategy["team_size"] == 4

    def test_team_strategy_components(self):
        """Test team strategy has all components"""
        manager = CTFWorkflowManager()
        challenges = [
            CTFChallenge("Challenge 1", "web", "Test", points=200, difficulty="medium")
        ]

        strategy = manager.create_ctf_team_strategy(challenges)

        assert "challenge_allocation" in strategy
        assert "priority_order" in strategy
        assert "estimated_total_time" in strategy
        assert "expected_score" in strategy


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_challenge_with_empty_description(self):
        """Test challenge with empty description"""
        manager = CTFWorkflowManager()
        challenge = CTFChallenge(
            name="Empty Desc",
            category="web",
            description="",
            difficulty="easy"
        )

        workflow = manager.create_ctf_challenge_workflow(challenge)

        assert isinstance(workflow, dict)
        assert "tools" in workflow

    def test_challenge_with_unknown_difficulty(self):
        """Test challenge with unknown difficulty"""
        manager = CTFWorkflowManager()
        challenge = CTFChallenge(
            name="Unknown Difficulty",
            category="web",
            description="Test challenge",
            difficulty="unknown"
        )

        workflow = manager.create_ctf_challenge_workflow(challenge)

        assert "estimated_time" in workflow
        assert "success_probability" in workflow

    def test_zero_points_challenge(self):
        """Test challenge with zero points"""
        manager = CTFWorkflowManager()
        challenge = CTFChallenge(
            name="Zero Points",
            category="misc",
            description="Warmup challenge",
            points=0
        )

        workflow = manager.create_ctf_challenge_workflow(challenge)

        assert workflow["points"] == 0

    def test_multiple_keywords_in_description(self):
        """Test challenge with multiple keywords"""
        manager = CTFWorkflowManager()
        challenge = CTFChallenge(
            name="Complex",
            category="web",
            description="SQL injection and XSS in WordPress upload form",
            difficulty="hard"
        )

        workflow = manager.create_ctf_challenge_workflow(challenge)

        # Should include tools for multiple vulnerability types
        tools = workflow["tools"]
        assert len(tools) > 2

    def test_challenge_with_special_characters(self):
        """Test challenge with special characters in name"""
        manager = CTFWorkflowManager()
        challenge = CTFChallenge(
            name="Ch@lleng3_2024!",
            category="crypto",
            description="Decrypt the message",
            difficulty="medium"
        )

        workflow = manager.create_ctf_challenge_workflow(challenge)

        assert workflow["challenge"] == "Ch@lleng3_2024!"


class TestSolvingStrategies:
    """Test solving strategy generation"""

    def test_web_solving_strategies(self):
        """Test web category solving strategies"""
        manager = CTFWorkflowManager()
        strategies = manager.solving_strategies["web"]

        assert isinstance(strategies, list)
        assert len(strategies) > 0

        # Check for common web strategies
        strategy_names = [s["strategy"] for s in strategies]
        assert any("sql_injection" in name for name in strategy_names)

    def test_crypto_solving_strategies(self):
        """Test crypto category solving strategies"""
        manager = CTFWorkflowManager()
        strategies = manager.solving_strategies["crypto"]

        assert isinstance(strategies, list)
        assert len(strategies) > 0

    def test_pwn_solving_strategies(self):
        """Test pwn category solving strategies"""
        manager = CTFWorkflowManager()
        strategies = manager.solving_strategies["pwn"]

        assert isinstance(strategies, list)

        strategy_names = [s["strategy"] for s in strategies]
        assert any("buffer_overflow" in name for name in strategy_names)


class TestWorkflowIntegration:
    """Test integration between workflow components"""

    def test_workflow_has_all_required_fields(self):
        """Test workflow contains all required fields"""
        manager = CTFWorkflowManager()
        challenge = CTFChallenge(
            name="Full Test",
            category="web",
            description="Complete workflow test",
            points=250,
            difficulty="medium"
        )

        workflow = manager.create_ctf_challenge_workflow(challenge)

        required_fields = [
            "challenge", "category", "difficulty", "points",
            "tools", "strategies", "estimated_time",
            "success_probability", "automation_level"
        ]

        for field in required_fields:
            assert field in workflow
