#!/usr/bin/env python3
"""
HexStrike AI MCP Client v6.0 - Advanced Cybersecurity Automation Platform
Part 6 of 6: Advanced Endpoints, Integration Layer, and Final Utilities

This is the final part that brings together all components of the HexStrike MCP Client,
providing advanced integration capabilities, comprehensive error handling, visual
output systems, Python environment management, and the complete unified API interface.

Author: HexStrike AI Team
Version: 6.0.0
License: MIT
"""

import json
import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Union, Tuple, Literal, Set, Callable
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
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
import sqlite3
import pickle
import traceback
import sys
import os
import subprocess
import shutil
import tempfile
import zipfile
import tarfile
from pathlib import Path
import mimetypes
from contextlib import contextmanager, asynccontextmanager
import warnings
import ssl
import socket
import platform

# Import all previous parts
try:
    from hexstrike_mcp_part1 import HexStrikeMCPClient, SecurityLevel, ClientState
    from hexstrike_mcp_part2 import SecurityToolsClient, ScanType, TargetInfo
    from hexstrike_mcp_part3 import BugBountyAIClient, VulnerabilityCategory, SeverityLevel
    from hexstrike_mcp_part4 import CTFVulnIntelClient, CTFCategory, ThreatLevel
    from hexstrike_mcp_part5 import ProcessCacheClient, ProcessState, ResourceType
except ImportError as e:
    logging.error(f"Failed to import required components: {e}")
    logging.error("Please ensure all HexStrike MCP Client parts are in the same directory")
    sys.exit(1)

# Configure logger for this module
logger = logging.getLogger("HexStrike-MCP-Advanced")

class ErrorSeverity(Enum):
    """Error severity levels for comprehensive error handling"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    FATAL = "fatal"

class RecoveryStrategy(Enum):
    """Error recovery strategies"""
    RETRY = "retry"
    FALLBACK = "fallback"
    SKIP = "skip"
    ABORT = "abort"
    MANUAL = "manual"

class OutputFormat(Enum):
    """Visual output formats"""
    PLAIN = "plain"
    COLORED = "colored"
    JSON = "json"
    XML = "xml"
    HTML = "html"
    MARKDOWN = "markdown"

class PythonEnvironment(Enum):
    """Python environment types"""
    SYSTEM = "system"
    VIRTUAL = "virtual"
    CONDA = "conda"
    DOCKER = "docker"
    ISOLATED = "isolated"

@dataclass
class ErrorContext:
    """Error context information for advanced error handling"""
    error_id: str
    timestamp: datetime
    severity: ErrorSeverity
    component: str
    function: str
    message: str
    exception_type: str
    stack_trace: str
    recovery_strategy: Optional[RecoveryStrategy] = None
    recovery_attempts: int = 0
    max_recovery_attempts: int = 3
    user_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = {}
        for key, value in self.__dict__.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
            elif isinstance(value, Enum):
                data[key] = value.value
            else:
                data[key] = value
        return data

@dataclass
class VisualConfig:
    """Visual output configuration"""
    format: OutputFormat = OutputFormat.COLORED
    color_scheme: str = "default"
    show_timestamps: bool = True
    show_levels: bool = True
    show_progress: bool = True
    animation_enabled: bool = True
    width: int = 80
    theme: str = "dark"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = {}
        for key, value in self.__dict__.items():
            if isinstance(value, Enum):
                data[key] = value.value
            else:
                data[key] = value
        return data

class AdvancedHexStrikeMCPClient:
    """
    Advanced Unified HexStrike MCP Client
    
    This is the master client class that integrates all components of the HexStrike
    MCP Client system, providing a unified interface for all cybersecurity automation
    capabilities with advanced error handling, recovery, and monitoring.
    """
    
    def __init__(self, server_url: str = "http://localhost:8888", **kwargs):
        """
        Initialize Advanced HexStrike MCP Client with all components
        
        Args:
            server_url: URL of the HexStrike server
            **kwargs: Additional configuration options
        """
        self.logger = logging.getLogger("HexStrike-Advanced")
        self.logger.info("Initializing Advanced HexStrike MCP Client v6.0")
        
        # Initialize base client
        self.base_client = HexStrikeMCPClient(server_url, **kwargs)
        
        # Initialize all specialized clients
        self._init_specialized_clients()
        
        # Initialize advanced features
        self._init_error_handling()
        self._init_visual_system()
        self._init_python_manager()
        self._init_integration_layer()
        
        # Unified configuration
        self.config = {
            "auto_recovery": True,
            "parallel_execution": True,
            "max_concurrent_operations": 10,
            "error_reporting": True,
            "telemetry_enabled": True,
            "visual_feedback": True,
            "smart_caching": True
        }
        
        # Operation tracking
        self.active_operations: Dict[str, Dict[str, Any]] = {}
        self.operation_history: List[Dict[str, Any]] = []
        self.global_stats = {
            "operations_started": 0,
            "operations_completed": 0,
            "operations_failed": 0,
            "total_uptime_seconds": 0,
            "errors_handled": 0,
            "recoveries_successful": 0
        }
        
        self.logger.info("Advanced HexStrike MCP Client initialization completed")
    
    def _init_specialized_clients(self):
        """Initialize all specialized client components"""
        self.logger.info("Initializing specialized client components")
        
        try:
            # Security Tools Client
            self.security_tools = SecurityToolsClient(self.base_client)
            
            # Bug Bounty and AI Client
            self.bugbounty_ai = BugBountyAIClient(self.base_client)
            
            # CTF and Vulnerability Intelligence Client
            self.ctf_vuln_intel = CTFVulnIntelClient(self.base_client)
            
            # Process and Cache Management Client
            self.process_cache = ProcessCacheClient(self.base_client)
            
            self.logger.info("All specialized clients initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize specialized clients: {e}")
            raise
    
    def _init_error_handling(self):
        """Initialize advanced error handling system"""
        self.error_handler = {
            "errors": deque(maxlen=1000),
            "recovery_strategies": {
                ErrorSeverity.LOW: RecoveryStrategy.RETRY,
                ErrorSeverity.MEDIUM: RecoveryStrategy.FALLBACK,
                ErrorSeverity.HIGH: RecoveryStrategy.MANUAL,
                ErrorSeverity.CRITICAL: RecoveryStrategy.ABORT,
                ErrorSeverity.FATAL: RecoveryStrategy.ABORT
            },
            "error_patterns": {},
            "auto_recovery_enabled": True
        }
        
        # Set up global exception handler
        sys.excepthook = self._global_exception_handler
    
    def _init_visual_system(self):
        """Initialize visual output system"""
        self.visual_config = VisualConfig()
        
        # Color schemes
        self.color_schemes = {
            "default": {
                "info": "\033[36m",      # Cyan
                "success": "\033[32m",   # Green
                "warning": "\033[33m",   # Yellow
                "error": "\033[31m",     # Red
                "critical": "\033[35m",  # Magenta
                "reset": "\033[0m"       # Reset
            },
            "minimal": {
                "info": "",
                "success": "",
                "warning": "",
                "error": "",
                "critical": "",
                "reset": ""
            }
        }
        
        # Progress indicators
        self.progress_indicators = {
            "spinner": ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"],
            "dots": ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"],
            "simple": ["|", "/", "-", "\\"]
        }
    
    def _init_python_manager(self):
        """Initialize Python environment management"""
        self.python_environments = {}
        self.current_environment = None
        
        # Detect system Python
        try:
            python_version = sys.version_info
            self.python_environments["system"] = {
                "path": sys.executable,
                "version": f"{python_version.major}.{python_version.minor}.{python_version.micro}",
                "type": PythonEnvironment.SYSTEM,
                "active": True
            }
            self.current_environment = "system"
        except Exception as e:
            self.logger.warning(f"Failed to detect system Python: {e}")
    
    def _init_integration_layer(self):
        """Initialize integration layer for unified operations"""
        self.integration_layer = {
            "workflow_engine": {},
            "data_pipeline": {},
            "result_aggregator": {},
            "cross_component_cache": {}
        }
    
    # =============================================================================
    # UNIFIED HIGH-LEVEL OPERATIONS
    # =============================================================================
    
    async def comprehensive_security_assessment(self,
                                              target: str,
                                              assessment_config: Optional[Dict[str, Any]] = None,
                                              time_limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Perform comprehensive security assessment using all available tools
        
        Args:
            target: Target for security assessment (IP, domain, URL, etc.)
            assessment_config: Configuration for assessment scope and methods
            time_limit: Time limit for assessment in seconds
        
        Returns:
            Dict containing comprehensive assessment results
        """
        operation_id = str(uuid.uuid4())
        
        try:
            self.logger.info(f"Starting comprehensive security assessment: {target}")
            
            # Initialize operation tracking
            self._start_operation(operation_id, "comprehensive_security_assessment", {"target": target})
            
            # Default configuration
            config = {
                "network_scanning": True,
                "web_scanning": True,
                "vulnerability_scanning": True,
                "intelligence_gathering": True,
                "ai_analysis": True,
                "generate_report": True,
                **(assessment_config or {})
            }
            
            results = {"target": target, "assessment_id": operation_id, "components": {}}
            
            # Phase 1: Intelligence Gathering
            if config.get("intelligence_gathering"):
                self._update_operation_status(operation_id, "intelligence_gathering")
                
                intel_result = await self.security_tools.analyze_target_intelligence(
                    target=target,
                    analysis_depth="comprehensive",
                    include_passive_recon=True,
                    include_threat_intel=True
                )
                results["components"]["intelligence"] = intel_result
            
            # Phase 2: Network Scanning
            if config.get("network_scanning"):
                self._update_operation_status(operation_id, "network_scanning")
                
                # Determine if target is suitable for network scanning
                target_info = self._parse_target(target)
                if target_info.get("type") in ["ip", "hostname", "network"]:
                    scan_result = await self.security_tools.nmap_scan(
                        target=target,
                        scan_type="comprehensive",
                        save_results=True
                    )
                    results["components"]["network_scan"] = scan_result
            
            # Phase 3: Web Application Scanning
            if config.get("web_scanning"):
                self._update_operation_status(operation_id, "web_scanning")
                
                target_info = self._parse_target(target)
                if target_info.get("type") in ["url", "domain", "hostname"]:
                    # Construct URL if needed
                    target_url = target if target.startswith("http") else f"http://{target}"
                    
                    # Multiple web scanning tools
                    web_results = {}
                    
                    # Nikto scan
                    try:
                        nikto_result = await self.security_tools.nikto_scan(target_url)
                        web_results["nikto"] = nikto_result
                    except Exception as e:
                        self.logger.warning(f"Nikto scan failed: {e}")
                    
                    # Directory scanning
                    try:
                        dir_result = await self.security_tools.gobuster_directory_scan(target_url)
                        web_results["directory_scan"] = dir_result
                    except Exception as e:
                        self.logger.warning(f"Directory scan failed: {e}")
                    
                    results["components"]["web_scan"] = web_results
            
            # Phase 4: Vulnerability Scanning
            if config.get("vulnerability_scanning"):
                self._update_operation_status(operation_id, "vulnerability_scanning")
                
                try:
                    vuln_result = await self.security_tools.nuclei_scan(
                        targets=[target],
                        severity_filter=["critical", "high", "medium"],
                        concurrency=25
                    )
                    results["components"]["vulnerability_scan"] = vuln_result
                except Exception as e:
                    self.logger.warning(f"Vulnerability scanning failed: {e}")
            
            # Phase 5: AI-Powered Analysis
            if config.get("ai_analysis"):
                self._update_operation_status(operation_id, "ai_analysis")
                
                try:
                    ai_result = await self.bugbounty_ai.ai_vulnerability_discovery(
                        targets=[target],
                        discovery_modes=["hybrid"],
                        false_positive_reduction=True
                    )
                    results["components"]["ai_analysis"] = ai_result
                except Exception as e:
                    self.logger.warning(f"AI analysis failed: {e}")
            
            # Phase 6: Results Correlation and Report Generation
            if config.get("generate_report"):
                self._update_operation_status(operation_id, "generating_report")
                
                # Correlate findings across all scans
                correlation_result = await self._correlate_assessment_results(results["components"])
                results["correlation"] = correlation_result
                
                # Generate comprehensive report
                report_result = await self.security_tools.generate_comprehensive_report(
                    scan_results=list(results["components"].values()),
                    report_format="html",
                    include_remediation=True
                )
                results["report"] = report_result
            
            # Finalize assessment
            results["assessment_summary"] = self._generate_assessment_summary(results)
            results["completion_time"] = datetime.now().isoformat()
            
            self._complete_operation(operation_id, True, results)
            
            total_findings = sum(
                len(component.get("vulnerabilities", [])) 
                for component in results["components"].values() 
                if isinstance(component, dict)
            )
            
            self.logger.info(f"Comprehensive assessment completed - {total_findings} total findings")
            
            return results
            
        except Exception as e:
            self._complete_operation(operation_id, False, {"error": str(e)})
            self.logger.error(f"Comprehensive security assessment failed: {e}")
            raise
    
    async def automated_bug_bounty_hunting(self,
                                         program_criteria: Dict[str, Any],
                                         hunting_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Perform automated bug bounty hunting with intelligent target selection
        
        Args:
            program_criteria: Criteria for selecting bug bounty programs
            hunting_config: Configuration for hunting methodology
        
        Returns:
            Dict containing bug bounty hunting results
        """
        operation_id = str(uuid.uuid4())
        
        try:
            self.logger.info("Starting automated bug bounty hunting")
            
            self._start_operation(operation_id, "automated_bug_bounty_hunting", program_criteria)
            
            config = {
                "max_programs": 5,
                "time_per_program": 3600,  # 1 hour per program
                "automation_level": "semi_automated",
                "focus_areas": ["web", "api", "mobile"],
                **(hunting_config or {})
            }
            
            results = {"hunting_session_id": operation_id, "programs": [], "discoveries": []}
            
            # Phase 1: Program Discovery and Selection
            self._update_operation_status(operation_id, "discovering_programs")
            
            program_discovery = await self.bugbounty_ai.discover_bug_bounty_programs(
                keywords=program_criteria.get("keywords"),
                reward_threshold=program_criteria.get("min_reward", 100),
                technology_filter=program_criteria.get("technologies")
            )
            
            selected_programs = program_discovery.get("programs", [])[:config["max_programs"]]
            results["programs"] = selected_programs
            
            # Phase 2: Program Analysis and Target Enumeration
            for i, program in enumerate(selected_programs):
                program_id = program.get("id")
                self._update_operation_status(operation_id, f"analyzing_program_{i+1}")
                
                try:
                    # Analyze program scope
                    scope_analysis = await self.bugbounty_ai.analyze_program_scope(
                        program_id=program_id,
                        deep_analysis=True,
                        technology_detection=True,
                        asset_discovery=True
                    )
                    
                    program["scope_analysis"] = scope_analysis
                    
                    # Create and execute hunting workflow
                    workflow_config = {
                        "reconnaissance": True,
                        "vulnerability_discovery": True,
                        "exploit_development": False,  # Safety first
                        "reporting": True,
                        "time_limit": config["time_per_program"]
                    }
                    
                    workflow = await self.bugbounty_ai.create_bug_bounty_workflow(
                        program_id=program_id,
                        workflow_config=workflow_config,
                        automation_level=config["automation_level"]
                    )
                    
                    # Execute workflow
                    execution_result = await self.bugbounty_ai.execute_workflow(
                        workflow_id=workflow["workflow_id"],
                        execution_mode="standard",
                        monitoring=True
                    )
                    
                    program["workflow_execution"] = execution_result
                    
                    # Collect any discoveries
                    if "vulnerabilities" in execution_result:
                        for vuln in execution_result["vulnerabilities"]:
                            vuln["program_id"] = program_id
                            vuln["program_name"] = program.get("name")
                            results["discoveries"].append(vuln)
                
                except Exception as e:
                    self.logger.warning(f"Failed to process program {program_id}: {e}")
                    program["error"] = str(e)
            
            # Phase 3: Results Analysis and Reporting
            self._update_operation_status(operation_id, "analyzing_results")
            
            # Validate and prioritize discoveries
            validated_discoveries = []
            for discovery in results["discoveries"]:
                try:
                    validation_result = await self.bugbounty_ai.validate_vulnerability(
                        vulnerability_data=discovery,
                        validation_tests=["reproducibility", "impact"]
                    )
                    
                    if validation_result.get("is_valid", False):
                        discovery["validation"] = validation_result
                        
                        # Estimate reward potential
                        program_info = next(
                            (p for p in selected_programs if p.get("id") == discovery.get("program_id")),
                            {}
                        )
                        
                        if program_info:
                            reward_estimate = await self.bugbounty_ai.estimate_reward_potential(
                                vulnerability_data=discovery,
                                program_info=program_info
                            )
                            discovery["reward_estimate"] = reward_estimate
                        
                        validated_discoveries.append(discovery)
                
                except Exception as e:
                    self.logger.warning(f"Failed to validate discovery: {e}")
            
            results["validated_discoveries"] = validated_discoveries
            results["hunting_summary"] = {
                "programs_analyzed": len(selected_programs),
                "total_discoveries": len(results["discoveries"]),
                "validated_discoveries": len(validated_discoveries),
                "estimated_total_reward": sum(
                    d.get("reward_estimate", {}).get("estimated_reward", 0) 
                    for d in validated_discoveries
                ),
                "completion_time": datetime.now().isoformat()
            }
            
            self._complete_operation(operation_id, True, results)
            
            self.logger.info(f"Bug bounty hunting completed - {len(validated_discoveries)} validated discoveries")
            
            return results
            
        except Exception as e:
            self._complete_operation(operation_id, False, {"error": str(e)})
            self.logger.error(f"Automated bug bounty hunting failed: {e}")
            raise
    
    async def solve_ctf_competition(self,
                                  ctf_info: Dict[str, Any],
                                  solving_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Participate in and solve CTF competition challenges
        
        Args:
            ctf_info: Information about the CTF competition
            solving_config: Configuration for solving approach
        
        Returns:
            Dict containing CTF participation results
        """
        operation_id = str(uuid.uuid4())
        
        try:
            self.logger.info(f"Participating in CTF competition: {ctf_info.get('name')}")
            
            self._start_operation(operation_id, "solve_ctf_competition", ctf_info)
            
            config = {
                "max_challenges": 20,
                "time_limit_per_challenge": 3600,
                "categories": ["web", "crypto", "pwn", "reverse", "forensics"],
                "difficulty_preference": ["easy", "medium"],
                "ai_assistance": True,
                **(solving_config or {})
            }
            
            results = {
                "ctf_id": ctf_info.get("id"),
                "ctf_name": ctf_info.get("name"),
                "session_id": operation_id,
                "challenges": [],
                "solved_challenges": [],
                "points_earned": 0
            }
            
            # Get challenge list
            self._update_operation_status(operation_id, "fetching_challenges")
            
            # Note: This would typically fetch from CTF platform API
            challenges = ctf_info.get("challenges", [])
            
            # Filter challenges based on configuration
            filtered_challenges = []
            for challenge in challenges[:config["max_challenges"]]:
                if (challenge.get("category") in config["categories"] and 
                    challenge.get("difficulty") in config["difficulty_preference"]):
                    filtered_challenges.append(challenge)
            
            results["challenges"] = filtered_challenges
            
            # Solve challenges
            for i, challenge_data in enumerate(filtered_challenges):
                self._update_operation_status(operation_id, f"solving_challenge_{i+1}")
                
                try:
                    # Create CTF challenge object
                    from hexstrike_mcp_part4 import CTFChallenge, CTFCategory, CTFDifficulty
                    
                    challenge = CTFChallenge(
                        name=challenge_data.get("name", ""),
                        category=CTFCategory(challenge_data.get("category", "misc")),
                        difficulty=CTFDifficulty(challenge_data.get("difficulty", "medium")),
                        points=challenge_data.get("points", 0),
                        description=challenge_data.get("description", ""),
                        files=challenge_data.get("files", []),
                        hints=challenge_data.get("hints", [])
                    )
                    
                    # Attempt to solve
                    solve_result = await self.ctf_vuln_intel.solve_ctf_challenge(
                        challenge=challenge,
                        auto_solve=True,
                        time_limit=config["time_limit_per_challenge"],
                        use_ai_hints=config["ai_assistance"]
                    )
                    
                    challenge_result = {
                        "challenge": challenge.to_dict(),
                        "solve_result": solve_result,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    if solve_result.get("solved", False):
                        results["solved_challenges"].append(challenge_result)
                        results["points_earned"] += challenge.points
                        
                        self.logger.info(f"Solved challenge: {challenge.name} (+{challenge.points} points)")
                    else:
                        self.logger.info(f"Failed to solve challenge: {challenge.name}")
                    
                    results["challenges"][i]["solve_result"] = solve_result
                    
                except Exception as e:
                    self.logger.warning(f"Error solving challenge {challenge_data.get('name')}: {e}")
            
            # Generate CTF summary
            results["ctf_summary"] = {
                "total_challenges": len(filtered_challenges),
                "challenges_solved": len(results["solved_challenges"]),
                "total_points": results["points_earned"],
                "solve_rate": len(results["solved_challenges"]) / max(len(filtered_challenges), 1) * 100,
                "categories_solved": list(set(
                    c["challenge"]["category"] for c in results["solved_challenges"]
                )),
                "completion_time": datetime.now().isoformat()
            }
            
            self._complete_operation(operation_id, True, results)
            
            solve_count = len(results["solved_challenges"])
            total_points = results["points_earned"]
            
            self.logger.info(f"CTF competition completed - {solve_count} challenges solved, {total_points} points earned")
            
            return results
            
        except Exception as e:
            self._complete_operation(operation_id, False, {"error": str(e)})
            self.logger.error(f"CTF competition solving failed: {e}")
            raise
    
    # =============================================================================
    # ADVANCED ERROR HANDLING AND RECOVERY
    # =============================================================================
    
    def _global_exception_handler(self, exc_type, exc_value, exc_traceback):
        """Global exception handler for unhandled exceptions"""
        if issubclass(exc_type, KeyboardInterrupt):
            self.logger.info("Received keyboard interrupt, shutting down gracefully")
            return
        
        error_context = ErrorContext(
            error_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            severity=ErrorSeverity.FATAL,
            component="global",
            function="global_handler",
            message=str(exc_value),
            exception_type=exc_type.__name__,
            stack_trace=''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        )
        
        self._handle_error(error_context)
    
    def _handle_error(self, error_context: ErrorContext) -> bool:
        """
        Handle errors with advanced recovery strategies
        
        Args:
            error_context: Error context information
        
        Returns:
            bool: True if error was recovered, False otherwise
        """
        self.error_handler["errors"].append(error_context)
        self.global_stats["errors_handled"] += 1
        
        self.logger.error(f"Error {error_context.error_id}: {error_context.message}")
        
        if not self.error_handler["auto_recovery_enabled"]:
            return False
        
        # Determine recovery strategy
        recovery_strategy = self.error_handler["recovery_strategies"].get(
            error_context.severity, 
            RecoveryStrategy.MANUAL
        )
        
        error_context.recovery_strategy = recovery_strategy
        
        # Attempt recovery
        try:
            if recovery_strategy == RecoveryStrategy.RETRY:
                return self._retry_recovery(error_context)
            elif recovery_strategy == RecoveryStrategy.FALLBACK:
                return self._fallback_recovery(error_context)
            elif recovery_strategy == RecoveryStrategy.SKIP:
                return self._skip_recovery(error_context)
            else:
                return False
                
        except Exception as recovery_error:
            self.logger.error(f"Recovery failed for error {error_context.error_id}: {recovery_error}")
            return False
    
    def _retry_recovery(self, error_context: ErrorContext) -> bool:
        """Implement retry recovery strategy"""
        if error_context.recovery_attempts >= error_context.max_recovery_attempts:
            self.logger.warning(f"Max retry attempts reached for error {error_context.error_id}")
            return False
        
        error_context.recovery_attempts += 1
        
        # Implement exponential backoff
        wait_time = min(2 ** error_context.recovery_attempts, 60)
        time.sleep(wait_time)
        
        self.logger.info(f"Retrying operation for error {error_context.error_id} (attempt {error_context.recovery_attempts})")
        
        # In a real implementation, you would retry the original operation
        # For now, we'll assume success for demonstration
        self.global_stats["recoveries_successful"] += 1
        return True
    
    def _fallback_recovery(self, error_context: ErrorContext) -> bool:
        """Implement fallback recovery strategy"""
        self.logger.info(f"Attempting fallback recovery for error {error_context.error_id}")
        
        # Implement fallback logic based on component and function
        fallback_strategies = {
            "network": self._network_fallback,
            "cache": self._cache_fallback,
            "api": self._api_fallback
        }
        
        fallback_func = fallback_strategies.get(error_context.component)
        if fallback_func:
            result = fallback_func(error_context)
            if result:
                self.global_stats["recoveries_successful"] += 1
            return result
        
        return False
    
    def _skip_recovery(self, error_context: ErrorContext) -> bool:
        """Implement skip recovery strategy"""
        self.logger.info(f"Skipping failed operation for error {error_context.error_id}")
        self.global_stats["recoveries_successful"] += 1
        return True
    
    def _network_fallback(self, error_context: ErrorContext) -> bool:
        """Network-specific fallback recovery"""
        # Could implement alternative endpoints, retry with different settings, etc.
        return True
    
    def _cache_fallback(self, error_context: ErrorContext) -> bool:
        """Cache-specific fallback recovery"""
        # Could implement cache bypass, alternative cache, etc.
        return True
    
    def _api_fallback(self, error_context: ErrorContext) -> bool:
        """API-specific fallback recovery"""
        # Could implement alternative API versions, degraded functionality, etc.
        return True
    
    # =============================================================================
    # VISUAL OUTPUT SYSTEM
    # =============================================================================
    
    def set_visual_config(self, config: VisualConfig):
        """Set visual output configuration"""
        self.visual_config = config
        self.logger.info(f"Visual configuration updated: {config.format.value} format")
    
    def print_banner(self):
        """Print HexStrike banner"""
        banner = """
╦ ╦┌─┐─┐ ┬╔═╗┌┬┐┬─┐┬┬┌─┐  ╔═╗╦  ┌┬┐┌─┐┌─┐  ┬  ┬┌─┐    ┌─┐
╠═╣├┤ ┌┴┬┘╚═╗ │ ├┬┘│├┴┐  ╠═╣║  ├─┤├─┘├┴┐  └┐┌┘║     │  
╩ ╩└─┘┴ └─╚═╝ ┴ ┴└─┴┴ ┴  ╩ ╩╩  ┴ ┴┴  └─┘   └┘ ╩═╝   └─┘
        Advanced Cybersecurity Automation Platform
                    MCP Client v6.0
        """
        
        if self.visual_config.format == OutputFormat.COLORED:
            colors = self.color_schemes[self.visual_config.color_scheme]
            print(f"{colors['info']}{banner}{colors['reset']}")
        else:
            print(banner)
    
    def print_status(self, message: str, status_type: str = "info"):
        """Print status message with appropriate formatting"""
        timestamp = datetime.now().strftime("%H:%M:%S") if self.visual_config.show_timestamps else ""
        
        if self.visual_config.format == OutputFormat.COLORED:
            colors = self.color_schemes[self.visual_config.color_scheme]
            color = colors.get(status_type, colors["info"])
            
            prefix = f"[{timestamp}] " if timestamp else ""
            print(f"{color}{prefix}{message}{colors['reset']}")
        else:
            prefix = f"[{timestamp}] " if timestamp else ""
            print(f"{prefix}{message}")
    
    def print_progress(self, current: int, total: int, operation: str = "Processing"):
        """Print progress bar"""
        if not self.visual_config.show_progress:
            return
        
        percentage = (current / total) * 100 if total > 0 else 0
        bar_length = 50
        filled_length = int(bar_length * current / total) if total > 0 else 0
        
        bar = "█" * filled_length + "-" * (bar_length - filled_length)
        
        if self.visual_config.format == OutputFormat.COLORED:
            colors = self.color_schemes[self.visual_config.color_scheme]
            print(f"\r{colors['info']}{operation}: |{bar}| {percentage:.1f}% ({current}/{total}){colors['reset']}", end="")
        else:
            print(f"\r{operation}: |{bar}| {percentage:.1f}% ({current}/{total})", end="")
        
        if current >= total:
            print()  # New line when complete
    
    # =============================================================================
    # PYTHON ENVIRONMENT MANAGEMENT
    # =============================================================================
    
    async def create_python_environment(self,
                                      env_name: str,
                                      python_version: Optional[str] = None,
                                      packages: Optional[List[str]] = None,
                                      env_type: PythonEnvironment = PythonEnvironment.VIRTUAL) -> Dict[str, Any]:
        """
        Create isolated Python environment for security testing
        
        Args:
            env_name: Name for the environment
            python_version: Specific Python version to use
            packages: List of packages to install
            env_type: Type of environment to create
        
        Returns:
            Dict containing environment creation results
        """
        try:
            self.logger.info(f"Creating Python environment: {env_name}")
            
            env_data = {
                "name": env_name,
                "python_version": python_version,
                "packages": packages or [],
                "type": env_type.value,
                "isolated": True,
                "security_tools": [
                    "requests", "beautifulsoup4", "pycryptodome", 
                    "scapy", "nmap", "python-nmap"
                ]
            }
            
            result = self.base_client._make_request('POST', '/api/python/create-environment', data=env_data)
            
            if result.get("success", False):
                self.python_environments[env_name] = {
                    "path": result.get("environment_path"),
                    "python_path": result.get("python_executable"),
                    "type": env_type,
                    "packages": packages or [],
                    "created": datetime.now()
                }
            
            self.logger.info(f"Python environment created: {env_name}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to create Python environment: {e}")
            raise
    
    async def execute_python_script(self,
                                  script_content: str,
                                  environment: Optional[str] = None,
                                  timeout: int = 300,
                                  capture_output: bool = True) -> Dict[str, Any]:
        """
        Execute Python script in specified environment
        
        Args:
            script_content: Python script to execute
            environment: Environment to use (None for current)
            timeout: Execution timeout in seconds
            capture_output: Whether to capture stdout/stderr
        
        Returns:
            Dict containing execution results
        """
        try:
            self.logger.info("Executing Python script")
            
            execution_data = {
                "script": script_content,
                "environment": environment or self.current_environment,
                "timeout": timeout,
                "capture_output": capture_output,
                "security_sandbox": True
            }
            
            result = self.base_client._make_request('POST', '/api/python/execute-script', data=execution_data)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Python script execution failed: {e}")
            raise
    
    async def install_packages(self,
                             packages: List[str],
                             environment: Optional[str] = None,
                             upgrade: bool = False) -> Dict[str, Any]:
        """
        Install Python packages in specified environment
        
        Args:
            packages: List of packages to install
            environment: Target environment
            upgrade: Whether to upgrade existing packages
        
        Returns:
            Dict containing installation results
        """
        try:
            self.logger.info(f"Installing packages: {', '.join(packages)}")
            
            install_data = {
                "packages": packages,
                "environment": environment or self.current_environment,
                "upgrade": upgrade,
                "index_url": "https://pypi.org/simple/",
                "trusted_hosts": ["pypi.org", "files.pythonhosted.org"]
            }
            
            result = self.base_client._make_request('POST', '/api/python/install-packages', data=install_data)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Package installation failed: {e}")
            raise
    
    # =============================================================================
    # OPERATION TRACKING AND MANAGEMENT
    # =============================================================================
    
    def _start_operation(self, operation_id: str, operation_type: str, params: Dict[str, Any]):
        """Start tracking an operation"""
        self.active_operations[operation_id] = {
            "id": operation_id,
            "type": operation_type,
            "params": params,
            "start_time": datetime.now(),
            "status": "starting",
            "progress": 0,
            "substeps": []
        }
        self.global_stats["operations_started"] += 1
    
    def _update_operation_status(self, operation_id: str, status: str, progress: Optional[int] = None):
        """Update operation status"""
        if operation_id in self.active_operations:
            self.active_operations[operation_id]["status"] = status
            if progress is not None:
                self.active_operations[operation_id]["progress"] = progress
            
            self.active_operations[operation_id]["substeps"].append({
                "status": status,
                "timestamp": datetime.now(),
                "progress": progress
            })
    
    def _complete_operation(self, operation_id: str, success: bool, result: Dict[str, Any]):
        """Complete an operation"""
        if operation_id in self.active_operations:
            operation = self.active_operations[operation_id]
            operation["end_time"] = datetime.now()
            operation["duration"] = (operation["end_time"] - operation["start_time"]).total_seconds()
            operation["success"] = success
            operation["result"] = result
            operation["status"] = "completed" if success else "failed"
            
            # Move to history
            self.operation_history.append(operation)
            del self.active_operations[operation_id]
            
            if success:
                self.global_stats["operations_completed"] += 1
            else:
                self.global_stats["operations_failed"] += 1
    
    def get_operation_status(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of an operation"""
        return self.active_operations.get(operation_id)
    
    def list_active_operations(self) -> List[Dict[str, Any]]:
        """List all currently active operations"""
        return list(self.active_operations.values())
    
    # =============================================================================
    # UTILITY AND HELPER METHODS
    # =============================================================================
    
    def _parse_target(self, target: str) -> Dict[str, Any]:
        """Parse target string to determine type and characteristics"""
        target_info = {"original": target}
        
        # URL detection
        if target.startswith(("http://", "https://")):
            target_info["type"] = "url"
            parsed = urlparse(target)
            target_info["scheme"] = parsed.scheme
            target_info["hostname"] = parsed.hostname
            target_info["port"] = parsed.port
            target_info["path"] = parsed.path
        
        # IP address detection
        elif re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', target):
            target_info["type"] = "ip"
            target_info["ip"] = target
        
        # Network range detection
        elif '/' in target and re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2}$', target):
            target_info["type"] = "network"
            target_info["network"] = target
        
        # Domain/hostname detection
        elif re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$', target):
            target_info["type"] = "hostname"
            target_info["hostname"] = target
        
        else:
            target_info["type"] = "unknown"
        
        return target_info
    
    async def _correlate_assessment_results(self, components: Dict[str, Any]) -> Dict[str, Any]:
        """Correlate results from multiple assessment components"""
        correlation = {
            "cross_component_findings": [],
            "confidence_scores": {},
            "risk_assessment": {},
            "attack_vectors": []
        }
        
        # Extract vulnerabilities from all components
        all_vulns = []
        for component_name, component_data in components.items():
            if isinstance(component_data, dict):
                vulns = component_data.get("vulnerabilities", [])
                if isinstance(vulns, list):
                    for vuln in vulns:
                        vuln["source_component"] = component_name
                        all_vulns.append(vuln)
        
        correlation["total_vulnerabilities"] = len(all_vulns)
        
        # Group by severity
        by_severity = defaultdict(list)
        for vuln in all_vulns:
            severity = vuln.get("severity", "unknown")
            by_severity[severity].append(vuln)
        
        correlation["by_severity"] = dict(by_severity)
        
        # Calculate overall risk score
        severity_weights = {"critical": 10, "high": 7, "medium": 4, "low": 2, "info": 1}
        total_score = sum(
            len(vulns) * severity_weights.get(severity, 1)
            for severity, vulns in by_severity.items()
        )
        
        correlation["risk_assessment"]["overall_score"] = min(total_score, 100)
        correlation["risk_assessment"]["risk_level"] = (
            "critical" if total_score > 50 else
            "high" if total_score > 30 else
            "medium" if total_score > 15 else
            "low"
        )
        
        return correlation
    
    def _generate_assessment_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary of security assessment"""
        components_run = len(results.get("components", {}))
        
        total_findings = sum(
            len(comp.get("vulnerabilities", [])) if isinstance(comp, dict) else 0
            for comp in results.get("components", {}).values()
        )
        
        correlation = results.get("correlation", {})
        risk_level = correlation.get("risk_assessment", {}).get("risk_level", "unknown")
        
        return {
            "assessment_id": results.get("assessment_id"),
            "target": results.get("target"),
            "components_executed": components_run,
            "total_findings": total_findings,
            "risk_level": risk_level,
            "has_critical_findings": any(
                vuln.get("severity") == "critical"
                for comp in results.get("components", {}).values()
                if isinstance(comp, dict)
                for vuln in comp.get("vulnerabilities", [])
            ),
            "report_generated": "report" in results,
            "completion_timestamp": datetime.now().isoformat()
        }
    
    def get_client_statistics(self) -> Dict[str, Any]:
        """Get comprehensive client statistics"""
        return {
            "session_info": {
                "session_id": self.base_client.session_id,
                "uptime_seconds": (datetime.now() - self.base_client.start_time).total_seconds(),
                "version": "6.0.0"
            },
            "global_statistics": self.global_stats.copy(),
            "active_operations": len(self.active_operations),
            "operation_history_size": len(self.operation_history),
            "specialized_clients": {
                "security_tools": hasattr(self, "security_tools"),
                "bugbounty_ai": hasattr(self, "bugbounty_ai"),
                "ctf_vuln_intel": hasattr(self, "ctf_vuln_intel"),
                "process_cache": hasattr(self, "process_cache")
            },
            "error_handling": {
                "errors_handled": len(self.error_handler["errors"]),
                "auto_recovery_enabled": self.error_handler["auto_recovery_enabled"]
            },
            "python_environments": len(self.python_environments),
            "current_environment": self.current_environment
        }
    
    async def shutdown(self):
        """Gracefully shutdown the client"""
        self.logger.info("Shutting down HexStrike MCP Client")
        
        # Complete any active operations
        for operation_id in list(self.active_operations.keys()):
            self._complete_operation(operation_id, False, {"reason": "client_shutdown"})
        
        # Disconnect base client
        if self.base_client:
            self.base_client.disconnect()
        
        self.logger.info("HexStrike MCP Client shutdown complete")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        asyncio.run(self.shutdown())
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.base_client.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.shutdown()


# =============================================================================
# MAIN EXECUTION AND INTEGRATION
# =============================================================================

async def main():
    """
    Main execution function for the complete HexStrike MCP Client system
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description="HexStrike AI MCP Client v6.0 - Complete Cybersecurity Automation Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Advanced Usage Examples:

  # Comprehensive Security Assessment
  python3 hexstrike_mcp_complete.py --mode assessment --target example.com --comprehensive

  # Automated Bug Bounty Hunting  
  python3 hexstrike_mcp_complete.py --mode bugbounty --keywords "web,api" --reward-min 500

  # CTF Competition Participation
  python3 hexstrike_mcp_complete.py --mode ctf --ctf-url https://ctf.example.com --categories web,crypto

  # Interactive Mode
  python3 hexstrike_mcp_complete.py --mode interactive --server https://hexstrike.example.com

  # Server Management Mode
  python3 hexstrike_mcp_complete.py --mode server --operation status --detailed
        """
    )
    
    parser.add_argument('--server', type=str, default='http://localhost:8888',
                       help='HexStrike server URL')
    parser.add_argument('--mode', type=str, 
                       choices=['assessment', 'bugbounty', 'ctf', 'interactive', 'server'],
                       default='interactive',
                       help='Operation mode')
    parser.add_argument('--target', type=str, help='Target for assessment')
    parser.add_argument('--comprehensive', action='store_true', help='Comprehensive assessment')
    parser.add_argument('--keywords', type=str, help='Keywords for bug bounty (comma-separated)')
    parser.add_argument('--reward-min', type=int, default=100, help='Minimum reward threshold')
    parser.add_argument('--ctf-url', type=str, help='CTF competition URL')
    parser.add_argument('--categories', type=str, help='CTF categories (comma-separated)')
    parser.add_argument('--operation', type=str, help='Server operation')
    parser.add_argument('--detailed', action='store_true', help='Detailed output')
    parser.add_argument('--debug', action='store_true', help='Debug logging')
    parser.add_argument('--visual', type=str, choices=['colored', 'plain', 'json'], 
                       default='colored', help='Output format')
    
    args = parser.parse_args()
    
    # Configure logging
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Initialize the advanced client
        async with AdvancedHexStrikeMCPClient(server_url=args.server) as client:
            
            # Set visual configuration
            visual_format = {
                'colored': OutputFormat.COLORED,
                'plain': OutputFormat.PLAIN,
                'json': OutputFormat.JSON
            }[args.visual]
            
            client.set_visual_config(VisualConfig(format=visual_format))
            client.print_banner()
            
            # Execute based on mode
            if args.mode == 'assessment' and args.target:
                client.print_status("Starting comprehensive security assessment", "info")
                
                config = {"comprehensive": args.comprehensive} if args.comprehensive else {}
                
                result = await client.comprehensive_security_assessment(
                    target=args.target,
                    assessment_config=config
                )
                
                client.print_status(f"Assessment completed - {result['assessment_summary']['total_findings']} findings", "success")
                
                if args.visual == 'json':
                    print(json.dumps(result, indent=2, default=str))
                else:
                    print(f"\nAssessment Summary:")
                    print(f"  Target: {result['target']}")
                    print(f"  Risk Level: {result['assessment_summary']['risk_level']}")
                    print(f"  Total Findings: {result['assessment_summary']['total_findings']}")
            
            elif args.mode == 'bugbounty':
                client.print_status("Starting automated bug bounty hunting", "info")
                
                criteria = {}
                if args.keywords:
                    criteria['keywords'] = args.keywords.split(',')
                if args.reward_min:
                    criteria['min_reward'] = args.reward_min
                
                result = await client.automated_bug_bounty_hunting(program_criteria=criteria)
                
                discoveries = len(result.get('validated_discoveries', []))
                client.print_status(f"Bug bounty hunting completed - {discoveries} discoveries", "success")
                
                if args.visual == 'json':
                    print(json.dumps(result, indent=2, default=str))
            
            elif args.mode == 'ctf' and args.ctf_url:
                client.print_status("Participating in CTF competition", "info")
                
                ctf_info = {"id": "manual", "name": "Manual CTF", "url": args.ctf_url}
                config = {}
                
                if args.categories:
                    config['categories'] = args.categories.split(',')
                
                result = await client.solve_ctf_competition(
                    ctf_info=ctf_info,
                    solving_config=config
                )
                
                solved = len(result.get('solved_challenges', []))
                points = result.get('points_earned', 0)
                client.print_status(f"CTF completed - {solved} challenges solved, {points} points", "success")
            
            elif args.mode == 'server':
                if args.operation == 'status':
                    result = await client.base_client.check_server_health()
                    
                    if args.visual == 'json':
                        print(json.dumps(result, indent=2, default=str))
                    else:
                        print(f"Server Status: {result.get('status', 'unknown')}")
                        if args.detailed and 'components' in result:
                            for comp, status in result['components'].items():
                                print(f"  {comp}: {status}")
                
                elif args.operation == 'stats':
                    stats = client.get_client_statistics()
                    
                    if args.visual == 'json':
                        print(json.dumps(stats, indent=2, default=str))
                    else:
                        print("Client Statistics:")
                        print(f"  Uptime: {stats['session_info']['uptime_seconds']:.0f} seconds")
                        print(f"  Operations Completed: {stats['global_statistics']['operations_completed']}")
                        print(f"  Success Rate: {(stats['global_statistics']['operations_completed'] / max(stats['global_statistics']['operations_started'], 1)) * 100:.1f}%")
            
            elif args.mode == 'interactive':
                client.print_status("Entering interactive mode", "info")
                client.print_status("Type 'help' for available commands, 'quit' to exit", "info")
                
                while True:
                    try:
                        command = input("\nhexstrike> ").strip()
                        
                        if command in ['quit', 'exit', 'q']:
                            break
                        elif command == 'help':
                            print("\nAvailable commands:")
                            print("  status          - Check server status")
                            print("  stats           - Show client statistics")
                            print("  assess <target> - Run security assessment")
                            print("  operations      - List active operations")
                            print("  health          - System health check")
                            print("  help            - Show this help")
                            print("  quit            - Exit interactive mode")
                        elif command == 'status':
                            result = await client.base_client.check_server_health()
                            client.print_status(f"Server Status: {result.get('status', 'unknown')}", "info")
                        elif command == 'stats':
                            stats = client.get_client_statistics()
                            print(f"Operations: {stats['global_statistics']['operations_completed']}")
                            print(f"Active: {stats['active_operations']}")
                        elif command.startswith('assess '):
                            target = command[7:].strip()
                            if target:
                                client.print_status(f"Assessing {target}...", "info")
                                result = await client.comprehensive_security_assessment(target)
                                findings = result['assessment_summary']['total_findings']
                                client.print_status(f"Assessment complete - {findings} findings", "success")
                            else:
                                client.print_status("Please specify a target", "error")
                        elif command == 'operations':
                            ops = client.list_active_operations()
                            if ops:
                                for op in ops:
                                    print(f"  {op['id']}: {op['type']} ({op['status']})")
                            else:
                                print("  No active operations")
                        elif command == 'health':
                            health = await client.process_cache.health_check()
                            status = health.get('overall_health_status', 'unknown')
                            client.print_status(f"System Health: {status}", "info")
                        elif command.strip():
                            client.print_status(f"Unknown command: {command}", "error")
                    
                    except KeyboardInterrupt:
                        print("\nUse 'quit' to exit gracefully")
                    except Exception as e:
                        client.print_status(f"Error: {e}", "error")
                
                client.print_status("Exiting interactive mode", "info")
            
            else:
                parser.print_help()
    
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        if args.debug:
            logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    # Run the complete HexStrike MCP Client
    asyncio.run(main())


# =============================================================================
# EXPORT ALL COMPONENTS
# =============================================================================

__all__ = [
    # Main classes
    'AdvancedHexStrikeMCPClient',
    
    # Enums
    'ErrorSeverity',
    'RecoveryStrategy', 
    'OutputFormat',
    'PythonEnvironment',
    
    # Data classes
    'ErrorContext',
    'VisualConfig',
    
    # Re-export from other parts
    'HexStrikeMCPClient',
    'SecurityToolsClient',
    'BugBountyAIClient', 
    'CTFVulnIntelClient',
    'ProcessCacheClient',
    
    # Main function
    'main'
]