"""
OWASP ZAP tool implementation for web application security scanning
"""
from typing import Dict, Any, List
from tools.base import BaseTool
import json
import xml.etree.ElementTree as ET


class ZAPTool(BaseTool):
    """OWASP ZAP - Web application security scanner"""

    def __init__(self):
        super().__init__("OWASP ZAP", "zap-cli")

    def build_command(self, target: str, params: Dict[str, Any]) -> List[str]:
        """
        Build OWASP ZAP command with comprehensive options

        Args:
            target: Target URL to scan
            params: Dictionary containing:
                - scan_type: Type of scan (quick, baseline, full)
                - api_key: ZAP API key
                - port: ZAP proxy port
                - context: Context file for authenticated scans
                - user: User for authenticated scans
                - ajax_spider: Enable AJAX spider
                - active_scan: Enable active scanning
                - passive_scan_only: Only passive scanning
                - exclude: URL patterns to exclude
                - config: ZAP configuration options
                - format: Output format (html, xml, json, md)
                - output: Output file path
                - additional_args: Additional command-line arguments

        Returns:
            List of command arguments
        """
        scan_type = params.get("scan_type", "quick")

        if scan_type == "baseline":
            cmd_parts = ["zap-baseline.py", "-t", target]
        elif scan_type == "full":
            cmd_parts = ["zap-full-scan.py", "-t", target]
        else:  # quick
            cmd_parts = ["zap-cli", "quick-scan", target]

        # API key
        if params.get("api_key"):
            cmd_parts.extend(["--api-key", params["api_key"]])

        # Port
        if params.get("port"):
            cmd_parts.extend(["-p", str(params["port"])])

        # Context file
        if params.get("context"):
            cmd_parts.extend(["-n", params["context"]])

        # User
        if params.get("user"):
            cmd_parts.extend(["-u", params["user"]])

        # AJAX spider
        if params.get("ajax_spider", False):
            cmd_parts.append("-j")

        # Active scan
        if params.get("active_scan", True):
            cmd_parts.append("-a")

        # Passive scan only
        if params.get("passive_scan_only", False):
            cmd_parts.append("--passive")

        # Exclude patterns
        if params.get("exclude"):
            excludes = params["exclude"] if isinstance(params["exclude"], list) else [params["exclude"]]
            for exclude in excludes:
                cmd_parts.extend(["-x", exclude])

        # Configuration
        if params.get("config"):
            configs = params["config"] if isinstance(params["config"], list) else [params["config"]]
            for config in configs:
                cmd_parts.extend(["-z", config])

        # Format
        output_format = params.get("format", "json")
        cmd_parts.extend(["-f", output_format])

        # Output file
        if params.get("output"):
            cmd_parts.extend(["-r", params["output"]])

        # Additional arguments
        additional_args = params.get("additional_args", "")
        if additional_args:
            cmd_parts.extend(additional_args.split())

        return cmd_parts

    def parse_output(self, stdout: str, stderr: str, returncode: int) -> Dict[str, Any]:
        """
        Parse ZAP output to extract security findings

        Args:
            stdout: Command standard output
            stderr: Command standard error
            returncode: Command return code

        Returns:
            Dictionary containing:
                - alerts: List of security alerts
                - alert_count: Total number of alerts
                - alerts_by_risk: Alerts categorized by risk level
                - alerts_by_type: Alerts categorized by type
                - urls_scanned: List of URLs scanned
                - high_risk_alerts: High risk alerts
                - medium_risk_alerts: Medium risk alerts
                - low_risk_alerts: Low risk alerts
                - raw_output: Original stdout
                - stderr: Original stderr
                - returncode: Command return code
        """
        alerts = []
        alerts_by_risk = {
            'High': [],
            'Medium': [],
            'Low': [],
            'Informational': []
        }
        alerts_by_type = {}
        urls_scanned = set()

        # Try to parse as JSON first
        try:
            data = json.loads(stdout)

            # ZAP JSON format has 'site' array with alerts
            if isinstance(data, dict) and 'site' in data:
                for site in data['site']:
                    for alert in site.get('alerts', []):
                        alert_info = {
                            'name': alert.get('name', alert.get('alert', 'Unknown')),
                            'risk': alert.get('riskdesc', alert.get('risk', 'Informational')).split()[0],
                            'confidence': alert.get('confidence', 'Unknown'),
                            'url': alert.get('url', ''),
                            'description': alert.get('desc', alert.get('description', '')),
                            'solution': alert.get('solution', ''),
                            'reference': alert.get('reference', '')
                        }
                        alerts.append(alert_info)

                        # Categorize by risk
                        risk = alert_info['risk']
                        if risk in alerts_by_risk:
                            alerts_by_risk[risk].append(alert_info)

                        # Categorize by type
                        alert_type = alert_info['name']
                        if alert_type not in alerts_by_type:
                            alerts_by_type[alert_type] = []
                        alerts_by_type[alert_type].append(alert_info)

                        # Track URLs
                        if alert_info['url']:
                            urls_scanned.add(alert_info['url'])

        except json.JSONDecodeError:
            # Try to parse as XML
            try:
                root = ET.fromstring(stdout)
                for alert in root.findall('.//alertitem'):
                    alert_info = {
                        'name': alert.find('alert').text if alert.find('alert') is not None else 'Unknown',
                        'risk': alert.find('riskdesc').text.split()[0] if alert.find('riskdesc') is not None else 'Informational',
                        'confidence': alert.find('confidence').text if alert.find('confidence') is not None else 'Unknown',
                        'url': alert.find('url').text if alert.find('url') is not None else '',
                        'description': alert.find('desc').text if alert.find('desc') is not None else '',
                        'solution': alert.find('solution').text if alert.find('solution') is not None else '',
                        'reference': alert.find('reference').text if alert.find('reference') is not None else ''
                    }
                    alerts.append(alert_info)

                    # Categorize by risk
                    risk = alert_info['risk']
                    if risk in alerts_by_risk:
                        alerts_by_risk[risk].append(alert_info)

                    # Categorize by type
                    alert_type = alert_info['name']
                    if alert_type not in alerts_by_type:
                        alerts_by_type[alert_type] = []
                    alerts_by_type[alert_type].append(alert_info)

                    # Track URLs
                    if alert_info['url']:
                        urls_scanned.add(alert_info['url'])

            except ET.ParseError:
                # Parse plain text output
                import re
                for line in stdout.split('\n'):
                    # Look for alert patterns
                    alert_match = re.search(r'\[(High|Medium|Low|Informational)\]\s+(.+)', line)
                    if alert_match:
                        risk = alert_match.group(1)
                        name = alert_match.group(2)
                        alert_info = {
                            'name': name,
                            'risk': risk,
                            'finding': line
                        }
                        alerts.append(alert_info)

                        if risk in alerts_by_risk:
                            alerts_by_risk[risk].append(alert_info)

        # Get risk counts
        risk_counts = {k: len(v) for k, v in alerts_by_risk.items() if v}

        # Get type counts
        type_counts = {k: len(v) for k, v in alerts_by_type.items()}

        return {
            "alerts": alerts,
            "alert_count": len(alerts),
            "alerts_by_risk": alerts_by_risk,
            "risk_counts": risk_counts,
            "alerts_by_type": alerts_by_type,
            "type_counts": type_counts,
            "urls_scanned": sorted(list(urls_scanned)),
            "url_count": len(urls_scanned),
            "high_risk_alerts": alerts_by_risk.get('High', []),
            "high_count": len(alerts_by_risk.get('High', [])),
            "medium_risk_alerts": alerts_by_risk.get('Medium', []),
            "medium_count": len(alerts_by_risk.get('Medium', [])),
            "low_risk_alerts": alerts_by_risk.get('Low', []),
            "low_count": len(alerts_by_risk.get('Low', [])),
            "raw_output": stdout,
            "stderr": stderr,
            "returncode": returncode
        }
