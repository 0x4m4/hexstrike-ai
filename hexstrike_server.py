#!/usr/bin/env python3
"""
HexStrike AI - Advanced Penetration Testing Framework Server

Enhanced with AI-Powered Intelligence & Automation
🚀 Bug Bounty | CTF | Red Team | Security Research

RECENT ENHANCEMENTS (v6.0):
✅ Complete color consistency with reddish hacker theme
✅ Removed duplicate classes
"""

import os
import json
import logging
from flask import Flask, request, jsonify, send_file, render_template_string
from werkzeug.exceptions import InternalServerError

# Initialize Flask app
app = Flask(__name__)

# Configuration
REPORTS_DIR = os.path.join(os.path.dirname(__file__), 'reports')
os.makedirs(REPORTS_DIR, exist_ok=True)

# In-memory storage for scan results (simulated)
scans = {}

# Report template - simple HTML (replace with actual template if needed)
REPORT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><title>HexStrike Summary Report</title></head>
<body>
<h1>Scan Summary</h1>
<p>Target: {{ target }}</p>
<p>Timestamp: {{ timestamp }}</p>
<pre>{{ result }}</pre>
</body>
</html>
"""


@app.errorhandler(InternalServerError)
def handle_500(error):
    """Global handler for unhandled 500 errors."""
    app.logger.error(f"Unhandled exception: {error.original_exception}")
    return jsonify({
        "error": "Internal server error",
        "message": str(error.original_exception) if error.original_exception else "Unknown error"
    }), 500


@app.route('/api/visual/summary-report', methods=['POST'])
def generate_summary_report():
    """
    Generate and return a summary report for a given scan.
    Expects JSON: {'scan_id': <id>}
    """
    try:
        data = request.get_json(force=True)
        scan_id = data.get('scan_id')
        if not scan_id or scan_id not in scans:
            return jsonify({"error": "Invalid or missing scan_id"}), 400

        scan_data = scans[scan_id]

        # Ensure reports directory exists
        os.makedirs(REPORTS_DIR, exist_ok=True)

        # Generate report content (here we use a simple HTML template)
        report_html = render_template_string(
            REPORT_TEMPLATE,
            target=scan_data.get('target', 'unknown'),
            timestamp=scan_data.get('timestamp', 'N/A'),
            result=json.dumps(scan_data.get('result', {}), indent=2)
        )

        # Save report to file
        report_filename = f"summary_{scan_id}.html"
        report_path = os.path.join(REPORTS_DIR, report_filename)
        with open(report_path, 'w') as f:
            f.write(report_html)

        # Return the report file
        return send_file(report_path, as_attachment=True, download_name=report_filename)

    except Exception as e:
        app.logger.exception("Failed to generate summary report")
        # Raise to trigger 500 handler (already catches)
        raise InternalServerError(f"Report generation failed: {str(e)}")


# For testing: endpoint to simulate a scan
@app.route('/api/scan', methods=['POST'])
def create_scan():
    data = request.get_json(force=True)
    scan_id = str(len(scans) + 1)
    scans[scan_id] = {
        'target': data.get('target', 'unknown'),
        'timestamp': data.get('timestamp', 'N/A'),
        'result': data.get('result', {})
    }
    return jsonify({"scan_id": scan_id, "status": "created"})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8888, debug=False)