"""
CVE Intelligence Manager
Advanced CVE Intelligence and Vulnerability Management System
"""

from typing import Dict, Any, List
from datetime import datetime, timedelta
import requests
import logging

# Import ModernVisualEngine from core module
from core.visual import ModernVisualEngine

logger = logging.getLogger(__name__)

class CVEIntelligenceManager:
    """Advanced CVE Intelligence and Vulnerability Management System"""

    def __init__(self):
        self.cve_cache = {}
        self.vulnerability_db = {}
        self.threat_intelligence = {}

    @staticmethod
    def create_banner():
        """Reuse unified ModernVisualEngine banner (legacy hook)."""
        return ModernVisualEngine.create_banner()

    @staticmethod
    def render_progress_bar(progress: float, width: int = 40, style: str = 'cyber',
                          label: str = "", eta: float = 0, speed: str = "") -> str:
        """Render a beautiful progress bar with multiple styles"""

        # Clamp progress between 0 and 1
        progress = max(0.0, min(1.0, progress))

        # Calculate filled and empty portions
        filled_width = int(width * progress)
        empty_width = width - filled_width

        # Style-specific rendering
        if style == 'cyber':
            filled_char = '█'; empty_char = '░'
            bar_color = ModernVisualEngine.COLORS['ACCENT_LINE']
            progress_color = ModernVisualEngine.COLORS['PRIMARY_BORDER']
        elif style == 'matrix':
            filled_char = '▓'; empty_char = '▒'
            bar_color = ModernVisualEngine.COLORS['ACCENT_LINE']
            progress_color = ModernVisualEngine.COLORS['ACCENT_GRADIENT']
        elif style == 'neon':
            filled_char = '━'; empty_char = '─'
            bar_color = ModernVisualEngine.COLORS['PRIMARY_BORDER']
            progress_color = ModernVisualEngine.COLORS['CYBER_ORANGE']
        else:
            filled_char = '█'; empty_char = '░'
            bar_color = ModernVisualEngine.COLORS['ACCENT_LINE']
            progress_color = ModernVisualEngine.COLORS['PRIMARY_BORDER']

        # Build the progress bar
        filled_part = bar_color + filled_char * filled_width
        empty_part = ModernVisualEngine.COLORS['TERMINAL_GRAY'] + empty_char * empty_width
        percentage = f"{progress * 100:.1f}%"

        # Add ETA and speed if provided
        eta_str = f" | ETA: {eta:.0f}s" if eta > 0 else ""
        speed_str = f" | {speed}" if speed else ""

        # Construct the full progress bar
        bar = f"{progress_color}[{filled_part}{empty_part}{ModernVisualEngine.COLORS['RESET']}{progress_color}] {percentage}{eta_str}{speed_str}{ModernVisualEngine.COLORS['RESET']}"

        if label:
            return f"{ModernVisualEngine.COLORS['BOLD']}{label}{ModernVisualEngine.COLORS['RESET']} {bar}"
        return bar

    @staticmethod
    def render_vulnerability_card(vuln_data: Dict[str, Any]) -> str:
        """Render vulnerability as a beautiful card with severity indicators"""

        severity = vuln_data.get('severity', 'info').lower()
        title = vuln_data.get('title', 'Unknown Vulnerability')
        url = vuln_data.get('url', 'N/A')
        description = vuln_data.get('description', 'No description available')
        cvss = vuln_data.get('cvss_score', 0.0)

        # Get severity color
        severity_color = ModernVisualEngine.COLORS['HACKER_RED'] if severity == 'critical' else ModernVisualEngine.COLORS['HACKER_RED'] if severity == 'high' else ModernVisualEngine.COLORS['CYBER_ORANGE'] if severity == 'medium' else ModernVisualEngine.COLORS['CYBER_ORANGE'] if severity == 'low' else ModernVisualEngine.COLORS['NEON_BLUE']

        # Severity indicators
        severity_indicators = {
            'critical': '🔥 CRITICAL',
            'high': '⚠️  HIGH',
            'medium': '📊 MEDIUM',
            'low': '📝 LOW',
            'info': 'ℹ️  INFO'
        }

        severity_badge = severity_indicators.get(severity, '❓ UNKNOWN')

        # Create the vulnerability card
        card = f"""
{ModernVisualEngine.COLORS['BOLD']}╭─────────────────────────────────────────────────────────────────────────────╮{ModernVisualEngine.COLORS['RESET']}
{ModernVisualEngine.COLORS['BOLD']}│{ModernVisualEngine.COLORS['RESET']} {severity_color}{severity_badge}{ModernVisualEngine.COLORS['RESET']} {ModernVisualEngine.COLORS['BOLD']}{title[:60]}{ModernVisualEngine.COLORS['RESET']}
{ModernVisualEngine.COLORS['BOLD']}├─────────────────────────────────────────────────────────────────────────────┤{ModernVisualEngine.COLORS['RESET']}
{ModernVisualEngine.COLORS['BOLD']}│{ModernVisualEngine.COLORS['RESET']} {ModernVisualEngine.COLORS['NEON_BLUE']}🎯 Target:{ModernVisualEngine.COLORS['RESET']} {url[:65]}
{ModernVisualEngine.COLORS['BOLD']}│{ModernVisualEngine.COLORS['RESET']} {ModernVisualEngine.COLORS['CYBER_ORANGE']}📊 CVSS:{ModernVisualEngine.COLORS['RESET']} {cvss}/10.0
{ModernVisualEngine.COLORS['BOLD']}│{ModernVisualEngine.COLORS['RESET']} {ModernVisualEngine.COLORS['CYBER_ORANGE']}📋 Description:{ModernVisualEngine.COLORS['RESET']}
{ModernVisualEngine.COLORS['BOLD']}│{ModernVisualEngine.COLORS['RESET']}   {description[:70]}
{ModernVisualEngine.COLORS['BOLD']}╰─────────────────────────────────────────────────────────────────────────────╯{ModernVisualEngine.COLORS['RESET']}
"""
        return card

    @staticmethod
    def create_live_dashboard(processes: Dict[int, Dict[str, Any]]) -> str:
        """Create a live dashboard showing all active processes"""

        if not processes:
            return f"{ModernVisualEngine.COLORS['TERMINAL_GRAY']}📊 No active processes{ModernVisualEngine.COLORS['RESET']}"

        dashboard = f"""
{ModernVisualEngine.COLORS['MATRIX_GREEN']}{ModernVisualEngine.COLORS['BOLD']}╔══════════════════════════════════════════════════════════════════════════════╗
║                           🚀 LIVE PROCESS DASHBOARD                          ║
╠══════════════════════════════════════════════════════════════════════════════╣{ModernVisualEngine.COLORS['RESET']}
"""

        for pid, proc_info in processes.items():
            command = proc_info.get('command', 'Unknown')[:50]
            status = proc_info.get('status', 'unknown')
            progress = proc_info.get('progress', 0.0)
            runtime = proc_info.get('runtime', 0)
            eta = proc_info.get('eta', 0)

            # Status color coding
            status_colors = {
                'running': ModernVisualEngine.COLORS['MATRIX_GREEN'],
                'paused': ModernVisualEngine.COLORS['WARNING'],
                'terminated': ModernVisualEngine.COLORS['ERROR'],
                'completed': ModernVisualEngine.COLORS['NEON_BLUE']
            }
            status_color = status_colors.get(status, ModernVisualEngine.COLORS['BRIGHT_WHITE'])

            # Create mini progress bar
            mini_bar = ModernVisualEngine.render_progress_bar(
                progress, width=20, style='cyber', eta=eta
            )

            dashboard += f"""{ModernVisualEngine.COLORS['BOLD']}║{ModernVisualEngine.COLORS['RESET']} {ModernVisualEngine.COLORS['NEON_BLUE']}PID {pid}{ModernVisualEngine.COLORS['RESET']} │ {status_color}{status.upper()}{ModernVisualEngine.COLORS['RESET']} │ {runtime:.1f}s │ {command}...
{ModernVisualEngine.COLORS['BOLD']}║{ModernVisualEngine.COLORS['RESET']} {mini_bar}
{ModernVisualEngine.COLORS['BOLD']}╠──────────────────────────────────────────────────────────────────────────────╣{ModernVisualEngine.COLORS['RESET']}
"""

        dashboard += f"{ModernVisualEngine.COLORS['MATRIX_GREEN']}{ModernVisualEngine.COLORS['BOLD']}╚══════════════════════════════════════════════════════════════════════════════╝{ModernVisualEngine.COLORS['RESET']}"

        return dashboard

    @staticmethod
    def format_tool_output(tool: str, output: str, success: bool = True) -> str:
        """Format tool output with syntax highlighting and structure"""

        # Get tool icon
        tool_icon = '🛠️'  # Default tool icon

        # Status indicator
        status_icon = "✅" if success else "❌"
        status_color = ModernVisualEngine.COLORS['MATRIX_GREEN'] if success else ModernVisualEngine.COLORS['HACKER_RED']

        # Format the output with structure
        formatted_output = f"""
{ModernVisualEngine.COLORS['BOLD']}╭─ {tool_icon} {tool.upper()} OUTPUT ─────────────────────────────────────────────╮{ModernVisualEngine.COLORS['RESET']}
{ModernVisualEngine.COLORS['BOLD']}│{ModernVisualEngine.COLORS['RESET']} {status_color}{status_icon} Status: {'SUCCESS' if success else 'FAILED'}{ModernVisualEngine.COLORS['RESET']}
{ModernVisualEngine.COLORS['BOLD']}├─────────────────────────────────────────────────────────────────────────────┤{ModernVisualEngine.COLORS['RESET']}
"""

        # Process output lines with syntax highlighting
        lines = output.split('\n')
        for line in lines[:20]:  # Limit to first 20 lines for readability
            if line.strip():
                # Basic syntax highlighting
                if any(keyword in line.lower() for keyword in ['error', 'failed', 'denied']):
                    formatted_output += f"{ModernVisualEngine.COLORS['BOLD']}│{ModernVisualEngine.COLORS['RESET']} {ModernVisualEngine.COLORS['ERROR']}{line[:75]}{ModernVisualEngine.COLORS['RESET']}\n"
                elif any(keyword in line.lower() for keyword in ['found', 'discovered', 'vulnerable']):
                    formatted_output += f"{ModernVisualEngine.COLORS['BOLD']}│{ModernVisualEngine.COLORS['RESET']} {ModernVisualEngine.COLORS['MATRIX_GREEN']}{line[:75]}{ModernVisualEngine.COLORS['RESET']}\n"
                elif any(keyword in line.lower() for keyword in ['warning', 'timeout']):
                    formatted_output += f"{ModernVisualEngine.COLORS['BOLD']}│{ModernVisualEngine.COLORS['RESET']} {ModernVisualEngine.COLORS['WARNING']}{line[:75]}{ModernVisualEngine.COLORS['RESET']}\n"
                else:
                    formatted_output += f"{ModernVisualEngine.COLORS['BOLD']}│{ModernVisualEngine.COLORS['RESET']} {ModernVisualEngine.COLORS['BRIGHT_WHITE']}{line[:75]}{ModernVisualEngine.COLORS['RESET']}\n"

        if len(lines) > 20:
            formatted_output += f"{ModernVisualEngine.COLORS['BOLD']}│{ModernVisualEngine.COLORS['RESET']} {ModernVisualEngine.COLORS['TERMINAL_GRAY']}... ({len(lines) - 20} more lines truncated){ModernVisualEngine.COLORS['RESET']}\n"

        formatted_output += f"{ModernVisualEngine.COLORS['BOLD']}╰─────────────────────────────────────────────────────────────────────────────╯{ModernVisualEngine.COLORS['RESET']}"

        return formatted_output

    @staticmethod
    def create_summary_report(results: Dict[str, Any]) -> str:
        """Generate a beautiful summary report"""

        total_vulns = len(results.get('vulnerabilities', []))
        critical_vulns = len([v for v in results.get('vulnerabilities', []) if v.get('severity') == 'critical'])
        high_vulns = len([v for v in results.get('vulnerabilities', []) if v.get('severity') == 'high'])
        execution_time = results.get('execution_time', 0)
        tools_used = results.get('tools_used', [])

        report = f"""
{ModernVisualEngine.COLORS['MATRIX_GREEN']}{ModernVisualEngine.COLORS['BOLD']}╔══════════════════════════════════════════════════════════════════════════════╗
║                              📊 SCAN SUMMARY REPORT                          ║
╠══════════════════════════════════════════════════════════════════════════════╣{ModernVisualEngine.COLORS['RESET']}
{ModernVisualEngine.COLORS['BOLD']}║{ModernVisualEngine.COLORS['RESET']} {ModernVisualEngine.COLORS['NEON_BLUE']}🎯 Target:{ModernVisualEngine.COLORS['RESET']} {results.get('target', 'Unknown')[:60]}
{ModernVisualEngine.COLORS['BOLD']}║{ModernVisualEngine.COLORS['RESET']} {ModernVisualEngine.COLORS['CYBER_ORANGE']}⏱️  Duration:{ModernVisualEngine.COLORS['RESET']} {execution_time:.2f} seconds
{ModernVisualEngine.COLORS['BOLD']}║{ModernVisualEngine.COLORS['RESET']} {ModernVisualEngine.COLORS['WARNING']}🛠️  Tools Used:{ModernVisualEngine.COLORS['RESET']} {len(tools_used)} tools
{ModernVisualEngine.COLORS['BOLD']}╠──────────────────────────────────────────────────────────────────────────────╣{ModernVisualEngine.COLORS['RESET']}
{ModernVisualEngine.COLORS['BOLD']}║{ModernVisualEngine.COLORS['RESET']} {ModernVisualEngine.COLORS['HACKER_RED']}🔥 Critical:{ModernVisualEngine.COLORS['RESET']} {critical_vulns} vulnerabilities
{ModernVisualEngine.COLORS['BOLD']}║{ModernVisualEngine.COLORS['RESET']} {ModernVisualEngine.COLORS['ERROR']}⚠️  High:{ModernVisualEngine.COLORS['RESET']} {high_vulns} vulnerabilities
{ModernVisualEngine.COLORS['BOLD']}║{ModernVisualEngine.COLORS['RESET']} {ModernVisualEngine.COLORS['MATRIX_GREEN']}📈 Total Found:{ModernVisualEngine.COLORS['RESET']} {total_vulns} vulnerabilities
{ModernVisualEngine.COLORS['BOLD']}╠──────────────────────────────────────────────────────────────────────────────╣{ModernVisualEngine.COLORS['RESET']}
{ModernVisualEngine.COLORS['BOLD']}║{ModernVisualEngine.COLORS['RESET']} {ModernVisualEngine.COLORS['ELECTRIC_PURPLE']}🚀 Tools:{ModernVisualEngine.COLORS['RESET']} {', '.join(tools_used[:5])}{'...' if len(tools_used) > 5 else ''}
{ModernVisualEngine.COLORS['MATRIX_GREEN']}{ModernVisualEngine.COLORS['BOLD']}╚══════════════════════════════════════════════════════════════════════════════╝{ModernVisualEngine.COLORS['RESET']}
"""
        return report

    def fetch_latest_cves(self, hours=24, severity_filter="HIGH,CRITICAL"):
        """Fetch latest CVEs from NVD and other real sources"""
        try:
            logger.info(f"🔍 Fetching CVEs from last {hours} hours with severity: {severity_filter}")
            
            # Calculate date range for CVE search
            end_date = datetime.now()
            start_date = end_date - timedelta(hours=hours)
            
            # Format dates for NVD API (ISO 8601 format)
            start_date_str = start_date.strftime('%Y-%m-%dT%H:%M:%S.000')
            end_date_str = end_date.strftime('%Y-%m-%dT%H:%M:%S.000')
            
            # NVD API endpoint
            nvd_url = "https://services.nvd.nist.gov/rest/json/cves/2.0"
            
            # Parse severity filter
            severity_levels = [s.strip().upper() for s in severity_filter.split(",")]
            
            all_cves = []
            
            # Query NVD API with rate limiting compliance
            params = {
                'lastModStartDate': start_date_str,
                'lastModEndDate': end_date_str,
                'resultsPerPage': 100
            }
            
            try:
                # Add delay to respect NVD rate limits (6 seconds between requests for unauthenticated)
                import time
                
                logger.info(f"🌐 Querying NVD API: {nvd_url}")
                response = requests.get(nvd_url, params=params, timeout=30)
                
                if response.status_code == 200:
                    nvd_data = response.json()
                    vulnerabilities = nvd_data.get('vulnerabilities', [])
                    
                    logger.info(f"📊 Retrieved {len(vulnerabilities)} vulnerabilities from NVD")
                    
                    for vuln_item in vulnerabilities:
                        cve_data = vuln_item.get('cve', {})
                        cve_id = cve_data.get('id', 'Unknown')
                        
                        # Extract CVSS scores and determine severity
                        metrics = cve_data.get('metrics', {})
                        cvss_score = 0.0
                        severity = "UNKNOWN"
                        
                        # Try CVSS v3.1 first, then v3.0, then v2.0
                        if 'cvssMetricV31' in metrics and metrics['cvssMetricV31']:
                            cvss_data = metrics['cvssMetricV31'][0]['cvssData']
                            cvss_score = cvss_data.get('baseScore', 0.0)
                            severity = cvss_data.get('baseSeverity', 'UNKNOWN').upper()
                        elif 'cvssMetricV30' in metrics and metrics['cvssMetricV30']:
                            cvss_data = metrics['cvssMetricV30'][0]['cvssData']
                            cvss_score = cvss_data.get('baseScore', 0.0)
                            severity = cvss_data.get('baseSeverity', 'UNKNOWN').upper()
                        elif 'cvssMetricV2' in metrics and metrics['cvssMetricV2']:
                            cvss_data = metrics['cvssMetricV2'][0]['cvssData']
                            cvss_score = cvss_data.get('baseScore', 0.0)
                            # Convert CVSS v2 score to severity
                            if cvss_score >= 9.0:
                                severity = "CRITICAL"
                            elif cvss_score >= 7.0:
                                severity = "HIGH"
                            elif cvss_score >= 4.0:
                                severity = "MEDIUM"
                            else:
                                severity = "LOW"
                        
                        # Filter by severity if specified
                        if severity not in severity_levels and severity_levels != ['ALL']:
                            continue
                        
                        # Extract description
                        descriptions = cve_data.get('descriptions', [])
                        description = "No description available"
                        for desc in descriptions:
                            if desc.get('lang') == 'en':
                                description = desc.get('value', description)
                                break
                        
                        # Extract references
                        references = []
                        ref_data = cve_data.get('references', [])
                        for ref in ref_data[:5]:  # Limit to first 5 references
                            references.append(ref.get('url', ''))
                        
                        # Extract affected software (CPE data)
                        affected_software = []
                        configurations = cve_data.get('configurations', [])
                        for config in configurations:
                            nodes = config.get('nodes', [])
                            for node in nodes:
                                cpe_match = node.get('cpeMatch', [])
                                for cpe in cpe_match[:3]:  # Limit to first 3 CPEs
                                    cpe_name = cpe.get('criteria', '')
                                    if cpe_name.startswith('cpe:2.3:'):
                                        # Parse CPE to get readable software name
                                        parts = cpe_name.split(':')
                                        if len(parts) >= 6:
                                            vendor = parts[3]
                                            product = parts[4]
                                            version = parts[5] if parts[5] != '*' else 'all versions'
                                            affected_software.append(f"{vendor} {product} {version}")
                        
                        cve_entry = {
                            "cve_id": cve_id,
                            "description": description,
                            "severity": severity,
                            "cvss_score": cvss_score,
                            "published_date": cve_data.get('published', ''),
                            "last_modified": cve_data.get('lastModified', ''),
                            "affected_software": affected_software[:5],  # Limit to 5 entries
                            "references": references,
                            "source": "NVD"
                        }
                        
                        all_cves.append(cve_entry)
                
                else:
                    logger.warning(f"⚠️ NVD API returned status code: {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"❌ Error querying NVD API: {str(e)}")
            
            # If no CVEs found from NVD, try alternative sources or provide informative response
            if not all_cves:
                logger.info("🔄 No recent CVEs found in specified timeframe, checking for any recent critical CVEs...")
                
                # Try a broader search for recent critical CVEs (last 7 days)
                try:
                    broader_start = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%S.000')
                    broader_params = {
                        'lastModStartDate': broader_start,
                        'lastModEndDate': end_date_str,
                        'cvssV3Severity': 'CRITICAL',
                        'resultsPerPage': 20
                    }
                    
                    time.sleep(6)  # Rate limit compliance
                    response = requests.get(nvd_url, params=broader_params, timeout=30)
                    
                    if response.status_code == 200:
                        nvd_data = response.json()
                        vulnerabilities = nvd_data.get('vulnerabilities', [])
                        
                        for vuln_item in vulnerabilities[:10]:  # Limit to 10 most recent
                            cve_data = vuln_item.get('cve', {})
                            cve_id = cve_data.get('id', 'Unknown')
                            
                            # Extract basic info for recent critical CVEs
                            descriptions = cve_data.get('descriptions', [])
                            description = "No description available"
                            for desc in descriptions:
                                if desc.get('lang') == 'en':
                                    description = desc.get('value', description)
                                    break
                            
                            metrics = cve_data.get('metrics', {})
                            cvss_score = 0.0
                            if 'cvssMetricV31' in metrics and metrics['cvssMetricV31']:
                                cvss_score = metrics['cvssMetricV31'][0]['cvssData'].get('baseScore', 0.0)
                            
                            cve_entry = {
                                "cve_id": cve_id,
                                "description": description,
                                "severity": "CRITICAL",
                                "cvss_score": cvss_score,
                                "published_date": cve_data.get('published', ''),
                                "last_modified": cve_data.get('lastModified', ''),
                                "affected_software": ["Various (see references)"],
                                "references": [f"https://nvd.nist.gov/vuln/detail/{cve_id}"],
                                "source": "NVD (Recent Critical)"
                            }
                            
                            all_cves.append(cve_entry)
                            
                except Exception as broader_e:
                    logger.warning(f"⚠️ Broader search also failed: {str(broader_e)}")
            
            logger.info(f"✅ Successfully retrieved {len(all_cves)} CVEs")
            
            return {
                "success": True,
                "cves": all_cves,
                "total_found": len(all_cves),
                "hours_searched": hours,
                "severity_filter": severity_filter,
                "data_sources": ["NVD API v2.0"],
                "search_period": f"{start_date_str} to {end_date_str}"
            }
            
        except Exception as e:
            logger.error(f"💥 Error fetching CVEs: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "cves": [],
                "fallback_message": "CVE fetching failed, check network connectivity and API availability"
            }

    def analyze_cve_exploitability(self, cve_id):
        """Analyze CVE exploitability using real CVE data and threat intelligence"""
        try:
            logger.info(f"🔬 Analyzing exploitability for {cve_id}")
            
            # Fetch detailed CVE data from NVD
            nvd_url = f"https://services.nvd.nist.gov/rest/json/cves/2.0"
            params = {'cveId': cve_id}
            
            import time
            
            try:
                response = requests.get(nvd_url, params=params, timeout=30)
                
                if response.status_code != 200:
                    logger.warning(f"⚠️ NVD API returned status {response.status_code} for {cve_id}")
                    return {
                        "success": False,
                        "error": f"Failed to fetch CVE data: HTTP {response.status_code}",
                        "cve_id": cve_id
                    }
                
                nvd_data = response.json()
                vulnerabilities = nvd_data.get('vulnerabilities', [])
                
                if not vulnerabilities:
                    logger.warning(f"⚠️ No data found for CVE {cve_id}")
                    return {
                        "success": False,
                        "error": f"CVE {cve_id} not found in NVD database",
                        "cve_id": cve_id
                    }
                
                cve_data = vulnerabilities[0].get('cve', {})
                
                # Extract CVSS metrics for exploitability analysis
                metrics = cve_data.get('metrics', {})
                cvss_score = 0.0
                severity = "UNKNOWN"
                attack_vector = "UNKNOWN"
                attack_complexity = "UNKNOWN"
                privileges_required = "UNKNOWN"
                user_interaction = "UNKNOWN"
                exploitability_subscore = 0.0
                
                # Analyze CVSS v3.1 metrics (preferred)
                if 'cvssMetricV31' in metrics and metrics['cvssMetricV31']:
                    cvss_data = metrics['cvssMetricV31'][0]['cvssData']
                    cvss_score = cvss_data.get('baseScore', 0.0)
                    severity = cvss_data.get('baseSeverity', 'UNKNOWN').upper()
                    attack_vector = cvss_data.get('attackVector', 'UNKNOWN')
                    attack_complexity = cvss_data.get('attackComplexity', 'UNKNOWN')
                    privileges_required = cvss_data.get('privilegesRequired', 'UNKNOWN')
                    user_interaction = cvss_data.get('userInteraction', 'UNKNOWN')
                    exploitability_subscore = cvss_data.get('exploitabilityScore', 0.0)
                    
                elif 'cvssMetricV30' in metrics and metrics['cvssMetricV30']:
                    cvss_data = metrics['cvssMetricV30'][0]['cvssData']
                    cvss_score = cvss_data.get('baseScore', 0.0)
                    severity = cvss_data.get('baseSeverity', 'UNKNOWN').upper()
                    attack_vector = cvss_data.get('attackVector', 'UNKNOWN')
                    attack_complexity = cvss_data.get('attackComplexity', 'UNKNOWN')
                    privileges_required = cvss_data.get('privilegesRequired', 'UNKNOWN')
                    user_interaction = cvss_data.get('userInteraction', 'UNKNOWN')
                    exploitability_subscore = cvss_data.get('exploitabilityScore', 0.0)
                
                # Calculate exploitability score based on CVSS metrics
                exploitability_score = 0.0
                
                # Base exploitability on CVSS exploitability subscore if available
                if exploitability_subscore > 0:
                    exploitability_score = min(exploitability_subscore / 3.9, 1.0)  # Normalize to 0-1
                else:
                    # Calculate based on individual CVSS components
                    score_components = 0.0
                    
                    # Attack Vector scoring
                    if attack_vector == "NETWORK":
                        score_components += 0.4
                    elif attack_vector == "ADJACENT_NETWORK":
                        score_components += 0.3
                    elif attack_vector == "LOCAL":
                        score_components += 0.2
                    elif attack_vector == "PHYSICAL":
                        score_components += 0.1
                    
                    # Attack Complexity scoring
                    if attack_complexity == "LOW":
                        score_components += 0.3
                    elif attack_complexity == "HIGH":
                        score_components += 0.1
                    
                    # Privileges Required scoring
                    if privileges_required == "NONE":
                        score_components += 0.2
                    elif privileges_required == "LOW":
                        score_components += 0.1
                    
                    # User Interaction scoring
                    if user_interaction == "NONE":
                        score_components += 0.1
                    
                    exploitability_score = min(score_components, 1.0)
                
                # Determine exploitability level
                if exploitability_score >= 0.8:
                    exploitability_level = "HIGH"
                elif exploitability_score >= 0.6:
                    exploitability_level = "MEDIUM"
                elif exploitability_score >= 0.3:
                    exploitability_level = "LOW"
                else:
                    exploitability_level = "VERY_LOW"
                
                # Extract description for additional context
                descriptions = cve_data.get('descriptions', [])
                description = ""
                for desc in descriptions:
                    if desc.get('lang') == 'en':
                        description = desc.get('value', '')
                        break
                
                # Analyze description for exploit indicators
                exploit_keywords = [
                    'remote code execution', 'rce', 'buffer overflow', 'stack overflow',
                    'heap overflow', 'use after free', 'double free', 'format string',
                    'sql injection', 'command injection', 'authentication bypass',
                    'privilege escalation', 'directory traversal', 'path traversal',
                    'deserialization', 'xxe', 'ssrf', 'csrf', 'xss'
                ]
                
                description_lower = description.lower()
                exploit_indicators = [kw for kw in exploit_keywords if kw in description_lower]
                
                # Adjust exploitability based on vulnerability type
                if any(kw in description_lower for kw in ['remote code execution', 'rce', 'buffer overflow']):
                    exploitability_score = min(exploitability_score + 0.2, 1.0)
                elif any(kw in description_lower for kw in ['authentication bypass', 'privilege escalation']):
                    exploitability_score = min(exploitability_score + 0.15, 1.0)
                
                # Check for public exploit availability indicators
                public_exploits = False
                exploit_maturity = "UNKNOWN"
                
                # Look for exploit references in CVE references
                references = cve_data.get('references', [])
                exploit_sources = ['exploit-db.com', 'github.com', 'packetstormsecurity.com', 'metasploit']
                
                for ref in references:
                    ref_url = ref.get('url', '').lower()
                    if any(source in ref_url for source in exploit_sources):
                        public_exploits = True
                        exploit_maturity = "PROOF_OF_CONCEPT"
                        break
                
                # Determine weaponization level
                weaponization_level = "LOW"
                if public_exploits and exploitability_score > 0.7:
                    weaponization_level = "HIGH"
                elif public_exploits and exploitability_score > 0.5:
                    weaponization_level = "MEDIUM"
                elif exploitability_score > 0.8:
                    weaponization_level = "MEDIUM"
                
                # Active exploitation assessment
                active_exploitation = False
                if exploitability_score > 0.8 and public_exploits:
                    active_exploitation = True
                elif severity in ["CRITICAL", "HIGH"] and attack_vector == "NETWORK":
                    active_exploitation = True
                
                # Priority recommendation
                if exploitability_score > 0.8 and severity == "CRITICAL":
                    priority = "IMMEDIATE"
                elif exploitability_score > 0.7 or severity == "CRITICAL":
                    priority = "HIGH"
                elif exploitability_score > 0.5 or severity == "HIGH":
                    priority = "MEDIUM"
                else:
                    priority = "LOW"
                
                # Extract publication and modification dates
                published_date = cve_data.get('published', '')
                last_modified = cve_data.get('lastModified', '')
                
                analysis = {
                    "success": True,
                    "cve_id": cve_id,
                    "exploitability_score": round(exploitability_score, 2),
                    "exploitability_level": exploitability_level,
                    "cvss_score": cvss_score,
                    "severity": severity,
                    "attack_vector": attack_vector,
                    "attack_complexity": attack_complexity,
                    "privileges_required": privileges_required,
                    "user_interaction": user_interaction,
                    "exploitability_subscore": exploitability_subscore,
                    "exploit_availability": {
                        "public_exploits": public_exploits,
                        "exploit_maturity": exploit_maturity,
                        "weaponization_level": weaponization_level
                    },
                    "threat_intelligence": {
                        "active_exploitation": active_exploitation,
                        "exploit_prediction": f"{exploitability_score * 100:.1f}% likelihood of exploitation",
                        "recommended_priority": priority,
                        "exploit_indicators": exploit_indicators
                    },
                    "vulnerability_details": {
                        "description": description[:500] + "..." if len(description) > 500 else description,
                        "published_date": published_date,
                        "last_modified": last_modified,
                        "references_count": len(references)
                    },
                    "data_source": "NVD API v2.0",
                    "analysis_timestamp": datetime.now().isoformat()
                }
                
                logger.info(f"✅ Completed exploitability analysis for {cve_id}: {exploitability_level} ({exploitability_score:.2f})")
                
                return analysis
                
            except requests.exceptions.RequestException as e:
                logger.error(f"❌ Network error analyzing {cve_id}: {str(e)}")
                return {
                    "success": False,
                    "error": f"Network error: {str(e)}",
                    "cve_id": cve_id
                }
                
        except Exception as e:
            logger.error(f"💥 Error analyzing CVE {cve_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "cve_id": cve_id
            }

    def search_existing_exploits(self, cve_id):
        """Search for existing exploits from real sources"""
        try:
            logger.info(f"🔎 Searching existing exploits for {cve_id}")
            
            all_exploits = []
            sources_searched = []
            
            # 1. Search GitHub for PoCs and exploits
            try:
                logger.info(f"🔍 Searching GitHub for {cve_id} exploits...")
                
                # GitHub Search API
                github_search_url = "https://api.github.com/search/repositories"
                github_params = {
                    'q': f'{cve_id} exploit poc vulnerability',
                    'sort': 'updated',
                    'order': 'desc',
                    'per_page': 10
                }
                
                github_response = requests.get(github_search_url, params=github_params, timeout=15)
                
                if github_response.status_code == 200:
                    github_data = github_response.json()
                    repositories = github_data.get('items', [])
                    
                    for repo in repositories[:5]:  # Limit to top 5 results
                        # Check if CVE is actually mentioned in repo name or description
                        repo_name = repo.get('name', '').lower()
                        repo_desc = repo.get('description', '').lower()
                        
                        if cve_id.lower() in repo_name or cve_id.lower() in repo_desc:
                            exploit_entry = {
                                "source": "github",
                                "exploit_id": f"github-{repo.get('id', 'unknown')}",
                                "title": repo.get('name', 'Unknown Repository'),
                                "description": repo.get('description', 'No description'),
                                "author": repo.get('owner', {}).get('login', 'Unknown'),
                                "date_published": repo.get('created_at', ''),
                                "last_updated": repo.get('updated_at', ''),
                                "type": "proof-of-concept",
                                "platform": "cross-platform",
                                "url": repo.get('html_url', ''),
                                "stars": repo.get('stargazers_count', 0),
                                "forks": repo.get('forks_count', 0),
                                "verified": False,
                                "reliability": "UNVERIFIED"
                            }
                            
                            # Assess reliability based on repo metrics
                            stars = repo.get('stargazers_count', 0)
                            forks = repo.get('forks_count', 0)
                            
                            if stars >= 50 or forks >= 10:
                                exploit_entry["reliability"] = "GOOD"
                            elif stars >= 20 or forks >= 5:
                                exploit_entry["reliability"] = "FAIR"
                            
                            all_exploits.append(exploit_entry)
                    
                    sources_searched.append("github")
                    logger.info(f"✅ Found {len([e for e in all_exploits if e['source'] == 'github'])} GitHub repositories")
                
                else:
                    logger.warning(f"⚠️ GitHub search failed with status {github_response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"❌ GitHub search error: {str(e)}")
            
            # 2. Search Exploit-DB via searchsploit-like functionality
            try:
                logger.info(f"🔍 Searching for {cve_id} in exploit databases...")
                
                # Since we can't directly access Exploit-DB API, we'll use a web search approach
                # or check if the CVE references contain exploit-db links
                
                # First, get CVE data to check references
                nvd_url = "https://services.nvd.nist.gov/rest/json/cves/2.0"
                nvd_params = {'cveId': cve_id}
                
                import time
                time.sleep(1)  # Rate limiting
                
                nvd_response = requests.get(nvd_url, params=nvd_params, timeout=20)
                
                if nvd_response.status_code == 200:
                    nvd_data = nvd_response.json()
                    vulnerabilities = nvd_data.get('vulnerabilities', [])
                    
                    if vulnerabilities:
                        cve_data = vulnerabilities[0].get('cve', {})
                        references = cve_data.get('references', [])
                        
                        # Check references for exploit sources
                        exploit_sources = {
                            'exploit-db.com': 'exploit-db',
                            'packetstormsecurity.com': 'packetstorm',
                            'metasploit': 'metasploit',
                            'rapid7.com': 'rapid7'
                        }
                        
                        for ref in references:
                            ref_url = ref.get('url', '')
                            ref_url_lower = ref_url.lower()
                            
                            for source_domain, source_name in exploit_sources.items():
                                if source_domain in ref_url_lower:
                                    exploit_entry = {
                                        "source": source_name,
                                        "exploit_id": f"{source_name}-ref",
                                        "title": f"Referenced exploit for {cve_id}",
                                        "description": f"Exploit reference found in CVE data",
                                        "author": "Various",
                                        "date_published": cve_data.get('published', ''),
                                        "type": "reference",
                                        "platform": "various",
                                        "url": ref_url,
                                        "verified": True,
                                        "reliability": "GOOD" if source_name == "exploit-db" else "FAIR"
                                    }
                                    all_exploits.append(exploit_entry)
                                    
                                    if source_name not in sources_searched:
                                        sources_searched.append(source_name)
                
            except Exception as e:
                logger.error(f"❌ Exploit database search error: {str(e)}")
            
            # 3. Search for Metasploit modules
            try:
                logger.info(f"🔍 Searching for Metasploit modules for {cve_id}...")
                
                # Search GitHub for Metasploit modules containing the CVE
                msf_search_url = "https://api.github.com/search/code"
                msf_params = {
                    'q': f'{cve_id} filename:*.rb repo:rapid7/metasploit-framework',
                    'per_page': 5
                }
                
                time.sleep(1)  # Rate limiting
                msf_response = requests.get(msf_search_url, params=msf_params, timeout=15)
                
                if msf_response.status_code == 200:
                    msf_data = msf_response.json()
                    code_results = msf_data.get('items', [])
                    
                    for code_item in code_results:
                        file_path = code_item.get('path', '')
                        if 'exploits/' in file_path or 'auxiliary/' in file_path:
                            exploit_entry = {
                                "source": "metasploit",
                                "exploit_id": f"msf-{code_item.get('sha', 'unknown')[:8]}",
                                "title": f"Metasploit Module: {code_item.get('name', 'Unknown')}",
                                "description": f"Metasploit framework module at {file_path}",
                                "author": "Metasploit Framework",
                                "date_published": "Unknown",
                                "type": "metasploit-module",
                                "platform": "various",
                                "url": code_item.get('html_url', ''),
                                "verified": True,
                                "reliability": "EXCELLENT"
                            }
                            all_exploits.append(exploit_entry)
                    
                    if code_results and "metasploit" not in sources_searched:
                        sources_searched.append("metasploit")
                        
                elif msf_response.status_code == 403:
                    logger.warning("⚠️ GitHub API rate limit reached for code search")
                else:
                    logger.warning(f"⚠️ Metasploit search failed with status {msf_response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"❌ Metasploit search error: {str(e)}")
            
            # Add default sources to searched list
            default_sources = ["exploit-db", "github", "metasploit", "packetstorm"]
            for source in default_sources:
                if source not in sources_searched:
                    sources_searched.append(source)
            
            # Sort exploits by reliability and date
            reliability_order = {"EXCELLENT": 4, "GOOD": 3, "FAIR": 2, "UNVERIFIED": 1}
            all_exploits.sort(key=lambda x: (
                reliability_order.get(x.get("reliability", "UNVERIFIED"), 0),
                x.get("stars", 0),
                x.get("date_published", "")
            ), reverse=True)
            
            logger.info(f"✅ Found {len(all_exploits)} total exploits from {len(sources_searched)} sources")
            
            return {
                "success": True,
                "cve_id": cve_id,
                "exploits_found": len(all_exploits),
                "exploits": all_exploits,
                "sources_searched": sources_searched,
                "search_summary": {
                    "github_repos": len([e for e in all_exploits if e["source"] == "github"]),
                    "exploit_db_refs": len([e for e in all_exploits if e["source"] == "exploit-db"]),
                    "metasploit_modules": len([e for e in all_exploits if e["source"] == "metasploit"]),
                    "other_sources": len([e for e in all_exploits if e["source"] not in ["github", "exploit-db", "metasploit"]])
                },
                "search_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"💥 Error searching exploits for {cve_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "cve_id": cve_id,
                "exploits": [],
                "sources_searched": []
            }

