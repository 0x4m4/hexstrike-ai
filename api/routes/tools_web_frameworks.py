"""
Web Testing Frameworks API Routes
Handles http-framework, browser-agent, and burpsuite-alternative tools
"""

import logging
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

# Create blueprint
tools_web_frameworks_bp = Blueprint('tools_web_frameworks', __name__, url_prefix='/api/tools')

# Dependencies will be injected via init_app
http_framework = None
browser_agent = None

def init_app(http_testing_framework, browser_agent_instance):
    """Initialize blueprint with dependencies"""
    global http_framework, browser_agent
    http_framework = http_testing_framework
    browser_agent = browser_agent_instance


@tools_web_frameworks_bp.route("/http-framework", methods=["POST"])
def http_framework_route():
    """Advanced HTTP testing framework endpoint"""
    try:
        params = request.json
        action = params.get("action", "")

        if not action:
            logger.warning("HTTP Framework called without action parameter")
            return jsonify({
                "error": "Action parameter is required (intercept/spider/intruder/repeater/scope/rules)"
            }), 400

        # Intercept request
        if action == "intercept":
            url = params.get("url", "")
            method = params.get("method", "GET")
            data = params.get("data")
            headers = params.get("headers")
            cookies = params.get("cookies")

            if not url:
                return jsonify({"error": "URL is required for intercept action"}), 400

            logger.info(f"HTTP Framework: Intercepting {method} request to {url}")
            result = http_framework.intercept_request(url, method, data, headers, cookies)
            logger.info(f"HTTP Framework: Intercept completed for {url}")
            return jsonify(result)

        # Spider website
        elif action == "spider":
            base_url = params.get("base_url", "")
            max_depth = params.get("max_depth", 3)
            max_pages = params.get("max_pages", 100)

            if not base_url:
                return jsonify({"error": "base_url is required for spider action"}), 400

            logger.info(f"HTTP Framework: Spidering {base_url}")
            result = http_framework.spider_website(base_url, max_depth, max_pages)
            logger.info(f"HTTP Framework: Spider completed for {base_url}")
            return jsonify(result)

        # Intruder (fuzzing)
        elif action == "intruder":
            url = params.get("url", "")
            method = params.get("method", "GET")
            location = params.get("location", "query")
            params_list = params.get("params", [])
            payloads = params.get("payloads")
            base_data = params.get("base_data")
            max_requests = params.get("max_requests", 100)

            if not url:
                return jsonify({"error": "URL is required for intruder action"}), 400

            logger.info(f"HTTP Framework: Running Intruder on {url}")
            result = http_framework.intruder_sniper(url, method, location, params_list, payloads, base_data, max_requests)
            logger.info(f"HTTP Framework: Intruder completed for {url}")
            return jsonify(result)

        # Repeater (custom request)
        elif action == "repeater":
            request_spec = params.get("request_spec", {})

            if not request_spec:
                return jsonify({"error": "request_spec is required for repeater action"}), 400

            logger.info(f"HTTP Framework: Sending custom request")
            result = http_framework.send_custom_request(request_spec)
            logger.info(f"HTTP Framework: Custom request completed")
            return jsonify(result)

        # Set scope
        elif action == "scope":
            host = params.get("host", "")
            include_subdomains = params.get("include_subdomains", True)

            if not host:
                return jsonify({"error": "host is required for scope action"}), 400

            http_framework.set_scope(host, include_subdomains)
            logger.info(f"HTTP Framework: Scope set to {host}")
            return jsonify({"success": True, "message": f"Scope set to {host}"})

        # Set match/replace rules
        elif action == "rules":
            rules = params.get("rules", [])
            http_framework.set_match_replace_rules(rules)
            logger.info(f"HTTP Framework: Match/replace rules updated ({len(rules)} rules)")
            return jsonify({"success": True, "message": f"Set {len(rules)} match/replace rules"})

        else:
            return jsonify({
                "error": f"Unknown action: {action}. Valid actions: intercept, spider, intruder, repeater, scope, rules"
            }), 400

    except Exception as e:
        logger.error(f"Error in http-framework endpoint: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500


@tools_web_frameworks_bp.route("/browser-agent", methods=["POST"])
def browser_agent_route():
    """Browser automation agent endpoint"""
    try:
        params = request.json
        action = params.get("action", "")

        if not action:
            logger.warning("Browser Agent called without action parameter")
            return jsonify({
                "error": "Action parameter is required (navigate/setup/close/active-test)"
            }), 400

        # Setup browser
        if action == "setup":
            headless = params.get("headless", True)
            proxy_port = params.get("proxy_port")

            logger.info(f"Browser Agent: Setting up browser (headless={headless})")
            success = browser_agent.setup_browser(headless, proxy_port)

            if success:
                return jsonify({"success": True, "message": "Browser setup completed"})
            else:
                return jsonify({"success": False, "error": "Failed to setup browser"}), 500

        # Navigate and inspect
        elif action == "navigate":
            url = params.get("url", "")
            wait_time = params.get("wait_time", 5)

            if not url:
                return jsonify({"error": "URL is required for navigate action"}), 400

            logger.info(f"Browser Agent: Navigating to {url}")
            result = browser_agent.navigate_and_inspect(url, wait_time)
            logger.info(f"Browser Agent: Navigation completed for {url}")
            return jsonify(result)

        # Run active tests
        elif action == "active-test":
            page_info = params.get("page_info", {})
            payload = params.get("payload", "<hexstrikeXSSTest123>")

            if not page_info:
                return jsonify({"error": "page_info is required for active-test action"}), 400

            logger.info(f"Browser Agent: Running active tests")
            result = browser_agent.run_active_tests(page_info, payload)
            logger.info(f"Browser Agent: Active tests completed")
            return jsonify(result)

        # Close browser
        elif action == "close":
            browser_agent.close_browser()
            logger.info(f"Browser Agent: Browser closed")
            return jsonify({"success": True, "message": "Browser closed"})

        else:
            return jsonify({
                "error": f"Unknown action: {action}. Valid actions: setup, navigate, active-test, close"
            }), 400

    except Exception as e:
        logger.error(f"Error in browser-agent endpoint: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500


@tools_web_frameworks_bp.route("/burpsuite-alternative", methods=["POST"])
def burpsuite_alternative():
    """Burp Suite alternative interface combining HTTP framework and browser agent"""
    try:
        params = request.json
        mode = params.get("mode", "")
        url = params.get("url", "")

        if not mode:
            logger.warning("Burpsuite Alternative called without mode parameter")
            return jsonify({
                "error": "Mode parameter is required (proxy/spider/intruder/repeater/scanner)"
            }), 400

        if not url and mode != "proxy":
            return jsonify({"error": "URL parameter is required"}), 400

        # Proxy mode - intercept and analyze
        if mode == "proxy":
            method = params.get("method", "GET")
            data = params.get("data")
            headers = params.get("headers")

            logger.info(f"Burpsuite Alternative: Proxy mode for {url}")
            result = http_framework.intercept_request(url, method, data, headers)
            logger.info(f"Burpsuite Alternative: Proxy completed for {url}")
            return jsonify(result)

        # Spider mode - crawl website
        elif mode == "spider":
            max_depth = params.get("max_depth", 3)
            max_pages = params.get("max_pages", 100)

            logger.info(f"Burpsuite Alternative: Spider mode for {url}")
            result = http_framework.spider_website(url, max_depth, max_pages)
            logger.info(f"Burpsuite Alternative: Spider completed for {url}")
            return jsonify(result)

        # Intruder mode - fuzzing
        elif mode == "intruder":
            method = params.get("method", "GET")
            location = params.get("location", "query")
            params_list = params.get("params", [])
            payloads = params.get("payloads")
            base_data = params.get("base_data")
            max_requests = params.get("max_requests", 100)

            logger.info(f"Burpsuite Alternative: Intruder mode for {url}")
            result = http_framework.intruder_sniper(url, method, location, params_list, payloads, base_data, max_requests)
            logger.info(f"Burpsuite Alternative: Intruder completed for {url}")
            return jsonify(result)

        # Repeater mode - custom requests
        elif mode == "repeater":
            request_spec = params.get("request_spec", {})
            if not request_spec:
                request_spec = {"url": url, "method": params.get("method", "GET")}

            logger.info(f"Burpsuite Alternative: Repeater mode")
            result = http_framework.send_custom_request(request_spec)
            logger.info(f"Burpsuite Alternative: Repeater completed")
            return jsonify(result)

        # Scanner mode - automated vulnerability scanning
        elif mode == "scanner":
            wait_time = params.get("wait_time", 5)

            logger.info(f"Burpsuite Alternative: Scanner mode for {url}")

            # First, use browser agent to navigate and inspect
            browser_result = browser_agent.navigate_and_inspect(url, wait_time)

            if not browser_result.get("success"):
                return jsonify(browser_result), 500

            # Then, spider the website using HTTP framework
            spider_result = http_framework.spider_website(url, 2, 50)

            # Combine results
            combined_result = {
                "success": True,
                "browser_analysis": browser_result.get("security_analysis", {}),
                "spider_results": {
                    "discovered_urls": spider_result.get("discovered_urls", []),
                    "forms": spider_result.get("forms", []),
                    "total_pages": spider_result.get("total_pages", 0)
                },
                "vulnerabilities": browser_result.get("security_analysis", {}).get("issues", []) +
                                 spider_result.get("vulnerabilities", []),
                "screenshot": browser_result.get("screenshot", "")
            }

            logger.info(f"Burpsuite Alternative: Scanner completed for {url}")
            return jsonify(combined_result)

        else:
            return jsonify({
                "error": f"Unknown mode: {mode}. Valid modes: proxy, spider, intruder, repeater, scanner"
            }), 400

    except Exception as e:
        logger.error(f"Error in burpsuite-alternative endpoint: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}"
        }), 500
