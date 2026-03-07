"""
Forensics and Data Extraction Tool API Routes
Handles memory forensics, file carving, steganography, and metadata analysis tools
"""

import logging
import os
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

# Create blueprint
tools_forensics_bp = Blueprint('tools_forensics', __name__, url_prefix='/api/tools')

# Dependencies will be injected via init_app
execute_command = None

def init_app(exec_command):
    """Initialize blueprint with dependencies"""
    global execute_command
    execute_command = exec_command


@tools_forensics_bp.route("/volatility3", methods=["POST"])
def volatility3():
    """Execute Volatility3 for memory forensics analysis with enhanced logging"""
    try:
        params = request.json
        memory_file = params.get("memory_file", "")
        plugin = params.get("plugin", "")
        additional_args = params.get("additional_args", "")

        if not memory_file:
            logger.warning("🧠 Volatility3 called without memory_file parameter")
            return jsonify({
                "error": "Memory file parameter is required"
            }), 400

        if not plugin:
            logger.warning("🧠 Volatility3 called without plugin parameter")
            return jsonify({
                "error": "Plugin parameter is required"
            }), 400

        command = f"vol3 -f {memory_file} {plugin}"

        if additional_args:
            command += f" {additional_args}"

        logger.info(f"🧠 Starting Volatility3 analysis: {plugin}")
        result = execute_command(command)
        logger.info(f"📊 Volatility3 analysis completed")
        return jsonify(result)
    except Exception as e:
        logger.error(f"💥 Error in volatility3 endpoint: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500

@tools_forensics_bp.route("/foremost", methods=["POST"])
def foremost():
    """Execute Foremost for file carving with enhanced logging"""
    try:
        params = request.json
        input_file = params.get("input_file", "")
        output_dir = params.get("output_dir", "/tmp/foremost_output")
        file_types = params.get("file_types", "")
        additional_args = params.get("additional_args", "")

        if not input_file:
            logger.warning("🔍 Foremost called without input_file parameter")
            return jsonify({
                "error": "Input file parameter is required"
            }), 400

        command = f"foremost -o {output_dir}"

        if file_types:
            command += f" -t {file_types}"

        if additional_args:
            command += f" {additional_args}"

        command += f" -i {input_file}"

        logger.info(f"🔍 Starting Foremost file carving: {input_file}")
        result = execute_command(command)
        logger.info(f"📊 Foremost file carving completed")
        return jsonify(result)
    except Exception as e:
        logger.error(f"💥 Error in foremost endpoint: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500

@tools_forensics_bp.route("/steghide", methods=["POST"])
def steghide():
    """Execute Steghide for steganography analysis with enhanced logging"""
    try:
        params = request.json
        operation = params.get("operation", "extract")
        file_path = params.get("file_path", "")
        passphrase = params.get("passphrase", "")
        output_file = params.get("output_file", "")
        additional_args = params.get("additional_args", "")

        if not file_path:
            logger.warning("🔒 Steghide called without file_path parameter")
            return jsonify({
                "error": "File path parameter is required"
            }), 400

        if operation == "extract":
            command = f"steghide extract -sf {file_path}"
            if output_file:
                command += f" -xf {output_file}"
        elif operation == "info":
            command = f"steghide info {file_path}"
        else:
            logger.warning(f"🔒 Steghide called with invalid operation: {operation}")
            return jsonify({
                "error": "Operation must be 'extract' or 'info'"
            }), 400

        if passphrase:
            command += f" -p {passphrase}"
        else:
            command += " -p ''"

        if additional_args:
            command += f" {additional_args}"

        logger.info(f"🔒 Starting Steghide {operation}: {file_path}")
        result = execute_command(command)
        logger.info(f"📊 Steghide {operation} completed")
        return jsonify(result)
    except Exception as e:
        logger.error(f"💥 Error in steghide endpoint: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500

@tools_forensics_bp.route("/exiftool", methods=["POST"])
def exiftool():
    """Execute ExifTool for metadata analysis with enhanced logging"""
    try:
        params = request.json
        file_path = params.get("file_path", "")
        operation = params.get("operation", "read")
        metadata = params.get("metadata", {})
        additional_args = params.get("additional_args", "")

        if not file_path:
            logger.warning("📸 ExifTool called without file_path parameter")
            return jsonify({
                "error": "File path parameter is required"
            }), 400

        if operation == "read":
            command = f"exiftool {file_path}"
        elif operation == "write":
            if not metadata:
                logger.warning("📸 ExifTool write operation called without metadata")
                return jsonify({
                    "error": "Metadata parameter is required for write operation"
                }), 400
            command = f"exiftool"
            for key, value in metadata.items():
                command += f" -{key}='{value}'"
            command += f" {file_path}"
        else:
            logger.warning(f"📸 ExifTool called with invalid operation: {operation}")
            return jsonify({
                "error": "Operation must be 'read' or 'write'"
            }), 400

        if additional_args:
            command += f" {additional_args}"

        logger.info(f"📸 Starting ExifTool {operation}: {file_path}")
        result = execute_command(command)
        logger.info(f"📊 ExifTool {operation} completed")
        return jsonify(result)
    except Exception as e:
        logger.error(f"💥 Error in exiftool endpoint: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500

@tools_forensics_bp.route("/hashpump", methods=["POST"])
def hashpump():
    """Execute HashPump for hash length extension attacks with enhanced logging"""
    try:
        params = request.json
        signature = params.get("signature", "")
        data = params.get("data", "")
        append = params.get("append", "")
        key_length = params.get("key_length", "")
        algorithm = params.get("algorithm", "sha1")
        additional_args = params.get("additional_args", "")

        if not signature:
            logger.warning("🔐 HashPump called without signature parameter")
            return jsonify({
                "error": "Signature parameter is required"
            }), 400

        if not data:
            logger.warning("🔐 HashPump called without data parameter")
            return jsonify({
                "error": "Data parameter is required"
            }), 400

        if not append:
            logger.warning("🔐 HashPump called without append parameter")
            return jsonify({
                "error": "Append parameter is required"
            }), 400

        if not key_length:
            logger.warning("🔐 HashPump called without key_length parameter")
            return jsonify({
                "error": "Key length parameter is required"
            }), 400

        command = f"hashpump -s '{signature}' -d '{data}' -a '{append}' -k {key_length}"

        if algorithm != "sha1":
            command += f" --algorithm {algorithm}"

        if additional_args:
            command += f" {additional_args}"

        logger.info(f"🔐 Starting HashPump attack with {algorithm}")
        result = execute_command(command)
        logger.info(f"📊 HashPump attack completed")
        return jsonify(result)
    except Exception as e:
        logger.error(f"💥 Error in hashpump endpoint: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500
