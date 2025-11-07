# MindSync Oracle v7 - Ethical Guidelines & Usage Policy

## ⚠️ IMPORTANT - ETHICAL USE ONLY ⚠️

v7 introduces real-time threat intelligence capabilities including dark web OSINT. These features are **STRICTLY** for authorized, ethical, and defensive security research purposes.

---

## Ethical Use Requirements

By using MindSync Oracle v7, you **MUST**:

✅ **Have proper authorization** for security research activities
✅ **Comply with all applicable laws** in your jurisdiction
✅ **Use defensively only** - never for offensive or malicious purposes
✅ **Document your authorization** in audit logs
✅ **Respect privacy** and only access public information
✅ **Follow responsible disclosure** for any vulnerabilities discovered

---

## Forbidden Activities

❌ **NEVER use v7 for**:
- Illegal activities or unauthorized access
- Accessing illegal marketplaces or services
- Purchasing illicit goods or services
- Evading detection for malicious purposes
- Mass targeting or DoS attacks
- Supply chain compromise
- Any activity violating local, state, or federal laws

---

## v7 Features & Ethical Controls

### 1. Real-Time X/Twitter Firehose (`realtime_x_stream.py`)

**Purpose**: Monitor public X/Twitter posts for CVE mentions, exploit discussions, and security researcher activity

**Ethical Controls**:
- Only accesses public posts
- Keyword-based filtering (no broad surveillance)
- Rate limiting to prevent abuse
- Deduplication to minimize API load
- No personal data collection beyond publicly shared security info

**Configuration**:
```yaml
realtime_x:
  enabled: true
  keywords:
    - CVE
    - exploit
    - vulnerability
```

**Acceptable Use**:
- Monitoring for new CVE disclosures
- Tracking security researcher discussions
- Detecting vulnerability trends
- Building threat intelligence

**Unacceptable Use**:
- Stalking individuals
- Collecting personal information
- Harassment or doxxing
- Evading account restrictions

---

### 2. Ethical Tor Dark Web OSINT (`tor_dark_osint.py`)

**Purpose**: Access **PUBLIC** exploit database mirrors on Tor for defensive research

**⚠️ CRITICAL ETHICAL CONTROLS ⚠️**:

1. **Strict Allowlist**: Only approved .onion domains
   - Must be verified public research sources
   - No marketplaces, illegal services, or unauthorized content
   - Require explicit approval before adding domains

2. **Forbidden Pattern Blocking**:
   - Automatically blocks content mentioning markets, drugs, weapons, etc.
   - **Auto-shutdown** if forbidden content detected
   - All violations logged to audit file

3. **Credibility Filtering**:
   - Requires 60%+ credibility score
   - Cross-validation from multiple sources
   - Consensus-based acceptance

4. **Audit Logging**:
   - All access logged to `tor_osint_audit.log`
   - Includes timestamps, domains, actions
   - Required for compliance reviews

**Configuration**:
```yaml
tor_osint:
  enabled: true
  ethical_mode: true  # REQUIRED - must be true
  allowed_domains:
    - exploit-db-mirror.onion  # Example - verify first!
  audit_log_path: "tor_osint_audit.log"
```

**Acceptable Use**:
- Accessing public exploit database mirrors
- Defensive threat intelligence gathering
- CVE research from public sources
- Compliance-documented security research

**Unacceptable Use**:
- Accessing illegal marketplaces
- Purchasing illicit goods/services
- Unauthorized network access
- Evading law enforcement
- Any illegal activity

**Requirements**:
- Tor service running: `sudo systemctl start tor`
- Python packages: `pip install stem requests[socks]`
- Authorization documentation
- Compliance review approval

---

### 3. Unified Threat Hub (`unified_threat_hub.py`)

**Purpose**: Correlate threats from multiple sources for comprehensive intelligence

**Ethical Controls**:
- Inherits all controls from source modules
- Cross-source validation prevents false positives
- Auto-goal triggering only for high-confidence (75%+) threats
- Deduplication prevents duplicate actions

**Configuration**:
```yaml
unified_threat_hub:
  enabled: true
  auto_goal_confidence_threshold: 0.75
  auto_goal_min_sources: 2
```

---

## Compliance & Legal

### Authorization Documentation

Before enabling v7 features, document:

1. **Purpose**: Why are you using these features?
2. **Authorization**: Who approved this research?
3. **Scope**: What domains/sources will you access?
4. **Legal Review**: Has legal counsel approved?
5. **Compliance**: What regulations apply (GDPR, CCPA, etc.)?

### Audit Requirements

- Review audit logs monthly
- Report suspicious activity immediately
- Maintain logs for compliance period (check local laws)
- Document all approved .onion domains
- Keep authorization records

### Incident Response

If forbidden content is detected:

1. System auto-shuts down Tor OSINT
2. Review audit logs immediately
3. Investigate how content was accessed
4. Update allowlist/blocklists
5. File incident report
6. Review authorization

---

## Technical Safeguards

### Multi-Layer Protection

1. **Configuration Layer**: `ethical_mode: true` required
2. **Domain Layer**: Strict allowlist, no wildcards
3. **Content Layer**: Pattern-based forbidden content detection
4. **Credibility Layer**: Multi-source validation
5. **Audit Layer**: Comprehensive logging

### Default-Deny Policy

- All v7 features **disabled by default**
- Require explicit enable in config
- Tor OSINT requires `ethical_mode: true`
- Empty allowlists = no access

---

## Quick Start (Ethical)

### 1. Enable X Firehose Only (Safest)

```yaml
realtime_x:
  enabled: true
  keywords: [CVE, exploit, WordPress]

tor_osint:
  enabled: false  # Keep disabled

unified_threat_hub:
  enabled: true
```

### 2. Add Tor OSINT (Requires Authorization)

**Before enabling**:
1. Get authorization in writing
2. Verify all .onion domains are legitimate
3. Review audit log configuration
4. Test with mock data first

```yaml
tor_osint:
  enabled: true
  ethical_mode: true  # MUST be true
  allowed_domains:
    - verified-exploit-db.onion  # Verify first!
  audit_log_path: "tor_osint_audit.log"
```

### 3. Monitor Compliance

```bash
# Check audit logs
tail -f tor_osint_audit.log

# Review statistics
python mindsync_prod.py
# Then use /threats command

# Check for violations
grep "FORBIDDEN" tor_osint_audit.log
grep "BLOCKED" tor_osint_audit.log
```

---

## Responsible Disclosure

If you discover vulnerabilities using v7:

1. **Do not exploit** beyond proof-of-concept
2. **Notify vendor** privately first
3. **Allow time** for patching (90 days standard)
4. **Coordinate disclosure** with vendor
5. **Publish responsibly** after patch available

---

## Questions & Support

**Ethical Concerns**: Review this document and consult legal counsel

**Technical Issues**: Check logs and configuration

**Authorization**: Contact your security team/legal department

---

## Acknowledgment

By enabling v7 features, you acknowledge:

- You have read and understood these guidelines
- You have proper authorization for your use case
- You will use v7 ethically and legally
- You accept responsibility for your actions
- You will immediately report any violations

---

**Last Updated**: 2025-11-07
**Version**: 7.0
**Status**: Production with Ethical Safeguards Active

---

## Example: Ethical CTF/Research Workflow

```yaml
# config.yaml for authorized CTF/research
realtime_x:
  enabled: true
  keywords: [CVE, CTF, security, exploit]

tor_osint:
  enabled: true
  ethical_mode: true
  allowed_domains:
    - exploit-db-mirror.onion  # Verified public mirror
  audit_log_path: "research_audit.log"

unified_threat_hub:
  enabled: true
  auto_goal_confidence_threshold: 0.75
```

**Authorization checklist**:
- [x] Written authorization from supervisor
- [x] Legal review completed
- [x] Verified all .onion domains
- [x] Audit logging configured
- [x] Incident response plan documented
- [x] Compliance requirements met

---

**Remember**: Powerful tools require responsible use. MindSync Oracle v7 is designed for defenders. Use it wisely. 🛡️
