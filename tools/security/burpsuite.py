"""
Burp Suite tool implementation for web application security testing
"""
from typing import Dict, Any, List
from tools.base import BaseTool
import json
import xml.etree.ElementTree as ET


class BurpSuiteTool(BaseTool):
    """Burp Suite - Web application security testing platform"""

    def __init__(self):
        super().__init__("Burp Suite", "burp")

    def build_command(self, target: str, params: Dict[str, Any]) -> List[str]:
        """
        Build Burp Suite command with comprehensive options

        Args:
            target: Target URL to scan
            params: Dictionary containing:
                - config_file: Burp configuration file
                - project_file: Burp project file
                - scan_type: Type of scan (crawl, audit, crawl_and_audit)
                - scope: Scope configuration
                - user_agent: Custom user agent
                - auth: Authentication configuration
                - report_format: Report format (html, xml, json)
                - report_file: Report output file
                - resource_pool: Resource pool configuration
                - additional_args: Additional command-line arguments

        Returns:
            List of command arguments
        """
        # Burp Suite command line scanner
        cmd_parts = ["java", "-jar", "/opt/burpsuite/burpsuite.jar"]

        # Headless mode
        cmd_parts.append("--headless")

        # Project file
        if params.get("project_file"):
            cmd_parts.extend(["--project-file=" + params["project_file"]])
        else:
            # Temporary project
            cmd_parts.append("--project-file=temp_burp_project")

        # Configuration file
        if params.get("config_file"):
            cmd_parts.extend(["--config-file=" + params["config_file"]])

        # Scan type
        scan_type = params.get("scan_type", "crawl_and_audit")
        if scan_type == "crawl":
            cmd_parts.append("--crawl-only")
        elif scan_type == "audit":
            cmd_parts.append("--audit-only")
        # Default is crawl_and_audit

        # Target URL
        cmd_parts.extend(["--url=" + target])

        # Scope
        if params.get("scope"):
            cmd_parts.extend(["--scope=" + params["scope"]])

        # User agent
        if params.get("user_agent"):
            cmd_parts.extend(["--user-agent=" + params["user_agent"]])

        # Authentication
        if params.get("auth"):
            cmd_parts.extend(["--auth=" + params["auth"]])

        # Report format and file
        report_format = params.get("report_format", "html")
        report_file = params.get("report_file", "burp_report." + report_format)
        cmd_parts.extend([f"--report-output={report_file}"])
        cmd_parts.extend([f"--report-type={report_format}"])

        # Resource pool
        if params.get("resource_pool"):
            cmd_parts.extend(["--resource-pool=" + params["resource_pool"]])

        # Additional arguments
        additional_args = params.get("additional_args", "")
        if additional_args:
            cmd_parts.extend(additional_args.split())

        return cmd_parts

    def parse_output(self, stdout: str, stderr: str, returncode: int) -> Dict[str, Any]:
        """
        Parse Burp Suite output to extract security findings

        Args:
            stdout: Command standard output
            stderr: Command standard error
            returncode: Command return code

        Returns:
            Dictionary containing:
                - issues: List of security issues found
                - issue_count: Total number of issues
                - issues_by_severity: Issues categorized by severity
                - issues_by_type: Issues categorized by type
                - urls_tested: List of URLs tested
                - high_severity_issues: High severity issues
                - medium_severity_issues: Medium severity issues
                - low_severity_issues: Low severity issues
                - raw_output: Original stdout
                - stderr: Original stderr
                - returncode: Command return code
        """
        issues = []
        issues_by_severity = {
            'High': [],
            'Medium': [],
            'Low': [],
            'Information': []
        }
        issues_by_type = {}
        urls_tested = set()

        # Try to parse as JSON first
        try:
            data = json.loads(stdout)

            # Burp JSON format
            if isinstance(data, dict) and 'issue_events' in data:
                for issue in data['issue_events']:
                    issue_info = {
                        'name': issue.get('issue', {}).get('name', 'Unknown'),
                        'severity': issue.get('issue', {}).get('severity', 'Information'),
                        'confidence': issue.get('issue', {}).get('confidence', 'Unknown'),
                        'url': issue.get('url', ''),
                        'description': issue.get('issue', {}).get('description', ''),
                        'remediation': issue.get('issue', {}).get('remediation', ''),
                        'vulnerability_classifications': issue.get('issue', {}).get('vulnerability_classifications', [])
                    }
                    issues.append(issue_info)

                    # Categorize by severity
                    severity = issue_info['severity']
                    if severity in issues_by_severity:
                        issues_by_severity[severity].append(issue_info)

                    # Categorize by type
                    issue_type = issue_info['name']
                    if issue_type not in issues_by_type:
                        issues_by_type[issue_type] = []
                    issues_by_type[issue_type].append(issue_info)

                    # Track URLs
                    if issue_info['url']:
                        urls_tested.add(issue_info['url'])

        except json.JSONDecodeError:
            # Try to parse as XML
            try:
                root = ET.fromstring(stdout)
                for issue in root.findall('.//issue'):
                    issue_info = {
                        'name': issue.find('name').text if issue.find('name') is not None else 'Unknown',
                        'severity': issue.find('severity').text if issue.find('severity') is not None else 'Information',
                        'confidence': issue.find('confidence').text if issue.find('confidence') is not None else 'Unknown',
                        'url': issue.find('url').text if issue.find('url') is not None else '',
                        'description': issue.find('issueBackground').text if issue.find('issueBackground') is not None else '',
                        'remediation': issue.find('remediationBackground').text if issue.find('remediationBackground') is not None else ''
                    }
                    issues.append(issue_info)

                    # Categorize by severity
                    severity = issue_info['severity']
                    if severity in issues_by_severity:
                        issues_by_severity[severity].append(issue_info)

                    # Categorize by type
                    issue_type = issue_info['name']
                    if issue_type not in issues_by_type:
                        issues_by_type[issue_type] = []
                    issues_by_type[issue_type].append(issue_info)

                    # Track URLs
                    if issue_info['url']:
                        urls_tested.add(issue_info['url'])

            except ET.ParseError:
                # Parse plain text output
                import re
                for line in stdout.split('\n'):
                    # Look for issue patterns
                    issue_match = re.search(r'\[(High|Medium|Low|Information)\]\s+(.+)', line)
                    if issue_match:
                        severity = issue_match.group(1)
                        name = issue_match.group(2)
                        issue_info = {
                            'name': name,
                            'severity': severity,
                            'finding': line
                        }
                        issues.append(issue_info)

                        if severity in issues_by_severity:
                            issues_by_severity[severity].append(issue_info)

        # Get severity counts
        severity_counts = {k: len(v) for k, v in issues_by_severity.items() if v}

        # Get type counts
        type_counts = {k: len(v) for k, v in issues_by_type.items()}

        return {
            "issues": issues,
            "issue_count": len(issues),
            "issues_by_severity": issues_by_severity,
            "severity_counts": severity_counts,
            "issues_by_type": issues_by_type,
            "type_counts": type_counts,
            "urls_tested": sorted(list(urls_tested)),
            "url_count": len(urls_tested),
            "high_severity_issues": issues_by_severity.get('High', []),
            "high_count": len(issues_by_severity.get('High', [])),
            "medium_severity_issues": issues_by_severity.get('Medium', []),
            "medium_count": len(issues_by_severity.get('Medium', [])),
            "low_severity_issues": issues_by_severity.get('Low', []),
            "low_count": len(issues_by_severity.get('Low', [])),
            "raw_output": stdout,
            "stderr": stderr,
            "returncode": returncode
        }
