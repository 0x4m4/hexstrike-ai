"""
CTF Workflow Manager
Specialized workflow manager for CTF competitions and challenge solving
"""

from typing import Dict, Any, List
from dataclasses import dataclass, field

@dataclass
class CTFChallenge:
    """CTF challenge information"""
    name: str
    category: str  # web, crypto, pwn, forensics, rev, misc, osint
    description: str
    points: int = 0
    difficulty: str = "unknown"  # easy, medium, hard, insane
    files: List[str] = field(default_factory=list)
    url: str = ""
    hints: List[str] = field(default_factory=list)

class CTFWorkflowManager:
    """Specialized workflow manager for CTF competitions"""

    def __init__(self):
        self.category_tools = {
            "web": {
                "reconnaissance": ["httpx", "katana", "gau", "waybackurls"],
                "vulnerability_scanning": ["nuclei", "dalfox", "sqlmap", "nikto"],
                "content_discovery": ["gobuster", "dirsearch", "feroxbuster"],
                "parameter_testing": ["arjun", "paramspider", "x8"],
                "specialized": ["wpscan", "joomscan", "droopescan"]
            },
            "crypto": {
                "hash_analysis": ["hashcat", "john", "hash-identifier"],
                "cipher_analysis": ["cipher-identifier", "cryptool", "cyberchef"],
                "rsa_attacks": ["rsatool", "factordb", "yafu"],
                "frequency_analysis": ["frequency-analysis", "substitution-solver"],
                "modern_crypto": ["sage", "pycrypto", "cryptography"]
            },
            "pwn": {
                "binary_analysis": ["checksec", "ghidra", "radare2", "gdb-peda"],
                "exploit_development": ["pwntools", "ropper", "one-gadget"],
                "heap_exploitation": ["glibc-heap-analysis", "heap-viewer"],
                "format_string": ["format-string-exploiter"],
                "rop_chains": ["ropgadget", "ropper", "angr"]
            },
            "forensics": {
                "file_analysis": ["file", "binwalk", "foremost", "photorec"],
                "image_forensics": ["exiftool", "steghide", "stegsolve", "zsteg"],
                "memory_forensics": ["volatility", "rekall"],
                "network_forensics": ["wireshark", "tcpdump", "networkminer"],
                "disk_forensics": ["autopsy", "sleuthkit", "testdisk"]
            },
            "rev": {
                "disassemblers": ["ghidra", "ida", "radare2", "binary-ninja"],
                "debuggers": ["gdb", "x64dbg", "ollydbg"],
                "decompilers": ["ghidra", "hex-rays", "retdec"],
                "packers": ["upx", "peid", "detect-it-easy"],
                "analysis": ["strings", "ltrace", "strace", "objdump"]
            },
            "misc": {
                "encoding": ["base64", "hex", "url-decode", "rot13"],
                "compression": ["zip", "tar", "gzip", "7zip"],
                "qr_codes": ["qr-decoder", "zbar"],
                "audio_analysis": ["audacity", "sonic-visualizer"],
                "esoteric": ["brainfuck", "whitespace", "piet"]
            },
            "osint": {
                "search_engines": ["google-dorking", "shodan", "censys"],
                "social_media": ["sherlock", "social-analyzer"],
                "image_analysis": ["reverse-image-search", "exif-analysis"],
                "domain_analysis": ["whois", "dns-analysis", "certificate-transparency"],
                "geolocation": ["geoint", "osm-analysis", "satellite-imagery"]
            }
        }

        self.solving_strategies = {
            "web": [
                {"strategy": "source_code_analysis", "description": "Analyze HTML/JS source for hidden information"},
                {"strategy": "directory_traversal", "description": "Test for path traversal vulnerabilities"},
                {"strategy": "sql_injection", "description": "Test for SQL injection in all parameters"},
                {"strategy": "xss_exploitation", "description": "Test for XSS and exploit for admin access"},
                {"strategy": "authentication_bypass", "description": "Test for auth bypass techniques"},
                {"strategy": "session_manipulation", "description": "Analyze and manipulate session tokens"},
                {"strategy": "file_upload_bypass", "description": "Test file upload restrictions and bypasses"}
            ],
            "crypto": [
                {"strategy": "frequency_analysis", "description": "Perform frequency analysis for substitution ciphers"},
                {"strategy": "known_plaintext", "description": "Use known plaintext attacks"},
                {"strategy": "weak_keys", "description": "Test for weak cryptographic keys"},
                {"strategy": "implementation_flaws", "description": "Look for implementation vulnerabilities"},
                {"strategy": "side_channel", "description": "Exploit timing or other side channels"},
                {"strategy": "mathematical_attacks", "description": "Use mathematical properties to break crypto"}
            ],
            "pwn": [
                {"strategy": "buffer_overflow", "description": "Exploit buffer overflow vulnerabilities"},
                {"strategy": "format_string", "description": "Exploit format string vulnerabilities"},
                {"strategy": "rop_chains", "description": "Build ROP chains for exploitation"},
                {"strategy": "heap_exploitation", "description": "Exploit heap-based vulnerabilities"},
                {"strategy": "race_conditions", "description": "Exploit race condition vulnerabilities"},
                {"strategy": "integer_overflow", "description": "Exploit integer overflow conditions"}
            ],
            "forensics": [
                {"strategy": "file_carving", "description": "Recover deleted or hidden files"},
                {"strategy": "metadata_analysis", "description": "Analyze file metadata for hidden information"},
                {"strategy": "steganography", "description": "Extract hidden data from images/audio"},
                {"strategy": "memory_analysis", "description": "Analyze memory dumps for artifacts"},
                {"strategy": "network_analysis", "description": "Analyze network traffic for suspicious activity"},
                {"strategy": "timeline_analysis", "description": "Reconstruct timeline of events"}
            ],
            "rev": [
                {"strategy": "static_analysis", "description": "Analyze binary without execution"},
                {"strategy": "dynamic_analysis", "description": "Analyze binary during execution"},
                {"strategy": "anti_debugging", "description": "Bypass anti-debugging techniques"},
                {"strategy": "unpacking", "description": "Unpack packed/obfuscated binaries"},
                {"strategy": "algorithm_recovery", "description": "Reverse engineer algorithms"},
                {"strategy": "key_recovery", "description": "Extract encryption keys from binaries"}
            ]
        }

    def create_ctf_challenge_workflow(self, challenge: CTFChallenge) -> Dict[str, Any]:
        """Create advanced specialized workflow for CTF challenge with AI-powered optimization"""
        workflow = {
            "challenge": challenge.name,
            "category": challenge.category,
            "difficulty": challenge.difficulty,
            "points": challenge.points,
            "tools": [],
            "strategies": [],
            "estimated_time": 0,
            "success_probability": 0.0,
            "automation_level": "high",
            "parallel_tasks": [],
            "dependencies": [],
            "fallback_strategies": [],
            "resource_requirements": {},
            "expected_artifacts": [],
            "validation_steps": []
        }

        # Enhanced tool selection using CTFToolManager
        ctf_tool_manager = CTFToolManager()
        workflow["tools"] = ctf_tool_manager.suggest_tools_for_challenge(challenge.description, challenge.category)

        # Get category-specific strategies with enhanced intelligence
        if challenge.category in self.solving_strategies:
            workflow["strategies"] = self.solving_strategies[challenge.category]
            # Add fallback strategies for robustness
            workflow["fallback_strategies"] = self._generate_fallback_strategies(challenge.category)

        # Advanced time estimation with machine learning-like scoring
        base_times = {
            "easy": {"min": 15, "avg": 30, "max": 60},
            "medium": {"min": 30, "avg": 60, "max": 120},
            "hard": {"min": 60, "avg": 120, "max": 240},
            "insane": {"min": 120, "avg": 240, "max": 480},
            "unknown": {"min": 45, "avg": 90, "max": 180}
        }

        # Factor in category complexity
        category_multipliers = {
            "web": 1.0,
            "crypto": 1.3,
            "pwn": 1.5,
            "forensics": 1.2,
            "rev": 1.4,
            "misc": 0.8,
            "osint": 0.9
        }

        base_time = base_times[challenge.difficulty]["avg"]
        category_mult = category_multipliers.get(challenge.category, 1.0)

        # Adjust based on description complexity
        description_complexity = self._analyze_description_complexity(challenge.description)
        complexity_mult = 1.0 + (description_complexity * 0.3)

        workflow["estimated_time"] = int(base_time * category_mult * complexity_mult * 60)  # Convert to seconds

        # Enhanced success probability calculation
        base_success = {
            "easy": 0.85,
            "medium": 0.65,
            "hard": 0.45,
            "insane": 0.25,
            "unknown": 0.55
        }[challenge.difficulty]

        # Adjust based on tool availability and category expertise
        tool_availability_bonus = min(0.15, len(workflow["tools"]) * 0.02)
        workflow["success_probability"] = min(0.95, base_success + tool_availability_bonus)

        # Add advanced workflow components
        workflow["workflow_steps"] = self._create_advanced_category_workflow(challenge)
        workflow["parallel_tasks"] = self._identify_parallel_tasks(challenge.category)
        workflow["resource_requirements"] = self._calculate_resource_requirements(challenge)
        workflow["expected_artifacts"] = self._predict_expected_artifacts(challenge)
        workflow["validation_steps"] = self._create_validation_steps(challenge.category)

        return workflow

    def _select_tools_for_challenge(self, challenge: CTFChallenge, category_tools: Dict[str, List[str]]) -> List[str]:
        """Select appropriate tools based on challenge details"""
        selected_tools = []

        # Always include reconnaissance tools for the category
        if "reconnaissance" in category_tools:
            selected_tools.extend(category_tools["reconnaissance"][:2])  # Top 2 recon tools

        # Add specialized tools based on challenge description
        description_lower = challenge.description.lower()

        if challenge.category == "web":
            if any(keyword in description_lower for keyword in ["sql", "injection", "database"]):
                selected_tools.append("sqlmap")
            if any(keyword in description_lower for keyword in ["xss", "script", "javascript"]):
                selected_tools.append("dalfox")
            if any(keyword in description_lower for keyword in ["wordpress", "wp"]):
                selected_tools.append("wpscan")
            if any(keyword in description_lower for keyword in ["upload", "file"]):
                selected_tools.extend(["gobuster", "feroxbuster"])

        elif challenge.category == "crypto":
            if any(keyword in description_lower for keyword in ["hash", "md5", "sha"]):
                selected_tools.extend(["hashcat", "john"])
            if any(keyword in description_lower for keyword in ["rsa", "public key"]):
                selected_tools.extend(["rsatool", "factordb"])
            if any(keyword in description_lower for keyword in ["cipher", "encrypt"]):
                selected_tools.extend(["cipher-identifier", "cyberchef"])

        elif challenge.category == "pwn":
            selected_tools.extend(["checksec", "ghidra", "pwntools"])
            if any(keyword in description_lower for keyword in ["heap", "malloc"]):
                selected_tools.append("glibc-heap-analysis")
            if any(keyword in description_lower for keyword in ["format", "printf"]):
                selected_tools.append("format-string-exploiter")

        elif challenge.category == "forensics":
            if any(keyword in description_lower for keyword in ["image", "jpg", "png"]):
                selected_tools.extend(["exiftool", "steghide", "stegsolve"])
            if any(keyword in description_lower for keyword in ["memory", "dump"]):
                selected_tools.append("volatility")
            if any(keyword in description_lower for keyword in ["network", "pcap"]):
                selected_tools.extend(["wireshark", "tcpdump"])

        elif challenge.category == "rev":
            selected_tools.extend(["ghidra", "radare2", "strings"])
            if any(keyword in description_lower for keyword in ["packed", "upx"]):
                selected_tools.extend(["upx", "peid"])

        # Remove duplicates while preserving order
        return list(dict.fromkeys(selected_tools))

    def _create_category_workflow(self, challenge: CTFChallenge) -> List[Dict[str, Any]]:
        """Create category-specific workflow steps"""
        workflows = {
            "web": [
                {"step": 1, "action": "reconnaissance", "description": "Analyze target URL and gather information"},
                {"step": 2, "action": "source_analysis", "description": "Examine HTML/JS source code for clues"},
                {"step": 3, "action": "directory_discovery", "description": "Discover hidden directories and files"},
                {"step": 4, "action": "vulnerability_testing", "description": "Test for common web vulnerabilities"},
                {"step": 5, "action": "exploitation", "description": "Exploit discovered vulnerabilities"},
                {"step": 6, "action": "flag_extraction", "description": "Extract flag from compromised system"}
            ],
            "crypto": [
                {"step": 1, "action": "cipher_identification", "description": "Identify the type of cipher or encoding"},
                {"step": 2, "action": "key_analysis", "description": "Analyze key properties and weaknesses"},
                {"step": 3, "action": "attack_selection", "description": "Select appropriate cryptographic attack"},
                {"step": 4, "action": "implementation", "description": "Implement and execute the attack"},
                {"step": 5, "action": "verification", "description": "Verify the decrypted result"},
                {"step": 6, "action": "flag_extraction", "description": "Extract flag from decrypted data"}
            ],
            "pwn": [
                {"step": 1, "action": "binary_analysis", "description": "Analyze binary protections and architecture"},
                {"step": 2, "action": "vulnerability_discovery", "description": "Find exploitable vulnerabilities"},
                {"step": 3, "action": "exploit_development", "description": "Develop exploit payload"},
                {"step": 4, "action": "local_testing", "description": "Test exploit locally"},
                {"step": 5, "action": "remote_exploitation", "description": "Execute exploit against remote target"},
                {"step": 6, "action": "shell_interaction", "description": "Interact with gained shell to find flag"}
            ],
            "forensics": [
                {"step": 1, "action": "file_analysis", "description": "Analyze provided files and their properties"},
                {"step": 2, "action": "data_recovery", "description": "Recover deleted or hidden data"},
                {"step": 3, "action": "artifact_extraction", "description": "Extract relevant artifacts and evidence"},
                {"step": 4, "action": "timeline_reconstruction", "description": "Reconstruct timeline of events"},
                {"step": 5, "action": "correlation_analysis", "description": "Correlate findings across different sources"},
                {"step": 6, "action": "flag_discovery", "description": "Locate flag in recovered data"}
            ],
            "rev": [
                {"step": 1, "action": "static_analysis", "description": "Perform static analysis of the binary"},
                {"step": 2, "action": "dynamic_analysis", "description": "Run binary and observe behavior"},
                {"step": 3, "action": "algorithm_identification", "description": "Identify key algorithms and logic"},
                {"step": 4, "action": "key_extraction", "description": "Extract keys or important values"},
                {"step": 5, "action": "solution_implementation", "description": "Implement solution based on analysis"},
                {"step": 6, "action": "flag_generation", "description": "Generate or extract the flag"}
            ]
        }

        return workflows.get(challenge.category, [
            {"step": 1, "action": "analysis", "description": "Analyze the challenge"},
            {"step": 2, "action": "research", "description": "Research relevant techniques"},
            {"step": 3, "action": "implementation", "description": "Implement solution"},
            {"step": 4, "action": "testing", "description": "Test the solution"},
            {"step": 5, "action": "refinement", "description": "Refine approach if needed"},
            {"step": 6, "action": "flag_submission", "description": "Submit the flag"}
        ])

    def create_ctf_team_strategy(self, challenges: List[CTFChallenge], team_size: int = 4) -> Dict[str, Any]:
        """Create team strategy for CTF competition"""
        strategy = {
            "team_size": team_size,
            "challenge_allocation": {},
            "priority_order": [],
            "estimated_total_time": 0,
            "expected_score": 0
        }

        # Sort challenges by points/time ratio for optimal strategy
        challenge_efficiency = []
        for challenge in challenges:
            workflow = self.create_ctf_challenge_workflow(challenge)
            efficiency = (challenge.points * workflow["success_probability"]) / (workflow["estimated_time"] / 3600)  # points per hour
            challenge_efficiency.append({
                "challenge": challenge,
                "efficiency": efficiency,
                "workflow": workflow
            })

        # Sort by efficiency (highest first)
        challenge_efficiency.sort(key=lambda x: x["efficiency"], reverse=True)

        # Allocate challenges to team members
        team_workload = [0] * team_size
        for i, item in enumerate(challenge_efficiency):
            # Assign to team member with least workload
            team_member = team_workload.index(min(team_workload))

            if team_member not in strategy["challenge_allocation"]:
                strategy["challenge_allocation"][team_member] = []

            strategy["challenge_allocation"][team_member].append({
                "challenge": item["challenge"].name,
                "category": item["challenge"].category,
                "points": item["challenge"].points,
                "estimated_time": item["workflow"]["estimated_time"],
                "success_probability": item["workflow"]["success_probability"]
            })

            team_workload[team_member] += item["workflow"]["estimated_time"]
            strategy["expected_score"] += item["challenge"].points * item["workflow"]["success_probability"]

        strategy["estimated_total_time"] = max(team_workload)
        strategy["priority_order"] = [item["challenge"].name for item in challenge_efficiency]

        return strategy

    def _generate_fallback_strategies(self, category: str) -> List[Dict[str, str]]:
        """Generate fallback strategies for when primary approaches fail"""
        fallback_strategies = {
            "web": [
                {"strategy": "manual_source_review", "description": "Manually review all source code and comments"},
                {"strategy": "alternative_wordlists", "description": "Try alternative wordlists and fuzzing techniques"},
                {"strategy": "parameter_pollution", "description": "Test for HTTP parameter pollution vulnerabilities"},
                {"strategy": "race_conditions", "description": "Test for race condition vulnerabilities"},
                {"strategy": "business_logic", "description": "Focus on business logic flaws and edge cases"}
            ],
            "crypto": [
                {"strategy": "known_plaintext_attack", "description": "Use any known plaintext for cryptanalysis"},
                {"strategy": "frequency_analysis_variants", "description": "Try different frequency analysis approaches"},
                {"strategy": "mathematical_properties", "description": "Exploit mathematical properties of the cipher"},
                {"strategy": "implementation_weaknesses", "description": "Look for implementation-specific weaknesses"},
                {"strategy": "side_channel_analysis", "description": "Analyze timing or other side channels"}
            ],
            "pwn": [
                {"strategy": "alternative_exploitation", "description": "Try alternative exploitation techniques"},
                {"strategy": "information_leaks", "description": "Exploit information disclosure vulnerabilities"},
                {"strategy": "heap_feng_shui", "description": "Use heap manipulation techniques"},
                {"strategy": "ret2libc_variants", "description": "Try different ret2libc approaches"},
                {"strategy": "sigreturn_oriented", "description": "Use SIGROP (Signal Return Oriented Programming)"}
            ],
            "forensics": [
                {"strategy": "alternative_tools", "description": "Try different forensics tools and approaches"},
                {"strategy": "manual_hex_analysis", "description": "Manually analyze hex dumps and file structures"},
                {"strategy": "correlation_analysis", "description": "Correlate findings across multiple evidence sources"},
                {"strategy": "timeline_reconstruction", "description": "Reconstruct detailed timeline of events"},
                {"strategy": "deleted_data_recovery", "description": "Focus on recovering deleted or hidden data"}
            ],
            "rev": [
                {"strategy": "dynamic_analysis_focus", "description": "Shift focus to dynamic analysis techniques"},
                {"strategy": "anti_analysis_bypass", "description": "Bypass anti-analysis and obfuscation"},
                {"strategy": "library_analysis", "description": "Analyze linked libraries and dependencies"},
                {"strategy": "algorithm_identification", "description": "Focus on identifying key algorithms"},
                {"strategy": "patch_analysis", "description": "Analyze patches or modifications to standard code"}
            ],
            "misc": [
                {"strategy": "alternative_interpretations", "description": "Try alternative interpretations of the challenge"},
                {"strategy": "encoding_combinations", "description": "Try combinations of different encodings"},
                {"strategy": "esoteric_approaches", "description": "Consider esoteric or unusual solution approaches"},
                {"strategy": "metadata_focus", "description": "Focus heavily on metadata and hidden information"},
                {"strategy": "collaborative_solving", "description": "Use collaborative problem-solving techniques"}
            ],
            "osint": [
                {"strategy": "alternative_sources", "description": "Try alternative information sources"},
                {"strategy": "historical_data", "description": "Look for historical or archived information"},
                {"strategy": "social_engineering", "description": "Use social engineering techniques (ethically)"},
                {"strategy": "cross_reference", "description": "Cross-reference information across multiple platforms"},
                {"strategy": "deep_web_search", "description": "Search in deep web and specialized databases"}
            ]
        }
        return fallback_strategies.get(category, [])

    def _analyze_description_complexity(self, description: str) -> float:
        """Analyze challenge description complexity to adjust time estimates"""
        complexity_score = 0.0
        description_lower = description.lower()

        # Length-based complexity
        if len(description) > 500:
            complexity_score += 0.3
        elif len(description) > 200:
            complexity_score += 0.1

        # Technical term density
        technical_terms = [
            "algorithm", "encryption", "decryption", "vulnerability", "exploit",
            "buffer overflow", "sql injection", "xss", "csrf", "authentication",
            "authorization", "cryptography", "steganography", "forensics",
            "reverse engineering", "binary analysis", "memory corruption",
            "heap", "stack", "rop", "shellcode", "payload"
        ]

        term_count = sum(1 for term in technical_terms if term in description_lower)
        complexity_score += min(0.4, term_count * 0.05)

        # Multi-step indicators
        multi_step_indicators = ["first", "then", "next", "after", "finally", "step"]
        step_count = sum(1 for indicator in multi_step_indicators if indicator in description_lower)
        complexity_score += min(0.3, step_count * 0.1)

        return min(1.0, complexity_score)

    def _create_advanced_category_workflow(self, challenge: CTFChallenge) -> List[Dict[str, Any]]:
        """Create advanced category-specific workflow with parallel execution support"""
        advanced_workflows = {
            "web": [
                {"step": 1, "action": "automated_reconnaissance", "description": "Automated web reconnaissance and technology detection", "parallel": True, "tools": ["httpx", "whatweb", "katana"], "estimated_time": 300},
                {"step": 2, "action": "source_code_analysis", "description": "Comprehensive source code and comment analysis", "parallel": False, "tools": ["manual"], "estimated_time": 600},
                {"step": 3, "action": "directory_enumeration", "description": "Multi-tool directory and file enumeration", "parallel": True, "tools": ["gobuster", "dirsearch", "feroxbuster"], "estimated_time": 900},
                {"step": 4, "action": "parameter_discovery", "description": "Parameter discovery and testing", "parallel": True, "tools": ["arjun", "paramspider"], "estimated_time": 600},
                {"step": 5, "action": "vulnerability_scanning", "description": "Automated vulnerability scanning", "parallel": True, "tools": ["sqlmap", "dalfox", "nikto"], "estimated_time": 1200},
                {"step": 6, "action": "manual_testing", "description": "Manual testing of discovered attack vectors", "parallel": False, "tools": ["manual"], "estimated_time": 1800},
                {"step": 7, "action": "exploitation", "description": "Exploit discovered vulnerabilities", "parallel": False, "tools": ["custom"], "estimated_time": 900},
                {"step": 8, "action": "flag_extraction", "description": "Extract and validate flag", "parallel": False, "tools": ["manual"], "estimated_time": 300}
            ],
            "crypto": [
                {"step": 1, "action": "cipher_identification", "description": "Identify cipher type and properties", "parallel": False, "tools": ["cipher-identifier", "hash-identifier"], "estimated_time": 300},
                {"step": 2, "action": "key_space_analysis", "description": "Analyze key space and potential weaknesses", "parallel": False, "tools": ["manual"], "estimated_time": 600},
                {"step": 3, "action": "automated_attacks", "description": "Launch automated cryptographic attacks", "parallel": True, "tools": ["hashcat", "john", "factordb"], "estimated_time": 1800},
                {"step": 4, "action": "mathematical_analysis", "description": "Mathematical analysis of cipher properties", "parallel": False, "tools": ["sage", "python"], "estimated_time": 1200},
                {"step": 5, "action": "frequency_analysis", "description": "Statistical and frequency analysis", "parallel": True, "tools": ["frequency-analysis", "substitution-solver"], "estimated_time": 900},
                {"step": 6, "action": "known_plaintext", "description": "Known plaintext and chosen plaintext attacks", "parallel": False, "tools": ["custom"], "estimated_time": 1200},
                {"step": 7, "action": "implementation_analysis", "description": "Analyze implementation for weaknesses", "parallel": False, "tools": ["manual"], "estimated_time": 900},
                {"step": 8, "action": "solution_verification", "description": "Verify and extract flag", "parallel": False, "tools": ["manual"], "estimated_time": 300}
            ],
            "pwn": [
                {"step": 1, "action": "binary_reconnaissance", "description": "Comprehensive binary analysis and protection identification", "parallel": True, "tools": ["checksec", "file", "strings", "objdump"], "estimated_time": 600},
                {"step": 2, "action": "static_analysis", "description": "Static analysis with multiple tools", "parallel": True, "tools": ["ghidra", "radare2", "ida"], "estimated_time": 1800},
                {"step": 3, "action": "dynamic_analysis", "description": "Dynamic analysis and debugging", "parallel": False, "tools": ["gdb-peda", "ltrace", "strace"], "estimated_time": 1200},
                {"step": 4, "action": "vulnerability_identification", "description": "Identify exploitable vulnerabilities", "parallel": False, "tools": ["manual"], "estimated_time": 900},
                {"step": 5, "action": "exploit_development", "description": "Develop exploit payload", "parallel": False, "tools": ["pwntools", "ropper", "one-gadget"], "estimated_time": 2400},
                {"step": 6, "action": "local_testing", "description": "Test exploit locally", "parallel": False, "tools": ["gdb-peda"], "estimated_time": 600},
                {"step": 7, "action": "remote_exploitation", "description": "Execute exploit against remote target", "parallel": False, "tools": ["pwntools"], "estimated_time": 600},
                {"step": 8, "action": "post_exploitation", "description": "Post-exploitation and flag extraction", "parallel": False, "tools": ["manual"], "estimated_time": 300}
            ],
            "forensics": [
                {"step": 1, "action": "evidence_acquisition", "description": "Acquire and validate digital evidence", "parallel": False, "tools": ["file", "exiftool"], "estimated_time": 300},
                {"step": 2, "action": "file_analysis", "description": "Comprehensive file structure analysis", "parallel": True, "tools": ["binwalk", "foremost", "strings"], "estimated_time": 900},
                {"step": 3, "action": "metadata_extraction", "description": "Extract and analyze metadata", "parallel": True, "tools": ["exiftool", "steghide"], "estimated_time": 600},
                {"step": 4, "action": "steganography_detection", "description": "Detect and extract hidden data", "parallel": True, "tools": ["stegsolve", "zsteg", "outguess"], "estimated_time": 1200},
                {"step": 5, "action": "memory_analysis", "description": "Memory dump analysis if applicable", "parallel": False, "tools": ["volatility", "volatility3"], "estimated_time": 1800},
                {"step": 6, "action": "network_analysis", "description": "Network traffic analysis if applicable", "parallel": False, "tools": ["wireshark", "tcpdump"], "estimated_time": 1200},
                {"step": 7, "action": "timeline_reconstruction", "description": "Reconstruct timeline of events", "parallel": False, "tools": ["manual"], "estimated_time": 900},
                {"step": 8, "action": "evidence_correlation", "description": "Correlate findings and extract flag", "parallel": False, "tools": ["manual"], "estimated_time": 600}
            ],
            "rev": [
                {"step": 1, "action": "binary_triage", "description": "Initial binary triage and classification", "parallel": True, "tools": ["file", "strings", "checksec"], "estimated_time": 300},
                {"step": 2, "action": "packer_detection", "description": "Detect and unpack if necessary", "parallel": False, "tools": ["upx", "peid", "detect-it-easy"], "estimated_time": 600},
                {"step": 3, "action": "static_disassembly", "description": "Static disassembly and analysis", "parallel": True, "tools": ["ghidra", "ida", "radare2"], "estimated_time": 2400},
                {"step": 4, "action": "dynamic_analysis", "description": "Dynamic analysis and debugging", "parallel": False, "tools": ["gdb-peda", "ltrace", "strace"], "estimated_time": 1800},
                {"step": 5, "action": "algorithm_identification", "description": "Identify key algorithms and logic", "parallel": False, "tools": ["manual"], "estimated_time": 1200},
                {"step": 6, "action": "key_extraction", "description": "Extract keys, passwords, or critical values", "parallel": False, "tools": ["manual"], "estimated_time": 900},
                {"step": 7, "action": "solution_implementation", "description": "Implement solution based on analysis", "parallel": False, "tools": ["python", "custom"], "estimated_time": 1200},
                {"step": 8, "action": "flag_generation", "description": "Generate or extract the flag", "parallel": False, "tools": ["manual"], "estimated_time": 300}
            ],
            "misc": [
                {"step": 1, "action": "challenge_analysis", "description": "Analyze challenge type and requirements", "parallel": False, "tools": ["manual"], "estimated_time": 300},
                {"step": 2, "action": "encoding_detection", "description": "Detect encoding or obfuscation methods", "parallel": True, "tools": ["base64", "hex", "rot13"], "estimated_time": 600},
                {"step": 3, "action": "format_identification", "description": "Identify file formats or data structures", "parallel": False, "tools": ["file", "binwalk"], "estimated_time": 300},
                {"step": 4, "action": "specialized_analysis", "description": "Apply specialized analysis techniques", "parallel": True, "tools": ["qr-decoder", "audio-analysis"], "estimated_time": 900},
                {"step": 5, "action": "pattern_recognition", "description": "Identify patterns and relationships", "parallel": False, "tools": ["manual"], "estimated_time": 600},
                {"step": 6, "action": "solution_implementation", "description": "Implement solution approach", "parallel": False, "tools": ["python", "custom"], "estimated_time": 900},
                {"step": 7, "action": "validation", "description": "Validate solution and extract flag", "parallel": False, "tools": ["manual"], "estimated_time": 300}
            ],
            "osint": [
                {"step": 1, "action": "target_identification", "description": "Identify and validate targets", "parallel": False, "tools": ["manual"], "estimated_time": 300},
                {"step": 2, "action": "automated_reconnaissance", "description": "Automated OSINT gathering", "parallel": True, "tools": ["sherlock", "theHarvester", "sublist3r"], "estimated_time": 1200},
                {"step": 3, "action": "social_media_analysis", "description": "Social media intelligence gathering", "parallel": True, "tools": ["sherlock", "social-analyzer"], "estimated_time": 900},
                {"step": 4, "action": "domain_analysis", "description": "Domain and DNS intelligence", "parallel": True, "tools": ["whois", "dig", "amass"], "estimated_time": 600},
                {"step": 5, "action": "search_engine_intelligence", "description": "Search engine and database queries", "parallel": True, "tools": ["shodan", "censys"], "estimated_time": 900},
                {"step": 6, "action": "correlation_analysis", "description": "Correlate information across sources", "parallel": False, "tools": ["manual"], "estimated_time": 1200},
                {"step": 7, "action": "verification", "description": "Verify findings and extract flag", "parallel": False, "tools": ["manual"], "estimated_time": 600}
            ]
        }

        return advanced_workflows.get(challenge.category, [
            {"step": 1, "action": "analysis", "description": "Analyze the challenge", "parallel": False, "tools": ["manual"], "estimated_time": 600},
            {"step": 2, "action": "research", "description": "Research relevant techniques", "parallel": False, "tools": ["manual"], "estimated_time": 900},
            {"step": 3, "action": "implementation", "description": "Implement solution", "parallel": False, "tools": ["custom"], "estimated_time": 1800},
            {"step": 4, "action": "testing", "description": "Test the solution", "parallel": False, "tools": ["manual"], "estimated_time": 600},
            {"step": 5, "action": "refinement", "description": "Refine approach if needed", "parallel": False, "tools": ["manual"], "estimated_time": 900},
            {"step": 6, "action": "flag_submission", "description": "Submit the flag", "parallel": False, "tools": ["manual"], "estimated_time": 300}
        ])

    def _identify_parallel_tasks(self, category: str) -> List[Dict[str, Any]]:
        """Identify tasks that can be executed in parallel for efficiency"""
        parallel_tasks = {
            "web": [
                {"task_group": "reconnaissance", "tasks": ["httpx", "whatweb", "katana"], "max_concurrent": 3},
                {"task_group": "directory_enumeration", "tasks": ["gobuster", "dirsearch", "feroxbuster"], "max_concurrent": 2},
                {"task_group": "parameter_discovery", "tasks": ["arjun", "paramspider"], "max_concurrent": 2},
                {"task_group": "vulnerability_scanning", "tasks": ["sqlmap", "dalfox", "nikto"], "max_concurrent": 2}
            ],
            "crypto": [
                {"task_group": "hash_cracking", "tasks": ["hashcat", "john"], "max_concurrent": 2},
                {"task_group": "cipher_analysis", "tasks": ["frequency-analysis", "substitution-solver"], "max_concurrent": 2},
                {"task_group": "factorization", "tasks": ["factordb", "yafu"], "max_concurrent": 2}
            ],
            "pwn": [
                {"task_group": "binary_analysis", "tasks": ["checksec", "file", "strings", "objdump"], "max_concurrent": 4},
                {"task_group": "static_analysis", "tasks": ["ghidra", "radare2"], "max_concurrent": 2},
                {"task_group": "gadget_finding", "tasks": ["ropper", "ropgadget"], "max_concurrent": 2}
            ],
            "forensics": [
                {"task_group": "file_analysis", "tasks": ["binwalk", "foremost", "strings"], "max_concurrent": 3},
                {"task_group": "steganography", "tasks": ["stegsolve", "zsteg", "outguess"], "max_concurrent": 3},
                {"task_group": "metadata_extraction", "tasks": ["exiftool", "steghide"], "max_concurrent": 2}
            ],
            "rev": [
                {"task_group": "initial_analysis", "tasks": ["file", "strings", "checksec"], "max_concurrent": 3},
                {"task_group": "disassembly", "tasks": ["ghidra", "radare2"], "max_concurrent": 2},
                {"task_group": "packer_detection", "tasks": ["upx", "peid", "detect-it-easy"], "max_concurrent": 3}
            ],
            "osint": [
                {"task_group": "username_search", "tasks": ["sherlock", "social-analyzer"], "max_concurrent": 2},
                {"task_group": "domain_recon", "tasks": ["sublist3r", "amass", "dig"], "max_concurrent": 3},
                {"task_group": "search_engines", "tasks": ["shodan", "censys"], "max_concurrent": 2}
            ],
            "misc": [
                {"task_group": "encoding_detection", "tasks": ["base64", "hex", "rot13"], "max_concurrent": 3},
                {"task_group": "format_analysis", "tasks": ["file", "binwalk"], "max_concurrent": 2}
            ]
        }

        return parallel_tasks.get(category, [])

    def _calculate_resource_requirements(self, challenge: CTFChallenge) -> Dict[str, Any]:
        """Calculate estimated resource requirements for challenge"""
        base_requirements = {
            "cpu_cores": 2,
            "memory_mb": 2048,
            "disk_space_mb": 1024,
            "network_bandwidth": "medium",
            "gpu_required": False,
            "special_tools": []
        }

        # Adjust based on category
        category_adjustments = {
            "web": {"cpu_cores": 4, "memory_mb": 4096, "network_bandwidth": "high"},
            "crypto": {"cpu_cores": 8, "memory_mb": 8192, "gpu_required": True},
            "pwn": {"cpu_cores": 4, "memory_mb": 4096, "special_tools": ["gdb", "pwntools"]},
            "forensics": {"cpu_cores": 2, "memory_mb": 8192, "disk_space_mb": 4096},
            "rev": {"cpu_cores": 4, "memory_mb": 8192, "special_tools": ["ghidra", "ida"]},
            "osint": {"cpu_cores": 2, "memory_mb": 2048, "network_bandwidth": "high"},
            "misc": {"cpu_cores": 2, "memory_mb": 2048}
        }

        if challenge.category in category_adjustments:
            base_requirements.update(category_adjustments[challenge.category])

        # Adjust based on difficulty
        difficulty_multipliers = {
            "easy": 1.0,
            "medium": 1.2,
            "hard": 1.5,
            "insane": 2.0,
            "unknown": 1.3
        }

        multiplier = difficulty_multipliers[challenge.difficulty]
        base_requirements["cpu_cores"] = int(base_requirements["cpu_cores"] * multiplier)
        base_requirements["memory_mb"] = int(base_requirements["memory_mb"] * multiplier)
        base_requirements["disk_space_mb"] = int(base_requirements["disk_space_mb"] * multiplier)

        return base_requirements

    def _predict_expected_artifacts(self, challenge: CTFChallenge) -> List[Dict[str, str]]:
        """Predict expected artifacts and outputs from challenge solving"""
        artifacts = {
            "web": [
                {"type": "http_responses", "description": "HTTP response data and headers"},
                {"type": "source_code", "description": "Downloaded source code and scripts"},
                {"type": "directory_lists", "description": "Discovered directories and files"},
                {"type": "vulnerability_reports", "description": "Vulnerability scan results"},
                {"type": "exploit_payloads", "description": "Working exploit payloads"},
                {"type": "session_data", "description": "Session tokens and cookies"}
            ],
            "crypto": [
                {"type": "plaintext", "description": "Decrypted plaintext data"},
                {"type": "keys", "description": "Recovered encryption keys"},
                {"type": "cipher_analysis", "description": "Cipher analysis results"},
                {"type": "frequency_data", "description": "Frequency analysis data"},
                {"type": "mathematical_proof", "description": "Mathematical proof of solution"}
            ],
            "pwn": [
                {"type": "exploit_code", "description": "Working exploit code"},
                {"type": "shellcode", "description": "Custom shellcode payloads"},
                {"type": "memory_dumps", "description": "Memory dumps and analysis"},
                {"type": "rop_chains", "description": "ROP chain constructions"},
                {"type": "debug_output", "description": "Debugging session outputs"}
            ],
            "forensics": [
                {"type": "recovered_files", "description": "Recovered deleted files"},
                {"type": "extracted_data", "description": "Extracted hidden data"},
                {"type": "timeline", "description": "Timeline of events"},
                {"type": "metadata", "description": "File metadata and properties"},
                {"type": "network_flows", "description": "Network traffic analysis"}
            ],
            "rev": [
                {"type": "decompiled_code", "description": "Decompiled source code"},
                {"type": "algorithm_analysis", "description": "Identified algorithms"},
                {"type": "key_values", "description": "Extracted keys and constants"},
                {"type": "control_flow", "description": "Control flow analysis"},
                {"type": "solution_script", "description": "Solution implementation script"}
            ],
            "osint": [
                {"type": "intelligence_report", "description": "Compiled intelligence report"},
                {"type": "social_profiles", "description": "Discovered social media profiles"},
                {"type": "domain_data", "description": "Domain registration and DNS data"},
                {"type": "correlation_matrix", "description": "Information correlation analysis"},
                {"type": "verification_data", "description": "Verification of findings"}
            ],
            "misc": [
                {"type": "decoded_data", "description": "Decoded or decrypted data"},
                {"type": "pattern_analysis", "description": "Pattern recognition results"},
                {"type": "solution_explanation", "description": "Explanation of solution approach"},
                {"type": "intermediate_results", "description": "Intermediate calculation results"}
            ]
        }

        return artifacts.get(challenge.category, [
            {"type": "solution_data", "description": "Solution-related data"},
            {"type": "analysis_results", "description": "Analysis results and findings"}
        ])

    def _create_validation_steps(self, category: str) -> List[Dict[str, str]]:
        """Create validation steps to verify solution correctness"""
        validation_steps = {
            "web": [
                {"step": "response_validation", "description": "Validate HTTP responses and status codes"},
                {"step": "payload_verification", "description": "Verify exploit payloads work correctly"},
                {"step": "flag_format_check", "description": "Check flag format matches expected pattern"},
                {"step": "reproducibility_test", "description": "Test solution reproducibility"}
            ],
            "crypto": [
                {"step": "decryption_verification", "description": "Verify decryption produces readable text"},
                {"step": "key_validation", "description": "Validate recovered keys are correct"},
                {"step": "mathematical_check", "description": "Verify mathematical correctness"},
                {"step": "flag_extraction", "description": "Extract and validate flag from plaintext"}
            ],
            "pwn": [
                {"step": "exploit_reliability", "description": "Test exploit reliability and success rate"},
                {"step": "payload_verification", "description": "Verify payload executes correctly"},
                {"step": "shell_validation", "description": "Validate shell access and commands"},
                {"step": "flag_retrieval", "description": "Successfully retrieve flag from target"}
            ],
            "forensics": [
                {"step": "data_integrity", "description": "Verify integrity of recovered data"},
                {"step": "timeline_accuracy", "description": "Validate timeline accuracy"},
                {"step": "evidence_correlation", "description": "Verify evidence correlation is correct"},
                {"step": "flag_location", "description": "Confirm flag location and extraction"}
            ],
            "rev": [
                {"step": "algorithm_accuracy", "description": "Verify algorithm identification is correct"},
                {"step": "key_extraction", "description": "Validate extracted keys and values"},
                {"step": "solution_testing", "description": "Test solution against known inputs"},
                {"step": "flag_generation", "description": "Generate correct flag using solution"}
            ],
            "osint": [
                {"step": "source_verification", "description": "Verify information sources are reliable"},
                {"step": "cross_reference", "description": "Cross-reference findings across sources"},
                {"step": "accuracy_check", "description": "Check accuracy of gathered intelligence"},
                {"step": "flag_confirmation", "description": "Confirm flag from verified information"}
            ],
            "misc": [
                {"step": "solution_verification", "description": "Verify solution approach is correct"},
                {"step": "output_validation", "description": "Validate output format and content"},
                {"step": "edge_case_testing", "description": "Test solution with edge cases"},
                {"step": "flag_extraction", "description": "Extract and validate final flag"}
            ]
        }

        return validation_steps.get(category, [
            {"step": "general_validation", "description": "General solution validation"},
            {"step": "flag_verification", "description": "Verify flag format and correctness"}
        ])

class CTFToolManager:
    """Advanced tool manager for CTF challenges with comprehensive tool arsenal"""

    def __init__(self):
        self.tool_commands = {
            # Web Application Security Tools
            "httpx": "httpx -probe -tech-detect -status-code -title -content-length",
            "katana": "katana -depth 3 -js-crawl -form-extraction -headless",
            "sqlmap": "sqlmap --batch --level 3 --risk 2 --threads 5",
            "dalfox": "dalfox url --mining-dom --mining-dict --deep-domxss",
            "gobuster": "gobuster dir -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt -x php,html,txt,js",
            "dirsearch": "dirsearch -u {} -e php,html,js,txt,xml,json -t 50",
            "feroxbuster": "feroxbuster -u {} -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt -x php,html,js,txt",
            "arjun": "arjun -u {} --get --post",
            "paramspider": "paramspider -d {}",
            "wpscan": "wpscan --url {} --enumerate ap,at,cb,dbe",
            "nikto": "nikto -h {} -C all",
            "whatweb": "whatweb -v -a 3",

            # Cryptography Challenge Tools
            "hashcat": "hashcat -m 0 -a 0 --potfile-disable --quiet",
            "john": "john --wordlist=/usr/share/wordlists/rockyou.txt --format=Raw-MD5",
            "hash-identifier": "hash-identifier",
            "hashid": "hashid -m",
            "cipher-identifier": "python3 /opt/cipher-identifier/cipher_identifier.py",
            "factordb": "python3 /opt/factordb/factordb.py",
            "rsatool": "python3 /opt/rsatool/rsatool.py",
            "yafu": "yafu",
            "sage": "sage -python",
            "openssl": "openssl",
            "gpg": "gpg --decrypt",
            "steganography": "stegcracker",
            "frequency-analysis": "python3 /opt/frequency-analysis/freq_analysis.py",
            "substitution-solver": "python3 /opt/substitution-solver/solve.py",
            "vigenere-solver": "python3 /opt/vigenere-solver/vigenere.py",
            "base64": "base64 -d",
            "base32": "base32 -d",
            "hex": "xxd -r -p",
            "rot13": "tr 'A-Za-z' 'N-ZA-Mn-za-m'",

            # Binary Exploitation (Pwn) Tools
            "checksec": "checksec --file",
            "pwntools": "python3 -c 'from pwn import *; context.log_level = \"debug\"'",
            "ropper": "ropper --file {} --search",
            "ropgadget": "ROPgadget --binary",
            "one-gadget": "one_gadget",
            "gdb-peda": "gdb -ex 'source /opt/peda/peda.py'",
            "gdb-gef": "gdb -ex 'source /opt/gef/gef.py'",
            "gdb-pwngdb": "gdb -ex 'source /opt/Pwngdb/pwngdb.py'",
            "angr": "python3 -c 'import angr'",
            "radare2": "r2 -A",
            "ghidra": "analyzeHeadless /tmp ghidra_project -import",
            "binary-ninja": "binaryninja",
            "ltrace": "ltrace",
            "strace": "strace -f",
            "objdump": "objdump -d -M intel",
            "readelf": "readelf -a",
            "nm": "nm -D",
            "ldd": "ldd",
            "file": "file",
            "strings": "strings -n 8",
            "hexdump": "hexdump -C",
            "pwninit": "pwninit",
            "libc-database": "python3 /opt/libc-database/find.py",

            # Forensics Investigation Tools
            "binwalk": "binwalk -e --dd='.*'",
            "foremost": "foremost -i {} -o /tmp/foremost_output",
            "photorec": "photorec /log /cmd",
            "testdisk": "testdisk /log",
            "exiftool": "exiftool -all",
            "steghide": "steghide extract -sf {} -p ''",
            "stegsolve": "java -jar /opt/stegsolve/stegsolve.jar",
            "zsteg": "zsteg -a",
            "outguess": "outguess -r",
            "jsteg": "jsteg reveal",
            "volatility": "volatility -f {} imageinfo",
            "volatility3": "python3 /opt/volatility3/vol.py -f",
            "rekall": "rekall -f",
            "wireshark": "tshark -r",
            "tcpdump": "tcpdump -r",
            "networkminer": "mono /opt/NetworkMiner/NetworkMiner.exe",
            "autopsy": "autopsy",
            "sleuthkit": "fls -r",
            "scalpel": "scalpel -c /etc/scalpel/scalpel.conf",
            "bulk-extractor": "bulk_extractor -o /tmp/bulk_output",
            "ddrescue": "ddrescue",
            "dc3dd": "dc3dd",

            # Reverse Engineering Tools
            "ida": "ida64",
            "ida-free": "ida64 -A",
            "retdec": "retdec-decompiler",
            "upx": "upx -d",
            "peid": "peid",
            "detect-it-easy": "die",
            "x64dbg": "x64dbg",
            "ollydbg": "ollydbg",
            "immunity": "immunity",
            "windbg": "windbg",
            "apktool": "apktool d",
            "jadx": "jadx",
            "dex2jar": "dex2jar",
            "jd-gui": "jd-gui",
            "dnspy": "dnspy",
            "ilspy": "ilspy",
            "dotpeek": "dotpeek",

            # OSINT and Reconnaissance Tools
            "sherlock": "sherlock",
            "social-analyzer": "social-analyzer",
            "theHarvester": "theHarvester -d {} -b all",
            "recon-ng": "recon-ng",
            "maltego": "maltego",
            "spiderfoot": "spiderfoot",
            "shodan": "shodan search",
            "censys": "censys search",
            "whois": "whois",
            "dig": "dig",
            "nslookup": "nslookup",
            "host": "host",
            "dnsrecon": "dnsrecon -d",
            "fierce": "fierce -dns",
            "sublist3r": "sublist3r -d",
            "amass": "amass enum -d",
            "assetfinder": "assetfinder",
            "subfinder": "subfinder -d",
            "waybackurls": "waybackurls",
            "gau": "gau",
            "httpx-osint": "httpx -title -tech-detect -status-code",

            # Miscellaneous Challenge Tools
            "qr-decoder": "zbarimg",
            "barcode-decoder": "zbarimg",
            "audio-analysis": "audacity",
            "sonic-visualizer": "sonic-visualizer",
            "spectrum-analyzer": "python3 /opt/spectrum-analyzer/analyze.py",
            "brainfuck": "python3 /opt/brainfuck/bf.py",
            "whitespace": "python3 /opt/whitespace/ws.py",
            "piet": "python3 /opt/piet/piet.py",
            "malbolge": "python3 /opt/malbolge/malbolge.py",
            "ook": "python3 /opt/ook/ook.py",
            "zip": "unzip -P",
            "7zip": "7z x -p",
            "rar": "unrar x -p",
            "tar": "tar -xf",
            "gzip": "gunzip",
            "bzip2": "bunzip2",
            "xz": "unxz",
            "lzma": "unlzma",
            "compress": "uncompress",

            # Modern Web Technologies
            "jwt-tool": "python3 /opt/jwt_tool/jwt_tool.py",
            "jwt-cracker": "jwt-cracker",
            "graphql-voyager": "graphql-voyager",
            "graphql-playground": "graphql-playground",
            "postman": "newman run",
            "burpsuite": "java -jar /opt/burpsuite/burpsuite.jar",
            "owasp-zap": "zap.sh -cmd",
            "websocket-king": "python3 /opt/websocket-king/ws_test.py",

            # Cloud and Container Security
            "docker": "docker",
            "kubectl": "kubectl",
            "aws-cli": "aws",
            "azure-cli": "az",
            "gcloud": "gcloud",
            "terraform": "terraform",
            "ansible": "ansible",

            # Mobile Application Security
            "adb": "adb",
            "frida": "frida",
            "objection": "objection",
            "mobsf": "python3 /opt/mobsf/manage.py",
            "apkleaks": "apkleaks -f",
            "qark": "qark --apk"
        }

        # Tool categories for intelligent selection
        self.tool_categories = {
            "web_recon": ["httpx", "katana", "waybackurls", "gau", "whatweb"],
            "web_vuln": ["sqlmap", "dalfox", "nikto", "wpscan"],
            "web_discovery": ["gobuster", "dirsearch", "feroxbuster"],
            "web_params": ["arjun", "paramspider"],
            "crypto_hash": ["hashcat", "john", "hash-identifier", "hashid"],
            "crypto_cipher": ["cipher-identifier", "frequency-analysis", "substitution-solver"],
            "crypto_rsa": ["rsatool", "factordb", "yafu"],
            "crypto_modern": ["sage", "openssl", "gpg"],
            "pwn_analysis": ["checksec", "file", "strings", "objdump", "readelf"],
            "pwn_exploit": ["pwntools", "ropper", "ropgadget", "one-gadget"],
            "pwn_debug": ["gdb-peda", "gdb-gef", "ltrace", "strace"],
            "pwn_advanced": ["angr", "ghidra", "radare2"],
            "forensics_file": ["binwalk", "foremost", "photorec", "exiftool"],
            "forensics_image": ["steghide", "stegsolve", "zsteg", "outguess"],
            "forensics_memory": ["volatility", "volatility3", "rekall"],
            "forensics_network": ["wireshark", "tcpdump", "networkminer"],
            "rev_static": ["ghidra", "ida", "radare2", "strings"],
            "rev_dynamic": ["gdb-peda", "ltrace", "strace"],
            "rev_unpack": ["upx", "peid", "detect-it-easy"],
            "osint_social": ["sherlock", "social-analyzer", "theHarvester"],
            "osint_domain": ["whois", "dig", "sublist3r", "amass"],
            "osint_search": ["shodan", "censys", "recon-ng"],
            "misc_encoding": ["base64", "base32", "hex", "rot13"],
            "misc_compression": ["zip", "7zip", "rar", "tar"],
            "misc_esoteric": ["brainfuck", "whitespace", "piet", "malbolge"]
        }

    def get_tool_command(self, tool: str, target: str, additional_args: str = "") -> str:
        """Get optimized command for CTF tool with intelligent parameter selection"""
        base_command = self.tool_commands.get(tool, tool)

        # Add intelligent parameter optimization based on tool type
        if tool in ["hashcat", "john"]:
            # For hash cracking, add common wordlists and rules
            if "wordlist" not in base_command:
                base_command += " --wordlist=/usr/share/wordlists/rockyou.txt"
            if tool == "hashcat" and "--rules" not in base_command:
                base_command += " --rules-file=/usr/share/hashcat/rules/best64.rule"

        elif tool in ["sqlmap"]:
            # For SQL injection, add tamper scripts and optimization
            if "--tamper" not in base_command:
                base_command += " --tamper=space2comment,charencode,randomcase"
            if "--threads" not in base_command:
                base_command += " --threads=5"

        elif tool in ["gobuster", "dirsearch", "feroxbuster"]:
            # For directory brute forcing, optimize threads and extensions
            if tool == "gobuster" and "-t" not in base_command:
                base_command += " -t 50"
            elif tool == "dirsearch" and "-t" not in base_command:
                base_command += " -t 50"
            elif tool == "feroxbuster" and "-t" not in base_command:
                base_command += " -t 50"

        if additional_args:
            return f"{base_command} {additional_args} {target}"
        else:
            return f"{base_command} {target}"

    def get_category_tools(self, category: str) -> List[str]:
        """Get all tools for a specific category"""
        return self.tool_categories.get(category, [])

    def suggest_tools_for_challenge(self, challenge_description: str, category: str) -> List[str]:
        """Suggest optimal tools based on challenge description and category"""
        suggested_tools = []
        description_lower = challenge_description.lower()

        # Category-based tool suggestions
        if category == "web":
            suggested_tools.extend(self.tool_categories["web_recon"][:2])

            if any(keyword in description_lower for keyword in ["sql", "injection", "database", "mysql", "postgres"]):
                suggested_tools.extend(["sqlmap", "hash-identifier"])
            if any(keyword in description_lower for keyword in ["xss", "script", "javascript", "dom"]):
                suggested_tools.extend(["dalfox", "katana"])
            if any(keyword in description_lower for keyword in ["wordpress", "wp", "cms"]):
                suggested_tools.append("wpscan")
            if any(keyword in description_lower for keyword in ["directory", "hidden", "files", "admin"]):
                suggested_tools.extend(["gobuster", "dirsearch"])
            if any(keyword in description_lower for keyword in ["parameter", "param", "get", "post"]):
                suggested_tools.extend(["arjun", "paramspider"])
            if any(keyword in description_lower for keyword in ["jwt", "token", "session"]):
                suggested_tools.append("jwt-tool")
            if any(keyword in description_lower for keyword in ["graphql", "api"]):
                suggested_tools.append("graphql-voyager")

        elif category == "crypto":
            if any(keyword in description_lower for keyword in ["hash", "md5", "sha", "password"]):
                suggested_tools.extend(["hashcat", "john", "hash-identifier"])
            if any(keyword in description_lower for keyword in ["rsa", "public key", "private key", "factorization"]):
                suggested_tools.extend(["rsatool", "factordb", "yafu"])
            if any(keyword in description_lower for keyword in ["cipher", "encrypt", "decrypt", "substitution"]):
                suggested_tools.extend(["cipher-identifier", "frequency-analysis"])
            if any(keyword in description_lower for keyword in ["vigenere", "polyalphabetic"]):
                suggested_tools.append("vigenere-solver")
            if any(keyword in description_lower for keyword in ["base64", "base32", "encoding"]):
                suggested_tools.extend(["base64", "base32"])
            if any(keyword in description_lower for keyword in ["rot", "caesar", "shift"]):
                suggested_tools.append("rot13")
            if any(keyword in description_lower for keyword in ["pgp", "gpg", "signature"]):
                suggested_tools.append("gpg")

        elif category == "pwn":
            suggested_tools.extend(["checksec", "file", "strings"])

            if any(keyword in description_lower for keyword in ["buffer", "overflow", "bof"]):
                suggested_tools.extend(["pwntools", "gdb-peda", "ropper"])
            if any(keyword in description_lower for keyword in ["format", "printf", "string"]):
                suggested_tools.extend(["pwntools", "gdb-peda"])
            if any(keyword in description_lower for keyword in ["heap", "malloc", "free"]):
                suggested_tools.extend(["pwntools", "gdb-gef"])
            if any(keyword in description_lower for keyword in ["rop", "gadget", "chain"]):
                suggested_tools.extend(["ropper", "ropgadget"])
            if any(keyword in description_lower for keyword in ["shellcode", "exploit"]):
                suggested_tools.extend(["pwntools", "one-gadget"])
            if any(keyword in description_lower for keyword in ["canary", "stack", "protection"]):
                suggested_tools.extend(["checksec", "pwntools"])

        elif category == "forensics":
            if any(keyword in description_lower for keyword in ["image", "jpg", "png", "gif", "steganography"]):
                suggested_tools.extend(["exiftool", "steghide", "stegsolve", "zsteg"])
            if any(keyword in description_lower for keyword in ["memory", "dump", "ram"]):
                suggested_tools.extend(["volatility", "volatility3"])
            if any(keyword in description_lower for keyword in ["network", "pcap", "wireshark", "traffic"]):
                suggested_tools.extend(["wireshark", "tcpdump"])
            if any(keyword in description_lower for keyword in ["file", "deleted", "recovery", "carving"]):
                suggested_tools.extend(["binwalk", "foremost", "photorec"])
            if any(keyword in description_lower for keyword in ["disk", "filesystem", "partition"]):
                suggested_tools.extend(["testdisk", "sleuthkit"])
            if any(keyword in description_lower for keyword in ["audio", "wav", "mp3", "sound"]):
                suggested_tools.extend(["audacity", "sonic-visualizer"])

        elif category == "rev":
            suggested_tools.extend(["file", "strings", "objdump"])

            if any(keyword in description_lower for keyword in ["packed", "upx", "packer"]):
                suggested_tools.extend(["upx", "peid", "detect-it-easy"])
            if any(keyword in description_lower for keyword in ["android", "apk", "mobile"]):
                suggested_tools.extend(["apktool", "jadx", "dex2jar"])
            if any(keyword in description_lower for keyword in [".net", "dotnet", "csharp"]):
                suggested_tools.extend(["dnspy", "ilspy"])
            if any(keyword in description_lower for keyword in ["java", "jar", "class"]):
                suggested_tools.extend(["jd-gui", "jadx"])
            if any(keyword in description_lower for keyword in ["windows", "exe", "dll"]):
                suggested_tools.extend(["ghidra", "ida", "x64dbg"])
            if any(keyword in description_lower for keyword in ["linux", "elf", "binary"]):
                suggested_tools.extend(["ghidra", "radare2", "gdb-peda"])

        elif category == "osint":
            if any(keyword in description_lower for keyword in ["username", "social", "media"]):
                suggested_tools.extend(["sherlock", "social-analyzer"])
            if any(keyword in description_lower for keyword in ["domain", "subdomain", "dns"]):
                suggested_tools.extend(["sublist3r", "amass", "dig"])
            if any(keyword in description_lower for keyword in ["email", "harvest", "contact"]):
                suggested_tools.append("theHarvester")
            if any(keyword in description_lower for keyword in ["ip", "port", "service"]):
                suggested_tools.extend(["shodan", "censys"])
            if any(keyword in description_lower for keyword in ["whois", "registration", "owner"]):
                suggested_tools.append("whois")

        elif category == "misc":
            if any(keyword in description_lower for keyword in ["qr", "barcode", "code"]):
                suggested_tools.append("qr-decoder")
            if any(keyword in description_lower for keyword in ["zip", "archive", "compressed"]):
                suggested_tools.extend(["zip", "7zip", "rar"])
            if any(keyword in description_lower for keyword in ["brainfuck", "bf", "esoteric"]):
                suggested_tools.append("brainfuck")
            if any(keyword in description_lower for keyword in ["whitespace", "ws"]):
                suggested_tools.append("whitespace")
            if any(keyword in description_lower for keyword in ["piet", "image", "program"]):
                suggested_tools.append("piet")

        # Remove duplicates while preserving order
        return list(dict.fromkeys(suggested_tools))

# ============================================================================
# ADVANCED CTF AUTOMATION AND CHALLENGE SOLVING (v8.0 ENHANCEMENT)
# ============================================================================

