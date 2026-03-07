"""
Advanced Web Reconnaissance Tools API Routes
Handles gobuster, nuclei, feroxbuster, dirsearch, httpx, katana, gau, waybackurls, hakrawler, dnsenum, fierce, and wafw00f tools
"""

import logging
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

# Create blueprint
tools_web_advanced_bp = Blueprint('tools_web_advanced', __name__, url_prefix='/api/tools')

# Dependencies will be injected via init_app
execute_command = None

def init_app(exec_command):
    """Initialize blueprint with dependencies"""
    global execute_command
    execute_command = exec_command


@tools_web_advanced_bp.route("/gobuster", methods=["POST"])
def gobuster():
    """Execute gobuster for directory/DNS/vhost brute forcing with enhanced logging"""
    try:
        params = request.json
        target = params.get("target", "")
        mode = params.get("mode", "dir")
        wordlist = params.get("wordlist", "/usr/share/wordlists/dirb/common.txt")
        extensions = params.get("extensions", "")
        additional_args = params.get("additional_args", "")

        if not target:
            logger.warning("🎯 Gobuster called without target parameter")
            return jsonify({
                "error": "Target parameter is required"
            }), 400

        command = f"gobuster {mode} -u {target} -w {wordlist}"

        if extensions:
            command += f" -x {extensions}"

        if additional_args:
            command += f" {additional_args}"

        logger.info(f"🔍 Starting Gobuster {mode} scan: {target}")
        result = execute_command(command)
        logger.info(f"📊 Gobuster scan completed for {target}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"💥 Error in gobuster endpoint: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500

@tools_web_advanced_bp.route("/nuclei", methods=["POST"])
def nuclei():
    """Execute nuclei template-based vulnerability scanner with enhanced logging"""
    try:
        params = request.json
        target = params.get("target", "")
        templates = params.get("templates", "")
        severity = params.get("severity", "")
        tags = params.get("tags", "")
        additional_args = params.get("additional_args", "")

        if not target:
            logger.warning("🎯 Nuclei called without target parameter")
            return jsonify({
                "error": "Target parameter is required"
            }), 400

        command = f"nuclei -u {target}"

        if templates:
            command += f" -t {templates}"

        if severity:
            command += f" -s {severity}"

        if tags:
            command += f" -tags {tags}"

        if additional_args:
            command += f" {additional_args}"

        logger.info(f"🔬 Starting Nuclei scan: {target}")
        result = execute_command(command)
        logger.info(f"📊 Nuclei scan completed for {target}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"💥 Error in nuclei endpoint: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500

@tools_web_advanced_bp.route("/feroxbuster", methods=["POST"])
def feroxbuster():
    """Execute feroxbuster for fast content discovery with enhanced logging"""
    try:
        params = request.json
        target = params.get("target", "")
        wordlist = params.get("wordlist", "/usr/share/wordlists/dirb/common.txt")
        extensions = params.get("extensions", "")
        threads = params.get("threads", 50)
        depth = params.get("depth", 4)
        additional_args = params.get("additional_args", "")

        if not target:
            logger.warning("🎯 Feroxbuster called without target parameter")
            return jsonify({
                "error": "Target parameter is required"
            }), 400

        command = f"feroxbuster -u {target} -w {wordlist} -t {threads} -d {depth}"

        if extensions:
            command += f" -x {extensions}"

        if additional_args:
            command += f" {additional_args}"

        logger.info(f"⚡ Starting Feroxbuster scan: {target}")
        result = execute_command(command)
        logger.info(f"📊 Feroxbuster scan completed for {target}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"💥 Error in feroxbuster endpoint: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500

@tools_web_advanced_bp.route("/dirsearch", methods=["POST"])
def dirsearch():
    """Execute dirsearch for web path scanning with enhanced logging"""
    try:
        params = request.json
        target = params.get("target", "")
        wordlist = params.get("wordlist", "/usr/share/wordlists/dirb/common.txt")
        extensions = params.get("extensions", "php,html,js")
        threads = params.get("threads", 30)
        additional_args = params.get("additional_args", "")

        if not target:
            logger.warning("🎯 Dirsearch called without target parameter")
            return jsonify({
                "error": "Target parameter is required"
            }), 400

        command = f"dirsearch -u {target} -w {wordlist} -e {extensions} -t {threads}"

        if additional_args:
            command += f" {additional_args}"

        logger.info(f"🔍 Starting Dirsearch scan: {target}")
        result = execute_command(command)
        logger.info(f"📊 Dirsearch scan completed for {target}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"💥 Error in dirsearch endpoint: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500

@tools_web_advanced_bp.route("/httpx", methods=["POST"])
def httpx():
    """Execute httpx fast HTTP toolkit with enhanced logging"""
    try:
        params = request.json
        target = params.get("target", "")
        threads = params.get("threads", 50)
        status_code = params.get("status_code", False)
        tech_detect = params.get("tech_detect", False)
        follow_redirects = params.get("follow_redirects", False)
        additional_args = params.get("additional_args", "")

        if not target:
            logger.warning("🎯 Httpx called without target parameter")
            return jsonify({
                "error": "Target parameter is required"
            }), 400

        command = f"httpx -u {target} -threads {threads}"

        if status_code:
            command += " -sc"

        if tech_detect:
            command += " -td"

        if follow_redirects:
            command += " -fr"

        if additional_args:
            command += f" {additional_args}"

        logger.info(f"🌐 Starting Httpx scan: {target}")
        result = execute_command(command)
        logger.info(f"📊 Httpx scan completed for {target}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"💥 Error in httpx endpoint: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500

@tools_web_advanced_bp.route("/katana", methods=["POST"])
def katana():
    """Execute katana for crawling and spidering with enhanced logging"""
    try:
        params = request.json
        target = params.get("target", "")
        depth = params.get("depth", 3)
        js_crawl = params.get("js_crawl", False)
        headless = params.get("headless", False)
        additional_args = params.get("additional_args", "")

        if not target:
            logger.warning("🎯 Katana called without target parameter")
            return jsonify({
                "error": "Target parameter is required"
            }), 400

        command = f"katana -u {target} -d {depth}"

        if js_crawl:
            command += " -jc"

        if headless:
            command += " -hl"

        if additional_args:
            command += f" {additional_args}"

        logger.info(f"🕷️ Starting Katana crawl: {target}")
        result = execute_command(command)
        logger.info(f"📊 Katana crawl completed for {target}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"💥 Error in katana endpoint: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500

@tools_web_advanced_bp.route("/gau", methods=["POST"])
def gau():
    """Execute gau (Get All URLs) for wayback URLs with enhanced logging"""
    try:
        params = request.json
        target = params.get("target", "")
        threads = params.get("threads", 10)
        subs = params.get("subs", False)
        blacklist = params.get("blacklist", "")
        additional_args = params.get("additional_args", "")

        if not target:
            logger.warning("🎯 GAU called without target parameter")
            return jsonify({
                "error": "Target parameter is required"
            }), 400

        command = f"gau {target} --threads {threads}"

        if subs:
            command += " --subs"

        if blacklist:
            command += f" --blacklist {blacklist}"

        if additional_args:
            command += f" {additional_args}"

        logger.info(f"🔄 Starting GAU scan: {target}")
        result = execute_command(command)
        logger.info(f"📊 GAU scan completed for {target}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"💥 Error in gau endpoint: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500

@tools_web_advanced_bp.route("/waybackurls", methods=["POST"])
def waybackurls():
    """Execute waybackurls for Wayback Machine URLs with enhanced logging"""
    try:
        params = request.json
        target = params.get("target", "")
        dates = params.get("dates", False)
        additional_args = params.get("additional_args", "")

        if not target:
            logger.warning("🎯 Waybackurls called without target parameter")
            return jsonify({
                "error": "Target parameter is required"
            }), 400

        command = f"echo {target} | waybackurls"

        if dates:
            command += " -dates"

        if additional_args:
            command += f" {additional_args}"

        logger.info(f"🕰️ Starting Waybackurls scan: {target}")
        result = execute_command(command)
        logger.info(f"📊 Waybackurls scan completed for {target}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"💥 Error in waybackurls endpoint: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500

@tools_web_advanced_bp.route("/hakrawler", methods=["POST"])
def hakrawler():
    """Execute hakrawler web crawler with enhanced logging"""
    try:
        params = request.json
        target = params.get("target", "")
        depth = params.get("depth", 2)
        subs = params.get("subs", False)
        urls = params.get("urls", False)
        additional_args = params.get("additional_args", "")

        if not target:
            logger.warning("🎯 Hakrawler called without target parameter")
            return jsonify({
                "error": "Target parameter is required"
            }), 400

        command = f"echo {target} | hakrawler -d {depth}"

        if subs:
            command += " -s"

        if urls:
            command += " -u"

        if additional_args:
            command += f" {additional_args}"

        logger.info(f"🕸️ Starting Hakrawler scan: {target}")
        result = execute_command(command)
        logger.info(f"📊 Hakrawler scan completed for {target}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"💥 Error in hakrawler endpoint: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500

@tools_web_advanced_bp.route("/dnsenum", methods=["POST"])
def dnsenum():
    """Execute dnsenum for DNS enumeration with enhanced logging"""
    try:
        params = request.json
        target = params.get("target", "")
        threads = params.get("threads", 10)
        subfile = params.get("subfile", "")
        enum = params.get("enum", True)
        additional_args = params.get("additional_args", "")

        if not target:
            logger.warning("🎯 Dnsenum called without target parameter")
            return jsonify({
                "error": "Target parameter is required"
            }), 400

        command = f"dnsenum --threads {threads}"

        if subfile:
            command += f" -f {subfile}"

        if not enum:
            command += " --noreverse"

        command += f" {target}"

        if additional_args:
            command += f" {additional_args}"

        logger.info(f"🔍 Starting Dnsenum scan: {target}")
        result = execute_command(command)
        logger.info(f"📊 Dnsenum scan completed for {target}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"💥 Error in dnsenum endpoint: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500

@tools_web_advanced_bp.route("/fierce", methods=["POST"])
def fierce():
    """Execute fierce for DNS reconnaissance with enhanced logging"""
    try:
        params = request.json
        target = params.get("target", "")
        wide = params.get("wide", False)
        threads = params.get("threads", 10)
        additional_args = params.get("additional_args", "")

        if not target:
            logger.warning("🎯 Fierce called without target parameter")
            return jsonify({
                "error": "Target parameter is required"
            }), 400

        command = f"fierce --domain {target} --threads {threads}"

        if wide:
            command += " --wide"

        if additional_args:
            command += f" {additional_args}"

        logger.info(f"⚔️ Starting Fierce scan: {target}")
        result = execute_command(command)
        logger.info(f"📊 Fierce scan completed for {target}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"💥 Error in fierce endpoint: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500

@tools_web_advanced_bp.route("/wafw00f", methods=["POST"])
def wafw00f():
    """Execute wafw00f for WAF detection with enhanced logging"""
    try:
        params = request.json
        target = params.get("target", "")
        findall = params.get("findall", False)
        additional_args = params.get("additional_args", "")

        if not target:
            logger.warning("🎯 Wafw00f called without target parameter")
            return jsonify({
                "error": "Target parameter is required"
            }), 400

        command = f"wafw00f {target}"

        if findall:
            command += " -a"

        if additional_args:
            command += f" {additional_args}"

        logger.info(f"🛡️ Starting Wafw00f scan: {target}")
        result = execute_command(command)
        logger.info(f"📊 Wafw00f scan completed for {target}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"💥 Error in wafw00f endpoint: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500
