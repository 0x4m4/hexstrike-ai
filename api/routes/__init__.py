"""
API Routes Module
Organized Flask blueprints for HexStrike API endpoints
"""

from flask import Blueprint

# Import blueprints
from .files import files_bp
from .visual import visual_bp
from .error_handling import error_handling_bp
from .intelligence import intelligence_bp
from .processes import processes_bp
from .bugbounty import bugbounty_bp
from .ctf import ctf_bp
from .vuln_intel import vuln_intel_bp
from .core import core_bp
from .ai import ai_bp
from .python_env import python_env_bp
from .process_workflows import process_workflows_bp
from .tools_cloud import tools_cloud_bp
from .tools_web import tools_web_bp
from .tools_network import tools_network_bp
from .tools_exploit import tools_exploit_bp
from .tools_binary import tools_binary_bp

# List of all blueprints to register
__all__ = [
    'files_bp', 'visual_bp', 'error_handling_bp', 'intelligence_bp',
    'processes_bp', 'bugbounty_bp', 'ctf_bp', 'vuln_intel_bp',
    'core_bp', 'ai_bp', 'python_env_bp', 'process_workflows_bp',
    'tools_cloud_bp', 'tools_web_bp', 'tools_network_bp',
    'tools_exploit_bp', 'tools_binary_bp'
]
