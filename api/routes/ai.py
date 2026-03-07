"""
AI-Powered Payload Generation API Routes
Handles AI-powered contextual payload generation and testing
"""

import logging
from datetime import datetime
from typing import Dict, Any
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

# Create blueprint
ai_bp = Blueprint('ai', __name__, url_prefix='/api/ai')

# Dependencies will be injected via init_app
ai_payload_generator = None
execute_command = None

def init_app(payload_gen, exec_cmd):
    """Initialize blueprint with dependencies"""
    global ai_payload_generator, execute_command
    ai_payload_generator = payload_gen
    execute_command = exec_cmd


@ai_bp.route("/generate_payload", methods=["POST"])
def ai_generate_payload():
    """Generate AI-powered contextual payloads for security testing"""
    try:
        params = request.json
        target_info = {
            "attack_type": params.get("attack_type", "xss"),
            "complexity": params.get("complexity", "basic"),
            "technology": params.get("technology", ""),
            "url": params.get("url", "")
        }

        logger.info(f"🤖 Generating AI payloads for {target_info['attack_type']} attack")
        result = ai_payload_generator.generate_contextual_payload(target_info)

        logger.info(f"✅ Generated {result['payload_count']} contextual payloads")

        return jsonify({
            "success": True,
            "ai_payload_generation": result,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"💥 Error in AI payload generation: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Server error: {str(e)}"
        }), 500

@ai_bp.route("/test_payload", methods=["POST"])
def ai_test_payload():
    """Test generated payload against target with AI analysis"""
    try:
        params = request.json
        payload = params.get("payload", "")
        target_url = params.get("target_url", "")
        method = params.get("method", "GET")

        if not payload or not target_url:
            return jsonify({
                "success": False,
                "error": "Payload and target_url are required"
            }), 400

        logger.info(f"🧪 Testing AI-generated payload against {target_url}")

        # Create test command based on method and payload
        if method.upper() == "GET":
            encoded_payload = payload.replace(" ", "%20").replace("'", "%27")
            test_command = f"curl -s '{target_url}?test={encoded_payload}'"
        else:
            test_command = f"curl -s -X POST -d 'test={payload}' '{target_url}'"

        # Execute test
        result = execute_command(test_command, use_cache=False)

        # AI analysis of results
        analysis = {
            "payload_tested": payload,
            "target_url": target_url,
            "method": method,
            "response_size": len(result.get("stdout", "")),
            "success": result.get("success", False),
            "potential_vulnerability": payload.lower() in result.get("stdout", "").lower(),
            "recommendations": [
                "Analyze response for payload reflection",
                "Check for error messages indicating vulnerability",
                "Monitor application behavior changes"
            ]
        }

        logger.info(f"🔍 Payload test completed | Potential vuln: {analysis['potential_vulnerability']}")

        return jsonify({
            "success": True,
            "test_result": result,
            "ai_analysis": analysis,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"💥 Error in AI payload testing: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Server error: {str(e)}"
        }), 500

@ai_bp.route("/advanced-payload-generation", methods=["POST"])
def advanced_payload_generation():
    """Generate advanced contextual payloads using AI-powered techniques"""
    try:
        params = request.json
        attack_type = params.get("attack_type", "xss")
        target_context = params.get("target_context", {})
        complexity = params.get("complexity", "basic")
        technology = params.get("technology", "")
        url = params.get("url", "")

        # Build target info for AI payload generator
        target_info = {
            "attack_type": attack_type,
            "complexity": complexity,
            "technology": technology,
            "url": url
        }

        # Merge additional context
        if target_context:
            target_info.update(target_context)

        logger.info(f"🤖 Generating advanced payloads for {attack_type} attack with {complexity} complexity")
        result = ai_payload_generator.generate_contextual_payload(target_info)

        logger.info(f"✅ Generated {result['payload_count']} advanced contextual payloads")

        return jsonify({
            "success": True,
            "advanced_payload_generation": result,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"💥 Error in advanced payload generation: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Server error: {str(e)}"
        }), 500
