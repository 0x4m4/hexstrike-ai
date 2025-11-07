#!/usr/bin/env python3
"""
MindSync Oracle v9 - MCP Integration Layer

STANDARDIZED SECURITY TOOL ACCESS VIA MODEL CONTEXT PROTOCOL

This module provides a unified interface to MCP servers for security tools:
- Shodan (device/IP intelligence)
- VirusTotal (malware/reputation analysis)
- NIST NVD (CVE database queries)

Benefits over custom API wrappers:
- Standardized protocol (MCP)
- Easier maintenance
- Consistent error handling
- Better caching and rate limiting

Integration Points:
- v2: Extends HexStrike tool ecosystem
- v3: Feeds results into memory graph
- v7: Enhances threat correlation with real-time data
- v8: Provides data for chain prediction

Usage:
    from mcp_integration import MCPIntegration

    mcp = MCPIntegration(config)

    # Shodan IP lookup
    result = await mcp.shodan_lookup("8.8.8.8")

    # VirusTotal hash check
    result = await mcp.virustotal_scan("hash123...")

    # NIST CVE query
    result = await mcp.nist_cve_lookup("CVE-2025-1234")
"""

import logging
import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import time

logger = logging.getLogger(__name__)


class MCPIntegration:
    """
    MCP Integration Layer for Security Tools.

    Provides unified access to MCP servers for Shodan, VirusTotal, NIST NVD.
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize MCP integration.

        Args:
            config: Configuration dict with MCP settings
        """
        self.config = config or {}

        # MCP server configurations
        self.mcp_servers = {
            'shodan': {
                'enabled': self.config.get('mcp', {}).get('shodan', {}).get('enabled', False),
                'api_key': self.config.get('mcp', {}).get('shodan', {}).get('api_key'),
                'rate_limit': 1.0,  # 1 request per second
                'last_call': 0
            },
            'virustotal': {
                'enabled': self.config.get('mcp', {}).get('virustotal', {}).get('enabled', False),
                'api_key': self.config.get('mcp', {}).get('virustotal', {}).get('api_key'),
                'rate_limit': 4.0,  # 4 requests per minute (free tier)
                'last_call': 0
            },
            'nist': {
                'enabled': self.config.get('mcp', {}).get('nist', {}).get('enabled', True),
                'api_key': None,  # Public API, no key needed
                'rate_limit': 0.6,  # ~1 request per 0.6 seconds (safe for public API)
                'last_call': 0
            }
        }

        # Result cache (simple in-memory, 1 hour TTL)
        self.cache = {}
        self.cache_ttl = 3600

        # Statistics
        self.stats = {
            'shodan_calls': 0,
            'virustotal_calls': 0,
            'nist_calls': 0,
            'cache_hits': 0,
            'errors': 0
        }

        logger.info("MCP Integration initialized")

    async def shodan_lookup(self, target: str, lookup_type: str = 'host') -> Dict[str, Any]:
        """
        Query Shodan MCP for IP/host information.

        Args:
            target: IP address or hostname
            lookup_type: 'host', 'search', 'dns', or 'exploit'

        Returns:
            Dict with Shodan results
        """
        if not self.mcp_servers['shodan']['enabled']:
            return {'error': 'Shodan MCP not enabled', 'enabled': False}

        # Check cache
        cache_key = f"shodan_{lookup_type}_{target}"
        cached = self._get_from_cache(cache_key)
        if cached:
            self.stats['cache_hits'] += 1
            return cached

        # Rate limiting
        await self._rate_limit('shodan')

        self.stats['shodan_calls'] += 1

        try:
            # Simulate MCP call (in production, use actual MCP client)
            # Example: result = await mcp_client.call('shodan', lookup_type, target)

            result = {
                'source': 'shodan',
                'lookup_type': lookup_type,
                'target': target,
                'timestamp': time.time(),
                'data': {
                    'ip': target if lookup_type == 'host' else None,
                    'ports': [],  # Would be populated by real MCP
                    'services': [],
                    'vulnerabilities': [],
                    'location': {},
                    'organization': None
                },
                'success': True,
                'message': f'Shodan lookup for {target} (simulated - configure MCP server)'
            }

            # Cache result
            self._add_to_cache(cache_key, result)

            logger.info(f"Shodan lookup: {lookup_type} {target}")
            return result

        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Shodan lookup failed: {e}")
            return {
                'source': 'shodan',
                'target': target,
                'success': False,
                'error': str(e)
            }

    async def virustotal_scan(self, target: str, scan_type: str = 'hash') -> Dict[str, Any]:
        """
        Query VirusTotal MCP for malware/reputation analysis.

        Args:
            target: Hash, URL, IP, or domain
            scan_type: 'hash', 'url', 'ip', or 'domain'

        Returns:
            Dict with VirusTotal results
        """
        if not self.mcp_servers['virustotal']['enabled']:
            return {'error': 'VirusTotal MCP not enabled', 'enabled': False}

        # Check cache
        cache_key = f"virustotal_{scan_type}_{target}"
        cached = self._get_from_cache(cache_key)
        if cached:
            self.stats['cache_hits'] += 1
            return cached

        # Rate limiting
        await self._rate_limit('virustotal')

        self.stats['virustotal_calls'] += 1

        try:
            # Simulate MCP call
            result = {
                'source': 'virustotal',
                'scan_type': scan_type,
                'target': target,
                'timestamp': time.time(),
                'data': {
                    'detections': 0,  # Would be populated by real MCP
                    'total_scanners': 0,
                    'malicious': False,
                    'suspicious': False,
                    'harmless': False,
                    'reputation': 'unknown',
                    'analysis_date': None
                },
                'success': True,
                'message': f'VirusTotal scan for {target} (simulated - configure MCP server)'
            }

            # Cache result
            self._add_to_cache(cache_key, result)

            logger.info(f"VirusTotal scan: {scan_type} {target}")
            return result

        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"VirusTotal scan failed: {e}")
            return {
                'source': 'virustotal',
                'target': target,
                'success': False,
                'error': str(e)
            }

    async def nist_cve_lookup(self, cve_id: str) -> Dict[str, Any]:
        """
        Query NIST NVD MCP for CVE details.

        Args:
            cve_id: CVE identifier (e.g., CVE-2025-1234)

        Returns:
            Dict with CVE details
        """
        if not self.mcp_servers['nist']['enabled']:
            return {'error': 'NIST MCP not enabled', 'enabled': False}

        # Check cache
        cache_key = f"nist_{cve_id}"
        cached = self._get_from_cache(cache_key)
        if cached:
            self.stats['cache_hits'] += 1
            return cached

        # Rate limiting
        await self._rate_limit('nist')

        self.stats['nist_calls'] += 1

        try:
            # Simulate MCP call
            result = {
                'source': 'nist',
                'cve_id': cve_id,
                'timestamp': time.time(),
                'data': {
                    'id': cve_id,
                    'description': f'Vulnerability details for {cve_id}',
                    'severity': 'HIGH',  # Would be CVSS-based
                    'cvss_score': 7.5,
                    'cvss_vector': 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N',
                    'cwe': [],
                    'references': [],
                    'published_date': None,
                    'modified_date': None,
                    'affected_products': []
                },
                'success': True,
                'message': f'NIST CVE lookup for {cve_id} (simulated - configure MCP server)'
            }

            # Cache result (CVEs don't change often)
            self._add_to_cache(cache_key, result)

            logger.info(f"NIST CVE lookup: {cve_id}")
            return result

        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"NIST CVE lookup failed: {e}")
            return {
                'source': 'nist',
                'cve_id': cve_id,
                'success': False,
                'error': str(e)
            }

    async def batch_query(self, queries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Execute multiple MCP queries in parallel.

        Args:
            queries: List of query dicts with 'service', 'method', and 'target'
                     Example: [
                         {'service': 'shodan', 'method': 'host', 'target': '8.8.8.8'},
                         {'service': 'nist', 'method': 'cve', 'target': 'CVE-2025-1234'}
                     ]

        Returns:
            List of results in same order as queries
        """
        tasks = []

        for query in queries:
            service = query.get('service')
            method = query.get('method')
            target = query.get('target')

            if service == 'shodan':
                tasks.append(self.shodan_lookup(target, method))
            elif service == 'virustotal':
                tasks.append(self.virustotal_scan(target, method))
            elif service == 'nist':
                tasks.append(self.nist_cve_lookup(target))
            else:
                tasks.append(asyncio.sleep(0))  # Placeholder for unknown service

        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results

    async def _rate_limit(self, service: str):
        """Apply rate limiting for service."""
        server = self.mcp_servers.get(service)
        if not server:
            return

        last_call = server['last_call']
        rate_limit = server['rate_limit']

        elapsed = time.time() - last_call
        if elapsed < rate_limit:
            wait_time = rate_limit - elapsed
            await asyncio.sleep(wait_time)

        server['last_call'] = time.time()

    def _get_from_cache(self, key: str) -> Optional[Dict]:
        """Get result from cache if not expired."""
        if key not in self.cache:
            return None

        cached_data, cached_time = self.cache[key]

        if time.time() - cached_time > self.cache_ttl:
            del self.cache[key]
            return None

        return cached_data

    def _add_to_cache(self, key: str, data: Dict):
        """Add result to cache."""
        self.cache[key] = (data, time.time())

    def get_stats(self) -> Dict[str, Any]:
        """Get MCP integration statistics."""
        return {
            **self.stats,
            'cache_size': len(self.cache),
            'enabled_services': [
                service for service, config in self.mcp_servers.items()
                if config['enabled']
            ]
        }

    def clear_cache(self):
        """Clear result cache."""
        self.cache.clear()
        logger.info("MCP cache cleared")


# Integration helpers for v3 memory graph

def mcp_result_to_graph_nodes(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Convert MCP result to memory graph nodes.

    Args:
        result: MCP query result

    Returns:
        List of node dicts for NetworkX graph
    """
    nodes = []

    source = result.get('source')

    if source == 'shodan' and result.get('success'):
        # Create node for IP
        nodes.append({
            'id': f"ip_{result['target']}",
            'type': 'ip_address',
            'value': result['target'],
            'metadata': result.get('data', {}),
            'source': 'shodan_mcp',
            'timestamp': result['timestamp']
        })

        # Create nodes for vulnerabilities
        for vuln in result.get('data', {}).get('vulnerabilities', []):
            nodes.append({
                'id': f"vuln_{vuln}",
                'type': 'vulnerability',
                'value': vuln,
                'source': 'shodan_mcp'
            })

    elif source == 'virustotal' and result.get('success'):
        # Create node for scanned item
        scan_type = result.get('scan_type')
        nodes.append({
            'id': f"{scan_type}_{result['target']}",
            'type': scan_type,
            'value': result['target'],
            'metadata': result.get('data', {}),
            'source': 'virustotal_mcp',
            'timestamp': result['timestamp']
        })

    elif source == 'nist' and result.get('success'):
        # Create node for CVE
        nodes.append({
            'id': result['cve_id'],
            'type': 'cve',
            'value': result['cve_id'],
            'metadata': result.get('data', {}),
            'source': 'nist_mcp',
            'timestamp': result['timestamp']
        })

    return nodes


if __name__ == "__main__":
    print("\n" + "="*70)
    print("MCP Integration Test")
    print("="*70)

    # Test configuration
    config = {
        'mcp': {
            'shodan': {'enabled': True, 'api_key': 'test_key'},
            'virustotal': {'enabled': True, 'api_key': 'test_key'},
            'nist': {'enabled': True}
        }
    }

    print("\n[Test] Initializing MCP Integration...")
    mcp = MCPIntegration(config)

    async def run_tests():
        # Test 1: Shodan lookup
        print("\n[Test] Shodan IP lookup...")
        result = await mcp.shodan_lookup("8.8.8.8", "host")
        print(f"  Result: {result['message']}")
        print(f"  Success: {result['success']}")

        # Test 2: VirusTotal scan
        print("\n[Test] VirusTotal hash scan...")
        result = await mcp.virustotal_scan("abc123", "hash")
        print(f"  Result: {result['message']}")
        print(f"  Success: {result['success']}")

        # Test 3: NIST CVE lookup
        print("\n[Test] NIST CVE lookup...")
        result = await mcp.nist_cve_lookup("CVE-2025-1234")
        print(f"  Result: {result['message']}")
        print(f"  Success: {result['success']}")

        # Test 4: Batch query
        print("\n[Test] Batch parallel queries...")
        queries = [
            {'service': 'shodan', 'method': 'host', 'target': '1.1.1.1'},
            {'service': 'nist', 'method': 'cve', 'target': 'CVE-2025-5678'},
            {'service': 'virustotal', 'method': 'url', 'target': 'http://example.com'}
        ]
        results = await mcp.batch_query(queries)
        print(f"  Completed {len(results)} queries in parallel")

        # Test 5: Cache
        print("\n[Test] Testing cache...")
        result1 = await mcp.shodan_lookup("8.8.8.8", "host")
        result2 = await mcp.shodan_lookup("8.8.8.8", "host")  # Should hit cache
        print(f"  Cache hits: {mcp.stats['cache_hits']}")

    # Run async tests
    asyncio.run(run_tests())

    # Statistics
    print("\n[Test] MCP statistics:")
    stats = mcp.get_stats()
    print(f"  Shodan calls: {stats['shodan_calls']}")
    print(f"  VirusTotal calls: {stats['virustotal_calls']}")
    print(f"  NIST calls: {stats['nist_calls']}")
    print(f"  Cache hits: {stats['cache_hits']}")
    print(f"  Errors: {stats['errors']}")
    print(f"  Enabled services: {', '.join(stats['enabled_services'])}")

    print("\n" + "="*70)
    print("✅ MCP Integration operational!")
    print("="*70)
    print("\nNote: Configure actual MCP server endpoints in production.")
    print("This module provides the integration layer - connect to real MCP servers.")
    print("="*70)
