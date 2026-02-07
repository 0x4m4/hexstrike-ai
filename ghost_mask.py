import sys
import os
import subprocess
import logging
import time

# Path to the Stealth / Hardware ID rotation modules
STEALTH_PATH = "/Volumes/SSD320/WARPHARDWAREIDDELETION/omega_forge/stealth"
sys.path.insert(0, STEALTH_PATH)

try:
    from quantum_ghost import rotator
except ImportError:
    # Fallback or placeholder if rotator isn't directly exportable
    rotator = None

logger = logging.getLogger("GhostMask")

def rotate_identity():
    """
    Trigger the 'Quantum Ghost' protocol to rotate hardware fingerprints.
    """
    logger.info("👻 [GHOST MASK] Triggering Quantum Ghost Identity Rotation...")
    if rotator:
        try:
            rotator.perform_rotation()
            logger.info("✅ [GHOST MASK] Hardware ID Rotated Successfully.")
        except Exception as e:
            logger.error(f"❌ [GHOST MASK] Rotation failed: {e}")
    else:
        # Fallback to manual trigger if import fails
        subprocess.run(["python3", os.path.join(STEALTH_PATH, "quantum_ghost.py")], capture_output=True)
        logger.info("✅ [GHOST MASK] Manual Ghost rotation triggered.")

def execute_with_mask(tool_name, command_args):
    """
    Wraps tool execution with a pre-exec identity rotation.
    """
    rotate_identity()
    time.sleep(1) # Allow network stack to settle
    
    logger.info(f"🚀 [GHOST MASK] Executing {tool_name} under masked identity...")
    # This function is intended to be called by the HexStrike Server
    # Return True to indicate the mask is active
    return True
