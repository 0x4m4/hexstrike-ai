"""
Binary Analysis and Forensics Tool API Routes
Handles memory forensics, binary analysis, reverse engineering, and firmware analysis tools
"""

import logging
import os
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

# Create blueprint
tools_binary_bp = Blueprint('tools_binary', __name__, url_prefix='/api/tools')

# Dependencies will be injected via init_app
execute_command = None

def init_app(exec_command):
    """Initialize blueprint with dependencies"""
    global execute_command
    execute_command = exec_command


@tools_binary_bp.route("/volatility", methods=["POST"])
def volatility():
    """Execute Volatility for memory forensics with enhanced logging"""
    try:
        params = request.json
        memory_file = params.get("memory_file", "")
        plugin = params.get("plugin", "")
        profile = params.get("profile", "")
        additional_args = params.get("additional_args", "")

        if not memory_file:
            logger.warning("🧠 Volatility called without memory_file parameter")
            return jsonify({
                "error": "Memory file parameter is required"
            }), 400

        if not plugin:
            logger.warning("🧠 Volatility called without plugin parameter")
            return jsonify({
                "error": "Plugin parameter is required"
            }), 400

        command = f"volatility -f {memory_file}"

        if profile:
            command += f" --profile={profile}"

        command += f" {plugin}"

        if additional_args:
            command += f" {additional_args}"

        logger.info(f"🧠 Starting Volatility analysis: {plugin}")
        result = execute_command(command)
        logger.info(f"📊 Volatility analysis completed")
        return jsonify(result)
    except Exception as e:
        logger.error(f"💥 Error in volatility endpoint: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500

@tools_binary_bp.route("/gdb", methods=["POST"])
def gdb():
    """Execute GDB for binary analysis and debugging with enhanced logging"""
    try:
        params = request.json
        binary = params.get("binary", "")
        commands = params.get("commands", "")
        script_file = params.get("script_file", "")
        additional_args = params.get("additional_args", "")

        if not binary:
            logger.warning("🔧 GDB called without binary parameter")
            return jsonify({
                "error": "Binary parameter is required"
            }), 400

        command = f"gdb {binary}"

        if script_file:
            command += f" -x {script_file}"

        if commands:
            temp_script = "/tmp/gdb_commands.txt"
            with open(temp_script, "w") as f:
                f.write(commands)
            command += f" -x {temp_script}"

        if additional_args:
            command += f" {additional_args}"

        command += " -batch"

        logger.info(f"🔧 Starting GDB analysis: {binary}")
        result = execute_command(command)

        if commands and os.path.exists("/tmp/gdb_commands.txt"):
            try:
                os.remove("/tmp/gdb_commands.txt")
            except:
                pass

        logger.info(f"📊 GDB analysis completed for {binary}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"💥 Error in gdb endpoint: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500

@tools_binary_bp.route("/radare2", methods=["POST"])
def radare2():
    """Execute Radare2 for binary analysis and reverse engineering with enhanced logging"""
    try:
        params = request.json
        binary = params.get("binary", "")
        commands = params.get("commands", "")
        additional_args = params.get("additional_args", "")

        if not binary:
            logger.warning("🔧 Radare2 called without binary parameter")
            return jsonify({
                "error": "Binary parameter is required"
            }), 400

        if commands:
            temp_script = "/tmp/r2_commands.txt"
            with open(temp_script, "w") as f:
                f.write(commands)
            command = f"r2 -i {temp_script} -q {binary}"
        else:
            command = f"r2 -q {binary}"

        if additional_args:
            command += f" {additional_args}"

        logger.info(f"🔧 Starting Radare2 analysis: {binary}")
        result = execute_command(command)

        if commands and os.path.exists("/tmp/r2_commands.txt"):
            try:
                os.remove("/tmp/r2_commands.txt")
            except:
                pass

        logger.info(f"📊 Radare2 analysis completed for {binary}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"💥 Error in radare2 endpoint: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500

@tools_binary_bp.route("/binwalk", methods=["POST"])
def binwalk():
    """Execute Binwalk for firmware and file analysis with enhanced logging"""
    try:
        params = request.json
        file_path = params.get("file_path", "")
        extract = params.get("extract", False)
        additional_args = params.get("additional_args", "")

        if not file_path:
            logger.warning("🔧 Binwalk called without file_path parameter")
            return jsonify({
                "error": "File path parameter is required"
            }), 400

        command = f"binwalk"

        if extract:
            command += " -e"

        if additional_args:
            command += f" {additional_args}"

        command += f" {file_path}"

        logger.info(f"🔧 Starting Binwalk analysis: {file_path}")
        result = execute_command(command)
        logger.info(f"📊 Binwalk analysis completed for {file_path}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"💥 Error in binwalk endpoint: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500

@tools_binary_bp.route("/ropgadget", methods=["POST"])
def ropgadget():
    """Search for ROP gadgets in a binary using ROPgadget with enhanced logging"""
    try:
        params = request.json
        binary = params.get("binary", "")
        gadget_type = params.get("gadget_type", "")
        additional_args = params.get("additional_args", "")

        if not binary:
            logger.warning("🔧 ROPgadget called without binary parameter")
            return jsonify({
                "error": "Binary parameter is required"
            }), 400

        command = f"ROPgadget --binary {binary}"

        if gadget_type:
            command += f" --only '{gadget_type}'"

        if additional_args:
            command += f" {additional_args}"

        logger.info(f"🔧 Starting ROPgadget search: {binary}")
        result = execute_command(command)
        logger.info(f"📊 ROPgadget search completed for {binary}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"💥 Error in ropgadget endpoint: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500

@tools_binary_bp.route("/checksec", methods=["POST"])
def checksec():
    """Execute checksec for binary security checking with enhanced logging"""
    try:
        params = request.json
        binary = params.get("binary", "")
        additional_args = params.get("additional_args", "")

        if not binary:
            logger.warning("🔧 Checksec called without binary parameter")
            return jsonify({
                "error": "Binary parameter is required"
            }), 400

        command = f"checksec --file={binary}"

        if additional_args:
            command += f" {additional_args}"

        logger.info(f"🔧 Starting checksec analysis: {binary}")
        result = execute_command(command)
        logger.info(f"📊 Checksec analysis completed for {binary}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"💥 Error in checksec endpoint: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500

@tools_binary_bp.route("/xxd", methods=["POST"])
def xxd():
    """Execute xxd for hex dump with enhanced logging"""
    try:
        params = request.json
        file_path = params.get("file_path", "")
        length = params.get("length", "")
        seek = params.get("seek", "")
        additional_args = params.get("additional_args", "")

        if not file_path:
            logger.warning("🔧 xxd called without file_path parameter")
            return jsonify({
                "error": "File path parameter is required"
            }), 400

        command = f"xxd"

        if length:
            command += f" -l {length}"

        if seek:
            command += f" -s {seek}"

        if additional_args:
            command += f" {additional_args}"

        command += f" {file_path}"

        logger.info(f"🔧 Starting xxd hex dump: {file_path}")
        result = execute_command(command)
        logger.info(f"📊 xxd hex dump completed for {file_path}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"💥 Error in xxd endpoint: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500

@tools_binary_bp.route("/strings", methods=["POST"])
def strings():
    """Extract strings from binaries with enhanced logging"""
    try:
        params = request.json
        file_path = params.get("file_path", "")
        min_length = params.get("min_length", "")
        additional_args = params.get("additional_args", "")

        if not file_path:
            logger.warning("🔧 Strings called without file_path parameter")
            return jsonify({
                "error": "File path parameter is required"
            }), 400

        command = f"strings"

        if min_length:
            command += f" -n {min_length}"

        if additional_args:
            command += f" {additional_args}"

        command += f" {file_path}"

        logger.info(f"🔧 Starting strings extraction: {file_path}")
        result = execute_command(command)
        logger.info(f"📊 Strings extraction completed for {file_path}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"💥 Error in strings endpoint: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500

@tools_binary_bp.route("/objdump", methods=["POST"])
def objdump():
    """Execute objdump to display object file information with enhanced logging"""
    try:
        params = request.json
        file_path = params.get("file_path", "")
        disassemble = params.get("disassemble", False)
        headers = params.get("headers", False)
        additional_args = params.get("additional_args", "")

        if not file_path:
            logger.warning("🔧 Objdump called without file_path parameter")
            return jsonify({
                "error": "File path parameter is required"
            }), 400

        command = f"objdump"

        if disassemble:
            command += " -d"

        if headers:
            command += " -h"

        if additional_args:
            command += f" {additional_args}"

        command += f" {file_path}"

        logger.info(f"🔧 Starting objdump analysis: {file_path}")
        result = execute_command(command)
        logger.info(f"📊 Objdump analysis completed for {file_path}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"💥 Error in objdump endpoint: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500

@tools_binary_bp.route("/ghidra", methods=["POST"])
def ghidra():
    """Execute Ghidra for reverse engineering with enhanced logging"""
    try:
        params = request.json
        binary = params.get("binary", "")
        project_path = params.get("project_path", "")
        script = params.get("script", "")
        additional_args = params.get("additional_args", "")

        if not binary:
            logger.warning("🔧 Ghidra called without binary parameter")
            return jsonify({
                "error": "Binary parameter is required"
            }), 400

        command = f"analyzeHeadless"

        if project_path:
            command += f" {project_path} ghidra_project"
        else:
            command += " /tmp ghidra_project"

        command += f" -import {binary}"

        if script:
            command += f" -postScript {script}"

        if additional_args:
            command += f" {additional_args}"

        logger.info(f"🔧 Starting Ghidra analysis: {binary}")
        result = execute_command(command)
        logger.info(f"📊 Ghidra analysis completed for {binary}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"💥 Error in ghidra endpoint: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500

@tools_binary_bp.route("/pwntools", methods=["POST"])
def pwntools():
    """Execute pwntools for CTF framework and exploit development with enhanced logging"""
    try:
        params = request.json
        script = params.get("script", "")
        target = params.get("target", "")
        port = params.get("port", "")
        additional_args = params.get("additional_args", "")

        if not script:
            logger.warning("🔧 Pwntools called without script parameter")
            return jsonify({
                "error": "Script parameter is required"
            }), 400

        command = f"python3 {script}"

        if target:
            command += f" {target}"

        if port:
            command += f" {port}"

        if additional_args:
            command += f" {additional_args}"

        logger.info(f"🔧 Starting pwntools script: {script}")
        result = execute_command(command)
        logger.info(f"📊 Pwntools script completed")
        return jsonify(result)
    except Exception as e:
        logger.error(f"💥 Error in pwntools endpoint: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500

@tools_binary_bp.route("/one-gadget", methods=["POST"])
def one_gadget():
    """Execute one-gadget to find one gadget RCE with enhanced logging"""
    try:
        params = request.json
        libc_path = params.get("libc_path", "")
        additional_args = params.get("additional_args", "")

        if not libc_path:
            logger.warning("🔧 One-gadget called without libc_path parameter")
            return jsonify({
                "error": "Libc path parameter is required"
            }), 400

        command = f"one_gadget {libc_path}"

        if additional_args:
            command += f" {additional_args}"

        logger.info(f"🔧 Starting one-gadget search: {libc_path}")
        result = execute_command(command)
        logger.info(f"📊 One-gadget search completed for {libc_path}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"💥 Error in one-gadget endpoint: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500

@tools_binary_bp.route("/libc-database", methods=["POST"])
def libc_database():
    """Execute libc-database for libc version identification with enhanced logging"""
    try:
        params = request.json
        action = params.get("action", "")
        symbols = params.get("symbols", "")
        additional_args = params.get("additional_args", "")

        if not action:
            logger.warning("🔧 Libc-database called without action parameter")
            return jsonify({
                "error": "Action parameter is required"
            }), 400

        command = f"./libc-database/find {action}"

        if symbols:
            command += f" {symbols}"

        if additional_args:
            command += f" {additional_args}"

        logger.info(f"🔧 Starting libc-database search: {action}")
        result = execute_command(command)
        logger.info(f"📊 Libc-database search completed")
        return jsonify(result)
    except Exception as e:
        logger.error(f"💥 Error in libc-database endpoint: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500

@tools_binary_bp.route("/gdb-peda", methods=["POST"])
def gdb_peda():
    """Execute GDB with PEDA for Python Exploit Development Assistance with enhanced logging"""
    try:
        params = request.json
        binary = params.get("binary", "")
        commands = params.get("commands", "")
        additional_args = params.get("additional_args", "")

        if not binary:
            logger.warning("🔧 GDB-PEDA called without binary parameter")
            return jsonify({
                "error": "Binary parameter is required"
            }), 400

        command = f"gdb {binary}"

        if commands:
            temp_script = "/tmp/gdb_peda_commands.txt"
            with open(temp_script, "w") as f:
                f.write(commands)
            command += f" -x {temp_script}"

        if additional_args:
            command += f" {additional_args}"

        command += " -batch"

        logger.info(f"🔧 Starting GDB-PEDA analysis: {binary}")
        result = execute_command(command)

        if commands and os.path.exists("/tmp/gdb_peda_commands.txt"):
            try:
                os.remove("/tmp/gdb_peda_commands.txt")
            except:
                pass

        logger.info(f"📊 GDB-PEDA analysis completed for {binary}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"💥 Error in gdb-peda endpoint: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500

@tools_binary_bp.route("/angr", methods=["POST"])
def angr():
    """Execute angr for binary analysis framework with enhanced logging"""
    try:
        params = request.json
        script = params.get("script", "")
        binary = params.get("binary", "")
        additional_args = params.get("additional_args", "")

        if not script:
            logger.warning("🔧 Angr called without script parameter")
            return jsonify({
                "error": "Script parameter is required"
            }), 400

        command = f"python3 {script}"

        if binary:
            command += f" {binary}"

        if additional_args:
            command += f" {additional_args}"

        logger.info(f"🔧 Starting angr analysis: {script}")
        result = execute_command(command)
        logger.info(f"📊 Angr analysis completed")
        return jsonify(result)
    except Exception as e:
        logger.error(f"💥 Error in angr endpoint: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500

@tools_binary_bp.route("/ropper", methods=["POST"])
def ropper():
    """Execute ropper for ROP gadget finding with enhanced logging"""
    try:
        params = request.json
        binary = params.get("binary", "")
        search = params.get("search", "")
        additional_args = params.get("additional_args", "")

        if not binary:
            logger.warning("🔧 Ropper called without binary parameter")
            return jsonify({
                "error": "Binary parameter is required"
            }), 400

        command = f"ropper --file {binary}"

        if search:
            command += f" --search '{search}'"

        if additional_args:
            command += f" {additional_args}"

        logger.info(f"🔧 Starting ropper gadget search: {binary}")
        result = execute_command(command)
        logger.info(f"📊 Ropper gadget search completed for {binary}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"💥 Error in ropper endpoint: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500

@tools_binary_bp.route("/pwninit", methods=["POST"])
def pwninit():
    """Execute pwninit for CTF pwn challenge setup with enhanced logging"""
    try:
        params = request.json
        binary = params.get("binary", "")
        libc = params.get("libc", "")
        ld = params.get("ld", "")
        additional_args = params.get("additional_args", "")

        command = f"pwninit"

        if binary:
            command += f" --bin {binary}"

        if libc:
            command += f" --libc {libc}"

        if ld:
            command += f" --ld {ld}"

        if additional_args:
            command += f" {additional_args}"

        logger.info(f"🔧 Starting pwninit setup")
        result = execute_command(command)
        logger.info(f"📊 Pwninit setup completed")
        return jsonify(result)
    except Exception as e:
        logger.error(f"💥 Error in pwninit endpoint: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500
