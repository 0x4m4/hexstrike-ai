import pytest
from unittest.mock import patch
from hexstrike_server import ParameterOptimizer

class TestParameterOptimizer:
    @pytest.fixture
    def optimizer(self):
        return ParameterOptimizer()

    @pytest.mark.parametrize("tool, tech, expected_key, expected_val", [
        # CMS Optimizations
        ("gobuster", {"cms": ["wordpress"]}, "additional_paths", "/wp-content/"),
        ("gobuster", {"cms": ["wordpress"]}, "extensions", "php"),
        ("nuclei", {"cms": ["wordpress"]}, "tags", "wordpress"),
        ("wpscan", {"cms": ["wordpress"]}, "enumerate", "ap,at,cb,dbe"),
        
        # Web Server Optimizations
        ("gobuster", {"web_servers": ["apache"]}, "extensions", "php,html,txt,xml,conf"),
        ("nuclei", {"web_servers": ["apache"]}, "tags", "apache"),
        ("gobuster", {"web_servers": ["nginx"]}, "extensions", "php,html,txt,json,conf"),
        ("nuclei", {"web_servers": ["nginx"]}, "tags", "nginx"),
        
        # Language Optimizations
        ("gobuster", {"languages": ["php"]}, "extensions", "php,php3,php4,php5,phtml,html"),
        ("sqlmap", {"languages": ["php"]}, "dbms", "mysql"),
        ("gobuster", {"languages": ["dotnet"]}, "extensions", "aspx,asp,html,txt"),
        ("sqlmap", {"languages": ["dotnet"]}, "dbms", "mssql"),
        
        # Security/WAF Optimizations
        ("gobuster", {"security": ["cloudflare"]}, "_stealth_mode", True),
        ("gobuster", {"security": ["cloudflare"]}, "threads", 5),
        ("sqlmap", {"security": ["incapsula"]}, "delay", 2),
        ("sqlmap", {"security": ["sucuri"]}, "randomize", True),
    ])
    def test_apply_technology_optimizations_matrix(self, optimizer, tool, tech, expected_key, expected_val):
        params = {"target": "example.com"}
        optimized = optimizer._apply_technology_optimizations(tool, params, tech)
        
        actual_val = optimized.get(expected_key)
        if isinstance(expected_val, bool):
            assert actual_val is expected_val
        elif isinstance(expected_val, int):
            assert actual_val == expected_val
        else:
            assert expected_val in str(actual_val)

    def test_apply_profile_optimizations_stealth_override(self, optimizer):
        """Test that stealth mode forces stealth settings even if another profile is requested."""
        mock_profiles = {
            "nmap": {
                "stealth": {
                    "timing": "-T1",
                    "custom_flag": "stealth-on"
                },
                "normal": {
                    "timing": "-T4",
                    "custom_flag": "normal-on"
                }
            }
        }
        
        with patch.dict(optimizer.optimization_profiles, mock_profiles, clear=True):
            # If _stealth_mode is True, it should force stealth settings even if 'normal' profile requested
            params = {"target": "example.com", "_stealth_mode": True}
            
            optimized = optimizer._apply_profile_optimizations("nmap", params, "normal")
            
            # Check if stealth timing was applied instead of normal
            assert optimized["timing"] == "-T1"
            assert optimized["custom_flag"] == "stealth-on"

    def test_apply_profile_optimizations_normal(self, optimizer):
        """Test standard profile application without stealth override."""
        mock_profiles = {
            "nmap": {
                "stealth": {"timing": "-T1"},
                "normal": {"timing": "-T4"}
            }
        }
        
        with patch.dict(optimizer.optimization_profiles, mock_profiles, clear=True):
            params = {"target": "example.com", "_stealth_mode": False}
            optimized = optimizer._apply_profile_optimizations("nmap", params, "normal")
            assert optimized["timing"] == "-T4"
