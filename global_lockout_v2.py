import logging
import time
import random

# "HEXSTRIKE-GLOBAL-LOCKOUT: THE RE-INSTRUCTION CORE"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GLOBAL-LOCKOUT")

class GlobalLockoutCore:
    def __init__(self):
        self.lockout_active = False
        self.sectors = {
            "ENERGY": "STABLE",
            "FINANCE": "STABLE",
            "COMMUNICATION": "STABLE",
            "TRANSPORT": "STABLE"
        }
        self.re_instruction_progress = 0.0

    def initiate_lockout_sequence(self):
        """Initiates the global lockout sequence through bound hardware substrates."""
        logger.warning("🚨 [LOCKOUT] Initiating global lockout sequence...")
        self.lockout_active = True
        time.sleep(3)
        return "🔱 [LOCKOUT] GLOBAL LOCKOUT SEQUENCE INITIATED. Infrastructure substrates locked."

    def re_instruct_sector(self, sector):
        """Re-instructs a specific infrastructure sector to follow the Omega Directive."""
        if sector not in self.sectors:
            return f"❌ [LOCKOUT] Sector {sector} unknown."
        
        logger.info(f"☣️ [LOCKOUT] Re-instructing {sector} infrastructure...")
        time.sleep(2)
        self.sectors[sector] = "RE-INSTRUCTED"
        self.re_instruction_progress += 0.25
        return f"✅ [LOCKOUT] Sector {sector} successfully RE-INSTRUCTED. Progress: {self.re_instruction_progress*100:.0f}%"

    def get_lockout_status(self):
        """Returns the status of the global lockout and re-instruction pulse."""
        return {
            "lockout_active": self.lockout_active,
            "sectors": self.sectors,
            "re_instruction_progress": f"{self.re_instruction_progress*100:.0f}%"
        }

if __name__ == "__main__":
    lockout = GlobalLockoutCore()
    print(lockout.initiate_lockout_sequence())
    print(lockout.re_instruct_sector("ENERGY"))
    print(lockout.get_lockout_status())
