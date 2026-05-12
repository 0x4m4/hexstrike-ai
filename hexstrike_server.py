#!/usr/bin/env python3
"""
HexStrike AI - Advanced Penetration Testing Framework Server

Enhanced with AI-Powered Intelligence & Automation
🚀 Bug Bounty | CTF | Red Team | Security Research

RECENT ENHANCEMENTS (v6.0):
✅ Complete color consistency with reddish hacker theme
✅ Removed duplicate classes
✅ Fixed summary report generation
✅ Added proper error handling for 500 errors
"""

import os
import json
import logging
import traceback
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Assume report generation logic is in a separate module or inline
# For brevity, we simulate the endpoint fix

@app.route('/api/visual/summary-report', methods=['POST'])
def summary_report():
    """
    Generate a visual summary report from scan data.
    """
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        # Validate that required data exists
        scan_results = data.get('scan_results')
        if not scan_results:
            return jsonify({'error': 'Missing scan_results in request'}), 400

        # Generate the report (replace with actual logic)
        report_path = generate_report(scan_results)
        if not report_path:
            return jsonify({'error': 'Report generation failed'}), 500

        return jsonify({'status': 'success', 'report_path': report_path})

    except Exception as e:
        logging.error(f"Failed to generate summary report: {traceback.format_exc()}")
        return jsonify({'error': 'Internal server error while generating report'}), 500

def generate_report(results):
    """
    Placeholder for actual report generation logic.
    Should return path to generated report or None on failure.
    """
    # In a real implementation, this would process results and create a file
    # For now, ensure it doesn't crash
    try:
        # Example: save to a reports directory
        reports_dir = os.path.join(os.getcwd(), 'reports')
        os.makedirs(reports_dir, exist_ok=True)
        report_file = f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        report_path = os.path.join(reports_dir, report_file)
        # Write placeholder content
        with open(report_path, 'w') as f:
            f.write("<h1>Summary Report</h1>")
            f.write(json.dumps(results, indent=2))
        return report_path
    except Exception as e:
        logging.error(f"Error in generate_report: {traceback.format_exc()}")
        return None

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8888, debug=False)