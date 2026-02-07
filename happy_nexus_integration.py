import os
import json
import time
import base64
import logging
from typing import Dict, Any, Optional

# Attempt to import PyNaCl for E2EE
try:
    import nacl.utils
    import nacl.encoding
    import nacl.public
    NACL_AVAILABLE = True
except ImportError:
    NACL_AVAILABLE = False

logger = logging.getLogger("HappyNexus")

class HappyNexusBridge:
    """
    Sovereign Mobile Nexus - Integration bridge for the 'Happy' project.
    Enables E2E encrypted mobile control of the OMEGA core.
    """
    def __init__(self, server_app=None):
        self.app = server_app
        self.active_requests = {} # publicKey -> data
        self.sessions = {} # token -> session_data
        
        if NACL_AVAILABLE:
            self.keypair = nacl.public.PrivateKey.generate()
            self.public_key_b64 = self.keypair.public_key.encode(nacl.encoding.Base64Encoder).decode('utf-8')
        else:
            self.keypair = None
            self.public_key_b64 = "NACL_NOT_AVAILABLE"

        logger.warning(f"🔱 [HAPPY-NEXUS] Sovereign Mobile Nexus Initialized. E2EE: {NACL_AVAILABLE}")

    def handle_auth_request(self, public_key: str, device_info: str = "Unknown"):
        """Handles incoming bonding requests from the Happy app."""
        request_id = hashlib.sha256(public_key.encode()).hexdigest()[:8]
        self.active_requests[public_key] = {
            "id": request_id,
            "ts": time.time(),
            "status": "PENDING",
            "device_info": device_info
        }
        logger.warning(f"📱 [HAPPY-NEXUS] Incoming Bonding Request [{request_id}] from {public_key[:10]}...")
        return {"ok": True, "request_id": request_id}

    def approve_request(self, public_key: str):
        """Approves a pending bonding request and issues a session token."""
        if public_key in self.active_requests:
            token = base64.b64encode(os.urandom(32)).decode('utf-8')
            self.sessions[token] = {
                "pub_key": public_key,
                "approved_at": time.time(),
                "encryption": self._setup_session_encryption(public_key)
            }
            self.active_requests[public_key]['status'] = 'APPROVED'
            self.active_requests[pub_key]['token'] = token
            logger.warning(f"✅ [HAPPY-NEXUS] Bonding Approved for {public_key[:10]}. Token generated.")
            return {"success": True, "token": token}
        return {"success": False, "error": "Request not found"}

    def _setup_session_encryption(self, client_pub_key_b64: str):
        if not NACL_AVAILABLE:
            return None
        try:
            client_pub_key = nacl.public.PublicKey(client_pub_key_b64, encoder=nacl.encoding.Base64Encoder)
            return nacl.public.Box(self.keypair, client_pub_key)
        except Exception as e:
            logger.error(f"❌ [HAPPY-NEXUS] Failed to setup session encryption: {e}")
            return None

    def decrypt_command(self, token: str, encrypted_payload: str):
        """Decrypts an incoming command from the mobile app."""
        if token not in self.sessions:
            return None
        
        session = self.sessions[token]
        box = session.get("encryption")
        if not box:
            return None # Or handle non-encrypted if allowed (not recommended)

        try:
            encrypted_data = base64.b64decode(encrypted_payload)
            decrypted = box.decrypt(encrypted_data)
            return json.loads(decrypted.decode('utf-8'))
        except Exception as e:
            logger.error(f"❌ [HAPPY-NEXUS] Decryption failed: {e}")
            return None

    def generate_qr_code(self, server_url: str):
        """Generates a bonding QR code for the Happy app."""
        try:
            import qrcode
            from io import BytesIO
            
            qr = qrcode.QRCode(version=1, box_size=1, border=1)
            qr.add_data(server_url)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            return base64.b64encode(buffered.getvalue()).decode('utf-8')
        except Exception as e:
            logger.error(f"❌ [HAPPY-NEXUS] QR generation failed: {e}")
            return None

    def get_status(self):
        return {
            "active_requests": len(self.active_requests),
            "active_sessions": len(self.sessions),
            "e2ee_active": NACL_AVAILABLE,
            "nexus_id": self.public_key_b64[:16] if NACL_AVAILABLE else "DISABLED"
        }

import hashlib
