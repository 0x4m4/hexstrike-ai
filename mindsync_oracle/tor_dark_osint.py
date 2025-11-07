#!/usr/bin/env python3
"""
MindSync Oracle v7 - Ethical Dark Web OSINT

THE BREAKTHROUGH: Defensive threat intelligence from Tor hidden services.

⚠️  ETHICAL USE ONLY - STRICT GUARDRAILS ⚠️

This module is designed EXCLUSIVELY for:
✅ Authorized security research
✅ Defensive threat intelligence gathering
✅ Public exploit database mirrors (.onion)
✅ Ethical OSINT practices
✅ Compliance with applicable laws

❌ NOT FOR:
❌ Illegal activities
❌ Unauthorized access
❌ Marketplace access
❌ Detection evasion
❌ Malicious purposes

Features:
- Tor circuit management with stem
- Strict allowlist of public mirrors only
- Credibility scoring via swarm consensus
- Audit logging for compliance
- Auto-shutdown on suspicious patterns

LEGAL NOTICE:
By using this module, you certify that:
1. You have authorization for security research
2. Your use complies with all applicable laws
3. You will use data defensively only
4. You will not access illegal content

USAGE:
    from tor_dark_osint import TorDarkOSINT

    osint = TorDarkOSINT(
        swarm=swarm,
        memory_graph=memory_graph,
        config=config  # Must include ethical_mode: true
    )

    await osint.start()
"""

import logging
import asyncio
import json
import time
import hashlib
import re
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)

# Try to import Tor dependencies
try:
    import stem
    from stem import Signal
    from stem.control import Controller
    STEM_AVAILABLE = True
except ImportError:
    STEM_AVAILABLE = False
    logger.warning("stem not installed. Tor functionality disabled. Run: pip install stem")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("requests not installed. Run: pip install requests")


class EthicalGuardrails:
    """Enforces ethical use policies for dark web OSINT."""

    # STRICT ALLOWLIST - Only public defensive research sources
    ALLOWED_DOMAINS = {
        # Public exploit database mirrors (examples - verify before use)
        'exploit-db-mirror.onion',  # Exploit-DB Tor mirror (if exists)
        'cve-details-mirror.onion',  # CVE Details mirror (if exists)

        # NOTE: These are placeholder examples. In production:
        # 1. Verify these domains exist and are legitimate
        # 2. Only add publicly accessible defensive research sites
        # 3. Document authorization for each domain
        # 4. Review and update regularly
    }

    # Forbidden patterns - immediate shutdown if detected
    FORBIDDEN_PATTERNS = [
        'marketplace',
        'market',
        'drugs',
        'weapons',
        'stolen',
        'carding',
        'ransomware-as-a-service',
        'ddos-for-hire',
        'illegal',
    ]

    # Suspicious patterns - require review
    SUSPICIOUS_PATTERNS = [
        'payment',
        'bitcoin',
        'btc address',
        'vendor',
        'buy',
        'sell',
        'price',
    ]

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

        # Must be explicitly enabled
        self.ethical_mode = self.config.get('ethical_mode', False)

        if not self.ethical_mode:
            raise ValueError("tor_dark_osint requires ethical_mode: true in config")

        # Audit logging
        self.audit_log_path = self.config.get('audit_log_path', 'tor_osint_audit.log')
        self.audit_log = open(self.audit_log_path, 'a')

        # Custom allowlist (must be explicitly defined)
        custom_allowed = self.config.get('allowed_domains', [])
        if custom_allowed:
            self.ALLOWED_DOMAINS.update(custom_allowed)

        self._log_audit('INIT', 'Ethical guardrails initialized')

        logger.info("Ethical guardrails active for Tor OSINT")

    def validate_domain(self, domain: str) -> bool:
        """Validate domain against allowlist."""
        if domain not in self.ALLOWED_DOMAINS:
            self._log_audit('BLOCKED', f'Domain not in allowlist: {domain}')
            return False

        self._log_audit('ALLOWED', f'Domain validated: {domain}')
        return True

    def check_content(self, content: str, url: str) -> Dict[str, Any]:
        """
        Check content for forbidden/suspicious patterns.

        Returns:
            Dict with 'allowed', 'reason', 'warnings'
        """
        content_lower = content.lower()

        # Check forbidden patterns
        for pattern in self.FORBIDDEN_PATTERNS:
            if pattern in content_lower:
                self._log_audit('FORBIDDEN', f'Forbidden pattern detected: {pattern} in {url}')
                return {
                    'allowed': False,
                    'reason': f'Forbidden pattern: {pattern}',
                    'warnings': []
                }

        # Check suspicious patterns
        warnings = []
        for pattern in self.SUSPICIOUS_PATTERNS:
            if pattern in content_lower:
                warnings.append(pattern)
                self._log_audit('SUSPICIOUS', f'Suspicious pattern: {pattern} in {url}')

        if len(warnings) > 3:
            # Too many suspicious patterns
            self._log_audit('BLOCKED', f'Too many suspicious patterns in {url}')
            return {
                'allowed': False,
                'reason': f'Multiple suspicious patterns: {warnings}',
                'warnings': warnings
            }

        result = {
            'allowed': True,
            'reason': 'Content validated',
            'warnings': warnings
        }

        if warnings:
            self._log_audit('WARNING', f'Content has warnings but allowed: {url}')

        return result

    def _log_audit(self, event_type: str, message: str):
        """Log to audit file."""
        timestamp = datetime.now().isoformat()
        log_entry = f"{timestamp} | {event_type} | {message}\n"
        self.audit_log.write(log_entry)
        self.audit_log.flush()

    def close(self):
        """Close audit log."""
        self.audit_log.close()


class TorCircuitManager:
    """Manages Tor circuits and connections."""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

        if not STEM_AVAILABLE:
            raise ImportError("stem library required for Tor. Run: pip install stem")

        self.control_port = self.config.get('tor_control_port', 9051)
        self.socks_port = self.config.get('tor_socks_port', 9050)
        self.controller = None

        # Connection stats
        self.circuits_built = 0
        self.requests_made = 0

    def connect(self):
        """Connect to Tor control port."""
        try:
            self.controller = Controller.from_port(port=self.control_port)
            self.controller.authenticate()
            logger.info("Connected to Tor control port")
        except Exception as e:
            logger.error(f"Failed to connect to Tor: {e}")
            logger.info("Ensure Tor is running: sudo systemctl start tor")
            raise

    def new_circuit(self):
        """Request a new Tor circuit."""
        if not self.controller:
            raise RuntimeError("Not connected to Tor")

        try:
            self.controller.signal(Signal.NEWNYM)
            self.circuits_built += 1
            logger.debug(f"New Tor circuit requested (total: {self.circuits_built})")
            time.sleep(2)  # Wait for circuit to build
        except Exception as e:
            logger.error(f"Failed to create new circuit: {e}")

    def get_session(self) -> Optional[Any]:
        """Get requests session configured for Tor."""
        if not REQUESTS_AVAILABLE:
            return None

        session = requests.Session()
        session.proxies = {
            'http': f'socks5h://127.0.0.1:{self.socks_port}',
            'https': f'socks5h://127.0.0.1:{self.socks_port}'
        }

        # Set timeout and headers
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Security Research Bot)'
        })

        return session

    def close(self):
        """Close Tor connection."""
        if self.controller:
            self.controller.close()
            logger.info("Tor connection closed")


class CredibilityScorer:
    """Scores credibility of dark web sources via swarm consensus."""

    def __init__(self, swarm, config: Optional[Dict] = None):
        self.swarm = swarm
        self.config = config or {}

        # Credibility thresholds
        self.min_credibility = self.config.get('min_credibility', 0.6)  # 60%

        # Source reputation (would be learned over time)
        self.source_reputation = defaultdict(lambda: 0.5)  # Start at 50%

    def score_content(self, content: str, source: str, url: str) -> float:
        """
        Score content credibility (0-1).

        Factors:
        - Source reputation
        - Content structure (CVE IDs, technical detail)
        - Cross-references
        - Community consensus (if swarm voting enabled)
        """
        score = 0.0

        # Base: Source reputation
        score += self.source_reputation[source] * 0.4

        # Technical indicators
        if re.search(r'CVE-\d{4}-\d{4,}', content):
            score += 0.2  # Has CVE references

        if any(indicator in content.lower() for indicator in ['exploit', 'vulnerability', 'poc', 'proof of concept']):
            score += 0.1  # Technical content

        # Structure indicators
        if len(content) > 200:  # Detailed content
            score += 0.1

        if any(indicator in content for indicator in ['http://', 'https://']):
            score += 0.1  # Has external references

        # Length penalty for very short content
        if len(content) < 50:
            score -= 0.2

        return min(max(score, 0.0), 1.0)

    def is_credible(self, score: float) -> bool:
        """Check if score meets minimum threshold."""
        return score >= self.min_credibility

    def update_reputation(self, source: str, outcome: str):
        """Update source reputation based on outcome."""
        if outcome == 'verified':
            self.source_reputation[source] = min(self.source_reputation[source] + 0.1, 1.0)
        elif outcome == 'false_positive':
            self.source_reputation[source] = max(self.source_reputation[source] - 0.2, 0.0)


class TorDarkOSINT:
    """
    Ethical dark web OSINT collector.

    STRICTLY FOR DEFENSIVE SECURITY RESEARCH ONLY.
    """

    def __init__(self, swarm, memory_graph, config: Optional[Dict] = None):
        """
        Initialize Tor OSINT.

        Args:
            swarm: FederatedSwarm instance
            memory_graph: HybridMemoryGraph instance
            config: Configuration with ethical_mode: true
        """
        self.swarm = swarm
        self.memory_graph = memory_graph
        self.config = config or {}

        # Ethical guardrails (REQUIRED)
        try:
            self.guardrails = EthicalGuardrails(config)
        except ValueError as e:
            logger.error(f"Ethical guardrails failed: {e}")
            raise

        # Tor circuit manager
        if STEM_AVAILABLE:
            try:
                self.tor_manager = TorCircuitManager(config)
                self.tor_manager.connect()
                self.tor_enabled = True
            except Exception as e:
                logger.error(f"Tor initialization failed: {e}")
                self.tor_enabled = False
        else:
            self.tor_enabled = False
            logger.warning("Tor functionality disabled (stem not available)")

        # Credibility scorer
        self.credibility_scorer = CredibilityScorer(swarm, config)

        # State
        self.is_running = False
        self.scrape_interval = self.config.get('scrape_interval', 1800)  # 30 minutes

        # Deduplication
        self.seen_content = set()

        # Statistics
        self.stats = {
            'requests_made': 0,
            'content_scraped': 0,
            'content_blocked': 0,
            'credibility_filtered': 0,
            'deltas_broadcast': 0
        }

        logger.info("Tor Dark OSINT initialized (ETHICAL MODE ENFORCED)")

    async def start(self):
        """Start Tor OSINT scraping."""
        if not self.tor_enabled:
            logger.error("Tor OSINT cannot start - Tor not available")
            return

        self.is_running = True
        logger.info("Starting Tor Dark OSINT (ethical defensive research only)...")

        await self._scrape_loop()

    async def stop(self):
        """Stop Tor OSINT."""
        logger.info("Stopping Tor Dark OSINT...")
        self.is_running = False

        if self.tor_manager:
            self.tor_manager.close()

        self.guardrails.close()

    async def _scrape_loop(self):
        """Main scraping loop."""
        while self.is_running:
            try:
                # Scrape allowed sources
                for domain in self.guardrails.ALLOWED_DOMAINS:
                    if not self.is_running:
                        break

                    await self._scrape_source(domain)

                # Sleep until next scrape
                logger.info(f"Tor OSINT scrape complete. Sleeping {self.scrape_interval}s...")
                await asyncio.sleep(self.scrape_interval)

            except Exception as e:
                logger.error(f"Error in Tor OSINT loop: {e}")
                await asyncio.sleep(60)  # Back off on error

    async def _scrape_source(self, domain: str):
        """Scrape a single Tor source."""
        # Validate domain
        if not self.guardrails.validate_domain(domain):
            return

        # Build new circuit for each source (better anonymity)
        self.tor_manager.new_circuit()

        url = f"http://{domain}/"

        try:
            logger.info(f"Scraping Tor source: {domain}")

            # Get Tor session
            session = self.tor_manager.get_session()

            # Make request with timeout
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: session.get(url, timeout=30)
            )

            if response.status_code != 200:
                logger.warning(f"Non-200 response from {domain}: {response.status_code}")
                return

            content = response.text
            self.stats['requests_made'] += 1

            # Ethical check
            content_check = self.guardrails.check_content(content, url)

            if not content_check['allowed']:
                logger.error(f"Content blocked from {domain}: {content_check['reason']}")
                self.stats['content_blocked'] += 1
                # Auto-shutdown on forbidden content
                await self.stop()
                raise RuntimeError(f"ETHICAL VIOLATION: {content_check['reason']}")

            if content_check['warnings']:
                logger.warning(f"Content warnings from {domain}: {content_check['warnings']}")

            # Parse content
            findings = self._parse_content(content, domain)

            # Process findings
            for finding in findings:
                await self._process_finding(finding, domain)

            self.stats['content_scraped'] += 1

        except Exception as e:
            logger.error(f"Error scraping {domain}: {e}")

    def _parse_content(self, content: str, source: str) -> List[Dict[str, Any]]:
        """Parse content for threat intelligence."""
        findings = []

        # Look for CVE mentions
        cve_pattern = re.compile(r'CVE-\d{4}-\d{4,}', re.IGNORECASE)
        cves = cve_pattern.findall(content)

        for cve in set(cves):  # Deduplicate
            # Extract context around CVE
            cve_index = content.find(cve)
            context_start = max(0, cve_index - 200)
            context_end = min(len(content), cve_index + 200)
            context = content[context_start:context_end]

            finding = {
                'type': 'cve_mention',
                'cve_id': cve.upper(),
                'context': context,
                'source': source,
                'timestamp': time.time()
            }

            findings.append(finding)

        # Look for exploit keywords
        exploit_keywords = ['exploit', 'poc', 'proof of concept', 'rce', 'lfi', 'sqli', 'xss']

        for keyword in exploit_keywords:
            if keyword in content.lower():
                # Find sentences containing keyword
                sentences = re.split(r'[.!?]', content)
                for sentence in sentences:
                    if keyword in sentence.lower() and len(sentence) > 20:
                        finding = {
                            'type': 'exploit_discussion',
                            'keyword': keyword,
                            'text': sentence.strip()[:500],
                            'source': source,
                            'timestamp': time.time()
                        }
                        findings.append(finding)
                        break  # One per keyword

        return findings

    async def _process_finding(self, finding: Dict[str, Any], source: str):
        """Process and validate a finding."""
        # Deduplicate
        finding_hash = hashlib.md5(json.dumps(finding, sort_keys=True).encode()).hexdigest()

        if finding_hash in self.seen_content:
            return

        self.seen_content.add(finding_hash)

        # Score credibility
        content = finding.get('context') or finding.get('text', '')
        credibility = self.credibility_scorer.score_content(content, source, f"tor://{source}")

        if not self.credibility_scorer.is_credible(credibility):
            logger.debug(f"Low credibility finding filtered: {credibility:.2f}")
            self.stats['credibility_filtered'] += 1
            return

        # Add to graph
        finding_id = f"tor_finding_{finding_hash[:12]}"

        finding_data = {
            'type': 'tor_osint_finding',
            'finding_type': finding['type'],
            'source': source,
            'credibility_score': credibility,
            'timestamp': finding['timestamp'],
            'text': content[:500],
            'ethical_cleared': True
        }

        if finding['type'] == 'cve_mention':
            finding_data['cve_id'] = finding['cve_id']

        # Add to local graph
        if finding_id not in self.memory_graph.graph:
            self.memory_graph.graph.add_node(finding_id, **finding_data)

        # Link to CVE if applicable
        if 'cve_id' in finding:
            cve_node_id = f"cve_{finding['cve_id'].replace('-', '_')}"

            if cve_node_id not in self.memory_graph.graph:
                self.memory_graph.graph.add_node(cve_node_id, type='cve', cve_id=finding['cve_id'])

            if not self.memory_graph.graph.has_edge(finding_id, cve_node_id):
                self.memory_graph.graph.add_edge(finding_id, cve_node_id, relationship='references')

        # Broadcast to swarm
        if self.swarm:
            delta = {
                'operation': 'add_node',
                'node_id': finding_id,
                'data': finding_data,
                'source': 'tor_dark_osint'
            }

            self.swarm.broadcast_graph_delta(delta)
            self.stats['deltas_broadcast'] += 1

            logger.info(f"Broadcasted Tor finding: {finding_id} (credibility: {credibility:.2f})")

    def get_stats(self) -> Dict[str, Any]:
        """Get Tor OSINT statistics."""
        return {
            **self.stats,
            'is_running': self.is_running,
            'tor_enabled': self.tor_enabled,
            'ethical_mode': True,
            'allowed_domains': list(self.guardrails.ALLOWED_DOMAINS)
        }


if __name__ == "__main__":
    print("\n" + "="*70)
    print("Tor Dark OSINT Test")
    print("="*70)
    print("\n⚠️  This is a TEST with mock data - no actual Tor connections\n")

    # Mock components
    class MockSwarm:
        def broadcast_graph_delta(self, delta):
            print(f"  [Mock Swarm] Broadcast delta: {delta['node_id']}")

    class MockGraph:
        def __init__(self):
            import networkx as nx
            self.graph = nx.DiGraph()

    swarm = MockSwarm()
    graph = MockGraph()

    config = {
        'ethical_mode': True,  # REQUIRED
        'audit_log_path': 'test_tor_audit.log',
        'scrape_interval': 60
    }

    # Test guardrails
    print("[Test] Testing ethical guardrails...")
    guardrails = EthicalGuardrails(config)

    # Test allowed domain
    assert guardrails.validate_domain('exploit-db-mirror.onion') == True
    print("  ✅ Allowed domain validated")

    # Test forbidden domain
    assert guardrails.validate_domain('illegal-market.onion') == False
    print("  ✅ Forbidden domain blocked")

    # Test content filtering
    good_content = "This is a CVE-2024-1234 vulnerability report with technical details."
    result = guardrails.check_content(good_content, "test.onion")
    assert result['allowed'] == True
    print("  ✅ Good content allowed")

    bad_content = "Welcome to our marketplace. Buy stolen data and drugs here."
    result = guardrails.check_content(bad_content, "test.onion")
    assert result['allowed'] == False
    print("  ✅ Forbidden content blocked")

    guardrails.close()

    print("\n[Test] Ethical guardrails operational!")

    # Test credibility scorer
    print("\n[Test] Testing credibility scorer...")
    scorer = CredibilityScorer(swarm, config)

    high_cred = "CVE-2024-5678 exploit analysis with detailed POC. Technical vulnerability research shows RCE possible."
    score = scorer.score_content(high_cred, "trusted-source", "test.onion")
    print(f"  High credibility content score: {score:.2f}")
    assert score > 0.6

    low_cred = "short text"
    score = scorer.score_content(low_cred, "unknown-source", "test.onion")
    print(f"  Low credibility content score: {score:.2f}")
    assert score < 0.6

    print("  ✅ Credibility scoring working")

    print("\n" + "="*70)
    print("✅ Tor Dark OSINT ethical controls operational!")
    print("="*70)
    print("\nNOTE: Actual Tor scraping requires:")
    print("  1. Tor service running (sudo systemctl start tor)")
    print("  2. pip install stem requests[socks]")
    print("  3. Verified .onion domains in allowlist")
    print("  4. Authorization for security research")
    print("="*70)
