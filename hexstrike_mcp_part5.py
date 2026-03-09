#!/usr/bin/env python3
"""
HexStrike AI MCP Client v6.0 - Advanced Cybersecurity Automation Platform
Part 5 of 6: Process Management and Caching System Endpoints

This part focuses on advanced process management, resource monitoring, intelligent
caching systems, performance optimization, and comprehensive system telemetry.
It provides enterprise-grade process orchestration and resource management capabilities.

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
from concurrent.futures import ThreadPoolExecutor, Future
import sqlite3
import pickle
import psutil
import signal
import os
import resource
import platform
import gc
import weakref
from contextlib import contextmanager
import traceback

# Configure logger for this module
logger = logging.getLogger("HexStrike-MCP-Process-Cache")

class ProcessState(Enum):
    """Process execution states"""
    PENDING = "pending"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    COMPLETED = "completed"
    FAILED = "failed"
    KILLED = "killed"
    TIMEOUT = "timeout"

class ProcessPriority(Enum):
    """Process priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"

class ResourceType(Enum):
    """System resource types"""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    GPU = "gpu"
    FILE_DESCRIPTORS = "file_descriptors"

class CacheStrategy(Enum):
    """Cache eviction strategies"""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    FIFO = "fifo"  # First In First Out
    TTL = "ttl"  # Time To Live
    ADAPTIVE = "adaptive"  # Adaptive based on usage patterns

class MonitoringLevel(Enum):
    """Resource monitoring detail levels"""
    BASIC = "basic"
    DETAILED = "detailed"
    COMPREHENSIVE = "comprehensive"
    REAL_TIME = "real_time"

@dataclass
class ProcessConfig:
    """Process configuration and execution parameters"""
    command: str
    args: List[str] = field(default_factory=list)
    working_directory: Optional[str] = None
    environment: Dict[str, str] = field(default_factory=dict)
    timeout: Optional[int] = None
    priority: ProcessPriority = ProcessPriority.NORMAL
    resource_limits: Dict[str, Any] = field(default_factory=dict)
    capture_output: bool = True
    stream_output: bool = False
    auto_restart: bool = False
    max_restarts: int = 3
    health_check: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API requests"""
        data = {}
        for key, value in self.__dict__.items():
            if isinstance(value, Enum):
                data[key] = value.value
            else:
                data[key] = value
        return data

@dataclass
class ProcessInfo:
    """Process information and status"""
    process_id: str
    pid: Optional[int] = None
    command: str = ""
    state: ProcessState = ProcessState.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    exit_code: Optional[int] = None
    cpu_usage: float = 0.0
    memory_usage: int = 0
    output: str = ""
    error: str = ""
    resource_usage: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
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
class ResourceQuota:
    """Resource quota and limits"""
    cpu_percent: Optional[float] = None
    memory_bytes: Optional[int] = None
    disk_bytes: Optional[int] = None
    network_bytes_per_sec: Optional[int] = None
    file_descriptors: Optional[int] = None
    execution_time_seconds: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {k: v for k, v in self.__dict__.items() if v is not None}

@dataclass
class CacheConfig:
    """Cache configuration parameters"""
    max_size: int = 1000
    ttl_seconds: int = 3600
    strategy: CacheStrategy = CacheStrategy.LRU
    compression: bool = False
    persistence: bool = False
    auto_cleanup: bool = True
    hit_ratio_threshold: float = 0.8
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = {}
        for key, value in self.__dict__.items():
            if isinstance(value, Enum):
                data[key] = value.value
            else:
                data[key] = value
        return data

class ProcessCacheClient:
    """
    Advanced Process Management and Caching Client Extension for HexStrike MCP Client
    
    This class provides comprehensive process orchestration, resource monitoring,
    intelligent caching, performance optimization, and system telemetry capabilities.
    """
    
    def __init__(self, base_client):
        """
        Initialize Process Management and Caching Client
        
        Args:
            base_client: Instance of HexStrikeMCPClient
        """
        self.client = base_client
        self.logger = logging.getLogger(f"ProcessCache-{base_client.session_id[:8]}")
        
        # Initialize process management
        self._init_process_manager()
        self._init_resource_monitor()
        self._init_cache_manager()
        
        # Local process tracking
        self.active_processes: Dict[str, ProcessInfo] = {}
        self.process_history: List[ProcessInfo] = []
        self.resource_metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # Performance tracking
        self.performance_stats = {
            "processes_started": 0,
            "processes_completed": 0,
            "processes_failed": 0,
            "total_cpu_time": 0.0,
            "total_memory_used": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        
        self.logger.info("Process Management and Caching Client initialized")
    
    def _init_process_manager(self):
        """Initialize process management subsystem"""
        self.process_pools = {
            "critical": {"max_workers": 2, "active": 0},
            "high": {"max_workers": 4, "active": 0},
            "normal": {"max_workers": 8, "active": 0},
            "low": {"max_workers": 16, "active": 0},
            "background": {"max_workers": 32, "active": 0}
        }
        
        self.process_queues = {
            ProcessPriority.CRITICAL: deque(),
            ProcessPriority.HIGH: deque(),
            ProcessPriority.NORMAL: deque(),
            ProcessPriority.LOW: deque(),
            ProcessPriority.BACKGROUND: deque()
        }
        
        self.resource_quotas = {
            "default": ResourceQuota(
                cpu_percent=80.0,
                memory_bytes=1024 * 1024 * 1024,  # 1GB
                execution_time_seconds=3600  # 1 hour
            )
        }
    
    def _init_resource_monitor(self):
        """Initialize resource monitoring subsystem"""
        self.monitoring_config = {
            "interval_seconds": 5,
            "history_retention_hours": 24,
            "alert_thresholds": {
                "cpu_percent": 90.0,
                "memory_percent": 85.0,
                "disk_percent": 90.0,
                "network_utilization": 80.0
            },
            "auto_scaling": {
                "enabled": True,
                "cpu_scale_threshold": 80.0,
                "memory_scale_threshold": 75.0
            }
        }
        
        self.system_info = {
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "disk_total": sum(partition.total for partition in psutil.disk_usage('/') if hasattr(partition, 'total')),
            "platform": platform.platform(),
            "architecture": platform.architecture()[0]
        }
    
    def _init_cache_manager(self):
        """Initialize cache management subsystem"""
        self.cache_configs = {
            "command_results": CacheConfig(
                max_size=500,
                ttl_seconds=1800,
                strategy=CacheStrategy.LRU,
                compression=True
            ),
            "scan_results": CacheConfig(
                max_size=200,
                ttl_seconds=3600,
                strategy=CacheStrategy.ADAPTIVE,
                compression=True
            ),
            "intelligence_data": CacheConfig(
                max_size=1000,
                ttl_seconds=7200,
                strategy=CacheStrategy.TTL,
                persistence=True
            ),
            "temporary_files": CacheConfig(
                max_size=100,
                ttl_seconds=900,
                strategy=CacheStrategy.FIFO,
                auto_cleanup=True
            )
        }
        
        self.cache_metrics = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "evictions": 0,
            "storage_size_bytes": 0
        }
    
    # =============================================================================
    # PROCESS MANAGEMENT ENDPOINTS
    # =============================================================================
    
    async def start_process(self,
                          config: ProcessConfig,
                          process_group: Optional[str] = None,
                          dependencies: Optional[List[str]] = None,
                          scheduling_policy: str = "immediate") -> Dict[str, Any]:
        """
        Start a new process with comprehensive configuration and monitoring
        
        Args:
            config: Process configuration parameters
            process_group: Optional process group for batch management
            dependencies: List of process IDs this process depends on
            scheduling_policy: Scheduling policy (immediate, queued, conditional)
        
        Returns:
            Dict containing process startup results and monitoring information
        """
        try:
            self.logger.info(f"Starting process: {config.command}")
            
            process_data = {
                "config": config.to_dict(),
                "process_group": process_group,
                "dependencies": dependencies or [],
                "scheduling_policy": scheduling_policy,
                "resource_quotas": self.resource_quotas.get("default", ResourceQuota()).to_dict(),
                "monitoring_enabled": True,
                "auto_scaling": self.monitoring_config["auto_scaling"]["enabled"]
            }
            
            result = self.client._make_request('POST', '/api/processes/start', data=process_data)
            
            process_id = result.get('process_id')
            pid = result.get('pid')
            state = result.get('state', 'starting')
            
            self.logger.info(f"Process started - ID: {process_id}, PID: {pid}, State: {state}")
            
            # Track locally
            if process_id:
                process_info = ProcessInfo(
                    process_id=process_id,
                    pid=pid,
                    command=config.command,
                    state=ProcessState(state),
                    start_time=datetime.now()
                )
                self.active_processes[process_id] = process_info
                self.performance_stats["processes_started"] += 1
            
            return result
            
        except Exception as e:
            self.logger.error(f"Process start failed: {e}")
            raise
    
    async def get_process_status(self,
                               process_id: str,
                               include_metrics: bool = True,
                               include_output: bool = False) -> Dict[str, Any]:
        """
        Get comprehensive status information for a running process
        
        Args:
            process_id: Process identifier
            include_metrics: Include resource usage metrics
            include_output: Include process output/logs
        
        Returns:
            Dict containing detailed process status information
        """
        try:
            self.logger.debug(f"Getting status for process: {process_id}")
            
            params = {
                "include_metrics": include_metrics,
                "include_output": include_output,
                "metric_history": True
            }
            
            result = self.client._make_request('GET', f'/api/processes/{process_id}/status', params=params)
            
            # Update local tracking
            if process_id in self.active_processes:
                local_info = self.active_processes[process_id]
                local_info.state = ProcessState(result.get('state', 'unknown'))
                local_info.cpu_usage = result.get('cpu_usage', 0.0)
                local_info.memory_usage = result.get('memory_usage', 0)
                
                if result.get('state') in ['completed', 'failed', 'killed']:
                    local_info.end_time = datetime.now()
                    local_info.exit_code = result.get('exit_code')
                    
                    # Move to history
                    self.process_history.append(local_info)
                    del self.active_processes[process_id]
                    
                    if result.get('state') == 'completed':
                        self.performance_stats["processes_completed"] += 1
                    else:
                        self.performance_stats["processes_failed"] += 1
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to get process status: {e}")
            raise
    
    async def list_processes(self,
                           filter_criteria: Optional[Dict[str, Any]] = None,
                           include_metrics: bool = False,
                           sort_by: str = "start_time",
                           limit: Optional[int] = None) -> Dict[str, Any]:
        """
        List all processes with optional filtering and sorting
        
        Args:
            filter_criteria: Criteria to filter processes
            include_metrics: Include resource metrics for each process
            sort_by: Field to sort by (start_time, cpu_usage, memory_usage, state)
            limit: Maximum number of processes to return
        
        Returns:
            Dict containing list of processes and summary statistics
        """
        try:
            self.logger.info("Listing processes")
            
            params = {
                "filter": filter_criteria or {},
                "include_metrics": include_metrics,
                "sort_by": sort_by,
                "limit": limit
            }
            
            result = self.client._make_request('GET', '/api/processes', params=params)
            
            process_count = len(result.get('processes', []))
            active_count = len([p for p in result.get('processes', []) if p.get('state') == 'running'])
            
            self.logger.info(f"Retrieved {process_count} processes ({active_count} active)")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to list processes: {e}")
            raise
    
    async def terminate_process(self,
                              process_id: str,
                              signal_type: str = "SIGTERM",
                              timeout: int = 30,
                              force_kill: bool = True) -> Dict[str, Any]:
        """
        Terminate a running process with graceful shutdown options
        
        Args:
            process_id: Process identifier
            signal_type: Signal to send (SIGTERM, SIGKILL, SIGINT, SIGUSR1, etc.)
            timeout: Timeout before force kill
            force_kill: Whether to force kill after timeout
        
        Returns:
            Dict containing termination results
        """
        try:
            self.logger.info(f"Terminating process {process_id} with {signal_type}")
            
            termination_data = {
                "signal": signal_type,
                "timeout": timeout,
                "force_kill": force_kill,
                "cleanup_resources": True,
                "notify_dependents": True
            }
            
            result = self.client._make_request('DELETE', f'/api/processes/{process_id}', data=termination_data)
            
            success = result.get('terminated', False)
            exit_code = result.get('exit_code')
            
            self.logger.info(f"Process termination {'successful' if success else 'failed'} - Exit code: {exit_code}")
            
            # Update local tracking
            if process_id in self.active_processes and success:
                process_info = self.active_processes[process_id]
                process_info.state = ProcessState.KILLED
                process_info.end_time = datetime.now()
                process_info.exit_code = exit_code
                
                self.process_history.append(process_info)
                del self.active_processes[process_id]
            
            return result
            
        except Exception as e:
            self.logger.error(f"Process termination failed: {e}")
            raise
    
    async def pause_process(self, process_id: str) -> Dict[str, Any]:
        """
        Pause a running process
        
        Args:
            process_id: Process identifier
        
        Returns:
            Dict containing pause operation results
        """
        try:
            self.logger.info(f"Pausing process: {process_id}")
            
            result = self.client._make_request('POST', f'/api/processes/{process_id}/pause')
            
            # Update local state
            if process_id in self.active_processes:
                self.active_processes[process_id].state = ProcessState.PAUSED
            
            return result
            
        except Exception as e:
            self.logger.error(f"Process pause failed: {e}")
            raise
    
    async def resume_process(self, process_id: str) -> Dict[str, Any]:
        """
        Resume a paused process
        
        Args:
            process_id: Process identifier
        
        Returns:
            Dict containing resume operation results
        """
        try:
            self.logger.info(f"Resuming process: {process_id}")
            
            result = self.client._make_request('POST', f'/api/processes/{process_id}/resume')
            
            # Update local state
            if process_id in self.active_processes:
                self.active_processes[process_id].state = ProcessState.RUNNING
            
            return result
            
        except Exception as e:
            self.logger.error(f"Process resume failed: {e}")
            raise
    
    async def get_process_output(self,
                               process_id: str,
                               stream_type: str = "both",
                               lines: Optional[int] = None,
                               follow: bool = False) -> Dict[str, Any]:
        """
        Get output from a running or completed process
        
        Args:
            process_id: Process identifier
            stream_type: Output stream (stdout, stderr, both)
            lines: Number of lines to retrieve (None for all)
            follow: Follow output in real-time
        
        Returns:
            Dict containing process output
        """
        try:
            self.logger.debug(f"Getting output for process: {process_id}")
            
            params = {
                "stream": stream_type,
                "lines": lines,
                "follow": follow
            }
            
            result = self.client._make_request('GET', f'/api/processes/{process_id}/output', params=params)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to get process output: {e}")
            raise
    
    # =============================================================================
    # RESOURCE MONITORING AND MANAGEMENT
    # =============================================================================
    
    async def get_system_resources(self,
                                 resource_types: Optional[List[ResourceType]] = None,
                                 include_history: bool = False,
                                 time_range: Optional[Tuple[datetime, datetime]] = None) -> Dict[str, Any]:
        """
        Get comprehensive system resource information
        
        Args:
            resource_types: Specific resource types to retrieve
            include_history: Include historical resource data
            time_range: Time range for historical data
        
        Returns:
            Dict containing system resource information
        """
        try:
            self.logger.info("Getting system resource information")
            
            resource_data = {
                "resource_types": [r.value for r in (resource_types or list(ResourceType))],
                "include_history": include_history,
                "time_range": {
                    "start": time_range[0].isoformat() if time_range and time_range[0] else None,
                    "end": time_range[1].isoformat() if time_range and time_range[1] else None
                } if time_range else None,
                "include_predictions": True,
                "granularity": "detailed"
            }
            
            result = self.client._make_request('POST', '/api/processes/resources', data=resource_data)
            
            cpu_usage = result.get('cpu_usage_percent', 0)
            memory_usage = result.get('memory_usage_percent', 0)
            
            self.logger.info(f"System resources - CPU: {cpu_usage}%, Memory: {memory_usage}%")
            
            # Store metrics locally
            timestamp = datetime.now()
            self.resource_metrics['cpu_percent'].append((timestamp, cpu_usage))
            self.resource_metrics['memory_percent'].append((timestamp, memory_usage))
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to get system resources: {e}")
            raise
    
    async def monitor_resource_usage(self,
                                   process_ids: Optional[List[str]] = None,
                                   monitoring_duration: int = 3600,
                                   sampling_interval: int = 10,
                                   alert_thresholds: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """
        Start comprehensive resource monitoring for processes
        
        Args:
            process_ids: Specific processes to monitor (None for all)
            monitoring_duration: Duration to monitor in seconds
            sampling_interval: Interval between samples in seconds
            alert_thresholds: Custom alert thresholds
        
        Returns:
            Dict containing monitoring setup results
        """
        try:
            self.logger.info(f"Starting resource monitoring for {len(process_ids) if process_ids else 'all'} processes")
            
            monitoring_data = {
                "process_ids": process_ids,
                "duration_seconds": monitoring_duration,
                "interval_seconds": sampling_interval,
                "thresholds": alert_thresholds or self.monitoring_config["alert_thresholds"],
                "enable_alerts": True,
                "auto_scaling": True,
                "detailed_metrics": True
            }
            
            result = self.client._make_request('POST', '/api/processes/monitor', data=monitoring_data)
            
            monitoring_id = result.get('monitoring_id')
            processes_monitored = len(result.get('monitored_processes', []))
            
            self.logger.info(f"Resource monitoring started - ID: {monitoring_id}, Processes: {processes_monitored}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Resource monitoring setup failed: {e}")
            raise
    
    async def get_performance_metrics(self,
                                    metric_types: Optional[List[str]] = None,
                                    aggregation_level: str = "detailed",
                                    time_period: str = "last_hour") -> Dict[str, Any]:
        """
        Get comprehensive performance metrics and analytics
        
        Args:
            metric_types: Specific metrics to retrieve
            aggregation_level: Level of aggregation (summary, detailed, raw)
            time_period: Time period for metrics (last_hour, last_day, last_week)
        
        Returns:
            Dict containing performance metrics
        """
        try:
            self.logger.info(f"Getting performance metrics for {time_period}")
            
            metrics_data = {
                "metric_types": metric_types or ["cpu", "memory", "disk", "network", "processes"],
                "aggregation": aggregation_level,
                "period": time_period,
                "include_trends": True,
                "include_anomalies": True,
                "include_predictions": True
            }
            
            result = self.client._make_request('POST', '/api/processes/metrics', data=metrics_data)
            
            # Add local performance stats
            result['local_stats'] = self.performance_stats.copy()
            result['active_processes'] = len(self.active_processes)
            result['process_history_size'] = len(self.process_history)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to get performance metrics: {e}")
            raise
    
    async def optimize_resource_allocation(self,
                                         optimization_goals: Optional[List[str]] = None,
                                         constraints: Optional[Dict[str, Any]] = None,
                                         auto_apply: bool = False) -> Dict[str, Any]:
        """
        Optimize resource allocation across running processes
        
        Args:
            optimization_goals: Optimization objectives (performance, efficiency, cost)
            constraints: Resource constraints to consider
            auto_apply: Automatically apply optimizations
        
        Returns:
            Dict containing optimization recommendations and results
        """
        try:
            self.logger.info("Optimizing resource allocation")
            
            optimization_data = {
                "goals": optimization_goals or ["performance", "efficiency"],
                "constraints": constraints or {},
                "auto_apply": auto_apply,
                "consider_priorities": True,
                "machine_learning": True,
                "simulation_mode": not auto_apply
            }
            
            result = self.client._make_request('POST', '/api/processes/optimize', data=optimization_data)
            
            optimizations_found = len(result.get('optimizations', []))
            estimated_improvement = result.get('estimated_improvement_percent', 0)
            
            self.logger.info(f"Resource optimization completed - {optimizations_found} optimizations found ({estimated_improvement}% improvement)")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Resource optimization failed: {e}")
            raise
    
    # =============================================================================
    # INTELLIGENT CACHING SYSTEM
    # =============================================================================
    
    async def get_cache_statistics(self,
                                 cache_names: Optional[List[str]] = None,
                                 include_detailed_metrics: bool = True) -> Dict[str, Any]:
        """
        Get comprehensive cache statistics and performance metrics
        
        Args:
            cache_names: Specific caches to analyze
            include_detailed_metrics: Include detailed performance metrics
        
        Returns:
            Dict containing cache statistics and analysis
        """
        try:
            self.logger.info("Getting cache statistics")
            
            stats_data = {
                "cache_names": cache_names,
                "detailed_metrics": include_detailed_metrics,
                "include_trends": True,
                "include_efficiency_analysis": True,
                "optimization_suggestions": True
            }
            
            result = self.client._make_request('POST', '/api/cache/statistics', data=stats_data)
            
            # Add local cache metrics
            total_requests = self.cache_metrics["total_requests"]
            hit_rate = (self.cache_metrics["cache_hits"] / max(total_requests, 1)) * 100
            
            result['local_metrics'] = {
                **self.cache_metrics,
                "hit_rate_percent": hit_rate
            }
            
            self.logger.info(f"Cache hit rate: {hit_rate:.2f}%")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to get cache statistics: {e}")
            raise
    
    async def manage_cache_entries(self,
                                 operation: str,
                                 cache_name: str,
                                 keys: Optional[List[str]] = None,
                                 filter_criteria: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Manage cache entries with various operations
        
        Args:
            operation: Operation to perform (list, get, delete, clear, refresh)
            cache_name: Name of cache to operate on
            keys: Specific keys to operate on
            filter_criteria: Criteria for filtering cache entries
        
        Returns:
            Dict containing operation results
        """
        try:
            self.logger.info(f"Managing cache entries - Operation: {operation}, Cache: {cache_name}")
            
            management_data = {
                "operation": operation,
                "cache_name": cache_name,
                "keys": keys,
                "filter": filter_criteria or {},
                "batch_size": 100,
                "preserve_hot_data": True
            }
            
            result = self.client._make_request('POST', '/api/cache/manage', data=management_data)
            
            affected_entries = result.get('affected_entries', 0)
            
            self.logger.info(f"Cache management completed - {affected_entries} entries affected")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Cache management failed: {e}")
            raise
    
    async def optimize_cache_configuration(self,
                                         cache_name: str,
                                         usage_patterns: Optional[Dict[str, Any]] = None,
                                         performance_goals: Optional[List[str]] = None,
                                         auto_apply: bool = False) -> Dict[str, Any]:
        """
        Optimize cache configuration based on usage patterns
        
        Args:
            cache_name: Name of cache to optimize
            usage_patterns: Historical usage pattern data
            performance_goals: Performance optimization goals
            auto_apply: Automatically apply optimizations
        
        Returns:
            Dict containing optimization recommendations
        """
        try:
            self.logger.info(f"Optimizing cache configuration: {cache_name}")
            
            optimization_data = {
                "cache_name": cache_name,
                "usage_patterns": usage_patterns or {},
                "goals": performance_goals or ["hit_rate", "memory_efficiency", "response_time"],
                "auto_apply": auto_apply,
                "machine_learning_analysis": True,
                "predictive_scaling": True
            }
            
            result = self.client._make_request('POST', '/api/cache/optimize', data=optimization_data)
            
            recommendations = len(result.get('recommendations', []))
            expected_improvement = result.get('expected_improvement_percent', 0)
            
            self.logger.info(f"Cache optimization completed - {recommendations} recommendations ({expected_improvement}% improvement expected)")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Cache optimization failed: {e}")
            raise
    
    async def setup_cache_replication(self,
                                    primary_cache: str,
                                    replica_configs: List[Dict[str, Any]],
                                    replication_strategy: str = "async") -> Dict[str, Any]:
        """
        Setup cache replication for high availability
        
        Args:
            primary_cache: Name of primary cache
            replica_configs: Configuration for replica caches
            replication_strategy: Replication strategy (sync, async, eventual_consistency)
        
        Returns:
            Dict containing replication setup results
        """
        try:
            self.logger.info(f"Setting up cache replication for {primary_cache}")
            
            replication_data = {
                "primary_cache": primary_cache,
                "replicas": replica_configs,
                "strategy": replication_strategy,
                "consistency_level": "strong" if replication_strategy == "sync" else "eventual",
                "failover_enabled": True,
                "monitoring_enabled": True
            }
            
            result = self.client._make_request('POST', '/api/cache/setup-replication', data=replication_data)
            
            replicas_configured = len(result.get('configured_replicas', []))
            
            self.logger.info(f"Cache replication setup completed - {replicas_configured} replicas configured")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Cache replication setup failed: {e}")
            raise
    
    # =============================================================================
    # ADVANCED TELEMETRY AND ANALYTICS
    # =============================================================================
    
    async def get_telemetry_data(self,
                               data_types: Optional[List[str]] = None,
                               time_range: Optional[Tuple[datetime, datetime]] = None,
                               aggregation_level: str = "detailed") -> Dict[str, Any]:
        """
        Get comprehensive telemetry data from all system components
        
        Args:
            data_types: Types of telemetry data to collect
            time_range: Time range for data collection
            aggregation_level: Level of data aggregation
        
        Returns:
            Dict containing comprehensive telemetry data
        """
        try:
            self.logger.info("Collecting telemetry data")
            
            telemetry_data = {
                "types": data_types or ["performance", "resources", "processes", "cache", "errors"],
                "time_range": {
                    "start": time_range[0].isoformat() if time_range and time_range[0] else None,
                    "end": time_range[1].isoformat() if time_range and time_range[1] else None
                } if time_range else None,
                "aggregation": aggregation_level,
                "include_anomalies": True,
                "correlation_analysis": True
            }
            
            result = self.client._make_request('POST', '/api/telemetry', data=telemetry_data)
            
            # Add local telemetry
            result['local_telemetry'] = {
                "client_uptime_seconds": (datetime.now() - self.client.start_time).total_seconds(),
                "active_processes": len(self.active_processes),
                "process_success_rate": self._calculate_success_rate(),
                "resource_efficiency": self._calculate_resource_efficiency(),
                "cache_performance": self._calculate_cache_performance()
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Telemetry data collection failed: {e}")
            raise
    
    async def generate_performance_report(self,
                                        report_type: str = "comprehensive",
                                        time_period: str = "last_24_hours",
                                        include_recommendations: bool = True,
                                        output_format: str = "json") -> Dict[str, Any]:
        """
        Generate comprehensive performance analysis report
        
        Args:
            report_type: Type of report (summary, detailed, comprehensive)
            time_period: Time period to analyze
            include_recommendations: Include optimization recommendations
            output_format: Output format (json, html, pdf)
        
        Returns:
            Dict containing performance report
        """
        try:
            self.logger.info(f"Generating {report_type} performance report for {time_period}")
            
            report_data = {
                "type": report_type,
                "period": time_period,
                "include_recommendations": include_recommendations,
                "format": output_format,
                "include_trends": True,
                "include_comparisons": True,
                "include_predictions": True,
                "ai_analysis": True
            }
            
            result = self.client._make_request('POST', '/api/telemetry/generate-report', data=report_data)
            
            report_id = result.get('report_id')
            sections = len(result.get('sections', []))
            
            self.logger.info(f"Performance report generated - ID: {report_id}, Sections: {sections}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Performance report generation failed: {e}")
            raise
    
    async def setup_alerting_rules(self,
                                 alert_rules: List[Dict[str, Any]],
                                 notification_channels: List[str],
                                 escalation_policy: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Setup intelligent alerting rules for system monitoring
        
        Args:
            alert_rules: List of alerting rules to configure
            notification_channels: Channels for alert notifications
            escalation_policy: Policy for alert escalation
        
        Returns:
            Dict containing alerting setup results
        """
        try:
            self.logger.info(f"Setting up {len(alert_rules)} alerting rules")
            
            alerting_data = {
                "rules": alert_rules,
                "channels": notification_channels,
                "escalation": escalation_policy or {},
                "smart_filtering": True,
                "correlation_analysis": True,
                "false_positive_reduction": True
            }
            
            result = self.client._make_request('POST', '/api/telemetry/setup-alerts', data=alerting_data)
            
            rules_configured = len(result.get('configured_rules', []))
            
            self.logger.info(f"Alerting setup completed - {rules_configured} rules configured")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Alerting setup failed: {e}")
            raise
    
    # =============================================================================
    # UTILITY AND HELPER METHODS
    # =============================================================================
    
    def _calculate_success_rate(self) -> float:
        """Calculate process success rate"""
        total = self.performance_stats["processes_completed"] + self.performance_stats["processes_failed"]
        if total == 0:
            return 0.0
        return (self.performance_stats["processes_completed"] / total) * 100
    
    def _calculate_resource_efficiency(self) -> float:
        """Calculate overall resource efficiency"""
        if not self.resource_metrics['cpu_percent']:
            return 0.0
        
        recent_cpu = [metric[1] for metric in list(self.resource_metrics['cpu_percent'])[-10:]]
        avg_cpu = sum(recent_cpu) / len(recent_cpu) if recent_cpu else 0
        
        # Simple efficiency calculation - can be enhanced with more sophisticated algorithms
        return max(0, 100 - avg_cpu)
    
    def _calculate_cache_performance(self) -> Dict[str, float]:
        """Calculate cache performance metrics"""
        total_requests = self.cache_metrics["total_requests"]
        if total_requests == 0:
            return {"hit_rate": 0.0, "efficiency_score": 0.0}
        
        hit_rate = (self.cache_metrics["cache_hits"] / total_requests) * 100
        efficiency_score = hit_rate * (1 - self.cache_metrics["evictions"] / max(total_requests, 1))
        
        return {
            "hit_rate": hit_rate,
            "efficiency_score": efficiency_score
        }
    
    def get_process_summary(self) -> Dict[str, Any]:
        """
        Get summary of process management statistics
        
        Returns:
            Dict containing process management summary
        """
        return {
            "session_info": {
                "session_id": self.client.session_id,
                "client_uptime_hours": (datetime.now() - self.client.start_time).total_seconds() / 3600
            },
            "process_statistics": {
                **self.performance_stats,
                "active_processes": len(self.active_processes),
                "process_history_size": len(self.process_history),
                "success_rate_percent": self._calculate_success_rate()
            },
            "resource_utilization": {
                "monitoring_active": len(self.resource_metrics) > 0,
                "resource_efficiency_percent": self._calculate_resource_efficiency(),
                "system_info": self.system_info
            },
            "cache_performance": {
                **self.cache_metrics,
                **self._calculate_cache_performance(),
                "configured_caches": len(self.cache_configs)
            }
        }
    
    def cleanup_completed_processes(self, max_history_size: int = 1000):
        """
        Cleanup completed processes from history to manage memory
        
        Args:
            max_history_size: Maximum size of process history to maintain
        """
        if len(self.process_history) > max_history_size:
            # Keep only the most recent processes
            self.process_history = self.process_history[-max_history_size:]
            self.logger.info(f"Process history cleaned up - keeping {max_history_size} recent entries")
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check of process and cache systems
        
        Returns:
            Dict containing health check results
        """
        try:
            health_data = {
                "check_processes": True,
                "check_resources": True,
                "check_cache": True,
                "check_performance": True,
                "deep_analysis": True
            }
            
            result = self.client._make_request('POST', '/api/processes/health-check', data=health_data)
            
            # Add local health metrics
            result['local_health'] = {
                "active_processes_healthy": all(
                    p.state in [ProcessState.RUNNING, ProcessState.PAUSED] 
                    for p in self.active_processes.values()
                ),
                "cache_performance_good": self._calculate_cache_performance()["hit_rate"] > 70,
                "resource_efficiency_good": self._calculate_resource_efficiency() > 60,
                "process_success_rate_good": self._calculate_success_rate() > 80
            }
            
            overall_health = all(result['local_health'].values())
            result['overall_health_status'] = 'healthy' if overall_health else 'degraded'
            
            return result
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            raise


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def parse_resource_string(resource_string: str) -> int:
    """
    Parse resource string (e.g., "1GB", "500MB", "2TB") to bytes
    
    Args:
        resource_string: Resource string to parse
    
    Returns:
        Resource value in bytes
    """
    units = {
        'B': 1,
        'KB': 1024,
        'MB': 1024 ** 2,
        'GB': 1024 ** 3,
        'TB': 1024 ** 4,
        'PB': 1024 ** 5
    }
    
    resource_string = resource_string.upper().strip()
    
    # Extract number and unit
    match = re.match(r'(\d+(?:\.\d+)?)\s*([A-Z]+)', resource_string)
    if not match:
        raise ValueError(f"Invalid resource string format: {resource_string}")
    
    value, unit = match.groups()
    
    if unit not in units:
        raise ValueError(f"Unknown unit: {unit}")
    
    return int(float(value) * units[unit])

def format_bytes(bytes_value: int) -> str:
    """
    Format bytes value to human-readable string
    
    Args:
        bytes_value: Value in bytes
    
    Returns:
        Human-readable string
    """
    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    
    if bytes_value == 0:
        return "0 B"
    
    unit_index = 0
    value = float(bytes_value)
    
    while value >= 1024 and unit_index < len(units) - 1:
        value /= 1024
        unit_index += 1
    
    return f"{value:.2f} {units[unit_index]}"

def calculate_cpu_time(start_time: datetime, end_time: datetime, cpu_percent: float) -> float:
    """
    Calculate total CPU time used
    
    Args:
        start_time: Process start time
        end_time: Process end time
        cpu_percent: Average CPU percentage
    
    Returns:
        CPU time in seconds
    """
    duration_seconds = (end_time - start_time).total_seconds()
    return duration_seconds * (cpu_percent / 100.0)

def estimate_memory_efficiency(allocated_memory: int, peak_memory: int, avg_memory: int) -> float:
    """
    Estimate memory usage efficiency
    
    Args:
        allocated_memory: Total allocated memory
        peak_memory: Peak memory usage
        avg_memory: Average memory usage
    
    Returns:
        Memory efficiency score (0-100)
    """
    if allocated_memory == 0:
        return 0.0
    
    utilization = (avg_memory / allocated_memory) * 100
    peak_efficiency = (avg_memory / peak_memory) * 100 if peak_memory > 0 else 100
    
    # Combined efficiency score
    return (utilization + peak_efficiency) / 2


# =============================================================================
# EXPORT CLASSES AND FUNCTIONS
# =============================================================================

__all__ = [
    'ProcessCacheClient',
    'ProcessState',
    'ProcessPriority',
    'ResourceType',
    'CacheStrategy',
    'MonitoringLevel',
    'ProcessConfig',
    'ProcessInfo',
    'ResourceQuota',
    'CacheConfig',
    'parse_resource_string',
    'format_bytes',
    'calculate_cpu_time',
    'estimate_memory_efficiency'
]