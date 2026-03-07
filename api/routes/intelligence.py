"""
Intelligence Engine API Routes
Handles target analysis, tool selection, parameter optimization, and attack chains
"""

import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from flask import Blueprint, request, jsonify
from agents.decision_engine import TechnologyStack

logger = logging.getLogger(__name__)

# Create blueprint
intelligence_bp = Blueprint('intelligence', __name__, url_prefix='/api/intelligence')

# Dependencies will be injected via init_app
decision_engine = None
tool_executors = None  # Dictionary of tool execution functions

def init_app(dec_engine, executors):
    """Initialize blueprint with dependencies"""
    global decision_engine, tool_executors
    decision_engine = dec_engine
    tool_executors = executors


@intelligence_bp.route("/analyze-target", methods=["POST"])
def analyze_target():
    """Analyze target and create comprehensive profile using Intelligent Decision Engine"""
    try:
        data = request.get_json()
        if not data or 'target' not in data:
            return jsonify({"error": "Target is required"}), 400

        target = data['target']
        logger.info(f"🧠 Analyzing target: {target}")

        # Use the decision engine to analyze the target
        profile = decision_engine.analyze_target(target)

        logger.info(f"✅ Target analysis completed for {target}")
        logger.info(f"📊 Target type: {profile.target_type.value}, Risk level: {profile.risk_level}")

        return jsonify({
            "success": True,
            "target_profile": profile.to_dict(),
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"💥 Error analyzing target: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@intelligence_bp.route("/select-tools", methods=["POST"])
def select_optimal_tools():
    """Select optimal tools based on target profile and objective"""
    try:
        data = request.get_json()
        if not data or 'target' not in data:
            return jsonify({"error": "Target is required"}), 400

        target = data['target']
        objective = data.get('objective', 'comprehensive')  # comprehensive, quick, stealth

        logger.info(f"🎯 Selecting optimal tools for {target} with objective: {objective}")

        # Analyze target first
        profile = decision_engine.analyze_target(target)

        # Select optimal tools
        selected_tools = decision_engine.select_optimal_tools(profile, objective)

        logger.info(f"✅ Selected {len(selected_tools)} tools for {target}")

        return jsonify({
            "success": True,
            "target": target,
            "objective": objective,
            "target_profile": profile.to_dict(),
            "selected_tools": selected_tools,
            "tool_count": len(selected_tools),
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"💥 Error selecting tools: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@intelligence_bp.route("/optimize-parameters", methods=["POST"])
def optimize_tool_parameters():
    """Optimize tool parameters based on target profile and context"""
    try:
        data = request.get_json()
        if not data or 'target' not in data or 'tool' not in data:
            return jsonify({"error": "Target and tool are required"}), 400

        target = data['target']
        tool = data['tool']
        context = data.get('context', {})

        logger.info(f"⚙️  Optimizing parameters for {tool} against {target}")

        # Analyze target first
        profile = decision_engine.analyze_target(target)

        # Optimize parameters
        optimized_params = decision_engine.optimize_parameters(tool, profile, context)

        logger.info(f"✅ Parameters optimized for {tool}")

        return jsonify({
            "success": True,
            "target": target,
            "tool": tool,
            "context": context,
            "target_profile": profile.to_dict(),
            "optimized_parameters": optimized_params,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"💥 Error optimizing parameters: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@intelligence_bp.route("/create-attack-chain", methods=["POST"])
def create_attack_chain():
    """Create an intelligent attack chain based on target profile"""
    try:
        data = request.get_json()
        if not data or 'target' not in data:
            return jsonify({"error": "Target is required"}), 400

        target = data['target']
        objective = data.get('objective', 'comprehensive')

        logger.info(f"⚔️  Creating attack chain for {target} with objective: {objective}")

        # Analyze target first
        profile = decision_engine.analyze_target(target)

        # Create attack chain
        attack_chain = decision_engine.create_attack_chain(profile, objective)

        logger.info(f"✅ Attack chain created with {len(attack_chain.steps)} steps")
        logger.info(f"📊 Success probability: {attack_chain.success_probability:.2f}, Estimated time: {attack_chain.estimated_time}s")

        return jsonify({
            "success": True,
            "target": target,
            "objective": objective,
            "target_profile": profile.to_dict(),
            "attack_chain": attack_chain.to_dict(),
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"💥 Error creating attack chain: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@intelligence_bp.route("/smart-scan", methods=["POST"])
def intelligent_smart_scan():
    """Execute an intelligent scan using AI-driven tool selection and parameter optimization with parallel execution"""
    try:
        data = request.get_json()
        if not data or 'target' not in data:
            return jsonify({"error": "Target is required"}), 400

        target = data['target']
        objective = data.get('objective', 'comprehensive')
        max_tools = data.get('max_tools', 5)

        logger.info(f"🚀 Starting intelligent smart scan for {target}")

        # Analyze target
        profile = decision_engine.analyze_target(target)

        # Select optimal tools
        selected_tools = decision_engine.select_optimal_tools(profile, objective)[:max_tools]

        # Execute tools in parallel with real tool execution
        scan_results = {
            "target": target,
            "target_profile": profile.to_dict(),
            "tools_executed": [],
            "total_vulnerabilities": 0,
            "execution_summary": {},
            "combined_output": ""
        }

        def execute_single_tool(tool_name, target, profile):
            """Execute a single tool and return results"""
            try:
                logger.info(f"🔧 Executing {tool_name} with optimized parameters")

                # Get optimized parameters for this tool
                optimized_params = decision_engine.optimize_parameters(tool_name, profile)

                # Execute the tool if we have an executor for it
                if tool_name in tool_executors:
                    result = tool_executors[tool_name](target, optimized_params)

                    # Extract vulnerability count from result
                    vuln_count = 0
                    if result.get('success') and result.get('stdout'):
                        # Simple vulnerability detection based on common patterns
                        output = result.get('stdout', '')
                        vuln_indicators = ['CRITICAL', 'HIGH', 'MEDIUM', 'VULNERABILITY', 'EXPLOIT', 'SQL injection', 'XSS', 'CSRF']
                        vuln_count = sum(1 for indicator in vuln_indicators if indicator.lower() in output.lower())

                    return {
                        "tool": tool_name,
                        "parameters": optimized_params,
                        "status": "success" if result.get('success') else "failed",
                        "timestamp": datetime.now().isoformat(),
                        "execution_time": result.get('execution_time', 0),
                        "stdout": result.get('stdout', ''),
                        "stderr": result.get('stderr', ''),
                        "vulnerabilities_found": vuln_count,
                        "command": result.get('command', ''),
                        "success": result.get('success', False)
                    }
                else:
                    logger.warning(f"⚠️ No execution mapping found for tool: {tool_name}")
                    return {
                        "tool": tool_name,
                        "parameters": optimized_params,
                        "status": "skipped",
                        "timestamp": datetime.now().isoformat(),
                        "error": f"Tool {tool_name} not implemented in execution map",
                        "success": False
                    }

            except Exception as e:
                logger.error(f"❌ Error executing {tool_name}: {str(e)}")
                return {
                    "tool": tool_name,
                    "status": "failed",
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e),
                    "success": False
                }

        # Execute tools in parallel using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=min(len(selected_tools), 5)) as executor:
            # Submit all tool executions
            future_to_tool = {
                executor.submit(execute_single_tool, tool, target, profile): tool
                for tool in selected_tools
            }

            # Collect results as they complete
            for future in future_to_tool:
                tool_result = future.result()
                scan_results["tools_executed"].append(tool_result)

                # Accumulate vulnerability count
                if tool_result.get("vulnerabilities_found"):
                    scan_results["total_vulnerabilities"] += tool_result["vulnerabilities_found"]

                # Combine outputs
                if tool_result.get("stdout"):
                    scan_results["combined_output"] += f"\n=== {tool_result['tool'].upper()} OUTPUT ===\n"
                    scan_results["combined_output"] += tool_result["stdout"]
                    scan_results["combined_output"] += "\n" + "="*50 + "\n"

        # Create execution summary
        successful_tools = [t for t in scan_results["tools_executed"] if t.get("success")]
        failed_tools = [t for t in scan_results["tools_executed"] if not t.get("success")]

        scan_results["execution_summary"] = {
            "total_tools": len(selected_tools),
            "successful_tools": len(successful_tools),
            "failed_tools": len(failed_tools),
            "success_rate": len(successful_tools) / len(selected_tools) * 100 if selected_tools else 0,
            "total_execution_time": sum(t.get("execution_time", 0) for t in scan_results["tools_executed"]),
            "tools_used": [t["tool"] for t in successful_tools]
        }

        logger.info(f"✅ Intelligent smart scan completed for {target}")
        logger.info(f"📊 Results: {len(successful_tools)}/{len(selected_tools)} tools successful, {scan_results['total_vulnerabilities']} vulnerabilities found")

        return jsonify({
            "success": True,
            "scan_results": scan_results,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"💥 Error in intelligent smart scan: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@intelligence_bp.route("/technology-detection", methods=["POST"])
def detect_technologies():
    """Detect technologies and create technology-specific testing recommendations"""
    try:
        data = request.get_json()
        if not data or 'target' not in data:
            return jsonify({"error": "Target is required"}), 400

        target = data['target']

        logger.info(f"🔍 Detecting technologies for {target}")

        # Analyze target
        profile = decision_engine.analyze_target(target)

        # Get technology-specific recommendations
        tech_recommendations = {}
        for tech in profile.technologies:
            if tech == TechnologyStack.WORDPRESS:
                tech_recommendations["WordPress"] = {
                    "tools": ["wpscan", "nuclei"],
                    "focus_areas": ["plugin vulnerabilities", "theme issues", "user enumeration"],
                    "priority": "high"
                }
            elif tech == TechnologyStack.PHP:
                tech_recommendations["PHP"] = {
                    "tools": ["nikto", "sqlmap", "ffuf"],
                    "focus_areas": ["code injection", "file inclusion", "SQL injection"],
                    "priority": "high"
                }
            elif tech == TechnologyStack.NODEJS:
                tech_recommendations["Node.js"] = {
                    "tools": ["nuclei", "ffuf"],
                    "focus_areas": ["prototype pollution", "dependency vulnerabilities"],
                    "priority": "medium"
                }

        logger.info(f"✅ Technology detection completed for {target}")

        return jsonify({
            "success": True,
            "target": target,
            "detected_technologies": [tech.value for tech in profile.technologies],
            "cms_type": profile.cms_type,
            "technology_recommendations": tech_recommendations,
            "target_profile": profile.to_dict(),
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"💥 Error detecting technologies: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500
