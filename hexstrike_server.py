#!/usr/bin/env python3
"""
HexStrike AI - Advanced Penetration Testing Framework Server

Enhanced with AI-Powered Intelligence & Automation
🚀 Bug Bounty | CTF | Red Team | Security Research

RECENT ENHANCEMENTS (v6.0):
✅ Complete color consistency with reddish hacker theme
✅ Removed duplicate classes
✅ Fixed summary report 500 error
"""

import json
import logging
from flask import Flask, jsonify, request, session
from functools import wraps

app = Flask(__name__)
app.secret_key = 'hexstrike_secret_key_change_in_production'
logging.basicConfig(level=logging.INFO)

# Mock data store (replace with actual DB or file)
scan_results_store = {}

def require_scan(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        scan_id = request.args.get('scan_id') or session.get('last_scan_id')
        if not scan_id or scan_id not in scan_results_store:
            return jsonify({'error': 'No scan data found. Please run a scan first.'}), 400
        return f(scan_id, *args, **kwargs)
    return decorated

@app.route('/api/visual/summary-report', methods=['GET'])
@require_scan
def summary_report(scan_id):
    """Generate and return a summary report for the given scan."""
    try:
        scan_data = scan_results_store[scan_id]
        # Validate required fields
        if not scan_data or 'hosts' not in scan_data:
            return jsonify({'error': 'Scan data is incomplete'}), 400

        # Build summary report
        host_count = len(scan_data['hosts'])
        port_count = 0
        service_count = 0
        vulnerabilities = []
        for host in scan_data['hosts']:
            ports = host.get('ports', [])
            port_count += len(ports)
            for port in ports:
                service = port.get('service', 'unknown')
                if service != 'unknown':
                    service_count += 1
                vulns = port.get('vulnerabilities', [])
                vulnerabilities.extend(vulns)

        report = {
            'scan_id': scan_id,
            'total_hosts': host_count,
            'total_ports': port_count,
            'total_services': service_count,
            'total_vulnerabilities': len(vulnerabilities),
            'vulnerability_list': list(set(vulnerabilities))[:20]  # Top 20 distinct
        }
        return jsonify(report), 200

    except KeyError as e:
        app.logger.error(f"Summary report missing key: {e}")
        return jsonify({'error': f'Missing data: {str(e)}'}), 500
    except Exception as e:
        app.logger.error(f"Summary report error: {e}")
        return jsonify({'error': 'Internal server error. Please check server logs.'}), 500

@app.route('/api/scan/start', methods=['POST'])
def start_scan():
    """Mock endpoint to start a scan (for testing)."""
    target = request.json.get('target', '127.0.0.1')
    # Simulate scan results
    scan_id = f"scan_{len(scan_results_store)+1}"
    scan_results_store[scan_id] = {
        'hosts': [
            {
                'ip': target,
                'ports': [
                    {'port': 22, 'service': 'ssh', 'vulnerabilities': []},
                    {'port': 80, 'service': 'http', 'vulnerabilities': ['CVE-2024-1234']}
                ]
            }
        ]
    }
    session['last_scan_id'] = scan_id
    return jsonify({'scan_id': scan_id, 'status': 'completed'}), 200

@app.route('/')
def index():
    return jsonify({'status': 'HexStrike Server is running'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8888, debug=False)