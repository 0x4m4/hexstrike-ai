"""
Parameter Discovery and Fuzzing Tools API Routes
Handles arjun, paramspider, x8, wfuzz, dotdotpwn, anew, qsreplace, and uro tools
"""

import logging
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

# Create blueprint
tools_parameters_bp = Blueprint('tools_parameters', __name__, url_prefix='/api/tools')

# Dependencies will be injected via init_app
execute_command = None

def init_app(exec_command):
    """Initialize blueprint with dependencies"""
    global execute_command
    execute_command = exec_command


@tools_parameters_bp.route("/arjun", methods=["POST"])
def arjun():
    """Execute Arjun HTTP parameter discovery tool with enhanced logging"""
    try:
        params = request.json
        url = params.get("url", "")
        methods = params.get("methods", "GET,POST")
        wordlist = params.get("wordlist", "")
        additional_args = params.get("additional_args", "")

        if not url:
            logger.warning("Arjun called without URL parameter")
            return jsonify({
                "error": "URL parameter is required"
            }), 400

        command = f"arjun -u {url}"

        if methods:
            command += f" -m {methods}"

        if wordlist:
            command += f" -w {wordlist}"

        if additional_args:
            command += f" {additional_args}"

        logger.info(f"Starting Arjun parameter discovery: {url}")
        result = execute_command(command)
        logger.info(f"Arjun parameter discovery completed for {url}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in arjun endpoint: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500

@tools_parameters_bp.route("/paramspider", methods=["POST"])
def paramspider():
    """Execute ParamSpider parameter miner with enhanced logging"""
    try:
        params = request.json
        domain = params.get("domain", "")
        output = params.get("output", "")
        additional_args = params.get("additional_args", "")

        if not domain:
            logger.warning("ParamSpider called without domain parameter")
            return jsonify({
                "error": "Domain parameter is required"
            }), 400

        command = f"paramspider -d {domain}"

        if output:
            command += f" -o {output}"

        if additional_args:
            command += f" {additional_args}"

        logger.info(f"Starting ParamSpider mining: {domain}")
        result = execute_command(command)
        logger.info(f"ParamSpider mining completed for {domain}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in paramspider endpoint: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500

@tools_parameters_bp.route("/x8", methods=["POST"])
def x8():
    """Execute x8 hidden parameter discovery tool with enhanced logging"""
    try:
        params = request.json
        url = params.get("url", "")
        wordlist = params.get("wordlist", "")
        method = params.get("method", "GET")
        additional_args = params.get("additional_args", "")

        if not url:
            logger.warning("x8 called without URL parameter")
            return jsonify({
                "error": "URL parameter is required"
            }), 400

        command = f"x8 -u {url}"

        if wordlist:
            command += f" -w {wordlist}"

        if method:
            command += f" -X {method}"

        if additional_args:
            command += f" {additional_args}"

        logger.info(f"Starting x8 hidden parameter discovery: {url}")
        result = execute_command(command)
        logger.info(f"x8 hidden parameter discovery completed for {url}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in x8 endpoint: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500

@tools_parameters_bp.route("/wfuzz", methods=["POST"])
def wfuzz():
    """Execute Wfuzz web application fuzzer with enhanced logging"""
    try:
        params = request.json
        url = params.get("url", "")
        wordlist = params.get("wordlist", "/usr/share/wordlists/wfuzz/general/common.txt")
        hide_codes = params.get("hide_codes", "")
        show_codes = params.get("show_codes", "")
        additional_args = params.get("additional_args", "")

        if not url:
            logger.warning("Wfuzz called without URL parameter")
            return jsonify({
                "error": "URL parameter is required"
            }), 400

        command = f"wfuzz -w {wordlist}"

        if hide_codes:
            command += f" --hc {hide_codes}"

        if show_codes:
            command += f" --sc {show_codes}"

        if additional_args:
            command += f" {additional_args}"

        command += f" {url}"

        logger.info(f"Starting Wfuzz fuzzing: {url}")
        result = execute_command(command)
        logger.info(f"Wfuzz fuzzing completed for {url}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in wfuzz endpoint: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500

@tools_parameters_bp.route("/dotdotpwn", methods=["POST"])
def dotdotpwn():
    """Execute DotDotPwn directory traversal fuzzer with enhanced logging"""
    try:
        params = request.json
        host = params.get("host", "")
        module = params.get("module", "http")
        depth = params.get("depth", "6")
        additional_args = params.get("additional_args", "")

        if not host:
            logger.warning("DotDotPwn called without host parameter")
            return jsonify({
                "error": "Host parameter is required"
            }), 400

        command = f"dotdotpwn.pl -m {module} -h {host} -d {depth}"

        if additional_args:
            command += f" {additional_args}"

        logger.info(f"Starting DotDotPwn directory traversal fuzzing: {host}")
        result = execute_command(command)
        logger.info(f"DotDotPwn fuzzing completed for {host}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in dotdotpwn endpoint: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500

@tools_parameters_bp.route("/anew", methods=["POST"])
def anew():
    """Execute anew tool to add new lines to files with enhanced logging"""
    try:
        params = request.json
        input_file = params.get("input_file", "")
        output_file = params.get("output_file", "")
        additional_args = params.get("additional_args", "")

        if not input_file or not output_file:
            logger.warning("Anew called without required file parameters")
            return jsonify({
                "error": "Both input_file and output_file parameters are required"
            }), 400

        command = f"cat {input_file} | anew {output_file}"

        if additional_args:
            command += f" {additional_args}"

        logger.info(f"Starting anew processing: {input_file} -> {output_file}")
        result = execute_command(command)
        logger.info(f"Anew processing completed for {output_file}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in anew endpoint: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500

@tools_parameters_bp.route("/qsreplace", methods=["POST"])
def qsreplace():
    """Execute qsreplace query string replacer with enhanced logging"""
    try:
        params = request.json
        input_file = params.get("input_file", "")
        replace_value = params.get("replace_value", "")
        additional_args = params.get("additional_args", "")

        if not input_file or not replace_value:
            logger.warning("Qsreplace called without required parameters")
            return jsonify({
                "error": "Both input_file and replace_value parameters are required"
            }), 400

        command = f"cat {input_file} | qsreplace {replace_value}"

        if additional_args:
            command += f" {additional_args}"

        logger.info(f"Starting qsreplace processing: {input_file}")
        result = execute_command(command)
        logger.info(f"Qsreplace processing completed for {input_file}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in qsreplace endpoint: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500

@tools_parameters_bp.route("/uro", methods=["POST"])
def uro():
    """Execute uro URL deduplication tool with enhanced logging"""
    try:
        params = request.json
        input_file = params.get("input_file", "")
        output_file = params.get("output_file", "")
        additional_args = params.get("additional_args", "")

        if not input_file:
            logger.warning("Uro called without input_file parameter")
            return jsonify({
                "error": "input_file parameter is required"
            }), 400

        command = f"cat {input_file} | uro"

        if output_file:
            command += f" > {output_file}"

        if additional_args:
            command += f" {additional_args}"

        logger.info(f"Starting uro URL deduplication: {input_file}")
        result = execute_command(command)
        logger.info(f"Uro URL deduplication completed for {input_file}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in uro endpoint: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500
