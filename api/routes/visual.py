"""
Visual Generation API Routes
Handles vulnerability cards, summary reports, and tool output formatting
"""

import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from core.visual import ModernVisualEngine

logger = logging.getLogger(__name__)

# Create blueprint
visual_bp = Blueprint('visual', __name__, url_prefix='/api/visual')


@visual_bp.route("/vulnerability-card", methods=["POST"])
def create_vulnerability_card():
    """Create a beautiful vulnerability card using ModernVisualEngine"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Create vulnerability card
        card = ModernVisualEngine.render_vulnerability_card(data)

        return jsonify({
            "success": True,
            "vulnerability_card": card,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"💥 Error creating vulnerability card: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@visual_bp.route("/summary-report", methods=["POST"])
def create_summary_report():
    """Create a beautiful summary report using ModernVisualEngine"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Create summary report
        visual_engine = ModernVisualEngine()
        report = visual_engine.create_summary_report(data)

        return jsonify({
            "success": True,
            "summary_report": report,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"💥 Error creating summary report: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@visual_bp.route("/tool-output", methods=["POST"])
def format_tool_output():
    """Format tool output using ModernVisualEngine"""
    try:
        data = request.get_json()
        if not data or 'tool' not in data or 'output' not in data:
            return jsonify({"error": "Tool and output data required"}), 400

        tool = data['tool']
        output = data['output']
        success = data.get('success', True)

        # Format tool output
        formatted_output = ModernVisualEngine.format_tool_output(tool, output, success)

        return jsonify({
            "success": True,
            "formatted_output": formatted_output,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"💥 Error formatting tool output: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500
