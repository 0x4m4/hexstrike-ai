#!/usr/bin/env python3
"""
HexStrike AI MCP Client v6.0 - Advanced Cybersecurity Automation Platform
Part 2 of 6: Security Tools and Intelligence Endpoints

This part focuses on comprehensive wrappers for all security tools and intelligence
endpoints provided by the HexStrike server, including network scanning, web application
testing, intelligence analysis, and advanced AI-powered decision making.

Author: HexStrike AI Team
Version: 6.0.0
License: MIT
"""

import json
import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple, Literal
import ipaddress
import urllib.parse
from dataclasses import dataclass, field
from enum import Enum, auto
import re
import base64
import hashlib

# Configure logger for this module
logger = logging.getLogger("HexStrike-MCP-Tools")

class ScanType(Enum):
    """Types of security scans available"""
    NETWORK_DISCOVERY = "network_discovery"
    PORT_SCAN = "port_scan"
    VULNERABILITY_SCAN = "vulnerability_scan"
    WEB_SCAN = "web_scan"
    SERVICE_ENUMERATION = "service_enumeration"
    OS_FINGERPRINT = "os_fingerprint"
    SSL_SCAN = "ssl_scan"
    DNS_ENUMERATION = "dns_enumeration"
    SUBDOMAIN_ENUMERATION = "subdomain_enumeration"
    DIRECTORY_BRUTEFORCE = "directory_bruteforce"
    CREDENTIAL_BRUTEFORCE = "credential_bruteforce"

class ToolCategory(Enum):
    """Categories of security tools"""
    NETWORK = "network"
    WEB_APPLICATION = "web_application"
    VULNERABILITY_SCANNER = "vulnerability_scanner"
    EXPLOITATION = "exploitation"
    POST_EXPLOITATION = "post_exploitation"
    FORENSICS = "forensics"
    REVERSE_ENGINEERING = "reverse_engineering"
    CRYPTOGRAPHY = "cryptography"
    WIRELESS = "wireless"
    CLOUD = "cloud"
    OSINT = "osint"
    BINARY_ANALYSIS = "binary_analysis"

@dataclass
class TargetInfo:
    """Comprehensive target information structure"""
    hostname: Optional[str] = None
    ip_address: Optional[str] = None
    ip_range: Optional[str] = None
    ports: Optional[List[int]] = None
    services: Optional[List[str]] = None
    os_family: Optional[str] = None
    os_version: Optional[str] = None
    domain: Optional[str] = None
    subdomain: Optional[str] = None
    url: Optional[str] = None
    technology_stack: Optional[List[str]] = None
    vulnerabilities: Optional[List[str]] = None
    credentials: Optional[Dict[str, str]] = None
    custom_attributes: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API requests"""
        return {k: v for k, v in self.__dict__.items() if v is not None}

@dataclass
class ScanConfiguration:
    """Advanced scan configuration options"""
    scan_type: ScanType
    target: TargetInfo
    timing_template: Optional[str] = "normal"  # insane, aggressive, normal, polite, sneaky, paranoid
    stealth_mode: bool = False
    custom_user_agent: Optional[str] = None
    proxy_settings: Optional[Dict[str, str]] = None
    authentication: Optional[Dict[str, str]] = None
    custom_headers: Optional[Dict[str, str]] = None
    scan_depth: int = 1
    thread_count: int = 10
    timeout: int = 300
    output_format: str = "json"
    save_results: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API requests"""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, Enum):
                result[key] = value.value
            elif isinstance(value, TargetInfo):
                result[key] = value.to_dict()
            elif value is not None:
                result[key] = value
        return result

class SecurityToolsClient:
    """
    Advanced Security Tools Client Extension for HexStrike MCP Client
    
    This class extends the base HexStrike MCP Client with comprehensive
    wrappers for all security tools and intelligence capabilities.
    """
    
    def __init__(self, base_client):
        """
        Initialize Security Tools Client
        
        Args:
            base_client: Instance of HexStrikeMCPClient
        """
        self.client = base_client
        self.logger = logging.getLogger(f"SecurityTools-{base_client.session_id[:8]}")
        
        # Tool-specific configurations
        self.nmap_profiles = self._load_nmap_profiles()
        self.wordlists = self._load_wordlists()
        self.user_agents = self._load_user_agents()
        
        self.logger.info("Security Tools Client initialized")
    
    def _load_nmap_profiles(self) -> Dict[str, Dict[str, str]]:
        """Load predefined Nmap scan profiles"""
        return {
            "fast": {
                "description": "Fast scan for quick enumeration",
                "options": "-T4 -F --version-detection"
            },
            "comprehensive": {
                "description": "Comprehensive scan with all techniques",
                "options": "-T4 -A -sS -sU -sV -O --script=default,vuln"
            },
            "stealth": {
                "description": "Stealth scan to avoid detection",
                "options": "-T1 -sS -f --randomize-hosts --spoof-mac 0"
            },
            "vulnerability": {
                "description": "Focus on vulnerability detection",
                "options": "-T4 -sV --script=vuln,exploit,malware"
            },
            "service_enum": {
                "description": "Deep service enumeration",
                "options": "-T4 -sV -sC --version-all --script=banner,version"
            }
        }
    
    def _load_wordlists(self) -> Dict[str, str]:
        """Load available wordlists for various attacks"""
        return {
            "directories": "/usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt",
            "files": "/usr/share/wordlists/dirbuster/directory-list-2.3-small.txt", 
            "subdomains": "/usr/share/wordlists/amass/subdomains.txt",
            "passwords": "/usr/share/wordlists/rockyou.txt",
            "usernames": "/usr/share/wordlists/metasploit/unix_users.txt",
            "web_content": "/usr/share/wordlists/dirb/common.txt"
        }
    
    def _load_user_agents(self) -> List[str]:
        """Load common user agents for web scanning"""
        return [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101"
        ]
    
    # =============================================================================
    # NETWORK RECONNAISSANCE AND SCANNING
    # =============================================================================
    
    async def nmap_scan(self,
                       target: Union[str, List[str]],
                       scan_type: str = "comprehensive",
                       custom_options: Optional[str] = None,
                       output_formats: Optional[List[str]] = None,
                       save_results: bool = True) -> Dict[str, Any]:
        """
        Perform advanced Nmap network scanning
        
        This method provides comprehensive network reconnaissance using Nmap with
        intelligent profile selection, custom options, and multiple output formats.
        
        Args:
            target: Target IP, hostname, or CIDR range (or list of targets)
            scan_type: Predefined scan profile (fast, comprehensive, stealth, vulnerability, service_enum)
            custom_options: Custom Nmap command line options
            output_formats: Output formats to generate (xml, json, nmap, gnmap)
            save_results: Whether to save results to files
        
        Returns:
            Dict containing:
            - scan_id: Unique identifier for the scan
            - targets: List of targets scanned
            - scan_profile: Profile used for scanning
            - results: Detailed scan results
            - hosts: Information about discovered hosts
            - services: Information about discovered services
            - vulnerabilities: Potential vulnerabilities found
            - scan_statistics: Performance and timing statistics
            - output_files: Paths to generated output files
        """
        try:
            # Handle multiple targets
            if isinstance(target, str):
                targets = [target]
            else:
                targets = target
            
            self.logger.info(f"Starting Nmap scan of {len(targets)} targets with profile: {scan_type}")
            
            # Validate targets
            validated_targets = []
            for tgt in targets:
                if self._validate_target(tgt):
                    validated_targets.append(tgt)
                else:
                    self.logger.warning(f"Invalid target format: {tgt}")
            
            if not validated_targets:
                raise ValueError("No valid targets provided")
            
            # Prepare scan configuration
            scan_options = custom_options or self.nmap_profiles.get(scan_type, {}).get("options", "-T4 -sV")
            
            scan_data = {
                "tool": "nmap",
                "targets": validated_targets,
                "options": scan_options,
                "scan_profile": scan_type,
                "output_formats": output_formats or ["json", "xml"],
                "save_results": save_results,
                "timestamp": datetime.now().isoformat(),
                "client_session": self.client.session_id
            }
            
            # Execute scan via server
            result = self.client._make_request('POST', '/api/tools/nmap', data=scan_data)
            
            scan_id = result.get('scan_id')
            host_count = len(result.get('hosts', []))
            service_count = sum(len(host.get('services', [])) for host in result.get('hosts', []))
            
            self.logger.info(f"Nmap scan completed - ID: {scan_id}")
            self.logger.info(f"Discovered {host_count} hosts with {service_count} services")
            
            # Process and enhance results
            enhanced_result = self._enhance_nmap_results(result)
            
            return enhanced_result
            
        except Exception as e:
            self.logger.error(f"Nmap scan failed: {e}")
            raise
    
    def _validate_target(self, target: str) -> bool:
        """Validate target format (IP, hostname, or CIDR)"""
        try:
            # Try IP address
            ipaddress.ip_address(target)
            return True
        except ValueError:
            try:
                # Try CIDR network
                ipaddress.ip_network(target, strict=False)
                return True
            except ValueError:
                # Try hostname
                if re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$', target):
                    return True
        return False
    
    def _enhance_nmap_results(self, raw_results: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance Nmap results with additional intelligence"""
        enhanced = raw_results.copy()
        
        # Add risk analysis
        enhanced['risk_analysis'] = self._analyze_nmap_risks(raw_results)
        
        # Add service categorization
        enhanced['service_categories'] = self._categorize_services(raw_results)
        
        # Add attack surface analysis
        enhanced['attack_surface'] = self._analyze_attack_surface(raw_results)
        
        return enhanced
    
    def _analyze_nmap_risks(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze security risks from Nmap results"""
        risks = {
            "high_risk_services": [],
            "unencrypted_services": [],
            "default_configurations": [],
            "outdated_versions": [],
            "risk_score": 0
        }
        
        high_risk_ports = [21, 23, 53, 135, 139, 445, 1433, 3389]
        
        for host in results.get('hosts', []):
            for service in host.get('services', []):
                port = service.get('port')
                
                if port in high_risk_ports:
                    risks['high_risk_services'].append({
                        'host': host.get('ip'),
                        'port': port,
                        'service': service.get('service'),
                        'reason': 'Known high-risk service'
                    })
        
        # Calculate risk score
        risks['risk_score'] = len(risks['high_risk_services']) * 10
        
        return risks
    
    def _categorize_services(self, results: Dict[str, Any]) -> Dict[str, List[str]]:
        """Categorize discovered services"""
        categories = {
            "web_services": [],
            "database_services": [],
            "file_services": [],
            "remote_access": [],
            "network_services": [],
            "unknown_services": []
        }
        
        service_mapping = {
            "http": "web_services",
            "https": "web_services",
            "mysql": "database_services",
            "postgresql": "database_services",
            "ftp": "file_services",
            "ssh": "remote_access",
            "rdp": "remote_access",
            "dns": "network_services"
        }
        
        for host in results.get('hosts', []):
            for service in host.get('services', []):
                service_name = service.get('service', '').lower()
                category = service_mapping.get(service_name, "unknown_services")
                categories[category].append(f"{host.get('ip')}:{service.get('port')}")
        
        return categories
    
    def _analyze_attack_surface(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze attack surface from scan results"""
        attack_surface = {
            "total_hosts": len(results.get('hosts', [])),
            "total_services": 0,
            "open_ports": [],
            "web_applications": [],
            "databases": [],
            "remote_services": []
        }
        
        for host in results.get('hosts', []):
            services = host.get('services', [])
            attack_surface['total_services'] += len(services)
            
            for service in services:
                port_info = f"{host.get('ip')}:{service.get('port')}"
                attack_surface['open_ports'].append(port_info)
                
                service_name = service.get('service', '').lower()
                if service_name in ['http', 'https']:
                    attack_surface['web_applications'].append(port_info)
                elif service_name in ['mysql', 'postgresql', 'mssql']:
                    attack_surface['databases'].append(port_info)
                elif service_name in ['ssh', 'rdp', 'telnet']:
                    attack_surface['remote_services'].append(port_info)
        
        return attack_surface
    
    async def masscan_scan(self,
                          target_range: str,
                          ports: Union[str, List[int]],
                          rate: int = 1000,
                          interface: Optional[str] = None,
                          exclude_targets: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Perform high-speed port scanning with Masscan
        
        Args:
            target_range: IP range to scan (CIDR notation)
            ports: Ports to scan (string like "1-1000" or list of integers)
            rate: Packets per second rate
            interface: Network interface to use
            exclude_targets: List of targets to exclude
        
        Returns:
            Dict with Masscan results
        """
        try:
            self.logger.info(f"Starting Masscan of {target_range} on ports {ports}")
            
            # Format ports
            if isinstance(ports, list):
                port_string = ",".join(map(str, ports))
            else:
                port_string = str(ports)
            
            scan_data = {
                "tool": "masscan",
                "target_range": target_range,
                "ports": port_string,
                "rate": rate,
                "interface": interface,
                "exclude_targets": exclude_targets or [],
                "output_format": "json"
            }
            
            result = self.client._make_request('POST', '/api/tools/masscan', data=scan_data)
            
            discovered_hosts = len(result.get('hosts', []))
            self.logger.info(f"Masscan completed - Discovered {discovered_hosts} hosts")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Masscan failed: {e}")
            raise
    
    async def zmap_scan(self,
                       target_range: str,
                       port: int,
                       probe_module: str = "tcp_synscan",
                       rate: int = 10000,
                       interface: Optional[str] = None) -> Dict[str, Any]:
        """
        Perform Internet-wide network scanning with ZMap
        
        Args:
            target_range: IP range to scan
            port: Single port to scan
            probe_module: ZMap probe module to use
            rate: Scanning rate in packets per second
            interface: Network interface to use
        
        Returns:
            Dict with ZMap scanning results
        """
        try:
            self.logger.info(f"Starting ZMap scan of {target_range}:{port}")
            
            scan_data = {
                "tool": "zmap",
                "target_range": target_range,
                "port": port,
                "probe_module": probe_module,
                "rate": rate,
                "interface": interface
            }
            
            result = self.client._make_request('POST', '/api/tools/zmap', data=scan_data)
            
            return result
            
        except Exception as e:
            self.logger.error(f"ZMap scan failed: {e}")
            raise
    
    # =============================================================================
    # WEB APPLICATION SECURITY TESTING
    # =============================================================================
    
    async def nikto_scan(self,
                        target_url: str,
                        scan_tuning: Optional[str] = None,
                        plugins: Optional[List[str]] = None,
                        authentication: Optional[Dict[str, str]] = None,
                        proxy_settings: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Perform comprehensive web vulnerability scanning with Nikto
        
        Args:
            target_url: Target web application URL
            scan_tuning: Tuning options for scan behavior
            plugins: List of Nikto plugins to use
            authentication: Authentication credentials
            proxy_settings: Proxy configuration
        
        Returns:
            Dict containing comprehensive web vulnerability results
        """
        try:
            self.logger.info(f"Starting Nikto scan of {target_url}")
            
            scan_data = {
                "tool": "nikto",
                "target_url": target_url,
                "scan_tuning": scan_tuning,
                "plugins": plugins or [],
                "authentication": authentication,
                "proxy_settings": proxy_settings,
                "output_format": "json"
            }
            
            result = self.client._make_request('POST', '/api/tools/nikto', data=scan_data)
            
            vuln_count = len(result.get('vulnerabilities', []))
            self.logger.info(f"Nikto scan completed - Found {vuln_count} potential issues")
            
            # Enhance results with risk assessment
            enhanced_result = self._enhance_nikto_results(result)
            
            return enhanced_result
            
        except Exception as e:
            self.logger.error(f"Nikto scan failed: {e}")
            raise
    
    def _enhance_nikto_results(self, raw_results: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance Nikto results with additional analysis"""
        enhanced = raw_results.copy()
        
        # Categorize vulnerabilities by severity
        vulnerabilities = raw_results.get('vulnerabilities', [])
        enhanced['vulnerability_analysis'] = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": [],
            "info": []
        }
        
        # Risk keywords for categorization
        critical_keywords = ['sql injection', 'command injection', 'remote code execution']
        high_keywords = ['xss', 'csrf', 'authentication bypass']
        medium_keywords = ['information disclosure', 'directory traversal']
        
        for vuln in vulnerabilities:
            description = vuln.get('description', '').lower()
            
            if any(keyword in description for keyword in critical_keywords):
                enhanced['vulnerability_analysis']['critical'].append(vuln)
            elif any(keyword in description for keyword in high_keywords):
                enhanced['vulnerability_analysis']['high'].append(vuln)
            elif any(keyword in description for keyword in medium_keywords):
                enhanced['vulnerability_analysis']['medium'].append(vuln)
            else:
                enhanced['vulnerability_analysis']['low'].append(vuln)
        
        return enhanced
    
    async def gobuster_directory_scan(self,
                                    target_url: str,
                                    wordlist: str = "directories",
                                    extensions: Optional[List[str]] = None,
                                    threads: int = 10,
                                    timeout: int = 10,
                                    follow_redirects: bool = True,
                                    custom_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Perform directory and file discovery with Gobuster
        
        Args:
            target_url: Target web application URL
            wordlist: Wordlist to use for brute forcing
            extensions: File extensions to append
            threads: Number of concurrent threads
            timeout: Request timeout in seconds
            follow_redirects: Whether to follow HTTP redirects
            custom_headers: Custom HTTP headers
        
        Returns:
            Dict with discovered directories and files
        """
        try:
            self.logger.info(f"Starting Gobuster directory scan of {target_url}")
            
            # Get wordlist path
            wordlist_path = self.wordlists.get(wordlist, wordlist)
            
            scan_data = {
                "tool": "gobuster",
                "mode": "dir",
                "target_url": target_url,
                "wordlist": wordlist_path,
                "extensions": extensions or ["php", "html", "js", "txt"],
                "threads": threads,
                "timeout": timeout,
                "follow_redirects": follow_redirects,
                "custom_headers": custom_headers or {}
            }
            
            result = self.client._make_request('POST', '/api/tools/gobuster', data=scan_data)
            
            found_count = len(result.get('discovered_paths', []))
            self.logger.info(f"Gobuster completed - Found {found_count} paths")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Gobuster directory scan failed: {e}")
            raise
    
    async def dirbuster_scan(self,
                            target_url: str,
                            wordlist: str = "directories",
                            threads: int = 10,
                            file_extensions: Optional[List[str]] = None,
                            recursive_scan: bool = False,
                            max_depth: int = 3) -> Dict[str, Any]:
        """
        Perform web directory brute forcing with DirBuster
        
        Args:
            target_url: Target URL to scan
            wordlist: Wordlist to use
            threads: Number of threads
            file_extensions: Extensions to check
            recursive_scan: Whether to scan recursively
            max_depth: Maximum recursion depth
        
        Returns:
            Dict with discovered directories and files
        """
        try:
            self.logger.info(f"Starting DirBuster scan of {target_url}")
            
            wordlist_path = self.wordlists.get(wordlist, wordlist)
            
            scan_data = {
                "tool": "dirbuster",
                "target_url": target_url,
                "wordlist": wordlist_path,
                "threads": threads,
                "extensions": file_extensions or ["php", "html", "asp", "jsp"],
                "recursive": recursive_scan,
                "max_depth": max_depth
            }
            
            result = self.client._make_request('POST', '/api/tools/dirbuster', data=scan_data)
            
            return result
            
        except Exception as e:
            self.logger.error(f"DirBuster scan failed: {e}")
            raise
    
    async def wpscan(self,
                    target_url: str,
                    enumerate_options: Optional[List[str]] = None,
                    api_token: Optional[str] = None,
                    force_check: bool = False,
                    follow_redirects: bool = True) -> Dict[str, Any]:
        """
        Perform WordPress security scanning with WPScan
        
        Args:
            target_url: WordPress site URL
            enumerate_options: What to enumerate (plugins, themes, users, etc.)
            api_token: WPVulnDB API token for vulnerability data
            force_check: Force checking even if not WordPress
            follow_redirects: Follow HTTP redirects
        
        Returns:
            Dict with WordPress security analysis
        """
        try:
            self.logger.info(f"Starting WPScan of {target_url}")
            
            scan_data = {
                "tool": "wpscan",
                "target_url": target_url,
                "enumerate": enumerate_options or ["p", "t", "u"],  # plugins, themes, users
                "api_token": api_token,
                "force": force_check,
                "follow_redirects": follow_redirects,
                "format": "json"
            }
            
            result = self.client._make_request('POST', '/api/tools/wpscan', data=scan_data)
            
            vuln_count = len(result.get('vulnerabilities', []))
            self.logger.info(f"WPScan completed - Found {vuln_count} vulnerabilities")
            
            return result
            
        except Exception as e:
            self.logger.error(f"WPScan failed: {e}")
            raise
    
    async def sqlmap_scan(self,
                         target_url: str,
                         injection_points: Optional[List[str]] = None,
                         database_management: bool = False,
                         risk_level: int = 1,
                         level: int = 1,
                         custom_headers: Optional[Dict[str, str]] = None,
                         authentication: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Perform SQL injection testing with SQLMap
        
        Args:
            target_url: Target URL to test
            injection_points: Specific parameters to test
            database_management: Whether to perform database management
            risk_level: Risk level (1-3)
            level: Test level (1-5)
            custom_headers: Custom HTTP headers
            authentication: Authentication credentials
        
        Returns:
            Dict with SQL injection test results
        """
        try:
            self.logger.info(f"Starting SQLMap scan of {target_url}")
            
            scan_data = {
                "tool": "sqlmap",
                "target_url": target_url,
                "injection_points": injection_points,
                "database_management": database_management,
                "risk": risk_level,
                "level": level,
                "headers": custom_headers or {},
                "auth": authentication,
                "batch": True,  # Non-interactive mode
                "format": "json"
            }
            
            result = self.client._make_request('POST', '/api/tools/sqlmap', data=scan_data)
            
            injectable_params = len(result.get('injectable_parameters', []))
            self.logger.info(f"SQLMap completed - Found {injectable_params} injectable parameters")
            
            return result
            
        except Exception as e:
            self.logger.error(f"SQLMap scan failed: {e}")
            raise
    
    # =============================================================================
    # SUBDOMAIN AND DNS ENUMERATION
    # =============================================================================
    
    async def subdomain_enumeration(self,
                                  domain: str,
                                  tools: Optional[List[str]] = None,
                                  passive_only: bool = False,
                                  dns_servers: Optional[List[str]] = None,
                                  wordlist: Optional[str] = None) -> Dict[str, Any]:
        """
        Perform comprehensive subdomain enumeration
        
        Args:
            domain: Target domain to enumerate
            tools: List of tools to use (subfinder, amass, assetfinder, etc.)
            passive_only: Only use passive enumeration techniques
            dns_servers: Custom DNS servers to use
            wordlist: Wordlist for brute force enumeration
        
        Returns:
            Dict with discovered subdomains and analysis
        """
        try:
            self.logger.info(f"Starting subdomain enumeration for {domain}")
            
            scan_data = {
                "operation": "subdomain_enum",
                "domain": domain,
                "tools": tools or ["subfinder", "amass", "assetfinder"],
                "passive_only": passive_only,
                "dns_servers": dns_servers,
                "wordlist": wordlist,
                "resolve_subdomains": True,
                "check_alive": True
            }
            
            result = self.client._make_request('POST', '/api/tools/subdomain-enum', data=scan_data)
            
            subdomain_count = len(result.get('subdomains', []))
            alive_count = len(result.get('alive_subdomains', []))
            
            self.logger.info(f"Subdomain enumeration completed - Found {subdomain_count} subdomains ({alive_count} alive)")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Subdomain enumeration failed: {e}")
            raise
    
    async def amass_enumeration(self,
                               domain: str,
                               config_file: Optional[str] = None,
                               data_sources: Optional[List[str]] = None,
                               brute_force: bool = False,
                               passive_mode: bool = False) -> Dict[str, Any]:
        """
        Perform comprehensive asset discovery with Amass
        
        Args:
            domain: Target domain
            config_file: Amass configuration file path
            data_sources: Specific data sources to use
            brute_force: Enable brute force enumeration
            passive_mode: Use only passive techniques
        
        Returns:
            Dict with Amass enumeration results
        """
        try:
            self.logger.info(f"Starting Amass enumeration for {domain}")
            
            scan_data = {
                "tool": "amass",
                "domain": domain,
                "config": config_file,
                "sources": data_sources,
                "brute": brute_force,
                "passive": passive_mode,
                "output_format": "json"
            }
            
            result = self.client._make_request('POST', '/api/tools/amass', data=scan_data)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Amass enumeration failed: {e}")
            raise
    
    async def dns_enumeration(self,
                             domain: str,
                             record_types: Optional[List[str]] = None,
                             dns_servers: Optional[List[str]] = None,
                             zone_transfer: bool = True,
                             reverse_dns: bool = False) -> Dict[str, Any]:
        """
        Perform comprehensive DNS enumeration
        
        Args:
            domain: Target domain
            record_types: DNS record types to query
            dns_servers: DNS servers to use for queries
            zone_transfer: Attempt zone transfer
            reverse_dns: Perform reverse DNS lookups
        
        Returns:
            Dict with DNS enumeration results
        """
        try:
            self.logger.info(f"Starting DNS enumeration for {domain}")
            
            scan_data = {
                "tool": "dns_enum",
                "domain": domain,
                "record_types": record_types or ["A", "AAAA", "CNAME", "MX", "NS", "TXT", "SOA"],
                "dns_servers": dns_servers or ["8.8.8.8", "8.8.4.4"],
                "zone_transfer": zone_transfer,
                "reverse_dns": reverse_dns
            }
            
            result = self.client._make_request('POST', '/api/tools/dns-enum', data=scan_data)
            
            return result
            
        except Exception as e:
            self.logger.error(f"DNS enumeration failed: {e}")
            raise
    
    # =============================================================================
    # VULNERABILITY SCANNING AND ANALYSIS
    # =============================================================================
    
    async def nessus_scan(self,
                         targets: List[str],
                         policy_template: str = "basic_network_scan",
                         credentials: Optional[Dict[str, Any]] = None,
                         scan_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Perform vulnerability scanning with Nessus
        
        Args:
            targets: List of target hosts/networks
            policy_template: Nessus policy template to use
            credentials: Authentication credentials for authenticated scanning
            scan_name: Custom name for the scan
        
        Returns:
            Dict with Nessus scan results
        """
        try:
            self.logger.info(f"Starting Nessus scan of {len(targets)} targets")
            
            scan_data = {
                "tool": "nessus",
                "targets": targets,
                "policy": policy_template,
                "credentials": credentials,
                "scan_name": scan_name or f"HexStrike_Scan_{int(time.time())}",
                "launch_now": True
            }
            
            result = self.client._make_request('POST', '/api/tools/nessus', data=scan_data)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Nessus scan failed: {e}")
            raise
    
    async def openvas_scan(self,
                          targets: List[str],
                          scan_config: str = "Full and fast",
                          port_range: Optional[str] = None,
                          alive_test: str = "ICMP Ping") -> Dict[str, Any]:
        """
        Perform vulnerability scanning with OpenVAS
        
        Args:
            targets: List of targets to scan
            scan_config: OpenVAS scan configuration
            port_range: Port range to scan
            alive_test: Method for host alive detection
        
        Returns:
            Dict with OpenVAS scan results
        """
        try:
            self.logger.info(f"Starting OpenVAS scan of {len(targets)} targets")
            
            scan_data = {
                "tool": "openvas",
                "targets": targets,
                "config": scan_config,
                "port_range": port_range,
                "alive_test": alive_test
            }
            
            result = self.client._make_request('POST', '/api/tools/openvas', data=scan_data)
            
            return result
            
        except Exception as e:
            self.logger.error(f"OpenVAS scan failed: {e}")
            raise
    
    async def nuclei_scan(self,
                         targets: List[str],
                         templates: Optional[List[str]] = None,
                         severity_filter: Optional[List[str]] = None,
                         concurrency: int = 25,
                         rate_limit: int = 150,
                         custom_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Perform fast vulnerability scanning with Nuclei
        
        Args:
            targets: List of target URLs/IPs
            templates: Nuclei templates to use
            severity_filter: Filter by severity (critical, high, medium, low, info)
            concurrency: Number of concurrent requests
            rate_limit: Rate limit for requests per second
            custom_headers: Custom HTTP headers
        
        Returns:
            Dict with Nuclei scan results
        """
        try:
            self.logger.info(f"Starting Nuclei scan of {len(targets)} targets")
            
            scan_data = {
                "tool": "nuclei",
                "targets": targets,
                "templates": templates,
                "severity": severity_filter,
                "concurrency": concurrency,
                "rate_limit": rate_limit,
                "headers": custom_headers or {},
                "json_output": True
            }
            
            result = self.client._make_request('POST', '/api/tools/nuclei', data=scan_data)
            
            findings_count = len(result.get('findings', []))
            self.logger.info(f"Nuclei scan completed - Found {findings_count} issues")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Nuclei scan failed: {e}")
            raise
    
    # =============================================================================
    # INTELLIGENCE AND ANALYSIS ENDPOINTS
    # =============================================================================
    
    async def analyze_target_intelligence(self,
                                        target: str,
                                        analysis_depth: str = "comprehensive",
                                        include_passive_recon: bool = True,
                                        include_threat_intel: bool = True,
                                        include_vulnerability_intel: bool = True) -> Dict[str, Any]:
        """
        Perform comprehensive target intelligence analysis
        
        This method leverages the Intelligent Decision Engine to perform multi-layered
        analysis of a target, combining passive reconnaissance, threat intelligence,
        vulnerability intelligence, and behavioral analysis.
        
        Args:
            target: Target IP, domain, or URL to analyze
            analysis_depth: Depth of analysis (surface, standard, comprehensive, deep)
            include_passive_recon: Include passive reconnaissance data
            include_threat_intel: Include threat intelligence lookups
            include_vulnerability_intel: Include vulnerability intelligence
        
        Returns:
            Dict containing:
            - target_profile: Comprehensive target profile
            - technology_stack: Detected technologies and versions
            - threat_indicators: Threat intelligence findings
            - vulnerability_assessment: Vulnerability intelligence
            - risk_analysis: AI-powered risk assessment
            - attack_vectors: Potential attack vectors
            - recommendations: AI-generated recommendations
        """
        try:
            self.logger.info(f"Starting intelligence analysis for target: {target}")
            
            analysis_data = {
                "target": target,
                "analysis_depth": analysis_depth,
                "options": {
                    "passive_recon": include_passive_recon,
                    "threat_intel": include_threat_intel,
                    "vulnerability_intel": include_vulnerability_intel,
                    "behavioral_analysis": True,
                    "technology_detection": True,
                    "risk_assessment": True
                },
                "ai_enhancement": True
            }
            
            result = self.client._make_request('POST', '/api/intelligence/analyze-target', data=analysis_data)
            
            risk_score = result.get('risk_analysis', {}).get('overall_risk_score', 0)
            threat_count = len(result.get('threat_indicators', []))
            vuln_count = len(result.get('vulnerability_assessment', {}).get('vulnerabilities', []))
            
            self.logger.info(f"Intelligence analysis completed - Risk Score: {risk_score}/100")
            self.logger.info(f"Found {threat_count} threat indicators and {vuln_count} vulnerabilities")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Intelligence analysis failed: {e}")
            raise
    
    async def technology_detection(self,
                                 target_url: str,
                                 detection_methods: Optional[List[str]] = None,
                                 deep_analysis: bool = True) -> Dict[str, Any]:
        """
        Detect technologies used by target web application
        
        Args:
            target_url: Target web application URL
            detection_methods: Methods to use for detection
            deep_analysis: Perform deep technology analysis
        
        Returns:
            Dict with detected technologies and versions
        """
        try:
            self.logger.info(f"Starting technology detection for {target_url}")
            
            detection_data = {
                "target_url": target_url,
                "methods": detection_methods or ["headers", "cookies", "html", "css", "javascript", "dns"],
                "deep_analysis": deep_analysis,
                "version_detection": True
            }
            
            result = self.client._make_request('POST', '/api/intelligence/technology-detection', data=detection_data)
            
            tech_count = len(result.get('technologies', []))
            self.logger.info(f"Technology detection completed - Found {tech_count} technologies")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Technology detection failed: {e}")
            raise
    
    async def vulnerability_correlation(self,
                                      scan_results: List[Dict[str, Any]],
                                      correlation_algorithms: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Correlate vulnerabilities across multiple scan results
        
        Args:
            scan_results: List of scan results to correlate
            correlation_algorithms: Correlation algorithms to use
        
        Returns:
            Dict with correlated vulnerability analysis
        """
        try:
            self.logger.info(f"Starting vulnerability correlation for {len(scan_results)} scan results")
            
            correlation_data = {
                "scan_results": scan_results,
                "algorithms": correlation_algorithms or ["similarity", "chaining", "clustering"],
                "include_false_positives_analysis": True,
                "generate_attack_chains": True
            }
            
            result = self.client._make_request('POST', '/api/intelligence/vulnerability-correlation', data=correlation_data)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Vulnerability correlation failed: {e}")
            raise
    
    async def threat_intelligence_lookup(self,
                                       indicators: List[str],
                                       indicator_types: Optional[List[str]] = None,
                                       sources: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Perform threat intelligence lookup for indicators
        
        Args:
            indicators: List of indicators to lookup (IPs, domains, hashes, etc.)
            indicator_types: Types of indicators (ip, domain, url, hash, email)
            sources: Threat intelligence sources to query
        
        Returns:
            Dict with threat intelligence findings
        """
        try:
            self.logger.info(f"Starting threat intelligence lookup for {len(indicators)} indicators")
            
            lookup_data = {
                "indicators": indicators,
                "types": indicator_types,
                "sources": sources or ["virustotal", "abuseipdb", "otx", "misp"],
                "include_context": True,
                "malware_analysis": True
            }
            
            result = self.client._make_request('POST', '/api/intelligence/threat-lookup', data=lookup_data)
            
            malicious_count = len(result.get('malicious_indicators', []))
            self.logger.info(f"Threat intelligence lookup completed - Found {malicious_count} malicious indicators")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Threat intelligence lookup failed: {e}")
            raise
    
    async def behavioral_analysis(self,
                                target: str,
                                analysis_duration: int = 3600,
                                monitoring_methods: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Perform behavioral analysis of target system
        
        Args:
            target: Target to analyze
            analysis_duration: Duration of analysis in seconds
            monitoring_methods: Methods to use for behavioral monitoring
        
        Returns:
            Dict with behavioral analysis results
        """
        try:
            self.logger.info(f"Starting behavioral analysis for {target}")
            
            analysis_data = {
                "target": target,
                "duration": analysis_duration,
                "methods": monitoring_methods or ["network", "process", "file", "registry"],
                "baseline_establishment": True,
                "anomaly_detection": True
            }
            
            result = self.client._make_request('POST', '/api/intelligence/behavioral-analysis', data=analysis_data)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Behavioral analysis failed: {e}")
            raise
    
    # =============================================================================
    # SPECIALIZED SCANNING TOOLS
    # =============================================================================
    
    async def ssl_tls_analysis(self,
                              target: str,
                              port: int = 443,
                              analysis_depth: str = "comprehensive",
                              check_vulnerabilities: bool = True) -> Dict[str, Any]:
        """
        Perform comprehensive SSL/TLS security analysis
        
        Args:
            target: Target hostname or IP
            port: Port to analyze (default 443)
            analysis_depth: Depth of analysis
            check_vulnerabilities: Check for known SSL/TLS vulnerabilities
        
        Returns:
            Dict with SSL/TLS analysis results
        """
        try:
            self.logger.info(f"Starting SSL/TLS analysis for {target}:{port}")
            
            analysis_data = {
                "target": target,
                "port": port,
                "analysis_depth": analysis_depth,
                "check_vulnerabilities": check_vulnerabilities,
                "check_certificate": True,
                "check_protocols": True,
                "check_cipher_suites": True
            }
            
            result = self.client._make_request('POST', '/api/tools/ssl-analysis', data=analysis_data)
            
            return result
            
        except Exception as e:
            self.logger.error(f"SSL/TLS analysis failed: {e}")
            raise
    
    async def smtp_enumeration(self,
                              target: str,
                              port: int = 25,
                              user_enumeration: bool = True,
                              wordlist: Optional[str] = None) -> Dict[str, Any]:
        """
        Perform SMTP service enumeration
        
        Args:
            target: Target SMTP server
            port: SMTP port (default 25)
            user_enumeration: Perform user enumeration
            wordlist: Wordlist for user enumeration
        
        Returns:
            Dict with SMTP enumeration results
        """
        try:
            self.logger.info(f"Starting SMTP enumeration for {target}:{port}")
            
            enum_data = {
                "target": target,
                "port": port,
                "user_enum": user_enumeration,
                "wordlist": wordlist or self.wordlists.get("usernames"),
                "methods": ["VRFY", "EXPN", "RCPT"]
            }
            
            result = self.client._make_request('POST', '/api/tools/smtp-enum', data=enum_data)
            
            return result
            
        except Exception as e:
            self.logger.error(f"SMTP enumeration failed: {e}")
            raise
    
    async def snmp_enumeration(self,
                              target: str,
                              community_strings: Optional[List[str]] = None,
                              version: str = "2c") -> Dict[str, Any]:
        """
        Perform SNMP enumeration
        
        Args:
            target: Target device
            community_strings: SNMP community strings to try
            version: SNMP version to use
        
        Returns:
            Dict with SNMP enumeration results
        """
        try:
            self.logger.info(f"Starting SNMP enumeration for {target}")
            
            enum_data = {
                "target": target,
                "community_strings": community_strings or ["public", "private", "community"],
                "version": version,
                "timeout": 5,
                "retries": 3
            }
            
            result = self.client._make_request('POST', '/api/tools/snmp-enum', data=enum_data)
            
            return result
            
        except Exception as e:
            self.logger.error(f"SNMP enumeration failed: {e}")
            raise
    
    # =============================================================================
    # REPORTING AND ANALYSIS UTILITIES
    # =============================================================================
    
    def generate_comprehensive_report(self, 
                                    scan_results: List[Dict[str, Any]],
                                    report_format: str = "html",
                                    include_remediation: bool = True) -> Dict[str, Any]:
        """
        Generate comprehensive security assessment report
        
        Args:
            scan_results: List of all scan results to include
            report_format: Output format (html, pdf, json, xml)
            include_remediation: Include remediation recommendations
        
        Returns:
            Dict with report generation results
        """
        try:
            self.logger.info(f"Generating comprehensive report from {len(scan_results)} scan results")
            
            report_data = {
                "scan_results": scan_results,
                "format": report_format,
                "include_remediation": include_remediation,
                "include_executive_summary": True,
                "include_technical_details": True,
                "include_risk_analysis": True,
                "timestamp": datetime.now().isoformat()
            }
            
            result = self.client._make_request('POST', '/api/tools/generate-report', data=report_data)
            
            self.logger.info(f"Report generated successfully: {result.get('report_path')}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Report generation failed: {e}")
            raise
    
    def get_available_tools(self) -> Dict[str, Any]:
        """
        Get list of all available security tools and their capabilities
        
        Returns:
            Dict with available tools information
        """
        try:
            result = self.client._make_request('GET', '/api/tools/list')
            
            tool_count = len(result.get('tools', []))
            self.logger.info(f"Retrieved information for {tool_count} security tools")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to get available tools: {e}")
            raise
    
    def validate_scan_configuration(self, scan_config: ScanConfiguration) -> Dict[str, Any]:
        """
        Validate scan configuration before execution
        
        Args:
            scan_config: Scan configuration to validate
        
        Returns:
            Dict with validation results and recommendations
        """
        try:
            validation_data = scan_config.to_dict()
            
            result = self.client._make_request('POST', '/api/tools/validate-config', data=validation_data)
            
            is_valid = result.get('valid', False)
            warnings = len(result.get('warnings', []))
            
            self.logger.info(f"Configuration validation - Valid: {is_valid}, Warnings: {warnings}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Configuration validation failed: {e}")
            raise


# =============================================================================
# ADDITIONAL UTILITY FUNCTIONS
# =============================================================================

def create_target_from_string(target_string: str) -> TargetInfo:
    """
    Create TargetInfo object from string representation
    
    Args:
        target_string: String representation of target (IP, hostname, URL, etc.)
    
    Returns:
        TargetInfo object
    """
    target = TargetInfo()
    
    # Try to parse as URL
    if target_string.startswith(('http://', 'https://')):
        parsed_url = urllib.parse.urlparse(target_string)
        target.url = target_string
        target.hostname = parsed_url.hostname
        target.domain = parsed_url.hostname
        
    # Try to parse as IP address
    else:
        try:
            ipaddress.ip_address(target_string)
            target.ip_address = target_string
        except ValueError:
            # Assume hostname/domain
            target.hostname = target_string
            target.domain = target_string
    
    return target

def create_scan_config(scan_type: ScanType, 
                      target: Union[str, TargetInfo],
                      **kwargs) -> ScanConfiguration:
    """
    Create scan configuration with sensible defaults
    
    Args:
        scan_type: Type of scan to perform
        target: Target information
        **kwargs: Additional configuration options
    
    Returns:
        ScanConfiguration object
    """
    if isinstance(target, str):
        target_info = create_target_from_string(target)
    else:
        target_info = target
    
    config = ScanConfiguration(
        scan_type=scan_type,
        target=target_info,
        **kwargs
    )
    
    return config

def parse_nmap_output(nmap_output: str) -> Dict[str, Any]:
    """
    Parse Nmap output and extract structured information
    
    Args:
        nmap_output: Raw Nmap output
    
    Returns:
        Dict with parsed Nmap results
    """
    # This is a simplified parser - in practice, you would use python-nmap
    # or implement more comprehensive parsing
    
    results = {
        'hosts': [],
        'scan_stats': {},
        'command_line': ''
    }
    
    lines = nmap_output.split('\n')
    current_host = None
    
    for line in lines:
        line = line.strip()
        
        # Extract command line
        if line.startswith('Starting Nmap') or line.startswith('Nmap scan report'):
            if 'Nmap scan report for' in line:
                # Extract host information
                host_match = re.search(r'Nmap scan report for (.+)', line)
                if host_match:
                    current_host = {
                        'host': host_match.group(1),
                        'ports': [],
                        'status': 'up'
                    }
                    results['hosts'].append(current_host)
        
        # Extract port information
        elif current_host and re.match(r'\d+/(tcp|udp)', line):
            port_match = re.search(r'(\d+)/(tcp|udp)\s+(\w+)\s+(\S+)', line)
            if port_match:
                port_info = {
                    'port': int(port_match.group(1)),
                    'protocol': port_match.group(2),
                    'state': port_match.group(3),
                    'service': port_match.group(4)
                }
                current_host['ports'].append(port_info)
    
    return results

def calculate_risk_score(scan_results: Dict[str, Any]) -> int:
    """
    Calculate overall risk score based on scan results
    
    Args:
        scan_results: Combined scan results
    
    Returns:
        Risk score from 0-100
    """
    risk_score = 0
    
    # Factor in number of open ports
    open_ports = 0
    for host in scan_results.get('hosts', []):
        for port in host.get('ports', []):
            if port.get('state') == 'open':
                open_ports += 1
    
    # High-risk services
    high_risk_services = ['telnet', 'ftp', 'smtp', 'snmp']
    risk_services = 0
    
    for host in scan_results.get('hosts', []):
        for port in host.get('ports', []):
            if port.get('service', '').lower() in high_risk_services:
                risk_services += 1
    
    # Calculate base risk
    risk_score += min(open_ports * 2, 40)  # Max 40 points for open ports
    risk_score += min(risk_services * 10, 30)  # Max 30 points for risky services
    
    # Factor in vulnerabilities if present
    vulnerabilities = scan_results.get('vulnerabilities', [])
    critical_vulns = sum(1 for v in vulnerabilities if v.get('severity') == 'critical')
    high_vulns = sum(1 for v in vulnerabilities if v.get('severity') == 'high')
    
    risk_score += critical_vulns * 15
    risk_score += high_vulns * 10
    
    return min(risk_score, 100)

def generate_recommendations(scan_results: Dict[str, Any]) -> List[str]:
    """
    Generate security recommendations based on scan results
    
    Args:
        scan_results: Scan results to analyze
    
    Returns:
        List of security recommendations
    """
    recommendations = []
    
    # Check for high-risk services
    high_risk_services = ['telnet', 'ftp', 'rlogin', 'netbios-ssn']
    
    for host in scan_results.get('hosts', []):
        for port in host.get('ports', []):
            service = port.get('service', '').lower()
            
            if service in high_risk_services:
                recommendations.append(
                    f"Consider disabling {service} service on {host.get('ip')}:{port.get('port')} "
                    "or implementing additional access controls"
                )
            
            if service == 'http' and port.get('port') != 80:
                recommendations.append(
                    f"HTTP service on non-standard port {port.get('port')} detected on {host.get('ip')} - "
                    "verify this is intentional"
                )
    
    # Check for common vulnerabilities
    vulnerabilities = scan_results.get('vulnerabilities', [])
    critical_count = sum(1 for v in vulnerabilities if v.get('severity') == 'critical')
    
    if critical_count > 0:
        recommendations.append(
            f"Immediately address {critical_count} critical vulnerabilities found"
        )
    
    # General recommendations
    if not recommendations:
        recommendations.append("No immediate security concerns identified, but regular scanning is recommended")
    
    return recommendations

# =============================================================================
# EXPORT CLASSES AND FUNCTIONS
# =============================================================================

__all__ = [
    'SecurityToolsClient',
    'ScanType', 
    'ToolCategory',
    'TargetInfo',
    'ScanConfiguration',
    'create_target_from_string',
    'create_scan_config',
    'parse_nmap_output',
    'calculate_risk_score',
    'generate_recommendations'
]