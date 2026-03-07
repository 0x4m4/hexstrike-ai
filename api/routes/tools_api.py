"""
API Security Testing Tools Routes
Handles api_fuzzer, graphql_scanner, jwt_analyzer, and api_schema_analyzer tools
"""

import logging
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

# Create blueprint
tools_api_bp = Blueprint('tools_api', __name__, url_prefix='/api/tools')

# Dependencies will be injected via init_app
execute_command = None

def init_app(exec_command):
    """Initialize blueprint with dependencies"""
    global execute_command
    execute_command = exec_command


@tools_api_bp.route("/api-fuzzer", methods=["POST"])
def api_fuzzer():
    """Execute API endpoint fuzzer with enhanced logging"""
    try:
        params = request.json
        url = params.get("url", "")
        wordlist = params.get("wordlist", "/usr/share/wordlists/api-endpoints.txt")
        method = params.get("method", "GET")
        additional_args = params.get("additional_args", "")

        if not url:
            logger.warning("🌐 API Fuzzer called without URL parameter")
            return jsonify({
                "error": "URL parameter is required"
            }), 400

        command = f"ffuf -u {url}/FUZZ -w {wordlist} -X {method}"

        if additional_args:
            command += f" {additional_args}"

        logger.info(f"🔍 Starting API fuzzing: {url}")
        result = execute_command(command)
        logger.info(f"📊 API fuzzing completed for {url}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"💥 Error in api_fuzzer endpoint: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500

@tools_api_bp.route("/graphql-scanner", methods=["POST"])
def graphql_scanner():
    """Execute GraphQL vulnerability scanner with enhanced logging"""
    try:
        params = request.json
        url = params.get("url", "")
        additional_args = params.get("additional_args", "")

        if not url:
            logger.warning("🎯 GraphQL Scanner called without URL parameter")
            return jsonify({
                "error": "URL parameter is required"
            }), 400

        command = f"graphql-cop -t {url}"

        if additional_args:
            command += f" {additional_args}"

        logger.info(f"🔬 Starting GraphQL scan: {url}")
        result = execute_command(command)
        logger.info(f"📊 GraphQL scan completed for {url}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"💥 Error in graphql_scanner endpoint: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500

@tools_api_bp.route("/jwt-analyzer", methods=["POST"])
def jwt_analyzer():
    """Execute JWT token analyzer with enhanced logging"""
    try:
        params = request.json
        token = params.get("token", "")
        wordlist = params.get("wordlist", "")
        additional_args = params.get("additional_args", "")

        if not token:
            logger.warning("🎯 JWT Analyzer called without token parameter")
            return jsonify({
                "error": "Token parameter is required"
            }), 400

        command = f"jwt_tool {token}"

        if wordlist:
            command += f" -C -d {wordlist}"

        if additional_args:
            command += f" {additional_args}"

        logger.info(f"🔐 Starting JWT analysis")
        result = execute_command(command)
        logger.info(f"📊 JWT analysis completed")
        return jsonify(result)
    except Exception as e:
        logger.error(f"💥 Error in jwt_analyzer endpoint: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500

@tools_api_bp.route("/api-schema-analyzer", methods=["POST"])
def api_schema_analyzer():
    """Execute API schema security analyzer with enhanced logging"""
    try:
        params = request.json
        url = params.get("url", "")
        schema_type = params.get("schema_type", "openapi")
        additional_args = params.get("additional_args", "")

        if not url:
            logger.warning("🌐 API Schema Analyzer called without URL parameter")
            return jsonify({
                "error": "URL parameter is required"
            }), 400

        if schema_type == "openapi":
            command = f"openapi-scanner -u {url}"
        elif schema_type == "swagger":
            command = f"swagger-hack -u {url}"
        else:
            command = f"api-schema-check -u {url}"

        if additional_args:
            command += f" {additional_args}"

        logger.info(f"🔍 Starting API schema analysis: {url}")
        result = execute_command(command)
        logger.info(f"📊 API schema analysis completed for {url}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"💥 Error in api_schema_analyzer endpoint: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500
