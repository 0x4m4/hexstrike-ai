"""
Graceful Degradation System for HexStrike AI

Ensures the system continues operating even with partial tool failures by
providing fallback chains and alternative methods for critical operations.
"""

import logging
import socket
import requests
from typing import Dict, Any, List, Set
from datetime import datetime

logger = logging.getLogger(__name__)


class GracefulDegradation:
    """Ensure system continues operating even with partial tool failures"""

    def __init__(self):
        self.fallback_chains = self._initialize_fallback_chains()
        self.critical_operations = self._initialize_critical_operations()

    def _initialize_fallback_chains(self) -> Dict[str, List[List[str]]]:
        """Initialize fallback tool chains for critical operations"""
        return {
            "network_discovery": [
                ["nmap", "rustscan", "masscan"],
                ["rustscan", "nmap"],
                ["ping", "telnet"]  # Basic fallback
            ],
            "web_discovery": [
                ["gobuster", "feroxbuster", "dirsearch"],
                ["feroxbuster", "ffuf"],
                ["curl", "wget"]  # Basic fallback
            ],
            "vulnerability_scanning": [
                ["nuclei", "jaeles", "nikto"],
                ["nikto", "w3af"],
                ["curl"]  # Basic manual testing
            ],
            "subdomain_enumeration": [
                ["subfinder", "amass", "assetfinder"],
                ["amass", "findomain"],
                ["dig", "nslookup"]  # Basic DNS tools
            ],
            "parameter_discovery": [
                ["arjun", "paramspider", "x8"],
                ["ffuf", "wfuzz"],
                ["manual_testing"]  # Manual parameter testing
            ]
        }

    def _initialize_critical_operations(self) -> Set[str]:
        """Initialize set of critical operations that must not fail completely"""
        return {
            "network_discovery",
            "web_discovery",
            "vulnerability_scanning",
            "subdomain_enumeration"
        }

    def create_fallback_chain(self, operation: str, failed_tools: List[str] = None) -> List[str]:
        """Create fallback tool chain for critical operations"""
        if failed_tools is None:
            failed_tools = []

        chains = self.fallback_chains.get(operation, [])

        # Find first chain that doesn't contain failed tools
        for chain in chains:
            viable_chain = [tool for tool in chain if tool not in failed_tools]
            if viable_chain:
                logger.info(f"🔄 Fallback chain for {operation}: {viable_chain}")
                return viable_chain

        # If no viable chain found, return basic fallback
        basic_fallbacks = {
            "network_discovery": ["ping"],
            "web_discovery": ["curl"],
            "vulnerability_scanning": ["curl"],
            "subdomain_enumeration": ["dig"]
        }

        fallback = basic_fallbacks.get(operation, ["manual_testing"])
        logger.warning(f"⚠️  Using basic fallback for {operation}: {fallback}")
        return fallback

    def handle_partial_failure(self, operation: str, partial_results: Dict[str, Any],
                             failed_components: List[str]) -> Dict[str, Any]:
        """Handle partial results and fill gaps with alternative methods"""

        enhanced_results = partial_results.copy()
        enhanced_results["degradation_info"] = {
            "operation": operation,
            "failed_components": failed_components,
            "partial_success": True,
            "fallback_applied": True,
            "timestamp": datetime.now().isoformat()
        }

        # Try to fill gaps based on operation type
        if operation == "network_discovery" and "open_ports" not in partial_results:
            # Try basic port check if full scan failed
            enhanced_results["open_ports"] = self._basic_port_check(partial_results.get("target"))

        elif operation == "web_discovery" and "directories" not in partial_results:
            # Try basic directory check
            enhanced_results["directories"] = self._basic_directory_check(partial_results.get("target"))

        elif operation == "vulnerability_scanning" and "vulnerabilities" not in partial_results:
            # Provide basic security headers check
            enhanced_results["vulnerabilities"] = self._basic_security_check(partial_results.get("target"))

        # Add recommendations for manual follow-up
        enhanced_results["manual_recommendations"] = self._get_manual_recommendations(
            operation, failed_components
        )

        logger.info(f"🛡️  Graceful degradation applied for {operation}")
        return enhanced_results

    def _basic_port_check(self, target: str) -> List[int]:
        """Basic port connectivity check"""
        if not target:
            return []

        common_ports = [21, 22, 23, 25, 53, 80, 110, 143, 443, 993, 995]
        open_ports = []

        for port in common_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex((target, port))
                if result == 0:
                    open_ports.append(port)
                sock.close()
            except Exception:
                continue

        return open_ports

    def _basic_directory_check(self, target: str) -> List[str]:
        """Basic directory existence check"""
        if not target:
            return []

        common_dirs = ["/admin", "/login", "/api", "/wp-admin", "/phpmyadmin", "/robots.txt"]
        found_dirs = []

        for directory in common_dirs:
            try:
                url = f"{target.rstrip('/')}{directory}"
                response = requests.head(url, timeout=5, allow_redirects=True)
                if response.status_code in [200, 301, 302, 403]:
                    found_dirs.append(directory)
            except Exception:
                continue

        return found_dirs

    def _basic_security_check(self, target: str) -> List[Dict[str, Any]]:
        """Basic security headers check"""
        if not target:
            return []

        vulnerabilities = []

        try:
            response = requests.get(target, timeout=10)
            headers = response.headers

            # Check for missing security headers
            security_headers = {
                "X-Frame-Options": "Clickjacking protection missing",
                "X-Content-Type-Options": "MIME type sniffing protection missing",
                "X-XSS-Protection": "XSS protection missing",
                "Strict-Transport-Security": "HTTPS enforcement missing",
                "Content-Security-Policy": "Content Security Policy missing"
            }

            for header, description in security_headers.items():
                if header not in headers:
                    vulnerabilities.append({
                        "type": "missing_security_header",
                        "severity": "medium",
                        "description": description,
                        "header": header
                    })

        except Exception as e:
            vulnerabilities.append({
                "type": "connection_error",
                "severity": "info",
                "description": f"Could not perform basic security check: {str(e)}"
            })

        return vulnerabilities

    def _get_manual_recommendations(self, operation: str, failed_components: List[str]) -> List[str]:
        """Get manual recommendations for failed operations"""
        recommendations = []

        base_recommendations = {
            "network_discovery": [
                "Manually test common ports using telnet or nc",
                "Check for service banners manually",
                "Use online port scanners as alternative"
            ],
            "web_discovery": [
                "Manually browse common directories",
                "Check robots.txt and sitemap.xml",
                "Use browser developer tools for endpoint discovery"
            ],
            "vulnerability_scanning": [
                "Manually test for common vulnerabilities",
                "Check security headers using browser tools",
                "Perform manual input validation testing"
            ],
            "subdomain_enumeration": [
                "Use online subdomain discovery tools",
                "Check certificate transparency logs",
                "Perform manual DNS queries"
            ]
        }

        recommendations.extend(base_recommendations.get(operation, []))

        # Add specific recommendations based on failed components
        for component in failed_components:
            if component == "nmap":
                recommendations.append("Consider using online port scanners")
            elif component == "gobuster":
                recommendations.append("Try manual directory browsing")
            elif component == "nuclei":
                recommendations.append("Perform manual vulnerability testing")

        return recommendations

    def is_critical_operation(self, operation: str) -> bool:
        """Check if operation is critical and requires fallback"""
        return operation in self.critical_operations
