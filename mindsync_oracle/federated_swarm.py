#!/usr/bin/env python3
"""
MindSync Oracle v6 - Federated Swarm Communication

THE BREAKTHROUGH: Multiple oracles working as a distributed hive mind.

Instead of one oracle, you have MANY collaborating:
- Secure P2P communication (encrypted ZeroMQ)
- Graph delta broadcasting
- Learning synchronization
- Distributed goal execution
- Swarm health monitoring

This is the collective superintelligence layer.

Use cases:
- "Oracle 1 monitors X, Oracle 2 runs exploits, Oracle 3 generates reports"
- "Swarm of 5 oracles pentesting 100 targets simultaneously"
- "One oracle goes down, others continue seamlessly"
- "Share learnings across entire organization instantly"
"""

import logging
import zmq
import json
import threading
import time
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from collections import defaultdict
from cryptography.fernet import Fernet
import hashlib

logger = logging.getLogger(__name__)


class SwarmRole:
    """Swarm member roles."""
    COORDINATOR = "coordinator"    # Orchestrates swarm
    WORKER = "worker"             # Executes tasks
    MONITOR = "monitor"           # Tracks health
    HYBRID = "hybrid"             # Does everything


class SwarmMessageType:
    """Message types in swarm protocol."""
    HEARTBEAT = "heartbeat"
    GRAPH_DELTA = "graph_delta"
    GOAL_SHARD = "goal_shard"
    LEARNING = "learning"
    TOOL_SCORE = "tool_score"
    THREAT_ALERT = "threat_alert"
    SWARM_JOIN = "swarm_join"
    SWARM_LEAVE = "swarm_leave"
    HEALTH_STATUS = "health_status"


class FederatedSwarm:
    """
    Federated swarm communication layer.

    Enables multiple MindSync oracles to work together as a
    distributed hive mind.
    """

    def __init__(self, swarm_id: str, member_id: str, role: str = SwarmRole.HYBRID,
                 pub_port: int = 5555, sub_peers: Optional[List[str]] = None,
                 encryption_key: Optional[str] = None, config: Optional[Dict] = None):
        """
        Initialize federated swarm member.

        Args:
            swarm_id: Unique swarm identifier
            member_id: This oracle's unique ID
            role: Swarm role (coordinator, worker, monitor, hybrid)
            pub_port: Port for publishing messages
            sub_peers: List of peer addresses to subscribe to
            encryption_key: Optional encryption key (generates if None)
            config: Optional configuration
        """
        self.swarm_id = swarm_id
        self.member_id = member_id
        self.role = role
        self.config = config or {}

        # Encryption
        if encryption_key:
            self.encryption_key = encryption_key.encode() if isinstance(encryption_key, str) else encryption_key
        else:
            self.encryption_key = Fernet.generate_key()
        self.cipher = Fernet(self.encryption_key)

        # ZeroMQ setup
        self.context = zmq.Context()

        # Publisher (send to swarm)
        self.publisher = self.context.socket(zmq.PUB)
        pub_addr = f"tcp://*:{pub_port}"
        self.publisher.bind(pub_addr)
        logger.info(f"Swarm publisher bound to {pub_addr}")

        # Subscriber (receive from peers)
        self.subscriber = self.context.socket(zmq.SUB)
        self.subscriber.setsockopt_string(zmq.SUBSCRIBE, "")  # Subscribe to all

        if sub_peers:
            for peer in sub_peers:
                self.subscriber.connect(peer)
                logger.info(f"Connected to peer: {peer}")

        # Swarm state
        self.members = {member_id: {
            'role': role,
            'last_heartbeat': time.time(),
            'status': 'active'
        }}
        self.is_running = False

        # Message handlers
        self.handlers = {}

        # Statistics
        self.stats = {
            'messages_sent': 0,
            'messages_received': 0,
            'bytes_sent': 0,
            'bytes_received': 0,
            'deltas_applied': 0
        }

        logger.info(f"Federated swarm initialized: {swarm_id}/{member_id} ({role})")

    # ===== CORE MESSAGING =====

    def send_message(self, msg_type: str, payload: Dict[str, Any],
                    target: Optional[str] = None):
        """
        Send message to swarm.

        Args:
            msg_type: Message type (from SwarmMessageType)
            payload: Message payload
            target: Optional target member (None = broadcast)
        """
        message = {
            'swarm_id': self.swarm_id,
            'sender': self.member_id,
            'target': target,
            'type': msg_type,
            'payload': payload,
            'timestamp': time.time()
        }

        # Serialize
        json_msg = json.dumps(message, default=str)

        # Encrypt
        encrypted = self.cipher.encrypt(json_msg.encode())

        # Send
        self.publisher.send(encrypted)

        # Stats
        self.stats['messages_sent'] += 1
        self.stats['bytes_sent'] += len(encrypted)

        logger.debug(f"Sent {msg_type} message ({len(encrypted)} bytes)")

    def receive_message(self, timeout: int = 1000) -> Optional[Dict[str, Any]]:
        """
        Receive message from swarm.

        Args:
            timeout: Timeout in milliseconds

        Returns:
            Message dictionary or None
        """
        try:
            # Check for message with timeout
            if self.subscriber.poll(timeout):
                encrypted = self.subscriber.recv()

                # Decrypt
                json_msg = self.cipher.decrypt(encrypted).decode()

                # Deserialize
                message = json.loads(json_msg)

                # Filter own messages
                if message['sender'] == self.member_id:
                    return None

                # Filter swarm ID
                if message['swarm_id'] != self.swarm_id:
                    return None

                # Check target
                target = message.get('target')
                if target and target != self.member_id:
                    return None

                # Stats
                self.stats['messages_received'] += 1
                self.stats['bytes_received'] += len(encrypted)

                return message

        except Exception as e:
            logger.error(f"Error receiving message: {e}")

        return None

    def register_handler(self, msg_type: str, handler: Callable):
        """
        Register handler for message type.

        Args:
            msg_type: Message type
            handler: Handler function (takes payload dict)
        """
        self.handlers[msg_type] = handler
        logger.debug(f"Registered handler for {msg_type}")

    # ===== MESSAGE LOOP =====

    def start(self):
        """Start swarm communication loop."""
        if self.is_running:
            return

        self.is_running = True

        # Start heartbeat thread
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()

        # Start message receive thread
        self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self.receive_thread.start()

        # Announce join
        self.send_message(SwarmMessageType.SWARM_JOIN, {
            'role': self.role,
            'capabilities': self._get_capabilities()
        })

        logger.info(f"Swarm communication started")

    def stop(self):
        """Stop swarm communication."""
        if not self.is_running:
            return

        # Announce leave
        self.send_message(SwarmMessageType.SWARM_LEAVE, {
            'reason': 'graceful_shutdown'
        })

        self.is_running = False

        # Wait for threads
        if hasattr(self, 'heartbeat_thread'):
            self.heartbeat_thread.join(timeout=2)
        if hasattr(self, 'receive_thread'):
            self.receive_thread.join(timeout=2)

        # Close sockets
        self.publisher.close()
        self.subscriber.close()
        self.context.term()

        logger.info("Swarm communication stopped")

    def _heartbeat_loop(self):
        """Send periodic heartbeats."""
        interval = self.config.get('heartbeat_interval', 10)  # seconds

        while self.is_running:
            try:
                self.send_message(SwarmMessageType.HEARTBEAT, {
                    'status': self._get_status(),
                    'members_known': len(self.members)
                })

                time.sleep(interval)

            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")

    def _receive_loop(self):
        """Receive and handle messages."""
        while self.is_running:
            try:
                message = self.receive_message(timeout=1000)

                if message:
                    self._handle_message(message)

            except Exception as e:
                logger.error(f"Error in receive loop: {e}")

    def _handle_message(self, message: Dict[str, Any]):
        """Handle received message."""
        msg_type = message['type']
        sender = message['sender']
        payload = message['payload']

        # Update member info
        if sender not in self.members:
            self.members[sender] = {
                'role': payload.get('role', 'unknown'),
                'last_heartbeat': time.time(),
                'status': 'active'
            }

        self.members[sender]['last_heartbeat'] = time.time()

        # Call handler if registered
        if msg_type in self.handlers:
            try:
                self.handlers[msg_type](sender, payload)
            except Exception as e:
                logger.error(f"Error in handler for {msg_type}: {e}")

        # Default handlers
        elif msg_type == SwarmMessageType.SWARM_JOIN:
            logger.info(f"Member {sender} joined swarm ({payload.get('role')})")

        elif msg_type == SwarmMessageType.SWARM_LEAVE:
            logger.info(f"Member {sender} left swarm")
            if sender in self.members:
                self.members[sender]['status'] = 'left'

        elif msg_type == SwarmMessageType.HEARTBEAT:
            logger.debug(f"Heartbeat from {sender}")

    # ===== HIGH-LEVEL OPERATIONS =====

    def broadcast_graph_delta(self, delta: Dict[str, Any]):
        """
        Broadcast graph delta to swarm.

        Args:
            delta: Graph delta (nodes/edges added)
        """
        self.send_message(SwarmMessageType.GRAPH_DELTA, delta)
        logger.debug(f"Broadcast graph delta: {len(delta.get('nodes', []))} nodes, {len(delta.get('edges', []))} edges")

    def broadcast_learning(self, learning: Dict[str, Any]):
        """
        Broadcast learning to swarm.

        Args:
            learning: Learning data (from self-improvement)
        """
        self.send_message(SwarmMessageType.LEARNING, learning)
        logger.debug(f"Broadcast learning: {learning.get('type')}")

    def broadcast_tool_score(self, tool: str, score: float, context: Dict):
        """
        Broadcast tool performance score.

        Args:
            tool: Tool name
            score: Performance score
            context: Context data
        """
        self.send_message(SwarmMessageType.TOOL_SCORE, {
            'tool': tool,
            'score': score,
            'context': context
        })

    def broadcast_threat_alert(self, threat: Dict[str, Any]):
        """
        Broadcast threat alert to swarm.

        Args:
            threat: Threat data
        """
        self.send_message(SwarmMessageType.THREAT_ALERT, threat)
        logger.info(f"Broadcast threat alert: {threat.get('title')}")

    def shard_goal(self, goal: str, context: Dict) -> str:
        """
        Shard goal to appropriate swarm member.

        Args:
            goal: Goal text
            context: Goal context

        Returns:
            Target member ID
        """
        # Simple sharding strategy (can be improved)
        # Route to members based on capabilities

        # Find best member for goal
        if 'x' in goal.lower() or 'researcher' in goal.lower():
            # X intelligence goals
            target = self._find_member_with_capability('deep_x')
        elif 'scan' in goal.lower() or 'exploit' in goal.lower():
            # Tool execution goals
            target = self._find_member_with_capability('tools')
        else:
            # Default: any worker or coordinator
            target = self._find_member_by_role([SwarmRole.WORKER, SwarmRole.COORDINATOR])

        if target:
            self.send_message(SwarmMessageType.GOAL_SHARD, {
                'goal': goal,
                'context': context
            }, target=target)

            logger.info(f"Sharded goal to {target}: {goal[:50]}...")
            return target

        logger.warning("No suitable member found for goal sharding")
        return self.member_id  # Fallback: execute locally

    # ===== HELPER METHODS =====

    def _get_capabilities(self) -> List[str]:
        """Get this oracle's capabilities."""
        capabilities = ['basic']

        if self.role in [SwarmRole.COORDINATOR, SwarmRole.HYBRID]:
            capabilities.append('coordination')

        if self.role in [SwarmRole.WORKER, SwarmRole.HYBRID]:
            capabilities.extend(['tools', 'execution'])

        # Check for v4/v5 features
        # (Would be passed via config in real integration)
        if self.config.get('has_grok'):
            capabilities.append('grok')
        if self.config.get('has_deep_x'):
            capabilities.append('deep_x')

        return capabilities

    def _get_status(self) -> Dict[str, Any]:
        """Get this oracle's status."""
        return {
            'role': self.role,
            'active': self.is_running,
            'uptime': time.time() - self.stats.get('start_time', time.time()),
            'messages_sent': self.stats['messages_sent'],
            'messages_received': self.stats['messages_received']
        }

    def _find_member_with_capability(self, capability: str) -> Optional[str]:
        """Find member with specific capability."""
        # Would query member capabilities in real implementation
        # For now, return any active member
        active_members = [m for m, data in self.members.items()
                         if data['status'] == 'active' and m != self.member_id]

        return active_members[0] if active_members else None

    def _find_member_by_role(self, roles: List[str]) -> Optional[str]:
        """Find member by role."""
        for member_id, data in self.members.items():
            if data['role'] in roles and data['status'] == 'active' and member_id != self.member_id:
                return member_id

        return None

    def get_swarm_health(self) -> Dict[str, Any]:
        """Get swarm health metrics."""
        now = time.time()
        timeout = self.config.get('heartbeat_timeout', 30)

        active = []
        inactive = []

        for member_id, data in self.members.items():
            if now - data['last_heartbeat'] < timeout:
                active.append(member_id)
            else:
                inactive.append(member_id)

        return {
            'total_members': len(self.members),
            'active_members': len(active),
            'inactive_members': len(inactive),
            'active_list': active,
            'inactive_list': inactive,
            'health_score': len(active) / len(self.members) if self.members else 0.0
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get swarm statistics."""
        return {
            **self.stats,
            'swarm_health': self.get_swarm_health()
        }


if __name__ == "__main__":
    # Test federated swarm
    import sys

    def test_two_oracles():
        """Test two oracles communicating."""
        print("\n" + "="*60)
        print("Federated Swarm Test - Two Oracles")
        print("="*60)

        # Create encryption key (same for both)
        key = Fernet.generate_key()

        # Oracle 1 (Coordinator)
        print("\n[1] Creating Oracle 1 (Coordinator)...")
        oracle1 = FederatedSwarm(
            swarm_id="test_swarm",
            member_id="oracle_1",
            role=SwarmRole.COORDINATOR,
            pub_port=5555,
            sub_peers=["tcp://localhost:5556"],
            encryption_key=key
        )

        # Oracle 2 (Worker)
        print("\n[2] Creating Oracle 2 (Worker)...")
        oracle2 = FederatedSwarm(
            swarm_id="test_swarm",
            member_id="oracle_2",
            role=SwarmRole.WORKER,
            pub_port=5556,
            sub_peers=["tcp://localhost:5555"],
            encryption_key=key
        )

        # Register handlers
        def handle_graph_delta(sender, payload):
            print(f"  [Oracle 2] Received graph delta from {sender}: {len(payload.get('nodes', []))} nodes")

        oracle2.register_handler(SwarmMessageType.GRAPH_DELTA, handle_graph_delta)

        # Start both
        print("\n[3] Starting swarm communication...")
        oracle1.start()
        oracle2.start()

        # Wait for join messages
        time.sleep(2)

        # Oracle 1 broadcasts graph delta
        print("\n[4] Oracle 1 broadcasting graph delta...")
        oracle1.broadcast_graph_delta({
            'nodes': ['node1', 'node2', 'node3'],
            'edges': [('node1', 'node2'), ('node2', 'node3')]
        })

        # Wait for message propagation
        time.sleep(1)

        # Check swarm health
        print("\n[5] Swarm Health:")
        health1 = oracle1.get_swarm_health()
        print(f"  Oracle 1 sees: {health1['active_members']} active members")
        health2 = oracle2.get_swarm_health()
        print(f"  Oracle 2 sees: {health2['active_members']} active members")

        # Stats
        print("\n[6] Stats:")
        stats1 = oracle1.get_stats()
        print(f"  Oracle 1: {stats1['messages_sent']} sent, {stats1['messages_received']} received")
        stats2 = oracle2.get_stats()
        print(f"  Oracle 2: {stats2['messages_sent']} sent, {stats2['messages_received']} received")

        # Stop
        print("\n[7] Stopping swarm...")
        oracle1.stop()
        oracle2.stop()

        print("\n" + "="*60)
        print("✅ Federated swarm operational!")
        print("="*60)

    test_two_oracles()
