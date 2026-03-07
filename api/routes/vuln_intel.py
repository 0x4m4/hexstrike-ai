"""
Vulnerability Intelligence API Routes
Handles CVE monitoring, exploit generation, attack chain discovery, threat feeds, and zero-day research
"""

import logging
from datetime import datetime
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

# Create blueprint
vuln_intel_bp = Blueprint('vuln_intel', __name__, url_prefix='/api/vuln-intel')

# Dependencies will be injected via init_app
cve_intelligence = None
exploit_generator = None
vulnerability_correlator = None

def init_app(cve_intel, exploit_gen, vuln_correlator):
    """Initialize blueprint with dependencies"""
    global cve_intelligence, exploit_generator, vulnerability_correlator
    cve_intelligence = cve_intel
    exploit_generator = exploit_gen
    vulnerability_correlator = vuln_correlator


@vuln_intel_bp.route("/cve-monitor", methods=["POST"])
def cve_monitor():
    """Monitor CVE databases for new vulnerabilities with AI analysis"""
    try:
        params = request.json
        hours = params.get("hours", 24)
        severity_filter = params.get("severity_filter", "HIGH,CRITICAL")
        keywords = params.get("keywords", "")

        logger.info(f"🔍 Monitoring CVE feeds for last {hours} hours with severity filter: {severity_filter}")

        # Fetch latest CVEs
        cve_results = cve_intelligence.fetch_latest_cves(hours, severity_filter)

        # Filter by keywords if provided
        if keywords and cve_results.get("success"):
            keyword_list = [k.strip().lower() for k in keywords.split(",")]
            filtered_cves = []

            for cve in cve_results.get("cves", []):
                description = cve.get("description", "").lower()
                if any(keyword in description for keyword in keyword_list):
                    filtered_cves.append(cve)

            cve_results["cves"] = filtered_cves
            cve_results["filtered_by_keywords"] = keywords
            cve_results["total_after_filter"] = len(filtered_cves)

        # Analyze exploitability for top CVEs
        exploitability_analysis = []
        for cve in cve_results.get("cves", [])[:5]:  # Analyze top 5 CVEs
            cve_id = cve.get("cve_id", "")
            if cve_id:
                analysis = cve_intelligence.analyze_cve_exploitability(cve_id)
                if analysis.get("success"):
                    exploitability_analysis.append(analysis)

        result = {
            "success": True,
            "cve_monitoring": cve_results,
            "exploitability_analysis": exploitability_analysis,
            "timestamp": datetime.now().isoformat()
        }

        logger.info(f"📊 CVE monitoring completed | Found: {len(cve_results.get('cves', []))} CVEs")
        return jsonify(result)

    except Exception as e:
        logger.error(f"💥 Error in CVE monitoring: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Server error: {str(e)}"
        }), 500


@vuln_intel_bp.route("/exploit-generate", methods=["POST"])
def exploit_generate():
    """Generate exploits from vulnerability data using AI"""
    try:
        params = request.json
        cve_id = params.get("cve_id", "")
        target_os = params.get("target_os", "")
        target_arch = params.get("target_arch", "x64")
        exploit_type = params.get("exploit_type", "poc")
        evasion_level = params.get("evasion_level", "none")

        # Additional target context
        target_info = {
            "target_os": target_os,
            "target_arch": target_arch,
            "exploit_type": exploit_type,
            "evasion_level": evasion_level,
            "target_ip": params.get("target_ip", "192.168.1.100"),
            "target_port": params.get("target_port", 80),
            "description": params.get("target_description", f"Target for {cve_id}")
        }

        if not cve_id:
            logger.warning("🤖 Exploit generation called without CVE ID")
            return jsonify({
                "success": False,
                "error": "CVE ID parameter is required"
            }), 400

        logger.info(f"🤖 Generating exploit for {cve_id} | Target: {target_os} {target_arch}")

        # First analyze the CVE for context
        cve_analysis = cve_intelligence.analyze_cve_exploitability(cve_id)

        if not cve_analysis.get("success"):
            return jsonify({
                "success": False,
                "error": f"Failed to analyze CVE {cve_id}: {cve_analysis.get('error', 'Unknown error')}"
            }), 400

        # Prepare CVE data for exploit generation
        cve_data = {
            "cve_id": cve_id,
            "description": f"Vulnerability analysis for {cve_id}",
            "exploitability_level": cve_analysis.get("exploitability_level", "UNKNOWN"),
            "exploitability_score": cve_analysis.get("exploitability_score", 0)
        }

        # Generate exploit
        exploit_result = exploit_generator.generate_exploit_from_cve(cve_data, target_info)

        # Search for existing exploits for reference
        existing_exploits = cve_intelligence.search_existing_exploits(cve_id)

        result = {
            "success": True,
            "cve_analysis": cve_analysis,
            "exploit_generation": exploit_result,
            "existing_exploits": existing_exploits,
            "target_info": target_info,
            "timestamp": datetime.now().isoformat()
        }

        logger.info(f"🎯 Exploit generation completed for {cve_id}")
        return jsonify(result)

    except Exception as e:
        logger.error(f"💥 Error in exploit generation: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Server error: {str(e)}"
        }), 500


@vuln_intel_bp.route("/attack-chains", methods=["POST"])
def discover_attack_chains():
    """Discover multi-stage attack possibilities"""
    try:
        params = request.json
        target_software = params.get("target_software", "")
        attack_depth = params.get("attack_depth", 3)
        include_zero_days = params.get("include_zero_days", False)

        if not target_software:
            logger.warning("🔗 Attack chain discovery called without target software")
            return jsonify({
                "success": False,
                "error": "Target software parameter is required"
            }), 400

        logger.info(f"🔗 Discovering attack chains for {target_software} | Depth: {attack_depth}")

        # Discover attack chains
        chain_results = vulnerability_correlator.find_attack_chains(target_software, attack_depth)

        # Enhance with exploit generation for viable chains
        if chain_results.get("success") and chain_results.get("attack_chains"):
            enhanced_chains = []

            for chain in chain_results["attack_chains"][:2]:  # Enhance top 2 chains
                enhanced_chain = chain.copy()
                enhanced_stages = []

                for stage in chain["stages"]:
                    enhanced_stage = stage.copy()

                    # Try to generate exploit for this stage
                    vuln = stage.get("vulnerability", {})
                    cve_id = vuln.get("cve_id", "")

                    if cve_id:
                        try:
                            cve_data = {"cve_id": cve_id, "description": vuln.get("description", "")}
                            target_info = {"target_os": "linux", "target_arch": "x64", "evasion_level": "basic"}

                            exploit_result = exploit_generator.generate_exploit_from_cve(cve_data, target_info)
                            enhanced_stage["exploit_available"] = exploit_result.get("success", False)

                            if exploit_result.get("success"):
                                enhanced_stage["exploit_code"] = exploit_result.get("exploit_code", "")[:500] + "..."
                        except:
                            enhanced_stage["exploit_available"] = False

                    enhanced_stages.append(enhanced_stage)

                enhanced_chain["stages"] = enhanced_stages
                enhanced_chains.append(enhanced_chain)

            chain_results["enhanced_chains"] = enhanced_chains

        result = {
            "success": True,
            "attack_chain_discovery": chain_results,
            "parameters": {
                "target_software": target_software,
                "attack_depth": attack_depth,
                "include_zero_days": include_zero_days
            },
            "timestamp": datetime.now().isoformat()
        }

        logger.info(f"🎯 Attack chain discovery completed | Found: {len(chain_results.get('attack_chains', []))} chains")
        return jsonify(result)

    except Exception as e:
        logger.error(f"💥 Error in attack chain discovery: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Server error: {str(e)}"
        }), 500


@vuln_intel_bp.route("/threat-feeds", methods=["POST"])
def threat_intelligence_feeds():
    """Aggregate and correlate threat intelligence from multiple sources"""
    try:
        params = request.json
        indicators = params.get("indicators", [])
        timeframe = params.get("timeframe", "30d")
        sources = params.get("sources", "all")

        if isinstance(indicators, str):
            indicators = [i.strip() for i in indicators.split(",")]

        if not indicators:
            logger.warning("🧠 Threat intelligence called without indicators")
            return jsonify({
                "success": False,
                "error": "Indicators parameter is required"
            }), 400

        logger.info(f"🧠 Correlating threat intelligence for {len(indicators)} indicators")

        correlation_results = {
            "indicators_analyzed": indicators,
            "timeframe": timeframe,
            "sources": sources,
            "correlations": [],
            "threat_score": 0,
            "recommendations": []
        }

        # Analyze each indicator
        cve_indicators = [i for i in indicators if i.startswith("CVE-")]
        ip_indicators = [i for i in indicators if i.replace(".", "").isdigit()]
        hash_indicators = [i for i in indicators if len(i) in [32, 40, 64] and all(c in "0123456789abcdef" for c in i.lower())]

        # Process CVE indicators
        for cve_id in cve_indicators:
            try:
                cve_analysis = cve_intelligence.analyze_cve_exploitability(cve_id)
                if cve_analysis.get("success"):
                    correlation_results["correlations"].append({
                        "indicator": cve_id,
                        "type": "cve",
                        "analysis": cve_analysis,
                        "threat_level": cve_analysis.get("exploitability_level", "UNKNOWN")
                    })

                    # Add to threat score
                    exploit_score = cve_analysis.get("exploitability_score", 0)
                    correlation_results["threat_score"] += min(exploit_score, 100)

                # Search for existing exploits
                exploits = cve_intelligence.search_existing_exploits(cve_id)
                if exploits.get("success") and exploits.get("total_exploits", 0) > 0:
                    correlation_results["correlations"].append({
                        "indicator": cve_id,
                        "type": "exploit_availability",
                        "exploits_found": exploits.get("total_exploits", 0),
                        "threat_level": "HIGH"
                    })
                    correlation_results["threat_score"] += 25

            except Exception as e:
                logger.warning(f"Error analyzing CVE {cve_id}: {str(e)}")

        # Process IP indicators (basic reputation check simulation)
        for ip in ip_indicators:
            # Simulate threat intelligence lookup
            correlation_results["correlations"].append({
                "indicator": ip,
                "type": "ip_reputation",
                "analysis": {
                    "reputation": "unknown",
                    "geolocation": "unknown",
                    "associated_threats": []
                },
                "threat_level": "MEDIUM"  # Default for unknown IPs
            })

        # Process hash indicators
        for hash_val in hash_indicators:
            correlation_results["correlations"].append({
                "indicator": hash_val,
                "type": "file_hash",
                "analysis": {
                    "hash_type": f"hash{len(hash_val)}",
                    "malware_family": "unknown",
                    "detection_rate": "unknown"
                },
                "threat_level": "MEDIUM"
            })

        # Calculate overall threat score and generate recommendations
        total_indicators = len(indicators)
        if total_indicators > 0:
            correlation_results["threat_score"] = min(correlation_results["threat_score"] / total_indicators, 100)

            if correlation_results["threat_score"] >= 75:
                correlation_results["recommendations"] = [
                    "Immediate threat response required",
                    "Block identified indicators",
                    "Enhance monitoring for related IOCs",
                    "Implement emergency patches for identified CVEs"
                ]
            elif correlation_results["threat_score"] >= 50:
                correlation_results["recommendations"] = [
                    "Elevated threat level detected",
                    "Increase monitoring for identified indicators",
                    "Plan patching for identified vulnerabilities",
                    "Review security controls"
                ]
            else:
                correlation_results["recommendations"] = [
                    "Low to medium threat level",
                    "Continue standard monitoring",
                    "Plan routine patching",
                    "Consider additional threat intelligence sources"
                ]

        result = {
            "success": True,
            "threat_intelligence": correlation_results,
            "timestamp": datetime.now().isoformat()
        }

        logger.info(f"🎯 Threat intelligence correlation completed | Threat Score: {correlation_results['threat_score']:.1f}")
        return jsonify(result)

    except Exception as e:
        logger.error(f"💥 Error in threat intelligence: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Server error: {str(e)}"
        }), 500


@vuln_intel_bp.route("/zero-day-research", methods=["POST"])
def zero_day_research():
    """Automated zero-day vulnerability research using AI analysis"""
    try:
        params = request.json
        target_software = params.get("target_software", "")
        analysis_depth = params.get("analysis_depth", "standard")
        source_code_url = params.get("source_code_url", "")

        if not target_software:
            logger.warning("🔬 Zero-day research called without target software")
            return jsonify({
                "success": False,
                "error": "Target software parameter is required"
            }), 400

        logger.info(f"🔬 Starting zero-day research for {target_software} | Depth: {analysis_depth}")

        research_results = {
            "target_software": target_software,
            "analysis_depth": analysis_depth,
            "research_areas": [],
            "potential_vulnerabilities": [],
            "risk_assessment": {},
            "recommendations": []
        }

        # Define research areas based on software type
        common_research_areas = [
            "Input validation vulnerabilities",
            "Memory corruption issues",
            "Authentication bypasses",
            "Authorization flaws",
            "Cryptographic weaknesses",
            "Race conditions",
            "Logic flaws"
        ]

        # Software-specific research areas
        web_research_areas = [
            "Cross-site scripting (XSS)",
            "SQL injection",
            "Server-side request forgery (SSRF)",
            "Insecure deserialization",
            "Template injection"
        ]

        system_research_areas = [
            "Buffer overflows",
            "Privilege escalation",
            "Kernel vulnerabilities",
            "Service exploitation",
            "Configuration weaknesses"
        ]

        # Determine research areas based on target
        target_lower = target_software.lower()
        if any(web_tech in target_lower for web_tech in ["apache", "nginx", "tomcat", "php", "node", "django"]):
            research_results["research_areas"] = common_research_areas + web_research_areas
        elif any(sys_tech in target_lower for sys_tech in ["windows", "linux", "kernel", "driver"]):
            research_results["research_areas"] = common_research_areas + system_research_areas
        else:
            research_results["research_areas"] = common_research_areas

        # Simulate vulnerability discovery based on analysis depth
        vuln_count = {"quick": 2, "standard": 4, "comprehensive": 6}.get(analysis_depth, 4)

        for i in range(vuln_count):
            potential_vuln = {
                "id": f"RESEARCH-{target_software.upper()}-{i+1:03d}",
                "category": research_results["research_areas"][i % len(research_results["research_areas"])],
                "severity": ["LOW", "MEDIUM", "HIGH", "CRITICAL"][i % 4],
                "confidence": ["LOW", "MEDIUM", "HIGH"][i % 3],
                "description": f"Potential {research_results['research_areas'][i % len(research_results['research_areas'])].lower()} in {target_software}",
                "attack_vector": "To be determined through further analysis",
                "impact": "To be assessed",
                "proof_of_concept": "Research phase - PoC development needed"
            }
            research_results["potential_vulnerabilities"].append(potential_vuln)

        # Risk assessment
        high_risk_count = sum(1 for v in research_results["potential_vulnerabilities"] if v["severity"] in ["HIGH", "CRITICAL"])
        total_vulns = len(research_results["potential_vulnerabilities"])

        research_results["risk_assessment"] = {
            "total_areas_analyzed": len(research_results["research_areas"]),
            "potential_vulnerabilities_found": total_vulns,
            "high_risk_findings": high_risk_count,
            "risk_score": min((high_risk_count * 25 + (total_vulns - high_risk_count) * 10), 100),
            "research_confidence": analysis_depth
        }

        # Generate recommendations
        if high_risk_count > 0:
            research_results["recommendations"] = [
                "Prioritize security testing in identified high-risk areas",
                "Conduct focused penetration testing",
                "Implement additional security controls",
                "Consider bug bounty program for target software",
                "Perform code review in identified areas"
            ]
        else:
            research_results["recommendations"] = [
                "Continue standard security testing",
                "Monitor for new vulnerability research",
                "Implement defense-in-depth strategies",
                "Regular security assessments recommended"
            ]

        # Source code analysis simulation
        if source_code_url:
            research_results["source_code_analysis"] = {
                "repository_url": source_code_url,
                "analysis_status": "simulated",
                "findings": [
                    "Static analysis patterns identified",
                    "Potential code quality issues detected",
                    "Security-relevant functions located"
                ],
                "recommendation": "Manual code review recommended for identified areas"
            }

        result = {
            "success": True,
            "zero_day_research": research_results,
            "disclaimer": "This is simulated research for demonstration. Real zero-day research requires extensive manual analysis.",
            "timestamp": datetime.now().isoformat()
        }

        logger.info(f"🎯 Zero-day research completed | Risk Score: {research_results['risk_assessment']['risk_score']}")
        return jsonify(result)

    except Exception as e:
        logger.error(f"💥 Error in zero-day research: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Server error: {str(e)}"
        }), 500
