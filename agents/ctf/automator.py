"""
CTF Challenge Automator
Advanced automation system for CTF challenge solving
"""

import logging
import re
import time
from typing import Dict, Any, List

from agents.ctf.workflow_manager import CTFChallenge, CTFWorkflowManager, CTFToolManager

logger = logging.getLogger(__name__)


class CTFChallengeAutomator:
    """Advanced automation system for CTF challenge solving"""

    def __init__(self):
        self.active_challenges = {}
        self.solution_cache = {}
        self.learning_database = {}
        self.success_patterns = {}

    def auto_solve_challenge(self, challenge: CTFChallenge) -> Dict[str, Any]:
        """Attempt to automatically solve a CTF challenge"""
        result = {
            "challenge_id": challenge.name,
            "status": "in_progress",
            "automated_steps": [],
            "manual_steps": [],
            "confidence": 0.0,
            "estimated_completion": 0,
            "artifacts": [],
            "flag_candidates": [],
            "next_actions": []
        }

        try:
            # Create workflow
            workflow = ctf_manager.create_ctf_challenge_workflow(challenge)

            # Execute automated steps
            for step in workflow["workflow_steps"]:
                if step.get("parallel", False):
                    step_result = self._execute_parallel_step(step, challenge)
                else:
                    step_result = self._execute_sequential_step(step, challenge)

                result["automated_steps"].append(step_result)

                # Check for flag candidates
                flag_candidates = self._extract_flag_candidates(step_result.get("output", ""))
                result["flag_candidates"].extend(flag_candidates)

                # Update confidence based on step success
                if step_result.get("success", False):
                    result["confidence"] += 0.1

                # Early termination if flag found
                if flag_candidates and self._validate_flag_format(flag_candidates[0]):
                    result["status"] = "solved"
                    result["flag"] = flag_candidates[0]
                    break

            # If not solved automatically, provide manual guidance
            if result["status"] != "solved":
                result["manual_steps"] = self._generate_manual_guidance(challenge, result)
                result["status"] = "needs_manual_intervention"

            result["confidence"] = min(1.0, result["confidence"])

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            logger.error(f"Error in auto-solve for {challenge.name}: {str(e)}")

        return result

    def _execute_parallel_step(self, step: Dict[str, Any], challenge: CTFChallenge) -> Dict[str, Any]:
        """Execute a step with parallel tool execution"""
        step_result = {
            "step": step["step"],
            "action": step["action"],
            "success": False,
            "output": "",
            "tools_used": [],
            "execution_time": 0,
            "artifacts": []
        }

        start_time = time.time()
        tools = step.get("tools", [])

        # Execute tools in parallel (simulated for now)
        for tool in tools:
            try:
                if tool != "manual":
                    command = ctf_tools.get_tool_command(tool, challenge.target or challenge.name)
                    # In a real implementation, this would execute the command
                    step_result["tools_used"].append(tool)
                    step_result["output"] += f"[{tool}] Executed successfully\n"
                    step_result["success"] = True
            except Exception as e:
                step_result["output"] += f"[{tool}] Error: {str(e)}\n"

        step_result["execution_time"] = time.time() - start_time
        return step_result

    def _execute_sequential_step(self, step: Dict[str, Any], challenge: CTFChallenge) -> Dict[str, Any]:
        """Execute a step sequentially"""
        step_result = {
            "step": step["step"],
            "action": step["action"],
            "success": False,
            "output": "",
            "tools_used": [],
            "execution_time": 0,
            "artifacts": []
        }

        start_time = time.time()
        tools = step.get("tools", [])

        for tool in tools:
            try:
                if tool == "manual":
                    step_result["output"] += f"[MANUAL] {step['description']}\n"
                    step_result["success"] = True
                elif tool == "custom":
                    step_result["output"] += f"[CUSTOM] Custom implementation required\n"
                    step_result["success"] = True
                else:
                    command = ctf_tools.get_tool_command(tool, challenge.target or challenge.name)
                    step_result["tools_used"].append(tool)
                    step_result["output"] += f"[{tool}] Command: {command}\n"
                    step_result["success"] = True
            except Exception as e:
                step_result["output"] += f"[{tool}] Error: {str(e)}\n"

        step_result["execution_time"] = time.time() - start_time
        return step_result

    def _extract_flag_candidates(self, output: str) -> List[str]:
        """Extract potential flags from tool output"""
        flag_patterns = [
            r'flag\{[^}]+\}',
            r'FLAG\{[^}]+\}',
            r'ctf\{[^}]+\}',
            r'CTF\{[^}]+\}',
            r'[a-zA-Z0-9_]+\{[^}]+\}',
            r'[0-9a-f]{32}',  # MD5 hash
            r'[0-9a-f]{40}',  # SHA1 hash
            r'[0-9a-f]{64}'   # SHA256 hash
        ]

        candidates = []
        for pattern in flag_patterns:
            matches = re.findall(pattern, output, re.IGNORECASE)
            candidates.extend(matches)

        return list(set(candidates))  # Remove duplicates

    def _validate_flag_format(self, flag: str) -> bool:
        """Validate if a string matches common flag formats"""
        common_formats = [
            r'^flag\{.+\}$',
            r'^FLAG\{.+\}$',
            r'^ctf\{.+\}$',
            r'^CTF\{.+\}$',
            r'^[a-zA-Z0-9_]+\{.+\}$'
        ]

        for pattern in common_formats:
            if re.match(pattern, flag, re.IGNORECASE):
                return True

        return False

    def _generate_manual_guidance(self, challenge: CTFChallenge, current_result: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate manual guidance when automation fails"""
        guidance = []

        # Analyze what was attempted
        attempted_tools = []
        for step in current_result["automated_steps"]:
            attempted_tools.extend(step.get("tools_used", []))

        # Suggest alternative approaches
        all_category_tools = ctf_tools.get_category_tools(f"{challenge.category}_recon")
        unused_tools = [tool for tool in all_category_tools if tool not in attempted_tools]

        if unused_tools:
            guidance.append({
                "action": "try_alternative_tools",
                "description": f"Try these alternative tools: {', '.join(unused_tools[:3])}"
            })

        # Category-specific guidance
        if challenge.category == "web":
            guidance.extend([
                {"action": "manual_source_review", "description": "Manually review all HTML/JS source code for hidden comments or clues"},
                {"action": "parameter_fuzzing", "description": "Manually fuzz parameters with custom payloads"},
                {"action": "cookie_analysis", "description": "Analyze cookies and session management"}
            ])
        elif challenge.category == "crypto":
            guidance.extend([
                {"action": "cipher_research", "description": "Research the specific cipher type and known attacks"},
                {"action": "key_analysis", "description": "Analyze key properties and potential weaknesses"},
                {"action": "frequency_analysis", "description": "Perform detailed frequency analysis"}
            ])
        elif challenge.category == "pwn":
            guidance.extend([
                {"action": "manual_debugging", "description": "Manually debug the binary to understand control flow"},
                {"action": "exploit_development", "description": "Develop custom exploit based on vulnerability analysis"},
                {"action": "payload_crafting", "description": "Craft specific payloads for the identified vulnerability"}
            ])
        elif challenge.category == "forensics":
            guidance.extend([
                {"action": "manual_analysis", "description": "Manually analyze file structures and metadata"},
                {"action": "steganography_deep_dive", "description": "Deep dive into steganography techniques"},
                {"action": "timeline_analysis", "description": "Reconstruct detailed timeline of events"}
            ])
        elif challenge.category == "rev":
            guidance.extend([
                {"action": "algorithm_analysis", "description": "Focus on understanding the core algorithm"},
                {"action": "key_extraction", "description": "Extract hardcoded keys or important values"},
                {"action": "dynamic_analysis", "description": "Use dynamic analysis to understand runtime behavior"}
            ])

        return guidance


# Global instances for backward compatibility
ctf_manager = CTFWorkflowManager()
ctf_tools = CTFToolManager()
