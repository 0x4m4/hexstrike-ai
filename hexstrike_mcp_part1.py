#!/usr/bin/env python3
"""
HexStrike AI MCP Client v6.0 - Advanced Cybersecurity Automation Platform
Part 1 of 6: Core FastMCP Client Structure and Foundation Endpoints

This is an advanced Multi-Agent Communication Protocol (MCP) client designed to interface
with the HexStrike AI server. This client provides comprehensive wrapper methods for all
server endpoints with extensive error handling, type hints, and client-side intelligence.

Author: HexStrike AI Team
Version: 6.0.0
License: MIT
Created: 2025
"""

import json
import asyncio
import logging
import sys
import argparse
import time
from datetime import datetime, timedelta
from typing import (
    Dict, List, Any, Optional, Union, Tuple, Callable, 
    Type, TypeVar, Generic, Protocol, Literal, overload
)
import traceback
import hashlib
import base64
import os
from pathlib import Path
import subprocess
from dataclasses import dataclass, field
from enum import Enum, auto
from contextlib import contextmanager, asynccontextmanager
import threading
from concurrent.futures import ThreadPoolExecutor, Future
import queue
import uuid
import signal
import weakref
import inspect
from functools import wraps, lru_cache, partial
import re
import urllib.parse
from collections import defaultdict, deque, OrderedDict
import warnings
import socket
import ssl
import certifi

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    import aiohttp
    import asyncio
    from fastmcp import FastMCP, MCPError
    import psutil
except ImportError as e:
    logging.error(f"Required dependency missing: {e}")
    sys.exit(1)

# Configure comprehensive logging system
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('hexstrike_mcp_client.log')
    ]
)

# Custom logger for HexStrike MCP Client
logger = logging.getLogger("HexStrike-MCP-Client")

# Type definitions for enhanced type safety
T = TypeVar('T')
ResponseType = Union[Dict[str, Any], List[Dict[str, Any]], str, bytes]
EndpointMethod = Literal['GET', 'POST', 'PUT', 'DELETE', 'PATCH']

class LogLevel(Enum):
    """Enhanced logging levels for granular control"""
    TRACE = 5
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50
    SECURITY = 60

class ClientState(Enum):
    """Client connection states for state management"""
    DISCONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    AUTHENTICATING = auto()
    AUTHENTICATED = auto()
    ERROR = auto()
    RECONNECTING = auto()

class SecurityLevel(Enum):
    """Security levels for different operations"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4
    MAXIMUM = 5

@dataclass
class ServerConfig:
    """Configuration for HexStrike server connection"""
    host: str = "localhost"
    port: int = 8888
    protocol: str = "http"
    api_version: str = "v1"
    timeout: int = 300
    max_retries: int = 3
    retry_delay: float = 1.0
    ssl_verify: bool = True
    auth_token: Optional[str] = None
    user_agent: str = "HexStrike-MCP-Client/6.0"
    max_concurrent_requests: int = 10
    rate_limit_requests: int = 100
    rate_limit_window: int = 60
    
    @property
    def base_url(self) -> str:
        """Generate base URL for API requests"""
        return f"{self.protocol}://{self.host}:{self.port}"
    
    def validate(self) -> bool:
        """Validate server configuration"""
        if not self.host or not isinstance(self.port, int):
            return False
        if self.port < 1 or self.port > 65535:
            return False
        if self.protocol not in ['http', 'https']:
            return False
        return True

@dataclass
class RequestMetrics:
    """Metrics tracking for API requests"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time: float = 0.0
    last_request_time: Optional[datetime] = None
    errors_by_type: Dict[str, int] = field(default_factory=dict)
    response_times: deque = field(default_factory=lambda: deque(maxlen=100))
    
    def add_request(self, success: bool, response_time: float, error_type: Optional[str] = None):
        """Add request metrics"""
        self.total_requests += 1
        self.last_request_time = datetime.now()
        self.response_times.append(response_time)
        
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
            if error_type:
                self.errors_by_type[error_type] = self.errors_by_type.get(error_type, 0) + 1
        
        # Update average response time
        if self.response_times:
            self.average_response_time = sum(self.response_times) / len(self.response_times)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100

class CircuitBreaker:
    """Circuit breaker pattern implementation for resilient API calls"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0, expected_exception: Type[Exception] = Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self._lock = threading.Lock()
    
    def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        with self._lock:
            if self.state == "OPEN":
                if self._should_attempt_reset():
                    self.state = "HALF_OPEN"
                else:
                    raise Exception("Circuit breaker is OPEN")
            
            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except self.expected_exception as e:
                self._on_failure()
                raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt to reset"""
        return (
            self.last_failure_time and
            datetime.now() - self.last_failure_time >= timedelta(seconds=self.recovery_timeout)
        )
    
    def _on_success(self):
        """Handle successful call"""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"

class RateLimiter:
    """Token bucket rate limiter for API calls"""
    
    def __init__(self, max_requests: int = 100, time_window: float = 60.0):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
        self._lock = threading.Lock()
    
    def acquire(self) -> bool:
        """Acquire permission for API call"""
        with self._lock:
            now = time.time()
            # Remove old requests outside time window
            while self.requests and self.requests[0] <= now - self.time_window:
                self.requests.popleft()
            
            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True
            return False
    
    def wait_time(self) -> float:
        """Calculate wait time until next request is allowed"""
        with self._lock:
            if not self.requests:
                return 0.0
            oldest_request = self.requests[0]
            return max(0.0, self.time_window - (time.time() - oldest_request))

class ResponseCache:
    """Advanced caching system for API responses"""
    
    def __init__(self, max_size: int = 1000, default_ttl: float = 300.0):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache = OrderedDict()
        self._lock = threading.Lock()
    
    def _make_key(self, endpoint: str, params: Dict[str, Any]) -> str:
        """Generate cache key from endpoint and parameters"""
        param_str = json.dumps(params, sort_keys=True)
        return hashlib.sha256(f"{endpoint}:{param_str}".encode()).hexdigest()
    
    def get(self, endpoint: str, params: Dict[str, Any]) -> Optional[Any]:
        """Get cached response if available and not expired"""
        with self._lock:
            key = self._make_key(endpoint, params)
            if key in self.cache:
                entry_time, data = self.cache[key]
                if time.time() - entry_time < self.default_ttl:
                    # Move to end (LRU)
                    self.cache.move_to_end(key)
                    return data
                else:
                    del self.cache[key]
            return None
    
    def set(self, endpoint: str, params: Dict[str, Any], data: Any, ttl: Optional[float] = None):
        """Cache response data"""
        with self._lock:
            key = self._make_key(endpoint, params)
            
            # Remove oldest entries if cache is full
            while len(self.cache) >= self.max_size:
                self.cache.popitem(last=False)
            
            self.cache[key] = (time.time(), data)
    
    def clear(self):
        """Clear all cached responses"""
        with self._lock:
            self.cache.clear()

class SecurityValidator:
    """Advanced security validation for requests and responses"""
    
    def __init__(self):
        self.dangerous_patterns = [
            r'<script.*?>.*?</script>',
            r'javascript:',
            r'vbscript:',
            r'onload\s*=',
            r'onerror\s*=',
            r'eval\s*\(',
            r'exec\s*\(',
            r'system\s*\(',
            r'shell_exec\s*\(',
        ]
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE | re.DOTALL) 
                                for pattern in self.dangerous_patterns]
    
    def validate_input(self, data: Any, security_level: SecurityLevel = SecurityLevel.MEDIUM) -> bool:
        """Validate input data for security threats"""
        if security_level == SecurityLevel.LOW:
            return True
        
        if isinstance(data, str):
            return self._validate_string(data, security_level)
        elif isinstance(data, dict):
            return all(self.validate_input(v, security_level) for v in data.values())
        elif isinstance(data, list):
            return all(self.validate_input(item, security_level) for item in data)
        
        return True
    
    def _validate_string(self, text: str, security_level: SecurityLevel) -> bool:
        """Validate string content for security threats"""
        if security_level >= SecurityLevel.MEDIUM:
            for pattern in self.compiled_patterns:
                if pattern.search(text):
                    logger.warning(f"Security violation detected: {pattern.pattern}")
                    return False
        
        if security_level >= SecurityLevel.HIGH:
            # Additional validation for high security level
            if len(text) > 10000:  # Prevent DoS via large payloads
                return False
            
            # Check for SQL injection patterns
            sql_patterns = [r'union\s+select', r'drop\s+table', r'delete\s+from']
            for pattern in sql_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return False
        
        return True

class ConnectionPool:
    """Connection pool for efficient HTTP request management"""
    
    def __init__(self, max_connections: int = 10):
        self.max_connections = max_connections
        self.session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=max_connections)
        
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set common headers
        self.session.headers.update({
            'User-Agent': 'HexStrike-MCP-Client/6.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
    
    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make HTTP request using connection pool"""
        return self.session.request(method, url, **kwargs)
    
    def close(self):
        """Close connection pool"""
        self.session.close()

class EventSystem:
    """Event system for client-server communication events"""
    
    def __init__(self):
        self.listeners: Dict[str, List[Callable]] = defaultdict(list)
        self._lock = threading.Lock()
    
    def on(self, event_name: str, callback: Callable):
        """Register event listener"""
        with self._lock:
            self.listeners[event_name].append(callback)
    
    def off(self, event_name: str, callback: Callable):
        """Unregister event listener"""
        with self._lock:
            if callback in self.listeners[event_name]:
                self.listeners[event_name].remove(callback)
    
    def emit(self, event_name: str, *args, **kwargs):
        """Emit event to all registered listeners"""
        with self._lock:
            listeners = self.listeners[event_name][:]  # Copy to avoid modification during iteration
        
        for callback in listeners:
            try:
                callback(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in event listener for {event_name}: {e}")

class HexStrikeMCPClient:
    """
    Advanced FastMCP Client for HexStrike AI Server
    
    This is the core client class that provides comprehensive interface to all
    HexStrike AI server capabilities including 150+ security tools, 12+ AI agents,
    and advanced process management features.
    
    Features:
    - FastMCP protocol support
    - Advanced error handling and recovery
    - Circuit breaker pattern for resilience
    - Rate limiting and caching
    - Comprehensive security validation
    - Real-time metrics and monitoring
    - Event-driven architecture
    - Connection pooling and optimization
    """
    
    def __init__(self, server_url: str = "http://localhost:8888", **kwargs):
        """
        Initialize HexStrike MCP Client
        
        Args:
            server_url: URL of the HexStrike server
            **kwargs: Additional configuration options
        """
        # Parse server URL and initialize configuration
        parsed_url = urllib.parse.urlparse(server_url)
        self.config = ServerConfig(
            host=parsed_url.hostname or "localhost",
            port=parsed_url.port or 8888,
            protocol=parsed_url.scheme or "http",
            **kwargs
        )
        
        # Validate configuration
        if not self.config.validate():
            raise ValueError("Invalid server configuration")
        
        # Initialize core components
        self.state = ClientState.DISCONNECTED
        self.session_id = str(uuid.uuid4())
        self.start_time = datetime.now()
        
        # Initialize subsystems
        self._init_logging()
        self._init_networking()
        self._init_security()
        self._init_monitoring()
        self._init_events()
        
        # FastMCP client instance
        self.mcp_client = None
        self._mcp_lock = threading.Lock()
        
        logger.info(f"HexStrike MCP Client v6.0 initialized - Session: {self.session_id}")
        logger.info(f"Target server: {self.config.base_url}")
    
    def _init_logging(self):
        """Initialize advanced logging system"""
        self.client_logger = logging.getLogger(f"HexStrike-MCP-{self.session_id[:8]}")
        self.client_logger.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s'
        )
        
        # File handler for client-specific logs
        log_file = f"hexstrike_mcp_client_{self.session_id[:8]}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        self.client_logger.addHandler(file_handler)
        
        self.log_file_path = log_file
    
    def _init_networking(self):
        """Initialize networking components"""
        self.connection_pool = ConnectionPool(max_connections=self.config.max_concurrent_requests)
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60.0,
            expected_exception=requests.exceptions.RequestException
        )
        self.rate_limiter = RateLimiter(
            max_requests=self.config.rate_limit_requests,
            time_window=self.config.rate_limit_window
        )
        self.response_cache = ResponseCache(max_size=1000, default_ttl=300.0)
    
    def _init_security(self):
        """Initialize security components"""
        self.security_validator = SecurityValidator()
        self.request_signatures: Dict[str, str] = {}
        self.security_level = SecurityLevel.MEDIUM
    
    def _init_monitoring(self):
        """Initialize monitoring and metrics"""
        self.metrics = RequestMetrics()
        self.performance_data: Dict[str, List[float]] = defaultdict(list)
        self.health_status = "unknown"
        self.last_health_check = None
    
    def _init_events(self):
        """Initialize event system"""
        self.events = EventSystem()
        
        # Register default event handlers
        self.events.on('connection_established', self._on_connection_established)
        self.events.on('connection_lost', self._on_connection_lost)
        self.events.on('request_completed', self._on_request_completed)
        self.events.on('error_occurred', self._on_error_occurred)
    
    def _on_connection_established(self):
        """Handle connection establishment"""
        self.client_logger.info("Connection to HexStrike server established")
        self.state = ClientState.CONNECTED
    
    def _on_connection_lost(self):
        """Handle connection loss"""
        self.client_logger.warning("Connection to HexStrike server lost")
        self.state = ClientState.DISCONNECTED
    
    def _on_request_completed(self, endpoint: str, duration: float, success: bool):
        """Handle completed requests"""
        self.performance_data[endpoint].append(duration)
        if len(self.performance_data[endpoint]) > 100:
            self.performance_data[endpoint] = self.performance_data[endpoint][-100:]
    
    def _on_error_occurred(self, error: Exception, context: Dict[str, Any]):
        """Handle errors"""
        self.client_logger.error(f"Error in {context.get('function', 'unknown')}: {error}")
    
    async def connect(self) -> bool:
        """
        Establish connection to HexStrike server
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.state = ClientState.CONNECTING
            self.client_logger.info(f"Connecting to HexStrike server at {self.config.base_url}")
            
            # Initialize FastMCP client
            with self._mcp_lock:
                self.mcp_client = FastMCP(
                    name="hexstrike-ai-client",
                    description="HexStrike AI MCP Client v6.0 - Advanced Cybersecurity Automation"
                )
            
            # Test connection with health check
            health_result = await self.check_server_health()
            if health_result.get('status') == 'healthy':
                self.events.emit('connection_established')
                return True
            else:
                self.client_logger.error(f"Server health check failed: {health_result}")
                return False
                
        except Exception as e:
            self.client_logger.error(f"Failed to connect to server: {e}")
            self.events.emit('connection_lost')
            return False
    
    def disconnect(self):
        """Disconnect from HexStrike server"""
        try:
            self.client_logger.info("Disconnecting from HexStrike server")
            
            # Close connection pool
            if hasattr(self, 'connection_pool'):
                self.connection_pool.close()
            
            # Clear caches
            if hasattr(self, 'response_cache'):
                self.response_cache.clear()
            
            self.state = ClientState.DISCONNECTED
            self.events.emit('connection_lost')
            
        except Exception as e:
            self.client_logger.error(f"Error during disconnect: {e}")
    
    def _make_request(self, 
                     method: EndpointMethod,
                     endpoint: str,
                     params: Optional[Dict[str, Any]] = None,
                     data: Optional[Union[Dict[str, Any], str, bytes]] = None,
                     headers: Optional[Dict[str, str]] = None,
                     timeout: Optional[float] = None,
                     use_cache: bool = True,
                     security_level: Optional[SecurityLevel] = None) -> ResponseType:
        """
        Make HTTP request to HexStrike server with comprehensive error handling
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE, PATCH)
            endpoint: API endpoint path
            params: Query parameters
            data: Request body data
            headers: Additional headers
            timeout: Request timeout
            use_cache: Whether to use response caching
            security_level: Security validation level
        
        Returns:
            ResponseType: Server response data
        
        Raises:
            MCPError: If request fails after retries
        """
        start_time = time.time()
        params = params or {}
        headers = headers or {}
        security_level = security_level or self.security_level
        
        try:
            # Security validation
            if not self.security_validator.validate_input(params, security_level):
                raise MCPError("Security validation failed for request parameters")
            
            if data and not self.security_validator.validate_input(data, security_level):
                raise MCPError("Security validation failed for request data")
            
            # Check rate limiting
            if not self.rate_limiter.acquire():
                wait_time = self.rate_limiter.wait_time()
                self.client_logger.warning(f"Rate limit exceeded, waiting {wait_time:.2f}s")
                time.sleep(wait_time)
                if not self.rate_limiter.acquire():
                    raise MCPError("Rate limit exceeded")
            
            # Check cache for GET requests
            if method == 'GET' and use_cache:
                cached_response = self.response_cache.get(endpoint, params)
                if cached_response is not None:
                    self.client_logger.debug(f"Cache hit for {endpoint}")
                    return cached_response
            
            # Prepare request
            url = f"{self.config.base_url}{endpoint}"
            
            # Merge headers
            request_headers = {
                'User-Agent': self.config.user_agent,
                'Accept': 'application/json',
                'X-Session-ID': self.session_id,
                'X-Request-ID': str(uuid.uuid4()),
                **headers
            }
            
            if self.config.auth_token:
                request_headers['Authorization'] = f"Bearer {self.config.auth_token}"
            
            # Prepare request kwargs
            request_kwargs = {
                'timeout': timeout or self.config.timeout,
                'headers': request_headers,
                'verify': self.config.ssl_verify
            }
            
            if params:
                request_kwargs['params'] = params
            
            if data:
                if isinstance(data, (dict, list)):
                    request_kwargs['json'] = data
                    request_headers['Content-Type'] = 'application/json'
                else:
                    request_kwargs['data'] = data
            
            # Execute request with circuit breaker
            def make_http_request():
                return self.connection_pool.request(method, url, **request_kwargs)
            
            response = self.circuit_breaker.call(make_http_request)
            
            # Process response
            duration = time.time() - start_time
            
            if response.status_code >= 400:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                self.client_logger.error(f"Request failed: {error_msg}")
                self.metrics.add_request(False, duration, f"HTTP_{response.status_code}")
                self.events.emit('error_occurred', 
                               Exception(error_msg), 
                               {'endpoint': endpoint, 'method': method})
                raise MCPError(error_msg)
            
            # Parse response
            try:
                if response.headers.get('content-type', '').startswith('application/json'):
                    result = response.json()
                else:
                    result = response.text
            except json.JSONDecodeError:
                result = response.text
            
            # Cache successful GET responses
            if method == 'GET' and use_cache and response.status_code == 200:
                self.response_cache.set(endpoint, params, result)
            
            # Update metrics
            self.metrics.add_request(True, duration)
            self.events.emit('request_completed', endpoint, duration, True)
            
            self.client_logger.debug(f"Request completed: {method} {endpoint} ({duration:.3f}s)")
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            self.metrics.add_request(False, duration, type(e).__name__)
            self.events.emit('error_occurred', e, {'endpoint': endpoint, 'method': method})
            
            # Log detailed error information
            self.client_logger.error(f"Request failed: {method} {endpoint}")
            self.client_logger.error(f"Error: {e}")
            self.client_logger.error(f"Traceback: {traceback.format_exc()}")
            
            raise MCPError(f"Request failed: {e}")
    
    # =============================================================================
    # CORE SERVER ENDPOINTS - Health, Status, and Basic Operations
    # =============================================================================
    
    async def check_server_health(self) -> Dict[str, Any]:
        """
        Check HexStrike server health status
        
        This endpoint provides comprehensive health information about the server
        including system resources, component status, and performance metrics.
        
        Returns:
            Dict containing:
            - status: Overall health status ('healthy', 'degraded', 'unhealthy')
            - uptime: Server uptime in seconds
            - version: Server version information
            - components: Status of individual components
            - metrics: Performance metrics
            - timestamp: Health check timestamp
        
        Raises:
            MCPError: If health check fails
        """
        try:
            self.client_logger.info("Performing server health check")
            
            result = self._make_request('GET', '/health')
            
            # Update local health status
            self.health_status = result.get('status', 'unknown')
            self.last_health_check = datetime.now()
            
            # Log health status
            if self.health_status == 'healthy':
                self.client_logger.info("Server is healthy")
            else:
                self.client_logger.warning(f"Server health status: {self.health_status}")
            
            return result
            
        except Exception as e:
            self.client_logger.error(f"Health check failed: {e}")
            self.health_status = 'unhealthy'
            raise MCPError(f"Health check failed: {e}")
    
    async def get_server_info(self) -> Dict[str, Any]:
        """
        Get comprehensive server information
        
        Retrieves detailed information about the HexStrike server including
        version, configuration, capabilities, and runtime information.
        
        Returns:
            Dict containing:
            - version: Server version and build info
            - capabilities: List of supported features
            - tools: Available security tools
            - ai_agents: Available AI agents
            - configuration: Server configuration summary
            - runtime: Runtime information
        """
        try:
            self.client_logger.info("Fetching server information")
            
            result = self._make_request('GET', '/api/info')
            
            self.client_logger.info(f"Server version: {result.get('version', 'unknown')}")
            self.client_logger.info(f"Available tools: {len(result.get('tools', []))}")
            self.client_logger.info(f"Available AI agents: {len(result.get('ai_agents', []))}")
            
            return result
            
        except Exception as e:
            self.client_logger.error(f"Failed to get server info: {e}")
            raise MCPError(f"Failed to get server info: {e}")
    
    async def execute_command(self, 
                             command: str,
                             args: Optional[List[str]] = None,
                             timeout: Optional[int] = None,
                             working_directory: Optional[str] = None,
                             environment: Optional[Dict[str, str]] = None,
                             capture_output: bool = True,
                             stream_output: bool = False) -> Dict[str, Any]:
        """
        Execute command on HexStrike server with advanced options
        
        This is the core command execution endpoint that allows running security
        tools and commands on the server with comprehensive configuration options.
        
        Args:
            command: Command to execute
            args: Command arguments
            timeout: Execution timeout in seconds
            working_directory: Working directory for command
            environment: Environment variables
            capture_output: Whether to capture stdout/stderr
            stream_output: Whether to stream output in real-time
        
        Returns:
            Dict containing:
            - command_id: Unique identifier for the command execution
            - status: Execution status ('running', 'completed', 'failed', 'timeout')
            - exit_code: Command exit code (if completed)
            - stdout: Standard output (if capture_output=True)
            - stderr: Standard error (if capture_output=True)
            - start_time: Execution start timestamp
            - end_time: Execution end timestamp (if completed)
            - duration: Execution duration in seconds
            - process_info: Process information
        
        Raises:
            MCPError: If command execution fails to start
        """
        try:
            args = args or []
            
            self.client_logger.info(f"Executing command: {command} {' '.join(args)}")
            
            # Prepare command data
            command_data = {
                'command': command,
                'args': args,
                'options': {
                    'timeout': timeout or self.config.timeout,
                    'working_directory': working_directory,
                    'environment': environment or {},
                    'capture_output': capture_output,
                    'stream_output': stream_output
                }
            }
            
            result = self._make_request('POST', '/api/command', data=command_data)
            
            command_id = result.get('command_id')
            self.client_logger.info(f"Command started with ID: {command_id}")
            
            return result
            
        except Exception as e:
            self.client_logger.error(f"Command execution failed: {e}")
            raise MCPError(f"Command execution failed: {e}")
    
    async def get_command_status(self, command_id: str) -> Dict[str, Any]:
        """
        Get status of executing command
        
        Args:
            command_id: Unique identifier of the command
        
        Returns:
            Dict with command status information
        """
        try:
            self.client_logger.debug(f"Getting status for command: {command_id}")
            
            result = self._make_request('GET', f'/api/command/{command_id}')
            
            return result
            
        except Exception as e:
            self.client_logger.error(f"Failed to get command status: {e}")
            raise MCPError(f"Failed to get command status: {e}")
    
    async def terminate_command(self, command_id: str, signal_name: str = "SIGTERM") -> Dict[str, Any]:
        """
        Terminate running command
        
        Args:
            command_id: Unique identifier of the command
            signal_name: Signal to send (SIGTERM, SIGKILL, etc.)
        
        Returns:
            Dict with termination result
        """
        try:
            self.client_logger.info(f"Terminating command {command_id} with {signal_name}")
            
            result = self._make_request('DELETE', f'/api/command/{command_id}', 
                                      data={'signal': signal_name})
            
            return result
            
        except Exception as e:
            self.client_logger.error(f"Failed to terminate command: {e}")
            raise MCPError(f"Failed to terminate command: {e}")
    
    # =============================================================================
    # FILE OPERATIONS - Advanced File Management
    # =============================================================================
    
    async def upload_file(self,
                         file_path: str,
                         target_path: str,
                         overwrite: bool = False,
                         create_directories: bool = True,
                         file_permissions: Optional[str] = None) -> Dict[str, Any]:
        """
        Upload file to HexStrike server
        
        Args:
            file_path: Local file path to upload
            target_path: Target path on server
            overwrite: Whether to overwrite existing files
            create_directories: Whether to create target directories
            file_permissions: File permissions to set (e.g., '755', '644')
        
        Returns:
            Dict with upload result information
        """
        try:
            self.client_logger.info(f"Uploading file: {file_path} -> {target_path}")
            
            if not os.path.exists(file_path):
                raise MCPError(f"Local file not found: {file_path}")
            
            # Read file content
            with open(file_path, 'rb') as f:
                file_content = base64.b64encode(f.read()).decode('utf-8')
            
            # Get file info
            file_stat = os.stat(file_path)
            file_info = {
                'name': os.path.basename(file_path),
                'size': file_stat.st_size,
                'content': file_content,
                'target_path': target_path,
                'overwrite': overwrite,
                'create_directories': create_directories,
                'permissions': file_permissions
            }
            
            result = self._make_request('POST', '/api/files/upload', data=file_info)
            
            self.client_logger.info(f"File uploaded successfully: {target_path}")
            
            return result
            
        except Exception as e:
            self.client_logger.error(f"File upload failed: {e}")
            raise MCPError(f"File upload failed: {e}")
    
    async def download_file(self, 
                           remote_path: str,
                           local_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Download file from HexStrike server
        
        Args:
            remote_path: Remote file path on server
            local_path: Local path to save file (optional)
        
        Returns:
            Dict with download result and file content
        """
        try:
            self.client_logger.info(f"Downloading file: {remote_path}")
            
            result = self._make_request('GET', f'/api/files/download',
                                      params={'path': remote_path})
            
            # If local_path specified, save file
            if local_path:
                file_content = base64.b64decode(result['content'])
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                
                with open(local_path, 'wb') as f:
                    f.write(file_content)
                
                self.client_logger.info(f"File saved to: {local_path}")
            
            return result
            
        except Exception as e:
            self.client_logger.error(f"File download failed: {e}")
            raise MCPError(f"File download failed: {e}")
    
    async def list_files(self,
                        directory: str = "/",
                        recursive: bool = False,
                        include_hidden: bool = False,
                        file_pattern: Optional[str] = None) -> Dict[str, Any]:
        """
        List files and directories on server
        
        Args:
            directory: Directory to list
            recursive: Whether to list recursively
            include_hidden: Whether to include hidden files
            file_pattern: Pattern to filter files (glob pattern)
        
        Returns:
            Dict with file listing information
        """
        try:
            self.client_logger.info(f"Listing files in: {directory}")
            
            params = {
                'directory': directory,
                'recursive': recursive,
                'include_hidden': include_hidden
            }
            
            if file_pattern:
                params['pattern'] = file_pattern
            
            result = self._make_request('GET', '/api/files/list', params=params)
            
            file_count = len(result.get('files', []))
            dir_count = len(result.get('directories', []))
            
            self.client_logger.info(f"Found {file_count} files and {dir_count} directories")
            
            return result
            
        except Exception as e:
            self.client_logger.error(f"File listing failed: {e}")
            raise MCPError(f"File listing failed: {e}")
    
    async def delete_file(self, file_path: str, force: bool = False) -> Dict[str, Any]:
        """
        Delete file or directory on server
        
        Args:
            file_path: Path to delete
            force: Force deletion even if not empty (for directories)
        
        Returns:
            Dict with deletion result
        """
        try:
            self.client_logger.info(f"Deleting: {file_path}")
            
            data = {
                'path': file_path,
                'force': force
            }
            
            result = self._make_request('DELETE', '/api/files/delete', data=data)
            
            self.client_logger.info(f"Successfully deleted: {file_path}")
            
            return result
            
        except Exception as e:
            self.client_logger.error(f"File deletion failed: {e}")
            raise MCPError(f"File deletion failed: {e}")
    
    async def create_directory(self, 
                              directory_path: str,
                              permissions: Optional[str] = None,
                              create_parents: bool = True) -> Dict[str, Any]:
        """
        Create directory on server
        
        Args:
            directory_path: Directory path to create
            permissions: Directory permissions (e.g., '755')
            create_parents: Whether to create parent directories
        
        Returns:
            Dict with creation result
        """
        try:
            self.client_logger.info(f"Creating directory: {directory_path}")
            
            data = {
                'path': directory_path,
                'permissions': permissions,
                'create_parents': create_parents
            }
            
            result = self._make_request('POST', '/api/files/mkdir', data=data)
            
            self.client_logger.info(f"Directory created: {directory_path}")
            
            return result
            
        except Exception as e:
            self.client_logger.error(f"Directory creation failed: {e}")
            raise MCPError(f"Directory creation failed: {e}")
    
    # =============================================================================
    # PAYLOAD GENERATION - Advanced Exploit and Payload Generation
    # =============================================================================
    
    async def generate_payload(self,
                              payload_type: str,
                              target_info: Dict[str, Any],
                              exploit_options: Optional[Dict[str, Any]] = None,
                              encoding: Optional[List[str]] = None,
                              output_format: str = "raw") -> Dict[str, Any]:
        """
        Generate advanced security payload using AI-powered generation
        
        This endpoint leverages the AI Exploit Generator to create sophisticated
        payloads tailored to specific targets and vulnerabilities.
        
        Args:
            payload_type: Type of payload (shellcode, reverse_shell, bind_shell, 
                         web_shell, privilege_escalation, persistence, etc.)
            target_info: Information about target system
                - os: Target OS (windows, linux, macos, etc.)
                - arch: Architecture (x86, x64, arm, etc.)  
                - version: OS/service version
                - vulnerability: Specific vulnerability (CVE, etc.)
                - service: Target service information
            exploit_options: Advanced exploit configuration
                - lhost: Local host for reverse connections
                - lport: Local port for reverse connections
                - rhost: Remote host target
                - rport: Remote port target
                - timeout: Connection timeout
                - retries: Number of retry attempts
            encoding: List of encoding techniques to apply
                - base64, hex, url, unicode, etc.
            output_format: Output format (raw, c, python, powershell, bash, etc.)
        
        Returns:
            Dict containing:
            - payload_id: Unique identifier for generated payload
            - payload_data: The generated payload
            - payload_info: Metadata about the payload
            - encoding_applied: List of encoding techniques used
            - delivery_methods: Suggested delivery methods
            - mitigation_info: Information about detection/mitigation
            - success_probability: AI-estimated success probability
        """
        try:
            self.client_logger.info(f"Generating {payload_type} payload for {target_info.get('os', 'unknown')} target")
            
            # Validate required parameters
            if not payload_type:
                raise ValueError("payload_type is required")
            
            if not target_info:
                raise ValueError("target_info is required")
            
            # Prepare payload generation request
            payload_request = {
                'type': payload_type,
                'target': target_info,
                'options': exploit_options or {},
                'encoding': encoding or [],
                'format': output_format,
                'ai_optimization': True,  # Enable AI optimization
                'include_metadata': True
            }
            
            result = self._make_request('POST', '/api/payloads/generate', data=payload_request)
            
            payload_id = result.get('payload_id')
            success_prob = result.get('success_probability', 0)
            
            self.client_logger.info(f"Payload generated successfully: {payload_id}")
            self.client_logger.info(f"Estimated success probability: {success_prob}%")
            
            # Log security warning
            self.client_logger.warning("Generated payload should only be used for authorized testing")
            
            return result
            
        except Exception as e:
            self.client_logger.error(f"Payload generation failed: {e}")
            raise MCPError(f"Payload generation failed: {e}")
    
    async def customize_payload(self,
                               payload_id: str,
                               customizations: Dict[str, Any]) -> Dict[str, Any]:
        """
        Customize existing payload with additional modifications
        
        Args:
            payload_id: ID of existing payload to customize
            customizations: Customization options
        
        Returns:
            Dict with customized payload information
        """
        try:
            self.client_logger.info(f"Customizing payload: {payload_id}")
            
            data = {
                'payload_id': payload_id,
                'customizations': customizations
            }
            
            result = self._make_request('POST', '/api/payloads/customize', data=data)
            
            return result
            
        except Exception as e:
            self.client_logger.error(f"Payload customization failed: {e}")
            raise MCPError(f"Payload customization failed: {e}")
    
    async def get_payload_templates(self, category: Optional[str] = None) -> Dict[str, Any]:
        """
        Get available payload templates
        
        Args:
            category: Optional category filter
        
        Returns:
            Dict with available payload templates
        """
        try:
            self.client_logger.info("Fetching payload templates")
            
            params = {}
            if category:
                params['category'] = category
            
            result = self._make_request('GET', '/api/payloads/templates', params=params)
            
            template_count = len(result.get('templates', []))
            self.client_logger.info(f"Found {template_count} payload templates")
            
            return result
            
        except Exception as e:
            self.client_logger.error(f"Failed to get payload templates: {e}")
            raise MCPError(f"Failed to get payload templates: {e}")
    
    # =============================================================================
    # CACHE OPERATIONS - Advanced Caching System Management
    # =============================================================================
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive cache statistics and performance metrics
        
        Returns:
            Dict containing:
            - total_entries: Total number of cached entries
            - cache_size: Total cache size in bytes
            - hit_rate: Cache hit rate percentage
            - miss_rate: Cache miss rate percentage
            - eviction_count: Number of evicted entries
            - memory_usage: Memory usage statistics
            - performance_metrics: Detailed performance data
        """
        try:
            self.client_logger.info("Fetching cache statistics")
            
            result = self._make_request('GET', '/api/cache/stats')
            
            hit_rate = result.get('hit_rate', 0)
            total_entries = result.get('total_entries', 0)
            
            self.client_logger.info(f"Cache hit rate: {hit_rate:.2f}%")
            self.client_logger.info(f"Total cached entries: {total_entries}")
            
            return result
            
        except Exception as e:
            self.client_logger.error(f"Failed to get cache stats: {e}")
            raise MCPError(f"Failed to get cache stats: {e}")
    
    async def clear_cache(self, 
                         cache_type: Optional[str] = None,
                         pattern: Optional[str] = None) -> Dict[str, Any]:
        """
        Clear cache entries with optional filtering
        
        Args:
            cache_type: Specific cache type to clear (command, file, payload, etc.)
            pattern: Pattern to match cache keys for selective clearing
        
        Returns:
            Dict with cache clearing results
        """
        try:
            self.client_logger.info(f"Clearing cache - Type: {cache_type}, Pattern: {pattern}")
            
            data = {}
            if cache_type:
                data['type'] = cache_type
            if pattern:
                data['pattern'] = pattern
            
            result = self._make_request('DELETE', '/api/cache/clear', data=data)
            
            cleared_count = result.get('cleared_entries', 0)
            self.client_logger.info(f"Cleared {cleared_count} cache entries")
            
            return result
            
        except Exception as e:
            self.client_logger.error(f"Cache clearing failed: {e}")
            raise MCPError(f"Cache clearing failed: {e}")
    
    # =============================================================================
    # UTILITY METHODS - Helper Functions and Advanced Operations
    # =============================================================================
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive client metrics and performance data
        
        Returns:
            Dict with detailed metrics information
        """
        return {
            'session_id': self.session_id,
            'start_time': self.start_time.isoformat(),
            'uptime_seconds': (datetime.now() - self.start_time).total_seconds(),
            'state': self.state.name,
            'health_status': self.health_status,
            'last_health_check': self.last_health_check.isoformat() if self.last_health_check else None,
            'request_metrics': {
                'total_requests': self.metrics.total_requests,
                'successful_requests': self.metrics.successful_requests,
                'failed_requests': self.metrics.failed_requests,
                'success_rate': self.metrics.success_rate,
                'average_response_time': self.metrics.average_response_time,
                'errors_by_type': dict(self.metrics.errors_by_type)
            },
            'performance_data': {k: list(v) for k, v in self.performance_data.items()},
            'server_config': {
                'host': self.config.host,
                'port': self.config.port,
                'protocol': self.config.protocol,
                'base_url': self.config.base_url
            }
        }
    
    async def validate_server_connection(self) -> bool:
        """
        Validate connection to HexStrike server
        
        Returns:
            bool: True if connection is valid and responsive
        """
        try:
            health_result = await self.check_server_health()
            return health_result.get('status') == 'healthy'
        except:
            return False
    
    def set_security_level(self, level: SecurityLevel):
        """
        Set security validation level for requests
        
        Args:
            level: Security level to apply
        """
        self.security_level = level
        self.client_logger.info(f"Security level set to: {level.name}")
    
    def enable_debug_logging(self):
        """Enable debug logging for detailed troubleshooting"""
        self.client_logger.setLevel(logging.DEBUG)
        logging.getLogger("requests").setLevel(logging.DEBUG)
        logging.getLogger("urllib3").setLevel(logging.DEBUG)
    
    def disable_debug_logging(self):
        """Disable debug logging"""
        self.client_logger.setLevel(logging.INFO)
        logging.getLogger("requests").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    @contextmanager
    def temporary_config(self, **config_changes):
        """
        Temporarily modify configuration
        
        Args:
            **config_changes: Configuration parameters to temporarily change
        """
        original_values = {}
        
        try:
            # Store original values and apply changes
            for key, value in config_changes.items():
                if hasattr(self.config, key):
                    original_values[key] = getattr(self.config, key)
                    setattr(self.config, key, value)
            
            yield
            
        finally:
            # Restore original values
            for key, value in original_values.items():
                setattr(self.config, key, value)
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup"""
        self.disconnect()
    
    def __repr__(self) -> str:
        """String representation of client"""
        return (f"HexStrikeMCPClient(session={self.session_id[:8]}, "
                f"state={self.state.name}, server={self.config.base_url})")


# =============================================================================
# MAIN EXECUTION AND CLI INTERFACE
# =============================================================================

async def main():
    """
    Main execution function for HexStrike MCP Client
    
    This function handles command-line arguments, initializes the client,
    and establishes connection to the HexStrike server.
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="HexStrike AI MCP Client v6.0 - Advanced Cybersecurity Automation Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 hexstrike_mcp.py --server http://localhost:8888
  python3 hexstrike_mcp.py --server https://hexstrike.example.com:8888 --auth-token YOUR_TOKEN
  python3 hexstrike_mcp.py --server http://192.168.1.100:8888 --debug
        """
    )
    
    parser.add_argument(
        '--server', 
        type=str, 
        default='http://localhost:8888',
        help='HexStrike server URL (default: http://localhost:8888)'
    )
    
    parser.add_argument(
        '--auth-token',
        type=str,
        help='Authentication token for server access'
    )
    
    parser.add_argument(
        '--timeout',
        type=int,
        default=300,
        help='Request timeout in seconds (default: 300)'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    parser.add_argument(
        '--security-level',
        type=str,
        choices=['low', 'medium', 'high', 'critical', 'maximum'],
        default='medium',
        help='Security validation level (default: medium)'
    )
    
    parser.add_argument(
        '--max-retries',
        type=int,
        default=3,
        help='Maximum number of retry attempts (default: 3)'
    )
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("Debug logging enabled")
    
    # Parse security level
    security_level_map = {
        'low': SecurityLevel.LOW,
        'medium': SecurityLevel.MEDIUM,
        'high': SecurityLevel.HIGH,
        'critical': SecurityLevel.CRITICAL,
        'maximum': SecurityLevel.MAXIMUM
    }
    security_level = security_level_map[args.security_level]
    
    # Initialize client with configuration
    try:
        client = HexStrikeMCPClient(
            server_url=args.server,
            timeout=args.timeout,
            auth_token=args.auth_token,
            max_retries=args.max_retries
        )
        
        client.set_security_level(security_level)
        
        if args.debug:
            client.enable_debug_logging()
        
        logger.info(f"Initializing HexStrike MCP Client v6.0")
        logger.info(f"Target server: {args.server}")
        logger.info(f"Security level: {args.security_level}")
        
        # Connect to server
        logger.info("Connecting to HexStrike server...")
        connection_success = await client.connect()
        
        if not connection_success:
            logger.error("Failed to connect to HexStrike server")
            sys.exit(1)
        
        logger.info("Connected successfully to HexStrike server")
        
        # Get server information
        try:
            server_info = await client.get_server_info()
            logger.info(f"Server version: {server_info.get('version', 'unknown')}")
            logger.info(f"Available tools: {len(server_info.get('tools', []))}")
        except Exception as e:
            logger.warning(f"Could not retrieve server info: {e}")
        
        # Start FastMCP client loop
        logger.info("Starting FastMCP client...")
        
        # The FastMCP client will handle MCP protocol communication
        # This is where the actual MCP agent functionality runs
        
        # Keep the client running
        try:
            while True:
                await asyncio.sleep(1)
                
                # Periodic health check
                if client.last_health_check is None or \
                   (datetime.now() - client.last_health_check).total_seconds() > 300:
                    try:
                        await client.check_server_health()
                    except Exception as e:
                        logger.warning(f"Health check failed: {e}")
                
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        except Exception as e:
            logger.error(f"Client error: {e}")
        finally:
            logger.info("Disconnecting from server...")
            client.disconnect()
    
    except Exception as e:
        logger.error(f"Failed to initialize client: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)

# Signal handlers for graceful shutdown
def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)

if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run the client
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Client shutdown requested")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)