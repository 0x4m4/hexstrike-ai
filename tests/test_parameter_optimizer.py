import pytest
from unittest.mock import Mock, patch, MagicMock
from hexstrike_server import ParameterOptimizer, ErrorType

class TestParameterOptimizer:
    @pytest.fixture
    def optimizer(self):
        return ParameterOptimizer()

    def test_apply_technology_optimizations_wordpress(self, optimizer):
        params = {"target": "example.com"}
        tech = {"cms": ["wordpress"], "web_servers": ["apache"]}
        
        # Test for gobuster
        optimized = optimizer._apply_technology_optimizations("gobuster", params, tech)
        # Check if wordpress specific paths or extensions were added
        assert "wp-content" in optimized.get("additional_paths", "")
        assert "php" in optimized.get("extensions", "")

    def test_apply_profile_optimizations_stealth_override(self, optimizer):
        # If _stealth_mode is True, it should force stealth settings even if 'normal' profile requested
        params = {"target": "example.com", "_stealth_mode": True}
        
        # Use patch.dict to safely mock optimization_profiles if needed, 
        # or just use existing ones if they have stealth profiles
        optimized = optimizer._apply_profile_optimizations("nmap", params, "normal")
        # Check if stealth timing was applied (e.g., -T1 or -T2 instead of -T4)
        assert optimized["timing"] in ["-T1", "-T2"]
