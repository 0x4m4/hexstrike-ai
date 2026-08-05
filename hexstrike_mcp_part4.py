#!/usr/bin/env python3
"""
HexStrike AI MCP Client v6.0 - Advanced Cybersecurity Automation Platform
Part 4 of 6: CTF (Capture The Flag) and Vulnerability Intelligence Endpoints

This part focuses on comprehensive CTF challenge solving, vulnerability intelligence
gathering, CVE analysis, threat hunting, and advanced security research automation.
It provides specialized capabilities for competitive cybersecurity and research activities.

Author: HexStrike AI Team
Version: 6.0.0
License: MIT
"""

import json
import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Union, Tuple, Literal, Set
from dataclasses import dataclass, field
from enum import Enum, auto
import re
import hashlib
import base64
import uuid
from urllib.parse import urlparse, urljoin
import random
from collections import defaultdict, deque, Counter
import threading
from concurrent.futures import ThreadPoolExecutor
import sqlite3
import pickle
import binascii
import struct
import socket
import ipaddress

# Configure logger for this module
logger = logging.getLogger("HexStrike-MCP-CTF-VulnIntel")

class CTFCategory(Enum):
    """CTF challenge categories"""
    WEB = "web"
    PWNABLE = "pwnable" 
    REVERSE_ENGINEERING = "reverse_engineering"
    CRYPTOGRAPHY = "cryptography"
    FORENSICS = "forensics"
    STEGANOGRAPHY = "steganography"
    NETWORK = "network"
    MISC = "miscellaneous"
    OSINT = "osint"
    MOBILE = "mobile"
    HARDWARE = "hardware"
    BLOCKCHAIN = "blockchain"

class CTFDifficulty(Enum):
    """CTF challenge difficulty levels"""
    BEGINNER = "beginner"
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"
    INSANE = "insane"

class VulnerabilitySource(Enum):
    """Vulnerability intelligence sources"""
    NVD = "nvd"
    MITRE = "mitre"
    CVE_DETAILS = "cve_details"
    EXPLOIT_DB = "exploit_db"
    METASPLOIT = "metasploit"
    GITHUB = "github"
    TWITTER = "twitter"
    VENDOR_ADVISORIES = "vendor_advisories"
    SECURITY_BLOGS = "security_blogs"
    THREAT_FEEDS = "threat_feeds"

class ThreatLevel(Enum):
    """Threat intelligence levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"

class IOCType(Enum):
    """Indicator of Compromise types"""
    IP_ADDRESS = "ip_address"
    DOMAIN = "domain"
    URL = "url"
    FILE_HASH = "file_hash"
    EMAIL = "email"
    REGISTRY_KEY = "registry_key"
    MUTEX = "mutex"
    USER_AGENT = "user_agent"
    SSL_CERT = "ssl_cert"

@dataclass
class CTFChallenge:
    """CTF challenge information structure"""
    name: str
    category: CTFCategory
    difficulty: CTFDifficulty
    points: int
    description: str
    files: List[str] = field(default_factory=list)
    hints: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    author: Optional[str] = None
    created_date: Optional[datetime] = None
    solve_count: int = 0
    flag_format: Optional[str] = None
    challenge_url: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API requests"""
        data = {}
        for key, value in self.__dict__.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat() if value else None
            elif isinstance(value, Enum):
                data[key] = value.value
            else:
                data[key] = value
        return data

@dataclass
class CVEInfo:
    """CVE (Common Vulnerabilities and Exposures) information"""
    cve_id: str
    description: str
    cvss_score: float
    cvss_vector: str
    severity: str
    published_date: datetime
    modified_date: datetime
    affected_products: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    cwe_ids: List[str] = field(default_factory=list)
    exploits: List[str] = field(default_factory=list)
    patches: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API requests"""
        data = {}
        for key, value in self.__dict__.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat() if value else None
            else:
                data[key] = value
        return data

@dataclass
class ThreatIntelReport:
    """Threat intelligence report structure"""
    report_id: str
    title: str
    threat_level: ThreatLevel
    source: str
    description: str
    iocs: List[Dict[str, Any]] = field(default_factory=list)
    ttps: List[str] = field(default_factory=list)  # Tactics, Techniques, Procedures
    affected_sectors: List[str] = field(default_factory=list)
    campaign_name: Optional[str] = None
    threat_actor: Optional[str] = None
    published_date: Optional[datetime] = None
    confidence_level: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API requests"""
        data = {}
        for key, value in self.__dict__.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat() if value else None
            elif isinstance(value, Enum):
                data[key] = value.value
            else:
                data[key] = value
        return data

class CTFVulnIntelClient:
    """
    Advanced CTF and Vulnerability Intelligence Client Extension for HexStrike MCP Client
    
    This class provides comprehensive CTF challenge solving automation, vulnerability
    intelligence gathering, CVE analysis, threat hunting capabilities, and advanced
    security research tools.
    """
    
    def __init__(self, base_client):
        """
        Initialize CTF and Vulnerability Intelligence Client
        
        Args:
            base_client: Instance of HexStrikeMCPClient
        """
        self.client = base_client
        self.logger = logging.getLogger(f"CTF-VulnIntel-{base_client.session_id[:8]}")
        
        # Initialize CTF-specific components
        self._init_ctf_solvers()
        self._init_vuln_intel_sources()
        self._init_analysis_engines()
        
        # Data storage
        self.solved_challenges: List[CTFChallenge] = []
        self.vulnerability_database: Dict[str, CVEInfo] = {}
        self.threat_intelligence: List[ThreatIntelReport] = []
        self.ioc_database: Dict[str, Dict[str, Any]] = {}
        
        # Analysis cache
        self.analysis_cache = {}
        
        self.logger.info("CTF and Vulnerability Intelligence Client initialized")
    
    def _init_ctf_solvers(self):
        """Initialize CTF challenge solving engines"""
        self.ctf_solvers = {
            "web": {
                "sql_injection": {"enabled": True, "tools": ["sqlmap", "custom_payloads"]},
                "xss": {"enabled": True, "tools": ["xsshunter", "custom_payloads"]},
                "lfi": {"enabled": True, "tools": ["custom_fuzzer"]},
                "rfi": {"enabled": True, "tools": ["custom_fuzzer"]},
                "ssrf": {"enabled": True, "tools": ["custom_payloads"]},
                "deserialization": {"enabled": True, "tools": ["ysoserial", "custom"]}
            },
            "crypto": {
                "classical": {"enabled": True, "tools": ["sage", "custom_scripts"]},
                "modern": {"enabled": True, "tools": ["sage", "cryptohack_tools"]},
                "hash_analysis": {"enabled": True, "tools": ["hashcat", "john"]},
                "rsa": {"enabled": True, "tools": ["sage", "factordb"]},
                "ecc": {"enabled": True, "tools": ["sage", "custom"]}
            },
            "reverse": {
                "static_analysis": {"enabled": True, "tools": ["ida", "ghidra", "radare2"]},
                "dynamic_analysis": {"enabled": True, "tools": ["gdb", "x64dbg", "frida"]},
                "decompilation": {"enabled": True, "tools": ["ghidra", "ida", "retdec"]},
                "unpacking": {"enabled": True, "tools": ["upx", "custom_unpackers"]}
            },
            "pwn": {
                "buffer_overflow": {"enabled": True, "tools": ["pwntools", "ropper"]},
                "format_string": {"enabled": True, "tools": ["pwntools"]},
                "heap_exploitation": {"enabled": True, "tools": ["pwntools", "glibc_tools"]},
                "rop_chains": {"enabled": True, "tools": ["ropper", "pwntools"]}
            },
            "forensics": {
                "memory_analysis": {"enabled": True, "tools": ["volatility", "rekall"]},
                "disk_analysis": {"enabled": True, "tools": ["autopsy", "sleuthkit"]},
                "network_analysis": {"enabled": True, "tools": ["wireshark", "tshark"]},
                "file_recovery": {"enabled": True, "tools": ["foremost", "scalpel"]}
            }
        }
    
    def _init_vuln_intel_sources(self):
        """Initialize vulnerability intelligence sources"""
        self.vuln_intel_sources = {
            "cve_feeds": {
                "nvd": {"url": "https://nvd.nist.gov/feeds/json/cve/1.1/", "enabled": True},
                "mitre": {"url": "https://cve.mitre.org/data/downloads/", "enabled": True}
            },
            "exploit_databases": {
                "exploitdb": {"url": "https://www.exploit-db.com/", "enabled": True},
                "metasploit": {"url": "https://www.metasploit.com/", "enabled": True},
                "packetstorm": {"url": "https://packetstormsecurity.com/", "enabled": True}
            },
            "threat_intelligence": {
                "otx": {"url": "https://otx.alienvault.com/", "enabled": True},
                "virustotal": {"url": "https://www.virustotal.com/", "enabled": True},
                "misp": {"url": "https://www.misp-project.org/", "enabled": True}
            },
            "vendor_advisories": {
                "microsoft": {"url": "https://portal.msrc.microsoft.com/", "enabled": True},
                "adobe": {"url": "https://helpx.adobe.com/security.html", "enabled": True},
                "oracle": {"url": "https://www.oracle.com/security-alerts/", "enabled": True}
            }
        }
    
    def _init_analysis_engines(self):
        """Initialize analysis engines"""
        self.analysis_engines = {
            "static_analysis": {
                "binary_analysis": {"engine": "radare2", "enabled": True},
                "source_code": {"engine": "semgrep", "enabled": True},
                "malware_analysis": {"engine": "yara", "enabled": True}
            },
            "dynamic_analysis": {
                "sandbox_analysis": {"engine": "cuckoo", "enabled": True},
                "network_monitoring": {"engine": "suricata", "enabled": True},
                "behavior_analysis": {"engine": "custom", "enabled": True}
            },
            "intelligence_correlation": {
                "pattern_matching": {"engine": "custom_ml", "enabled": True},
                "graph_analysis": {"engine": "networkx", "enabled": True},
                "timeline_analysis": {"engine": "custom", "enabled": True}
            }
        }
    
    # =============================================================================
    # CTF CHALLENGE SOLVING
    # =============================================================================
    
    async def solve_ctf_challenge(self,
                                 challenge: CTFChallenge,
                                 auto_solve: bool = True,
                                 time_limit: Optional[int] = None,
                                 use_ai_hints: bool = True) -> Dict[str, Any]:
        """
        Automatically solve CTF challenge using AI-powered techniques
        
        Args:
            challenge: CTF challenge information
            auto_solve: Whether to attempt automatic solving
            time_limit: Time limit for solving in seconds
            use_ai_hints: Use AI to generate solution hints
        
        Returns:
            Dict containing solution results, flag, and methodology
        """
        try:
            self.logger.info(f"Starting CTF challenge solving: {challenge.name} ({challenge.category.value})")
            
            solve_data = {
                "challenge": challenge.to_dict(),
                "auto_solve": auto_solve,
                "time_limit": time_limit or 3600,  # 1 hour default
                "ai_assistance": use_ai_hints,
                "solver_config": self.ctf_solvers.get(challenge.category.value, {}),
                "enable_learning": True
            }
            
            result = self.client._make_request('POST', '/api/ctf/solve-challenge', data=solve_data)
            
            success = result.get('solved', False)
            flag = result.get('flag', '')
            solving_time = result.get('solving_time_seconds', 0)
            
            self.logger.info(f"CTF challenge {'solved' if success else 'not solved'} in {solving_time}s")
            
            if success and flag:
                self.logger.info(f"Flag found: {flag}")
                # Add to solved challenges
                challenge.solve_count += 1
                self.solved_challenges.append(challenge)
            
            return result
            
        except Exception as e:
            self.logger.error(f"CTF challenge solving failed: {e}")
            raise
    
    async def analyze_ctf_binary(self,
                               binary_path: str,
                               analysis_depth: str = "comprehensive",
                               include_dynamic_analysis: bool = True,
                               extract_strings: bool = True) -> Dict[str, Any]:
        """
        Perform comprehensive binary analysis for CTF reverse engineering challenges
        
        Args:
            binary_path: Path to binary file for analysis
            analysis_depth: Depth of analysis (quick, standard, comprehensive)
            include_dynamic_analysis: Include dynamic analysis
            extract_strings: Extract readable strings
        
        Returns:
            Dict containing binary analysis results
        """
        try:
            self.logger.info(f"Starting binary analysis: {binary_path}")
            
            analysis_data = {
                "binary_path": binary_path,
                "analysis_depth": analysis_depth,
                "dynamic_analysis": include_dynamic_analysis,
                "extract_strings": extract_strings,
                "disassemble": True,
                "detect_packing": True,
                "identify_functions": True,
                "control_flow_analysis": True,
                "vulnerability_detection": True
            }
            
            result = self.client._make_request('POST', '/api/ctf/analyze-binary', data=analysis_data)
            
            function_count = len(result.get('functions', []))
            strings_count = len(result.get('strings', []))
            vulnerabilities = len(result.get('vulnerabilities', []))
            
            self.logger.info(f"Binary analysis completed - Functions: {function_count}, Strings: {strings_count}, Vulnerabilities: {vulnerabilities}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Binary analysis failed: {e}")
            raise
    
    async def solve_cryptography_challenge(self,
                                         cipher_text: str,
                                         cipher_type: Optional[str] = None,
                                         known_plaintext: Optional[str] = None,
                                         key_hints: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Solve cryptography CTF challenges using various techniques
        
        Args:
            cipher_text: The encrypted text to decrypt
            cipher_type: Type of cipher if known
            known_plaintext: Any known plaintext
            key_hints: Hints about the key
        
        Returns:
            Dict containing decryption results
        """
        try:
            self.logger.info("Starting cryptography challenge solving")
            
            crypto_data = {
                "cipher_text": cipher_text,
                "cipher_type": cipher_type,
                "known_plaintext": known_plaintext,
                "key_hints": key_hints or [],
                "auto_detect_cipher": cipher_type is None,
                "brute_force_keys": True,
                "frequency_analysis": True,
                "dictionary_attack": True
            }
            
            result = self.client._make_request('POST', '/api/ctf/solve-crypto', data=crypto_data)
            
            solved = result.get('solved', False)
            plaintext = result.get('plaintext', '')
            method = result.get('method_used', '')
            
            self.logger.info(f"Cryptography challenge {'solved' if solved else 'not solved'} using {method}")
            
            if solved:
                self.logger.info(f"Plaintext: {plaintext}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Cryptography challenge solving failed: {e}")
            raise
    
    async def analyze_network_traffic(self,
                                    pcap_file: str,
                                    protocol_filter: Optional[List[str]] = None,
                                    extract_files: bool = True,
                                    decode_protocols: bool = True) -> Dict[str, Any]:
        """
        Analyze network traffic for CTF forensics challenges
        
        Args:
            pcap_file: Path to PCAP file
            protocol_filter: Protocols to focus on
            extract_files: Extract files from traffic
            decode_protocols: Decode application protocols
        
        Returns:
            Dict containing network analysis results
        """
        try:
            self.logger.info(f"Starting network traffic analysis: {pcap_file}")
            
            analysis_data = {
                "pcap_file": pcap_file,
                "protocol_filter": protocol_filter or [],
                "extract_files": extract_files,
                "decode_protocols": decode_protocols,
                "detect_anomalies": True,
                "timeline_analysis": True,
                "conversation_analysis": True
            }
            
            result = self.client._make_request('POST', '/api/ctf/analyze-network', data=analysis_data)
            
            packet_count = result.get('total_packets', 0)
            protocols = len(result.get('protocols_found', []))
            extracted_files = len(result.get('extracted_files', []))
            
            self.logger.info(f"Network analysis completed - Packets: {packet_count}, Protocols: {protocols}, Files: {extracted_files}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Network traffic analysis failed: {e}")
            raise
    
    async def solve_steganography_challenge(self,
                                          file_path: str,
                                          steg_methods: Optional[List[str]] = None,
                                          password_wordlist: Optional[str] = None) -> Dict[str, Any]:
        """
        Solve steganography challenges by detecting and extracting hidden data
        
        Args:
            file_path: Path to file that may contain hidden data
            steg_methods: Steganography methods to try
            password_wordlist: Wordlist for password-protected steganography
        
        Returns:
            Dict containing steganography analysis results
        """
        try:
            self.logger.info(f"Starting steganography analysis: {file_path}")
            
            steg_data = {
                "file_path": file_path,
                "methods": steg_methods or ["lsb", "dct", "outguess", "steghide", "f5"],
                "password_wordlist": password_wordlist,
                "try_common_passwords": True,
                "analyze_metadata": True,
                "visual_analysis": True
            }
            
            result = self.client._make_request('POST', '/api/ctf/solve-steganography', data=steg_data)
            
            hidden_found = result.get('hidden_data_found', False)
            methods_tried = len(result.get('methods_attempted', []))
            
            self.logger.info(f"Steganography analysis completed - Hidden data: {hidden_found}, Methods tried: {methods_tried}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Steganography analysis failed: {e}")
            raise
    
    async def get_ctf_leaderboard(self, ctf_id: str) -> Dict[str, Any]:
        """
        Get CTF competition leaderboard and statistics
        
        Args:
            ctf_id: CTF competition identifier
        
        Returns:
            Dict containing leaderboard information
        """
        try:
            result = self.client._make_request('GET', f'/api/ctf/leaderboard/{ctf_id}')
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to get CTF leaderboard: {e}")
            raise
    
    # =============================================================================
    # VULNERABILITY INTELLIGENCE
    # =============================================================================
    
    async def monitor_cve_feeds(self,
                              keywords: Optional[List[str]] = None,
                              severity_filter: Optional[List[str]] = None,
                              date_range: Optional[Tuple[datetime, datetime]] = None,
                              auto_analysis: bool = True) -> Dict[str, Any]:
        """
        Monitor CVE feeds for new vulnerabilities matching criteria
        
        Args:
            keywords: Keywords to filter CVEs
            severity_filter: Severity levels to include
            date_range: Date range for CVE filtering
            auto_analysis: Automatically analyze new CVEs
        
        Returns:
            Dict containing CVE monitoring results
        """
        try:
            self.logger.info("Starting CVE feed monitoring")
            
            monitoring_data = {
                "keywords": keywords or [],
                "severity_filter": severity_filter or ["HIGH", "CRITICAL"],
                "date_range": {
                    "start": date_range[0].isoformat() if date_range and date_range[0] else None,
                    "end": date_range[1].isoformat() if date_range and date_range[1] else None
                } if date_range else None,
                "auto_analysis": auto_analysis,
                "sources": list(self.vuln_intel_sources["cve_feeds"].keys()),
                "include_exploits": True,
                "include_patches": True
            }
            
            result = self.client._make_request('POST', '/api/vuln-intel/monitor-cves', data=monitoring_data)
            
            new_cves = len(result.get('new_cves', []))
            critical_count = len([cve for cve in result.get('new_cves', []) if cve.get('severity') == 'CRITICAL'])
            
            self.logger.info(f"CVE monitoring completed - New CVEs: {new_cves} (Critical: {critical_count})")
            
            # Update local vulnerability database
            for cve_data in result.get('new_cves', []):
                cve_info = CVEInfo(
                    cve_id=cve_data['cve_id'],
                    description=cve_data['description'],
                    cvss_score=cve_data.get('cvss_score', 0.0),
                    cvss_vector=cve_data.get('cvss_vector', ''),
                    severity=cve_data.get('severity', ''),
                    published_date=datetime.fromisoformat(cve_data['published_date'].replace('Z', '+00:00')),
                    modified_date=datetime.fromisoformat(cve_data['modified_date'].replace('Z', '+00:00')),
                    affected_products=cve_data.get('affected_products', []),
                    references=cve_data.get('references', [])
                )
                self.vulnerability_database[cve_data['cve_id']] = cve_info
            
            return result
            
        except Exception as e:
            self.logger.error(f"CVE feed monitoring failed: {e}")
            raise
    
    async def analyze_cve_impact(self,
                               cve_id: str,
                               target_environment: Optional[Dict[str, Any]] = None,
                               include_exploit_analysis: bool = True) -> Dict[str, Any]:
        """
        Perform comprehensive impact analysis for a specific CVE
        
        Args:
            cve_id: CVE identifier to analyze
            target_environment: Target environment details for impact assessment
            include_exploit_analysis: Include exploit availability analysis
        
        Returns:
            Dict containing CVE impact analysis
        """
        try:
            self.logger.info(f"Starting CVE impact analysis: {cve_id}")
            
            analysis_data = {
                "cve_id": cve_id,
                "target_environment": target_environment or {},
                "exploit_analysis": include_exploit_analysis,
                "patch_analysis": True,
                "business_impact": True,
                "attack_vector_analysis": True,
                "remediation_recommendations": True
            }
            
            result = self.client._make_request('POST', '/api/vuln-intel/analyze-cve-impact', data=analysis_data)
            
            impact_score = result.get('impact_analysis', {}).get('overall_impact_score', 0)
            exploits_available = len(result.get('exploit_analysis', {}).get('available_exploits', []))
            
            self.logger.info(f"CVE impact analysis completed - Impact Score: {impact_score}/100, Exploits: {exploits_available}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"CVE impact analysis failed: {e}")
            raise
    
    async def search_vulnerability_database(self,
                                          search_criteria: Dict[str, Any],
                                          include_exploits: bool = True,
                                          include_patches: bool = True) -> Dict[str, Any]:
        """
        Search comprehensive vulnerability database with advanced criteria
        
        Args:
            search_criteria: Search criteria (product, version, vendor, etc.)
            include_exploits: Include exploit information
            include_patches: Include patch information
        
        Returns:
            Dict containing search results
        """
        try:
            self.logger.info("Searching vulnerability database")
            
            search_data = {
                "criteria": search_criteria,
                "include_exploits": include_exploits,
                "include_patches": include_patches,
                "sources": ["nvd", "mitre", "exploitdb", "metasploit"],
                "sort_by": "cvss_score",
                "sort_order": "desc"
            }
            
            result = self.client._make_request('POST', '/api/vuln-intel/search-database', data=search_data)
            
            results_count = len(result.get('vulnerabilities', []))
            critical_count = len([v for v in result.get('vulnerabilities', []) if v.get('severity') == 'CRITICAL'])
            
            self.logger.info(f"Database search completed - Results: {results_count} (Critical: {critical_count})")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Vulnerability database search failed: {e}")
            raise
    
    async def track_exploit_development(self,
                                      cve_id: str,
                                      monitoring_sources: Optional[List[str]] = None,
                                      alert_threshold: str = "any_exploit") -> Dict[str, Any]:
        """
        Track exploit development for specific CVE across multiple sources
        
        Args:
            cve_id: CVE identifier to track
            monitoring_sources: Sources to monitor for exploits
            alert_threshold: Threshold for alerts (any_exploit, functional_exploit, weaponized)
        
        Returns:
            Dict containing exploit tracking setup and initial results
        """
        try:
            self.logger.info(f"Starting exploit development tracking: {cve_id}")
            
            tracking_data = {
                "cve_id": cve_id,
                "sources": monitoring_sources or ["exploitdb", "github", "twitter", "metasploit", "packetstorm"],
                "alert_threshold": alert_threshold,
                "monitor_poc": True,
                "monitor_weaponized": True,
                "sentiment_analysis": True,
                "automation_alerts": True
            }
            
            result = self.client._make_request('POST', '/api/vuln-intel/track-exploit-development', data=tracking_data)
            
            tracking_id = result.get('tracking_id')
            current_exploits = len(result.get('current_exploits', []))
            
            self.logger.info(f"Exploit tracking started - Tracking ID: {tracking_id}, Current exploits: {current_exploits}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Exploit development tracking failed: {e}")
            raise
    
    # =============================================================================
    # THREAT INTELLIGENCE
    # =============================================================================
    
    async def collect_threat_intelligence(self,
                                        indicators: List[str],
                                        indicator_types: Optional[List[IOCType]] = None,
                                        enrichment_sources: Optional[List[str]] = None,
                                        confidence_threshold: float = 0.5) -> Dict[str, Any]:
        """
        Collect and enrich threat intelligence for given indicators
        
        Args:
            indicators: List of indicators to analyze
            indicator_types: Types of indicators being analyzed
            enrichment_sources: Sources for threat intelligence enrichment
            confidence_threshold: Minimum confidence threshold for results
        
        Returns:
            Dict containing enriched threat intelligence
        """
        try:
            self.logger.info(f"Collecting threat intelligence for {len(indicators)} indicators")
            
            intel_data = {
                "indicators": indicators,
                "types": [t.value for t in (indicator_types or [])],
                "sources": enrichment_sources or ["virustotal", "otx", "misp", "threatcrowd"],
                "confidence_threshold": confidence_threshold,
                "include_malware_families": True,
                "include_attribution": True,
                "include_campaigns": True,
                "temporal_analysis": True
            }
            
            result = self.client._make_request('POST', '/api/vuln-intel/collect-threat-intelligence', data=intel_data)
            
            enriched_indicators = len(result.get('enriched_indicators', []))
            malicious_count = len([i for i in result.get('enriched_indicators', []) if i.get('malicious', False)])
            
            self.logger.info(f"Threat intelligence collection completed - Enriched: {enriched_indicators}, Malicious: {malicious_count}")
            
            # Update local IOC database
            for indicator in result.get('enriched_indicators', []):
                ioc_value = indicator.get('indicator')
                if ioc_value:
                    self.ioc_database[ioc_value] = indicator
            
            return result
            
        except Exception as e:
            self.logger.error(f"Threat intelligence collection failed: {e}")
            raise
    
    async def analyze_threat_campaign(self,
                                    campaign_indicators: List[str],
                                    campaign_name: Optional[str] = None,
                                    timeline_analysis: bool = True) -> Dict[str, Any]:
        """
        Analyze threat campaign using multiple indicators and intelligence sources
        
        Args:
            campaign_indicators: List of indicators associated with campaign
            campaign_name: Optional campaign name for context
            timeline_analysis: Perform timeline analysis of campaign activity
        
        Returns:
            Dict containing campaign analysis results
        """
        try:
            self.logger.info(f"Analyzing threat campaign with {len(campaign_indicators)} indicators")
            
            campaign_data = {
                "indicators": campaign_indicators,
                "campaign_name": campaign_name,
                "timeline_analysis": timeline_analysis,
                "attribution_analysis": True,
                "ttp_mapping": True,  # Map to MITRE ATT&CK framework
                "infrastructure_analysis": True,
                "victim_profiling": True
            }
            
            result = self.client._make_request('POST', '/api/vuln-intel/analyze-threat-campaign', data=campaign_data)
            
            ttps_identified = len(result.get('ttps', []))
            infrastructure_nodes = len(result.get('infrastructure', []))
            confidence_score = result.get('attribution_confidence', 0)
            
            self.logger.info(f"Threat campaign analysis completed - TTPs: {ttps_identified}, Infrastructure: {infrastructure_nodes}, Attribution confidence: {confidence_score}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Threat campaign analysis failed: {e}")
            raise
    
    async def hunt_advanced_threats(self,
                                  hunting_rules: List[Dict[str, Any]],
                                  data_sources: Optional[List[str]] = None,
                                  time_range: Optional[Tuple[datetime, datetime]] = None) -> Dict[str, Any]:
        """
        Perform advanced threat hunting using custom rules and multiple data sources
        
        Args:
            hunting_rules: List of hunting rules to apply
            data_sources: Data sources to hunt across
            time_range: Time range for threat hunting
        
        Returns:
            Dict containing threat hunting results
        """
        try:
            self.logger.info(f"Starting advanced threat hunting with {len(hunting_rules)} rules")
            
            hunting_data = {
                "rules": hunting_rules,
                "data_sources": data_sources or ["logs", "network_traffic", "endpoint_data", "threat_feeds"],
                "time_range": {
                    "start": time_range[0].isoformat() if time_range and time_range[0] else None,
                    "end": time_range[1].isoformat() if time_range and time_range[1] else None
                } if time_range else None,
                "behavioral_analysis": True,
                "anomaly_detection": True,
                "machine_learning": True
            }
            
            result = self.client._make_request('POST', '/api/vuln-intel/hunt-advanced-threats', data=hunting_data)
            
            matches_found = len(result.get('matches', []))
            high_confidence = len([m for m in result.get('matches', []) if m.get('confidence', 0) > 0.8])
            
            self.logger.info(f"Threat hunting completed - Matches: {matches_found} (High confidence: {high_confidence})")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Advanced threat hunting failed: {e}")
            raise
    
    async def generate_threat_report(self,
                                   threat_data: Dict[str, Any],
                                   report_format: str = "comprehensive",
                                   include_iocs: bool = True,
                                   include_mitigations: bool = True) -> Dict[str, Any]:
        """
        Generate comprehensive threat intelligence report
        
        Args:
            threat_data: Threat intelligence data to include in report
            report_format: Format of report (executive, technical, comprehensive)
            include_iocs: Include indicators of compromise
            include_mitigations: Include mitigation recommendations
        
        Returns:
            Dict containing generated threat report
        """
        try:
            self.logger.info("Generating threat intelligence report")
            
            report_data = {
                "threat_data": threat_data,
                "format": report_format,
                "include_iocs": include_iocs,
                "include_mitigations": include_mitigations,
                "include_timeline": True,
                "include_attribution": True,
                "include_recommendations": True,
                "ai_enhancement": True
            }
            
            result = self.client._make_request('POST', '/api/vuln-intel/generate-threat-report', data=report_data)
            
            report_id = result.get('report_id')
            page_count = result.get('pages', 0)
            
            self.logger.info(f"Threat report generated - ID: {report_id}, Pages: {page_count}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Threat report generation failed: {e}")
            raise
    
    # =============================================================================
    # RESEARCH AND ANALYSIS TOOLS
    # =============================================================================
    
    async def research_zero_day_trends(self,
                                     research_timeframe: int = 365,
                                     technology_focus: Optional[List[str]] = None,
                                     include_predictions: bool = True) -> Dict[str, Any]:
        """
        Research zero-day vulnerability trends and patterns
        
        Args:
            research_timeframe: Timeframe for research in days
            technology_focus: Specific technologies to focus on
            include_predictions: Include predictive analysis
        
        Returns:
            Dict containing zero-day research results
        """
        try:
            self.logger.info(f"Researching zero-day trends over {research_timeframe} days")
            
            research_data = {
                "timeframe_days": research_timeframe,
                "technology_focus": technology_focus or [],
                "include_predictions": include_predictions,
                "trend_analysis": True,
                "pattern_recognition": True,
                "market_impact_analysis": True,
                "attribution_patterns": True
            }
            
            result = self.client._make_request('POST', '/api/vuln-intel/research-zero-day-trends', data=research_data)
            
            trends_identified = len(result.get('trends', []))
            predictions = len(result.get('predictions', []))
            
            self.logger.info(f"Zero-day research completed - Trends: {trends_identified}, Predictions: {predictions}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Zero-day trends research failed: {e}")
            raise
    
    async def correlate_attack_patterns(self,
                                      incident_data: List[Dict[str, Any]],
                                      correlation_algorithms: Optional[List[str]] = None,
                                      similarity_threshold: float = 0.7) -> Dict[str, Any]:
        """
        Correlate attack patterns across multiple security incidents
        
        Args:
            incident_data: List of security incidents to correlate
            correlation_algorithms: Algorithms to use for correlation
            similarity_threshold: Threshold for pattern similarity
        
        Returns:
            Dict containing pattern correlation results
        """
        try:
            self.logger.info(f"Correlating attack patterns across {len(incident_data)} incidents")
            
            correlation_data = {
                "incidents": incident_data,
                "algorithms": correlation_algorithms or ["cosine_similarity", "jaccard", "hamming"],
                "similarity_threshold": similarity_threshold,
                "temporal_correlation": True,
                "geographic_correlation": True,
                "behavioral_correlation": True,
                "ttp_correlation": True
            }
            
            result = self.client._make_request('POST', '/api/vuln-intel/correlate-attack-patterns', data=correlation_data)
            
            pattern_groups = len(result.get('pattern_groups', []))
            strong_correlations = len([g for g in result.get('pattern_groups', []) if g.get('confidence', 0) > 0.8])
            
            self.logger.info(f"Pattern correlation completed - Groups: {pattern_groups} (Strong: {strong_correlations})")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Attack pattern correlation failed: {e}")
            raise
    
    async def analyze_dark_web_intelligence(self,
                                          search_terms: List[str],
                                          monitoring_duration: int = 86400,  # 24 hours
                                          risk_assessment: bool = True) -> Dict[str, Any]:
        """
        Analyze dark web for threat intelligence and security-related discussions
        
        Args:
            search_terms: Terms to search for on dark web
            monitoring_duration: Duration to monitor in seconds
            risk_assessment: Perform risk assessment on findings
        
        Returns:
            Dict containing dark web intelligence
        """
        try:
            self.logger.info(f"Analyzing dark web intelligence for {len(search_terms)} terms")
            
            # Note: This would require specialized dark web monitoring capabilities
            analysis_data = {
                "search_terms": search_terms,
                "monitoring_duration": monitoring_duration,
                "risk_assessment": risk_assessment,
                "sentiment_analysis": True,
                "threat_actor_tracking": True,
                "marketplace_monitoring": True,
                "credential_monitoring": True
            }
            
            result = self.client._make_request('POST', '/api/vuln-intel/analyze-dark-web', data=analysis_data)
            
            mentions_found = len(result.get('mentions', []))
            high_risk_items = len([m for m in result.get('mentions', []) if m.get('risk_level') == 'high'])
            
            self.logger.info(f"Dark web analysis completed - Mentions: {mentions_found} (High risk: {high_risk_items})")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Dark web intelligence analysis failed: {e}")
            raise
    
    # =============================================================================
    # UTILITY AND REPORTING METHODS
    # =============================================================================
    
    def get_ctf_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive CTF statistics and performance metrics
        
        Returns:
            Dict containing CTF statistics
        """
        solved_by_category = Counter(c.category.value for c in self.solved_challenges)
        solved_by_difficulty = Counter(c.difficulty.value for c in self.solved_challenges)
        total_points = sum(c.points for c in self.solved_challenges)
        
        return {
            "session_info": {
                "session_id": self.client.session_id,
                "total_challenges_solved": len(self.solved_challenges),
                "total_points_earned": total_points
            },
            "category_distribution": dict(solved_by_category),
            "difficulty_distribution": dict(solved_by_difficulty),
            "average_points_per_challenge": total_points / max(len(self.solved_challenges), 1),
            "solver_efficiency": {
                "web_challenges": len([c for c in self.solved_challenges if c.category == CTFCategory.WEB]),
                "crypto_challenges": len([c for c in self.solved_challenges if c.category == CTFCategory.CRYPTOGRAPHY]),
                "reverse_challenges": len([c for c in self.solved_challenges if c.category == CTFCategory.REVERSE_ENGINEERING])
            }
        }
    
    def get_vulnerability_intelligence_summary(self) -> Dict[str, Any]:
        """
        Get summary of vulnerability intelligence data
        
        Returns:
            Dict containing vulnerability intelligence summary
        """
        return {
            "vulnerability_database": {
                "total_cves": len(self.vulnerability_database),
                "critical_cves": len([cve for cve in self.vulnerability_database.values() if cve.severity == "CRITICAL"]),
                "high_cves": len([cve for cve in self.vulnerability_database.values() if cve.severity == "HIGH"]),
                "recent_cves": len([cve for cve in self.vulnerability_database.values() 
                                 if (datetime.now() - cve.published_date).days <= 30])
            },
            "threat_intelligence": {
                "total_reports": len(self.threat_intelligence),
                "high_confidence_reports": len([r for r in self.threat_intelligence if r.confidence_level > 0.8]),
                "recent_reports": len([r for r in self.threat_intelligence 
                                     if r.published_date and (datetime.now() - r.published_date).days <= 7])
            },
            "ioc_database": {
                "total_iocs": len(self.ioc_database),
                "malicious_iocs": len([ioc for ioc in self.ioc_database.values() if ioc.get('malicious', False)]),
                "ioc_types": Counter(ioc.get('type', 'unknown') for ioc in self.ioc_database.values())
            }
        }
    
    async def export_intelligence_data(self,
                                     export_format: str = "json",
                                     include_sensitive: bool = False,
                                     date_filter: Optional[Tuple[datetime, datetime]] = None) -> Dict[str, Any]:
        """
        Export collected intelligence data in various formats
        
        Args:
            export_format: Format for export (json, csv, stix, misp)
            include_sensitive: Include sensitive information
            date_filter: Optional date range filter
        
        Returns:
            Dict containing export results
        """
        try:
            self.logger.info(f"Exporting intelligence data in {export_format} format")
            
            export_data = {
                "format": export_format,
                "include_sensitive": include_sensitive,
                "date_filter": {
                    "start": date_filter[0].isoformat() if date_filter and date_filter[0] else None,
                    "end": date_filter[1].isoformat() if date_filter and date_filter[1] else None
                } if date_filter else None,
                "data": {
                    "cves": [cve.to_dict() for cve in self.vulnerability_database.values()],
                    "threat_reports": [report.to_dict() for report in self.threat_intelligence],
                    "iocs": dict(self.ioc_database),
                    "ctf_results": [challenge.to_dict() for challenge in self.solved_challenges]
                }
            }
            
            result = self.client._make_request('POST', '/api/vuln-intel/export-data', data=export_data)
            
            export_size = result.get('export_size_bytes', 0)
            records_exported = result.get('records_exported', 0)
            
            self.logger.info(f"Intelligence data exported - Records: {records_exported}, Size: {export_size} bytes")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Intelligence data export failed: {e}")
            raise


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def parse_cve_id(cve_string: str) -> Optional[str]:
    """
    Parse and validate CVE identifier format
    
    Args:
        cve_string: String that may contain CVE ID
    
    Returns:
        Validated CVE ID or None if invalid
    """
    cve_pattern = r'CVE-\d{4}-\d{4,}'
    match = re.search(cve_pattern, cve_string.upper())
    return match.group(0) if match else None

def calculate_cvss_score(cvss_vector: str) -> float:
    """
    Calculate CVSS score from CVSS vector string
    
    Args:
        cvss_vector: CVSS vector string
    
    Returns:
        Calculated CVSS score
    """
    # Simplified CVSS calculation - in practice, would use proper CVSS library
    if not cvss_vector or not cvss_vector.startswith('CVSS:'):
        return 0.0
    
    # Extract base score if present
    score_match = re.search(r'(\d+\.\d+)', cvss_vector)
    if score_match:
        return float(score_match.group(1))
    
    return 0.0

def classify_threat_level(indicators: Dict[str, Any]) -> ThreatLevel:
    """
    Classify threat level based on indicators
    
    Args:
        indicators: Threat indicators dictionary
    
    Returns:
        Classified threat level
    """
    malicious_count = sum(1 for indicator in indicators.values() if indicator.get('malicious', False))
    high_confidence = sum(1 for indicator in indicators.values() if indicator.get('confidence', 0) > 0.8)
    
    total_indicators = len(indicators)
    
    if total_indicators == 0:
        return ThreatLevel.INFORMATIONAL
    
    malicious_ratio = malicious_count / total_indicators
    confidence_ratio = high_confidence / total_indicators
    
    if malicious_ratio > 0.7 and confidence_ratio > 0.6:
        return ThreatLevel.CRITICAL
    elif malicious_ratio > 0.4 and confidence_ratio > 0.4:
        return ThreatLevel.HIGH
    elif malicious_ratio > 0.2:
        return ThreatLevel.MEDIUM
    elif malicious_count > 0:
        return ThreatLevel.LOW
    else:
        return ThreatLevel.INFORMATIONAL

def extract_iocs_from_text(text: str) -> Dict[IOCType, List[str]]:
    """
    Extract indicators of compromise from text using regex patterns
    
    Args:
        text: Text to extract IOCs from
    
    Returns:
        Dictionary of IOC types and their extracted values
    """
    iocs = {ioc_type: [] for ioc_type in IOCType}
    
    # IP addresses
    ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
    iocs[IOCType.IP_ADDRESS] = re.findall(ip_pattern, text)
    
    # Domain names
    domain_pattern = r'\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b'
    iocs[IOCType.DOMAIN] = re.findall(domain_pattern, text)
    
    # URLs
    url_pattern = r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:\w*))?)?'
    iocs[IOCType.URL] = re.findall(url_pattern, text)
    
    # Email addresses
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    iocs[IOCType.EMAIL] = re.findall(email_pattern, text)
    
    # File hashes (MD5, SHA1, SHA256)
    hash_patterns = {
        32: IOCType.FILE_HASH,   # MD5
        40: IOCType.FILE_HASH,   # SHA1
        64: IOCType.FILE_HASH    # SHA256
    }
    
    for length, ioc_type in hash_patterns.items():
        pattern = r'\b[a-fA-F0-9]{' + str(length) + r'}\b'
        hashes = re.findall(pattern, text)
        iocs[ioc_type].extend(hashes)
    
    # Remove duplicates and empty lists
    return {k: list(set(v)) for k, v in iocs.items() if v}


# =============================================================================
# EXPORT CLASSES AND FUNCTIONS
# =============================================================================

__all__ = [
    'CTFVulnIntelClient',
    'CTFCategory',
    'CTFDifficulty',
    'VulnerabilitySource',
    'ThreatLevel', 
    'IOCType',
    'CTFChallenge',
    'CVEInfo',
    'ThreatIntelReport',
    'parse_cve_id',
    'calculate_cvss_score',
    'classify_threat_level',
    'extract_iocs_from_text'
]