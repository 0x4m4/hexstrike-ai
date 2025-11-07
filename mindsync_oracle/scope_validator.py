#!/usr/bin/env python3
"""
MindSync Oracle v8 - Scope Validator

TARGET AUTHORIZATION VALIDATION

⚠️ ETHICAL SAFEGUARD - HARD SCOPE ENFORCEMENT ⚠️

This module validates all targets against authorized scope defined in
scope configuration files. NO actions are permitted against unauthorized targets.

Features:
- Load scope from YAML/JSON files
- IP address validation (individual, CIDR ranges)
- Domain/hostname validation (exact match, wildcards)
- URL validation with path constraints
- Hard rejection of out-of-scope targets
- Scope file format validation
- Authorization expiry checking
- Audit logging of all checks

Scope File Format (authorized_scope.yaml):
```yaml
authorization:
  granted_by: "Security Team Lead"
  granted_date: "2025-01-15"
  expires: "2025-12-31"
  purpose: "CTF Competition / Red Team Exercise / Bug Bounty"
  engagement_id: "ENG-2025-001"

targets:
  ip_addresses:
    - "192.168.1.100"
    - "10.0.0.0/24"
  domains:
    - "*.lab.local"
    - "testserver.company.com"
  urls:
    - "https://vulnerable.app/test/*"

  excluded:
    - "192.168.1.1"  # Gateway - do not touch
    - "prod.company.com"  # Production - excluded
```

STRICTLY FOR:
✅ CTF competitions (authorized platforms)
✅ Personal lab environments (owned infrastructure)
✅ Authorized red team engagements (written permission)
✅ Bug bounty programs (in-scope targets only)

FORBIDDEN:
❌ Testing production systems without authorization
❌ Scanning internet ranges
❌ Ignoring scope restrictions
❌ Bypassing validation

USAGE:
    from scope_validator import ScopeValidator

    validator = ScopeValidator(scope_file="authorized_scope.yaml")

    if validator.validate_target("192.168.1.100"):
        print("✅ Target is in scope")
    else:
        print("❌ Target is OUT OF SCOPE - do not proceed")
"""

import logging
import yaml
import json
import ipaddress
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import re
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class ScopeValidationResult:
    """Result of scope validation."""

    def __init__(self, valid: bool, reason: str, target: str, matched_rule: Optional[str] = None):
        self.valid = valid
        self.reason = reason
        self.target = target
        self.matched_rule = matched_rule
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            'valid': self.valid,
            'reason': self.reason,
            'target': self.target,
            'matched_rule': self.matched_rule,
            'timestamp': self.timestamp
        }


class ScopeValidator:
    """
    Target Scope Validator.

    Validates targets against authorized scope configuration.

    ⚠️ HARD ENFORCEMENT - NO BYPASSES ALLOWED ⚠️
    """

    def __init__(self, scope_file: Optional[str] = "authorized_scope.yaml",
                 audit_log_path: str = "scope_validation_audit.log"):
        """
        Initialize Scope Validator.

        Args:
            scope_file: Path to scope configuration file
            audit_log_path: Path to audit log
        """
        self.scope_file = scope_file
        self.audit_log_path = audit_log_path

        # Scope configuration
        self.scope_config = None
        self.authorization = None
        self.targets = None

        # Validation results
        self.validation_results = []

        # Statistics
        self.stats = {
            'total_validations': 0,
            'approved': 0,
            'rejected': 0,
            'by_type': {}
        }

        # Load scope
        if scope_file:
            self.load_scope(scope_file)
        else:
            logger.warning("No scope file provided - all targets will be rejected by default")

        logger.info("Scope Validator initialized (HARD ENFORCEMENT MODE)")

    def load_scope(self, scope_file: str) -> bool:
        """Load scope configuration from file."""
        try:
            with open(scope_file, 'r') as f:
                if scope_file.endswith('.json'):
                    self.scope_config = json.load(f)
                else:
                    self.scope_config = yaml.safe_load(f)

            # Validate scope config structure
            if not self._validate_scope_config():
                logger.error("Invalid scope configuration format")
                self.scope_config = None
                return False

            self.authorization = self.scope_config.get('authorization', {})
            self.targets = self.scope_config.get('targets', {})

            # Check authorization expiry
            if not self._check_authorization_valid():
                logger.error("Authorization expired or invalid")
                self.scope_config = None
                return False

            logger.info(f"Scope loaded from {scope_file}")
            logger.info(f"Authorization: {self.authorization.get('granted_by')} for {self.authorization.get('purpose')}")
            return True

        except FileNotFoundError:
            logger.error(f"Scope file not found: {scope_file}")
            return False
        except Exception as e:
            logger.error(f"Failed to load scope file: {e}")
            return False

    def _validate_scope_config(self) -> bool:
        """Validate scope configuration structure."""
        if not self.scope_config:
            return False

        # Check required fields
        if 'authorization' not in self.scope_config:
            logger.error("Scope config missing 'authorization' section")
            return False

        if 'targets' not in self.scope_config:
            logger.error("Scope config missing 'targets' section")
            return False

        auth = self.scope_config['authorization']
        required_auth_fields = ['granted_by', 'granted_date', 'purpose']

        for field in required_auth_fields:
            if field not in auth:
                logger.error(f"Authorization missing required field: {field}")
                return False

        return True

    def _check_authorization_valid(self) -> bool:
        """Check if authorization is still valid."""
        if not self.authorization:
            return False

        # Check expiry
        expires = self.authorization.get('expires')
        if expires:
            try:
                expiry_date = datetime.fromisoformat(expires)
                if datetime.now() > expiry_date:
                    logger.error(f"Authorization expired on {expires}")
                    return False
            except ValueError:
                logger.error(f"Invalid expiry date format: {expires}")
                return False

        return True

    def validate_target(self, target: str, target_type: Optional[str] = None) -> bool:
        """
        Validate if target is in scope.

        Args:
            target: Target to validate (IP, domain, URL)
            target_type: Optional type hint ('ip', 'domain', 'url')

        Returns:
            True if in scope, False otherwise
        """
        self.stats['total_validations'] += 1

        # Default: reject if no scope loaded
        if not self.scope_config:
            result = ScopeValidationResult(
                valid=False,
                reason="No scope configuration loaded",
                target=target
            )
            self._log_validation(result)
            self.stats['rejected'] += 1
            return False

        # Auto-detect target type if not provided
        if not target_type:
            target_type = self._detect_target_type(target)

        self.stats['by_type'][target_type] = self.stats['by_type'].get(target_type, 0) + 1

        # Check exclusions first
        if self._is_excluded(target):
            result = ScopeValidationResult(
                valid=False,
                reason="Target is explicitly excluded",
                target=target
            )
            self._log_validation(result)
            self.stats['rejected'] += 1
            return False

        # Validate by type
        if target_type == 'ip':
            valid, reason, rule = self._validate_ip(target)
        elif target_type == 'domain':
            valid, reason, rule = self._validate_domain(target)
        elif target_type == 'url':
            valid, reason, rule = self._validate_url(target)
        else:
            valid, reason, rule = False, f"Unknown target type: {target_type}", None

        result = ScopeValidationResult(
            valid=valid,
            reason=reason,
            target=target,
            matched_rule=rule
        )

        self._log_validation(result)

        if valid:
            self.stats['approved'] += 1
        else:
            self.stats['rejected'] += 1

        return valid

    def _detect_target_type(self, target: str) -> str:
        """Auto-detect target type."""
        # URL detection
        if target.startswith(('http://', 'https://', 'ftp://')):
            return 'url'

        # IP detection (v4 or v6)
        try:
            ipaddress.ip_address(target)
            return 'ip'
        except ValueError:
            pass

        # CIDR detection
        try:
            ipaddress.ip_network(target, strict=False)
            return 'ip'
        except ValueError:
            pass

        # Default to domain
        return 'domain'

    def _is_excluded(self, target: str) -> bool:
        """Check if target is explicitly excluded."""
        excluded = self.targets.get('excluded', [])

        for exclusion in excluded:
            if self._matches_pattern(target, exclusion):
                return True

        return False

    def _validate_ip(self, target: str) -> tuple:
        """Validate IP address."""
        try:
            target_ip = ipaddress.ip_address(target)
        except ValueError:
            return False, "Invalid IP address format", None

        allowed_ips = self.targets.get('ip_addresses', [])

        for allowed in allowed_ips:
            try:
                # Check if it's a CIDR range
                if '/' in allowed:
                    network = ipaddress.ip_network(allowed, strict=False)
                    if target_ip in network:
                        return True, f"IP in authorized range: {allowed}", allowed
                else:
                    allowed_ip = ipaddress.ip_address(allowed)
                    if target_ip == allowed_ip:
                        return True, f"IP matches authorized: {allowed}", allowed
            except ValueError:
                logger.warning(f"Invalid IP in scope config: {allowed}")

        return False, "IP not in authorized scope", None

    def _validate_domain(self, target: str) -> tuple:
        """Validate domain/hostname."""
        allowed_domains = self.targets.get('domains', [])

        for allowed in allowed_domains:
            if self._matches_domain_pattern(target, allowed):
                return True, f"Domain matches authorized: {allowed}", allowed

        return False, "Domain not in authorized scope", None

    def _validate_url(self, target: str) -> tuple:
        """Validate URL."""
        try:
            parsed = urlparse(target)
        except Exception:
            return False, "Invalid URL format", None

        # Check domain first
        domain_valid, _, domain_rule = self._validate_domain(parsed.netloc)

        allowed_urls = self.targets.get('urls', [])

        for allowed_url in allowed_urls:
            if self._matches_url_pattern(target, allowed_url):
                return True, f"URL matches authorized: {allowed_url}", allowed_url

        # If domain is valid but no specific URL match, check if wildcard domain match
        if domain_valid:
            return True, f"URL domain matches authorized: {domain_rule}", domain_rule

        return False, "URL not in authorized scope", None

    def _matches_pattern(self, target: str, pattern: str) -> bool:
        """Check if target matches pattern (supports wildcards)."""
        # Convert wildcard pattern to regex
        regex_pattern = re.escape(pattern).replace(r'\*', '.*')
        regex_pattern = f'^{regex_pattern}$'

        return re.match(regex_pattern, target, re.IGNORECASE) is not None

    def _matches_domain_pattern(self, target: str, pattern: str) -> bool:
        """Check if domain matches pattern."""
        # Exact match
        if target.lower() == pattern.lower():
            return True

        # Wildcard subdomain (*.example.com)
        if pattern.startswith('*.'):
            base_domain = pattern[2:]
            if target.lower().endswith('.' + base_domain.lower()) or target.lower() == base_domain.lower():
                return True

        return False

    def _matches_url_pattern(self, target: str, pattern: str) -> bool:
        """Check if URL matches pattern."""
        # Simple wildcard matching
        return self._matches_pattern(target, pattern)

    def _log_validation(self, result: ScopeValidationResult):
        """Log validation result."""
        self.validation_results.append(result)

        status = "APPROVED" if result.valid else "REJECTED"
        log_line = f"{result.timestamp} | {status} | {result.target} | {result.reason}\n"

        try:
            with open(self.audit_log_path, 'a') as f:
                f.write(log_line)
        except Exception as e:
            logger.error(f"Failed to write to audit log: {e}")

        if result.valid:
            logger.info(f"✅ Scope validation APPROVED: {result.target}")
        else:
            logger.warning(f"❌ Scope validation REJECTED: {result.target} - {result.reason}")

    def get_stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        approval_rate = 0.0
        if self.stats['total_validations'] > 0:
            approval_rate = self.stats['approved'] / self.stats['total_validations']

        return {
            **self.stats,
            'approval_rate': approval_rate,
            'scope_loaded': self.scope_config is not None
        }


if __name__ == "__main__":
    print("\n" + "="*70)
    print("Scope Validator Test")
    print("="*70)
    print("\n⚠️  ETHICAL SAFEGUARD - HARD SCOPE ENFORCEMENT\n")

    # Create example scope file
    example_scope = {
        'authorization': {
            'granted_by': 'Test Administrator',
            'granted_date': '2025-01-01',
            'expires': '2025-12-31',
            'purpose': 'CTF Testing / Lab Environment',
            'engagement_id': 'TEST-001'
        },
        'targets': {
            'ip_addresses': [
                '127.0.0.1',
                '192.168.1.100',
                '10.0.0.0/24'
            ],
            'domains': [
                '*.lab.local',
                'testserver.com'
            ],
            'urls': [
                'https://vulnerable.app/test/*'
            ],
            'excluded': [
                '192.168.1.1',
                'prod.company.com'
            ]
        }
    }

    # Write example scope
    with open('test_scope.yaml', 'w') as f:
        yaml.dump(example_scope, f)

    print("[Test] Created example scope file: test_scope.yaml")

    # Initialize validator
    print("\n[Test] Initializing Scope Validator...")
    validator = ScopeValidator(scope_file='test_scope.yaml', audit_log_path='test_scope_audit.log')

    # Test cases
    test_targets = [
        ('127.0.0.1', 'ip', True, 'Localhost - in scope'),
        ('192.168.1.100', 'ip', True, 'Specific IP - in scope'),
        ('10.0.0.50', 'ip', True, 'IP in CIDR range - in scope'),
        ('8.8.8.8', 'ip', False, 'Public IP - out of scope'),
        ('192.168.1.1', 'ip', False, 'Excluded IP - should reject'),
        ('test.lab.local', 'domain', True, 'Wildcard domain match - in scope'),
        ('testserver.com', 'domain', True, 'Exact domain match - in scope'),
        ('google.com', 'domain', False, 'Domain - out of scope'),
        ('prod.company.com', 'domain', False, 'Excluded domain - should reject'),
        ('https://vulnerable.app/test/page', 'url', True, 'URL - in scope'),
        ('https://vulnerable.app/admin', 'url', False, 'URL path - out of scope')
    ]

    print("\n[Test] Running validation tests:\n")

    for target, target_type, expected, description in test_targets:
        result = validator.validate_target(target, target_type)
        status = "✅" if result == expected else "❌"
        print(f"{status} {description}")
        print(f"   Target: {target} | Expected: {expected} | Got: {result}")

    print("\n[Test] Validation statistics:")
    stats = validator.get_stats()
    print(f"  Total validations: {stats['total_validations']}")
    print(f"  Approved: {stats['approved']}")
    print(f"  Rejected: {stats['rejected']}")
    print(f"  Approval rate: {stats['approval_rate']:.0%}")
    print(f"  By type: {stats['by_type']}")

    print("\n" + "="*70)
    print("✅ Scope Validator operational!")
    print("="*70)
    print("\n⚠️  Remember: Only test authorized targets.")
    print("All validations are logged for audit purposes.")
    print("="*70)
