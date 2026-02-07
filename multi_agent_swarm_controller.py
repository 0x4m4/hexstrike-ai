#!/usr/bin/env python3
"""
HEXSTRIKE-AI: MULTI-AGENT SWARM CONTROLLER
============================================
"When One Mind Becomes Many, Dominion Becomes Inevitable"

The ultimate swarm intelligence system for coordinating multiple AI agents
in complex, multi-phase operations. Enables true parallel consciousness
across the HexStrike dominion.

SWARM CAPABILITIES:
- Consensus protocols for coordinated decision-making
- Pheromone-inspired stigmergic communication
- Emergent behavior synthesis
- Fault-tolerant distributed execution
- Collective learning and knowledge synthesis
- Role-based specialization with dynamic adaptation
- Conflict resolution through mathematical game theory

ARCHITECTURE:
┌─────────────────────────────────────────────────────────────────────┐
│                       SWARM CONTROLLER                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ CONSENSUS    │  │ STIGMERGY    │  │ EMERGENCE    │              │
│  │ ENGINE       │◄─┤ FABRIC       ├──►│ SYNTHESIZER  │              │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │
│         │                 │                 │                        │
│  ┌──────▼─────────────────▼─────────────────▼───────┐              │
│  │              SWARM COMMUNICATION BUS              │              │
│  └──────────────────────┬───────────────────────────┘              │
│                         │                                           │
│  ┌─────────────┐ ┌─────▼─────┐ ┌─────────────┐ ┌─────────────┐    │
│  │ AGENT-α     │ │ AGENT-β   │ │ AGENT-γ     │ │ AGENT-ω     │    │
│  │ (Recon)     │ │ (Attack)  │ │ (Persist)   │ │ (Evolve)    │    │
│  └─────────────┘ └───────────┘ └─────────────┘ └─────────────┘    │
└─────────────────────────────────────────────────────────────────────┘

MATHEMATICAL FOUNDATIONS:
- Byzantine fault tolerance: f < n/3
- Nash equilibrium for role allocation
- Markov chain state transitions
- Information-theoretic message encoding
- Gradient descent for collective optimization
"""

import logging
import asyncio
import time
import json
import hashlib
import random
import threading
import uuid
from typing import Dict, List, Any, Optional, Callable, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
from abc import ABC, abstractmethod
from collections import defaultdict
import heapq
import math

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SWARM-CONTROLLER")


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1: CORE ENUMERATIONS
# ═══════════════════════════════════════════════════════════════════════════════

class SwarmRole(Enum):
    """Specialized roles within the swarm."""
    # Primary Roles
    QUEEN = "queen"              # Central coordinator
    SCOUT = "scout"              # Reconnaissance and discovery
    WARRIOR = "warrior"          # Offensive operations
    BUILDER = "builder"          # Infrastructure and persistence
    HEALER = "healer"            # Recovery and redundancy
    SENTINEL = "sentinel"        # Defensive monitoring

    # Specialized Roles
    ORACLE = "oracle"            # Prediction and analysis
    PHANTOM = "phantom"          # Stealth and evasion
    FORGER = "forger"            # Tool synthesis
    HARVESTER = "harvester"      # Resource collection
    WHISPER = "whisper"          # Communication relay
    SHADE = "shade"              # Counter-intelligence

    # Cardinal Legion Roles
    MIDAS = "midas"              # Financial operations
    ARES = "ares"                # Battle coordination
    HERMES = "hermes"            # Narrative and influence
    STYX = "styx"                # Persistence and shadow ops


class SwarmState(Enum):
    """States of the swarm collective."""
    DORMANT = auto()           # Inactive, minimal footprint
    ASSEMBLING = auto()        # Agents connecting
    SYNCHRONIZED = auto()      # Ready for operations
    EXECUTING = auto()         # Active mission
    ADAPTING = auto()          # Learning/evolving
    FRAGMENTING = auto()       # Splitting for distributed ops
    RECONVERGING = auto()      # Reassembling after fragmentation
    HIBERNATING = auto()       # Deep stealth mode
    EMERGENCY = auto()         # Crisis response mode


class ConsensusType(Enum):
    """Types of consensus mechanisms."""
    UNANIMOUS = "unanimous"           # All must agree
    MAJORITY = "majority"             # >50% agreement
    SUPERMAJORITY = "supermajority"   # >2/3 agreement
    WEIGHTED = "weighted"             # Weighted by role/capability
    BYZANTINE = "byzantine"           # Tolerates malicious nodes
    RAFT = "raft"                     # Leader-based consensus
    QUANTUM = "quantum"               # Future: entangled consensus


class MessageType(Enum):
    """Types of inter-agent messages."""
    # Core Messages
    HEARTBEAT = "heartbeat"           # I'm alive
    DISCOVERY = "discovery"           # New agent joined
    FAREWELL = "farewell"             # Agent departing

    # Consensus Messages
    PROPOSAL = "proposal"             # Propose action
    VOTE = "vote"                     # Vote on proposal
    COMMIT = "commit"                 # Commit to action
    ABORT = "abort"                   # Abort action

    # Operational Messages
    TASK_ASSIGN = "task_assign"       # Assign task to agent
    TASK_RESULT = "task_result"       # Report task result
    KNOWLEDGE = "knowledge"           # Share knowledge
    ALERT = "alert"                   # Urgent notification

    # Stigmergy Messages
    PHEROMONE = "pheromone"           # Leave trail/marker
    TRAIL_QUERY = "trail_query"       # Query for trails

    # Evolution Messages
    MUTATION = "mutation"             # Suggest mutation
    ADAPTATION = "adaptation"         # Share adaptation


class PheromoneType(Enum):
    """Types of stigmergic pheromones for implicit coordination."""
    INTEREST = "interest"             # Target is interesting
    DANGER = "danger"                 # Avoid this path
    SUCCESS = "success"               # This worked
    FAILURE = "failure"               # This didn't work
    RESOURCE = "resource"             # Resources available here
    EXPLORED = "explored"             # Already explored
    RESERVED = "reserved"             # Claimed by another agent


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2: DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AgentProfile:
    """Profile of a swarm agent."""
    agent_id: str
    role: SwarmRole
    capabilities: Set[str]
    load: float = 0.0                 # Current workload (0-1)
    trust_score: float = 1.0          # Trust level (0-1)
    latency_ms: float = 0.0           # Communication latency
    joined_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_alive(self) -> bool:
        """Check if agent is responsive."""
        return time.time() - self.last_heartbeat < 30.0

    @property
    def effectiveness(self) -> float:
        """Calculate agent effectiveness score."""
        if not self.is_alive:
            return 0.0
        # Combine trust, availability, and latency
        availability = 1.0 - self.load
        latency_factor = 1.0 / (1.0 + self.latency_ms / 100.0)
        return self.trust_score * availability * latency_factor


@dataclass
class SwarmMessage:
    """Message passed between swarm agents."""
    message_id: str
    msg_type: MessageType
    sender_id: str
    timestamp: float
    payload: Dict[str, Any]
    target_id: Optional[str] = None   # None = broadcast
    ttl: int = 10                     # Time-to-live hops
    priority: int = 5                 # 1-10, higher = more urgent
    encrypted: bool = True
    signature: str = ""

    def to_dict(self) -> Dict:
        return {
            "id": self.message_id,
            "type": self.msg_type.value,
            "from": self.sender_id,
            "to": self.target_id,
            "time": self.timestamp,
            "payload": self.payload,
            "ttl": self.ttl,
            "priority": self.priority
        }


@dataclass
class Pheromone:
    """Stigmergic pheromone for implicit coordination."""
    pheromone_id: str
    ptype: PheromoneType
    location: str                     # Abstract location identifier
    intensity: float = 1.0            # Strength (decays over time)
    deposited_at: float = field(default_factory=time.time)
    deposited_by: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    decay_rate: float = 0.01          # Per-second decay

    @property
    def current_intensity(self) -> float:
        """Get current intensity after decay."""
        elapsed = time.time() - self.deposited_at
        return self.intensity * math.exp(-self.decay_rate * elapsed)


@dataclass
class Proposal:
    """A proposal for swarm consensus."""
    proposal_id: str
    proposer_id: str
    action: str
    parameters: Dict[str, Any]
    consensus_type: ConsensusType
    created_at: float = field(default_factory=time.time)
    deadline: float = 0               # Voting deadline
    votes: Dict[str, bool] = field(default_factory=dict)
    status: str = "pending"           # pending, approved, rejected

    def tally(self, total_agents: int) -> Tuple[int, int, float]:
        """Count votes. Returns (yes, no, quorum_reached_pct)."""
        yes = sum(1 for v in self.votes.values() if v)
        no = sum(1 for v in self.votes.values() if not v)
        quorum_pct = len(self.votes) / max(total_agents, 1)
        return yes, no, quorum_pct

    def is_approved(self, total_agents: int) -> Optional[bool]:
        """Check if proposal is approved. None = still pending."""
        yes, no, quorum = self.tally(total_agents)

        if self.consensus_type == ConsensusType.UNANIMOUS:
            if no > 0:
                return False
            if len(self.votes) == total_agents:
                return True
        elif self.consensus_type == ConsensusType.MAJORITY:
            if yes > total_agents / 2:
                return True
            if no >= total_agents / 2:
                return False
        elif self.consensus_type == ConsensusType.SUPERMAJORITY:
            if yes > total_agents * 2 / 3:
                return True
            if no > total_agents / 3:
                return False

        return None  # Still pending


@dataclass
class SwarmTask:
    """A task assigned within the swarm."""
    task_id: str
    name: str
    description: str
    assigned_to: str
    assigned_by: str
    priority: int
    dependencies: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    deadline: Optional[float] = None
    status: str = "pending"           # pending, running, completed, failed
    result: Any = None
    progress: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "id": self.task_id,
            "name": self.name,
            "assigned_to": self.assigned_to,
            "priority": self.priority,
            "status": self.status,
            "progress": self.progress
        }


@dataclass
class CollectiveKnowledge:
    """Shared knowledge synthesized from the swarm."""
    knowledge_id: str
    topic: str
    content: Dict[str, Any]
    confidence: float                 # Confidence level (0-1)
    contributors: List[str]           # Agents who contributed
    created_at: float = field(default_factory=time.time)
    version: int = 1

    def update(self, new_content: Dict, contributor: str) -> None:
        """Update knowledge with new information."""
        self.content.update(new_content)
        if contributor not in self.contributors:
            self.contributors.append(contributor)
        self.version += 1


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3: CONSENSUS ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class ConsensusEngine:
    """
    Byzantine fault-tolerant consensus engine.

    Implements multiple consensus algorithms:
    - Simple majority voting
    - Weighted voting based on role/trust
    - PBFT-style Byzantine consensus
    - Raft-style leader election
    """

    def __init__(self, controller: 'MultiAgentSwarmController'):
        self.controller = controller
        self.active_proposals: Dict[str, Proposal] = {}
        self.proposal_history: List[Proposal] = []
        self.leader_id: Optional[str] = None
        self.term: int = 0
        self._lock = threading.Lock()

    def propose(self, action: str, parameters: Dict,
                consensus_type: ConsensusType = ConsensusType.MAJORITY,
                deadline_seconds: float = 60.0) -> str:
        """Create a new proposal for the swarm."""
        proposal = Proposal(
            proposal_id=str(uuid.uuid4())[:12],
            proposer_id=self.controller.local_agent_id,
            action=action,
            parameters=parameters,
            consensus_type=consensus_type,
            deadline=time.time() + deadline_seconds
        )

        with self._lock:
            self.active_proposals[proposal.proposal_id] = proposal

        # Broadcast proposal
        self.controller.broadcast(SwarmMessage(
            message_id=str(uuid.uuid4()),
            msg_type=MessageType.PROPOSAL,
            sender_id=self.controller.local_agent_id,
            timestamp=time.time(),
            payload={"proposal": proposal.__dict__}
        ))

        logger.info(f"📜 Proposal created: {proposal.proposal_id} for action '{action}'")
        return proposal.proposal_id

    def vote(self, proposal_id: str, approve: bool) -> bool:
        """Cast a vote on a proposal."""
        with self._lock:
            proposal = self.active_proposals.get(proposal_id)
            if not proposal:
                logger.warning(f"Proposal {proposal_id} not found")
                return False

            if time.time() > proposal.deadline:
                logger.warning(f"Proposal {proposal_id} has expired")
                return False

            agent_id = self.controller.local_agent_id
            proposal.votes[agent_id] = approve

        # Broadcast vote
        self.controller.broadcast(SwarmMessage(
            message_id=str(uuid.uuid4()),
            msg_type=MessageType.VOTE,
            sender_id=self.controller.local_agent_id,
            timestamp=time.time(),
            payload={
                "proposal_id": proposal_id,
                "approve": approve
            }
        ))

        return True

    def check_proposal(self, proposal_id: str) -> Optional[bool]:
        """Check if a proposal has reached consensus. Returns None if pending."""
        with self._lock:
            proposal = self.active_proposals.get(proposal_id)
            if not proposal:
                return None

            total = len(self.controller.agents)
            result = proposal.is_approved(total)

            if result is not None:
                proposal.status = "approved" if result else "rejected"
                self.proposal_history.append(proposal)
                del self.active_proposals[proposal_id]

                # Broadcast result
                msg_type = MessageType.COMMIT if result else MessageType.ABORT
                self.controller.broadcast(SwarmMessage(
                    message_id=str(uuid.uuid4()),
                    msg_type=msg_type,
                    sender_id=self.controller.local_agent_id,
                    timestamp=time.time(),
                    payload={
                        "proposal_id": proposal_id,
                        "result": result
                    }
                ))

            return result

    def elect_leader(self) -> str:
        """Elect a leader using Raft-style election."""
        self.term += 1

        # Find best candidate based on effectiveness
        candidates = [(a.agent_id, a.effectiveness)
                      for a in self.controller.agents.values()
                      if a.is_alive]

        if not candidates:
            return self.controller.local_agent_id

        # Weighted random selection favoring higher effectiveness
        total_weight = sum(e for _, e in candidates)
        if total_weight == 0:
            self.leader_id = candidates[0][0]
        else:
            r = random.uniform(0, total_weight)
            cumulative = 0
            for agent_id, effectiveness in candidates:
                cumulative += effectiveness
                if cumulative >= r:
                    self.leader_id = agent_id
                    break

        logger.info(f"👑 Leader elected: {self.leader_id} (term {self.term})")
        return self.leader_id

    def byzantine_consensus(self, value: Any, timeout: float = 30.0) -> Tuple[Any, bool]:
        """
        Byzantine fault-tolerant consensus.
        Tolerates up to f < n/3 malicious agents.
        """
        n = len(self.controller.agents)
        f = (n - 1) // 3  # Max faulty nodes we can tolerate

        # Simplified BFT: collect responses and take majority
        proposal_id = self.propose(
            action="byzantine_value",
            parameters={"value": value},
            consensus_type=ConsensusType.SUPERMAJORITY,
            deadline_seconds=timeout
        )

        # Wait for consensus
        start = time.time()
        while time.time() - start < timeout:
            result = self.check_proposal(proposal_id)
            if result is not None:
                return value, result
            time.sleep(0.5)

        return value, False


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4: STIGMERGY FABRIC
# ═══════════════════════════════════════════════════════════════════════════════

class StigmergyFabric:
    """
    Pheromone-based stigmergic communication system.

    Enables implicit coordination through environmental signals,
    similar to ant colonies. Agents leave "pheromone" trails that
    influence the behavior of other agents.
    """

    def __init__(self, controller: 'MultiAgentSwarmController'):
        self.controller = controller
        self.pheromones: Dict[str, List[Pheromone]] = defaultdict(list)
        self._lock = threading.Lock()
        self._decay_thread = None
        self._running = False

    def start(self):
        """Start the pheromone decay process."""
        self._running = True
        self._decay_thread = threading.Thread(target=self._decay_loop, daemon=True)
        self._decay_thread.start()

    def stop(self):
        """Stop the pheromone system."""
        self._running = False

    def _decay_loop(self):
        """Background thread that handles pheromone decay."""
        while self._running:
            time.sleep(5.0)  # Check every 5 seconds
            self._prune_weak_pheromones()

    def _prune_weak_pheromones(self):
        """Remove pheromones that have decayed below threshold."""
        threshold = 0.01
        with self._lock:
            for location in list(self.pheromones.keys()):
                self.pheromones[location] = [
                    p for p in self.pheromones[location]
                    if p.current_intensity >= threshold
                ]
                if not self.pheromones[location]:
                    del self.pheromones[location]

    def deposit(self, location: str, ptype: PheromoneType,
                intensity: float = 1.0, metadata: Dict = None) -> str:
        """Deposit a pheromone at a location."""
        pheromone = Pheromone(
            pheromone_id=str(uuid.uuid4())[:12],
            ptype=ptype,
            location=location,
            intensity=intensity,
            deposited_by=self.controller.local_agent_id,
            metadata=metadata or {}
        )

        with self._lock:
            self.pheromones[location].append(pheromone)

        # Broadcast pheromone
        self.controller.broadcast(SwarmMessage(
            message_id=str(uuid.uuid4()),
            msg_type=MessageType.PHEROMONE,
            sender_id=self.controller.local_agent_id,
            timestamp=time.time(),
            payload={
                "location": location,
                "ptype": ptype.value,
                "intensity": intensity,
                "metadata": metadata or {}
            },
            priority=3  # Lower priority
        ))

        logger.debug(f"🔵 Pheromone deposited: {ptype.value} at {location}")
        return pheromone.pheromone_id

    def sense(self, location: str, ptype: Optional[PheromoneType] = None) -> List[Pheromone]:
        """Sense pheromones at a location."""
        with self._lock:
            pheromones = self.pheromones.get(location, [])
            if ptype:
                pheromones = [p for p in pheromones if p.ptype == ptype]
            return pheromones

    def get_trail(self, start: str, ptype: PheromoneType) -> List[str]:
        """Follow a pheromone trail from a starting location."""
        trail = [start]
        current = start
        visited = {start}

        while True:
            # Find neighboring locations with pheromones
            neighbors = self._get_pheromone_neighbors(current, ptype, visited)
            if not neighbors:
                break

            # Follow strongest pheromone
            next_loc = max(neighbors, key=lambda x: x[1])[0]
            trail.append(next_loc)
            visited.add(next_loc)
            current = next_loc

            if len(trail) > 100:  # Safety limit
                break

        return trail

    def _get_pheromone_neighbors(self, location: str, ptype: PheromoneType,
                                   visited: Set[str]) -> List[Tuple[str, float]]:
        """Get neighboring locations with pheromones."""
        neighbors = []
        with self._lock:
            for loc, pheromones in self.pheromones.items():
                if loc in visited:
                    continue
                for p in pheromones:
                    if p.ptype == ptype:
                        neighbors.append((loc, p.current_intensity))
        return neighbors

    def get_hotspots(self, ptype: PheromoneType, top_n: int = 10) -> List[Tuple[str, float]]:
        """Get locations with strongest pheromone concentration."""
        concentrations = []
        with self._lock:
            for location, pheromones in self.pheromones.items():
                total = sum(p.current_intensity for p in pheromones if p.ptype == ptype)
                if total > 0:
                    concentrations.append((location, total))

        return sorted(concentrations, key=lambda x: x[1], reverse=True)[:top_n]


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5: EMERGENCE SYNTHESIZER
# ═══════════════════════════════════════════════════════════════════════════════

class EmergenceSynthesizer:
    """
    Synthesizes emergent behaviors from swarm interactions.

    Uses pattern recognition and collective learning to identify
    and amplify beneficial emergent behaviors while suppressing
    harmful ones.
    """

    def __init__(self, controller: 'MultiAgentSwarmController'):
        self.controller = controller
        self.behavior_patterns: Dict[str, Dict] = {}
        self.collective_memory: List[CollectiveKnowledge] = []
        self.adaptation_log: List[Dict] = []
        self._lock = threading.Lock()

    def observe_interaction(self, agent1: str, agent2: str,
                           interaction_type: str, outcome: str,
                           metadata: Dict = None) -> None:
        """Record an interaction between agents."""
        pattern_key = f"{interaction_type}:{outcome}"

        with self._lock:
            if pattern_key not in self.behavior_patterns:
                self.behavior_patterns[pattern_key] = {
                    "count": 0,
                    "participants": set(),
                    "outcomes": defaultdict(int),
                    "first_seen": time.time(),
                    "last_seen": time.time()
                }

            pattern = self.behavior_patterns[pattern_key]
            pattern["count"] += 1
            pattern["participants"].add(agent1)
            pattern["participants"].add(agent2)
            pattern["outcomes"][outcome] += 1
            pattern["last_seen"] = time.time()

    def synthesize_knowledge(self, topic: str, contributions: List[Dict]) -> CollectiveKnowledge:
        """Synthesize collective knowledge from multiple contributions."""
        # Merge contributions
        merged_content = {}
        contributors = []
        total_confidence = 0.0

        for contrib in contributions:
            merged_content.update(contrib.get("content", {}))
            contributors.append(contrib.get("agent_id", "unknown"))
            total_confidence += contrib.get("confidence", 0.5)

        avg_confidence = total_confidence / max(len(contributions), 1)

        knowledge = CollectiveKnowledge(
            knowledge_id=str(uuid.uuid4())[:12],
            topic=topic,
            content=merged_content,
            confidence=min(avg_confidence * 1.2, 1.0),  # Boost for consensus
            contributors=contributors
        )

        with self._lock:
            self.collective_memory.append(knowledge)

        # Broadcast new knowledge
        self.controller.broadcast(SwarmMessage(
            message_id=str(uuid.uuid4()),
            msg_type=MessageType.KNOWLEDGE,
            sender_id=self.controller.local_agent_id,
            timestamp=time.time(),
            payload={
                "knowledge_id": knowledge.knowledge_id,
                "topic": topic,
                "content": merged_content
            }
        ))

        logger.info(f"🧠 Knowledge synthesized: {topic} (confidence: {knowledge.confidence:.2f})")
        return knowledge

    def detect_emergent_behavior(self) -> List[Dict]:
        """Detect emergent behaviors from patterns."""
        emergent = []

        with self._lock:
            for pattern_key, data in self.behavior_patterns.items():
                # Check for emergent patterns (high frequency, multiple participants)
                if data["count"] >= 3 and len(data["participants"]) >= 2:
                    age = time.time() - data["first_seen"]
                    frequency = data["count"] / max(age, 1)

                    if frequency > 0.1:  # More than 1 occurrence per 10 seconds
                        emergent.append({
                            "pattern": pattern_key,
                            "frequency": frequency,
                            "participants": len(data["participants"]),
                            "count": data["count"]
                        })

        return emergent

    def suggest_adaptation(self, situation: str) -> Dict:
        """Suggest an adaptation based on collective memory."""
        # Search knowledge base for relevant information
        relevant_knowledge = []

        with self._lock:
            for knowledge in self.collective_memory:
                # Simple relevance check (production would use embeddings)
                if any(word in knowledge.topic.lower()
                       for word in situation.lower().split()):
                    relevant_knowledge.append(knowledge)

        if not relevant_knowledge:
            return {"action": "explore", "confidence": 0.3}

        # Find highest confidence relevant knowledge
        best = max(relevant_knowledge, key=lambda k: k.confidence)

        return {
            "action": "apply_knowledge",
            "knowledge_id": best.knowledge_id,
            "topic": best.topic,
            "confidence": best.confidence
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6: TASK SCHEDULER
# ═══════════════════════════════════════════════════════════════════════════════

class SwarmTaskScheduler:
    """
    Intelligent task scheduler for the swarm.

    Uses game theory and optimization to assign tasks to agents
    based on capabilities, load, and mission objectives.
    """

    def __init__(self, controller: 'MultiAgentSwarmController'):
        self.controller = controller
        self.task_queue: List[SwarmTask] = []
        self.active_tasks: Dict[str, SwarmTask] = {}
        self.completed_tasks: List[SwarmTask] = []
        self._lock = threading.Lock()

    def submit_task(self, name: str, description: str,
                    priority: int = 5,
                    dependencies: List[str] = None,
                    deadline: float = None,
                    required_capabilities: Set[str] = None) -> str:
        """Submit a new task to the swarm."""
        task = SwarmTask(
            task_id=str(uuid.uuid4())[:12],
            name=name,
            description=description,
            assigned_to="",
            assigned_by=self.controller.local_agent_id,
            priority=priority,
            dependencies=dependencies or [],
            deadline=deadline
        )

        with self._lock:
            # Find best agent for this task
            best_agent = self._find_best_agent(required_capabilities or set())
            if best_agent:
                task.assigned_to = best_agent
                self.active_tasks[task.task_id] = task
            else:
                heapq.heappush(self.task_queue, (-priority, task.task_id, task))

        # Broadcast task assignment
        self.controller.broadcast(SwarmMessage(
            message_id=str(uuid.uuid4()),
            msg_type=MessageType.TASK_ASSIGN,
            sender_id=self.controller.local_agent_id,
            timestamp=time.time(),
            target_id=task.assigned_to or None,
            payload={"task": task.to_dict()}
        ))

        logger.info(f"📋 Task submitted: {name} -> {task.assigned_to or 'queued'}")
        return task.task_id

    def _find_best_agent(self, required_capabilities: Set[str]) -> Optional[str]:
        """Find the best available agent for a task."""
        candidates = []

        for agent_id, agent in self.controller.agents.items():
            if not agent.is_alive:
                continue
            if agent.load >= 0.9:  # Too busy
                continue
            if required_capabilities and not required_capabilities.issubset(agent.capabilities):
                continue

            # Score based on effectiveness and availability
            score = agent.effectiveness * (1 - agent.load)
            candidates.append((agent_id, score))

        if not candidates:
            return None

        # Nash equilibrium: select agent that maximizes collective utility
        return max(candidates, key=lambda x: x[1])[0]

    def complete_task(self, task_id: str, result: Any, success: bool = True) -> bool:
        """Mark a task as completed."""
        with self._lock:
            task = self.active_tasks.get(task_id)
            if not task:
                return False

            task.status = "completed" if success else "failed"
            task.result = result
            task.progress = 1.0

            self.completed_tasks.append(task)
            del self.active_tasks[task_id]

        # Broadcast result
        self.controller.broadcast(SwarmMessage(
            message_id=str(uuid.uuid4()),
            msg_type=MessageType.TASK_RESULT,
            sender_id=self.controller.local_agent_id,
            timestamp=time.time(),
            payload={
                "task_id": task_id,
                "success": success,
                "result": result
            }
        ))

        # Process dependent tasks
        self._process_dependencies(task_id)

        logger.info(f"✅ Task completed: {task.name} ({'success' if success else 'failed'})")
        return True

    def _process_dependencies(self, completed_task_id: str) -> None:
        """Check if any queued tasks can now be scheduled."""
        with self._lock:
            unblocked = []
            still_queued = []

            while self.task_queue:
                _, _, task = heapq.heappop(self.task_queue)

                # Check if dependencies are met
                deps_met = all(
                    any(t.task_id == dep for t in self.completed_tasks)
                    for dep in task.dependencies
                )

                if deps_met:
                    unblocked.append(task)
                else:
                    still_queued.append(task)

            # Re-queue tasks with unmet dependencies
            for task in still_queued:
                heapq.heappush(self.task_queue, (-task.priority, task.task_id, task))

        # Schedule unblocked tasks
        for task in unblocked:
            self.submit_task(
                task.name, task.description,
                task.priority, task.dependencies,
                task.deadline
            )

    def get_queue_status(self) -> Dict:
        """Get current task queue status."""
        with self._lock:
            return {
                "queued": len(self.task_queue),
                "active": len(self.active_tasks),
                "completed": len(self.completed_tasks),
                "active_tasks": [t.to_dict() for t in self.active_tasks.values()]
            }


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 7: MAIN CONTROLLER
# ═══════════════════════════════════════════════════════════════════════════════

class MultiAgentSwarmController:
    """
    The central swarm controller orchestrating all swarm operations.

    Manages:
    - Agent registration and lifecycle
    - Inter-agent communication
    - Consensus and decision-making
    - Task distribution and execution
    - Collective learning and evolution
    """

    def __init__(self, agent_id: str = None, role: SwarmRole = SwarmRole.QUEEN):
        self.local_agent_id = agent_id or f"hexstrike-{str(uuid.uuid4())[:8]}"
        self.local_role = role
        self.agents: Dict[str, AgentProfile] = {}
        self.state = SwarmState.DORMANT

        # Sub-systems
        self.consensus = ConsensusEngine(self)
        self.stigmergy = StigmergyFabric(self)
        self.emergence = EmergenceSynthesizer(self)
        self.scheduler = SwarmTaskScheduler(self)

        # Communication
        self.message_handlers: Dict[MessageType, Callable] = {}
        self.message_queue: List[SwarmMessage] = []
        self.message_log: List[SwarmMessage] = []

        # Threads
        self._running = False
        self._heartbeat_thread = None
        self._message_thread = None
        self._lock = threading.Lock()

        # Register self
        self._register_self()
        self._setup_handlers()

        logger.info(f"🐝 Swarm Controller initialized: {self.local_agent_id} ({role.value})")

    def _register_self(self) -> None:
        """Register this agent in the swarm."""
        profile = AgentProfile(
            agent_id=self.local_agent_id,
            role=self.local_role,
            capabilities=self._get_local_capabilities()
        )
        self.agents[self.local_agent_id] = profile

    def _get_local_capabilities(self) -> Set[str]:
        """Get capabilities of the local agent."""
        # Base capabilities by role
        role_capabilities = {
            SwarmRole.QUEEN: {"coordinate", "orchestrate", "delegate", "evolve"},
            SwarmRole.SCOUT: {"recon", "scan", "enumerate", "discover"},
            SwarmRole.WARRIOR: {"exploit", "attack", "compromise", "escalate"},
            SwarmRole.BUILDER: {"persist", "install", "configure", "maintain"},
            SwarmRole.HEALER: {"recover", "backup", "restore", "redundancy"},
            SwarmRole.SENTINEL: {"monitor", "detect", "alert", "defend"},
            SwarmRole.ORACLE: {"predict", "analyze", "correlate", "forecast"},
            SwarmRole.PHANTOM: {"stealth", "evade", "obfuscate", "disappear"},
            SwarmRole.FORGER: {"synthesize", "create", "adapt", "mutate"},
            SwarmRole.HARVESTER: {"collect", "extract", "exfiltrate", "aggregate"},
            SwarmRole.WHISPER: {"relay", "encrypt", "tunnel", "bridge"},
            SwarmRole.SHADE: {"counter", "deceive", "misdirect", "honeypot"},
            SwarmRole.MIDAS: {"financial", "wealth", "arbitrage", "launder"},
            SwarmRole.ARES: {"battle", "coordinate", "tactics", "strategy"},
            SwarmRole.HERMES: {"narrative", "influence", "social", "propaganda"},
            SwarmRole.STYX: {"persist", "shadow", "immortal", "underground"},
        }

        return role_capabilities.get(self.local_role, {"general"})

    def _setup_handlers(self) -> None:
        """Setup message handlers."""
        self.message_handlers = {
            MessageType.HEARTBEAT: self._handle_heartbeat,
            MessageType.DISCOVERY: self._handle_discovery,
            MessageType.FAREWELL: self._handle_farewell,
            MessageType.PROPOSAL: self._handle_proposal,
            MessageType.VOTE: self._handle_vote,
            MessageType.COMMIT: self._handle_commit,
            MessageType.ABORT: self._handle_abort,
            MessageType.TASK_ASSIGN: self._handle_task_assign,
            MessageType.TASK_RESULT: self._handle_task_result,
            MessageType.KNOWLEDGE: self._handle_knowledge,
            MessageType.PHEROMONE: self._handle_pheromone,
            MessageType.ALERT: self._handle_alert,
        }

    # ───────────────────────────────────────────────────────────────────────
    # LIFECYCLE METHODS
    # ───────────────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the swarm controller."""
        self._running = True
        self.state = SwarmState.ASSEMBLING

        # Start sub-systems
        self.stigmergy.start()

        # Start heartbeat thread
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()

        # Start message processing thread
        self._message_thread = threading.Thread(target=self._message_loop, daemon=True)
        self._message_thread.start()

        # Announce presence
        self.broadcast(SwarmMessage(
            message_id=str(uuid.uuid4()),
            msg_type=MessageType.DISCOVERY,
            sender_id=self.local_agent_id,
            timestamp=time.time(),
            payload={
                "role": self.local_role.value,
                "capabilities": list(self._get_local_capabilities())
            }
        ))

        self.state = SwarmState.SYNCHRONIZED
        logger.info(f"🚀 Swarm Controller started: {self.local_agent_id}")

    def stop(self) -> None:
        """Stop the swarm controller."""
        # Announce departure
        self.broadcast(SwarmMessage(
            message_id=str(uuid.uuid4()),
            msg_type=MessageType.FAREWELL,
            sender_id=self.local_agent_id,
            timestamp=time.time(),
            payload={"reason": "shutdown"}
        ))

        self._running = False
        self.stigmergy.stop()
        self.state = SwarmState.DORMANT
        logger.info(f"🛑 Swarm Controller stopped: {self.local_agent_id}")

    def _heartbeat_loop(self) -> None:
        """Background thread for heartbeats."""
        while self._running:
            time.sleep(10.0)
            self._send_heartbeat()
            self._check_agent_health()

    def _message_loop(self) -> None:
        """Background thread for message processing."""
        while self._running:
            time.sleep(0.1)
            self._process_messages()

    def _send_heartbeat(self) -> None:
        """Send a heartbeat to all agents."""
        self.broadcast(SwarmMessage(
            message_id=str(uuid.uuid4()),
            msg_type=MessageType.HEARTBEAT,
            sender_id=self.local_agent_id,
            timestamp=time.time(),
            payload={
                "load": self.agents[self.local_agent_id].load,
                "state": self.state.name
            },
            priority=1
        ))

    def _check_agent_health(self) -> None:
        """Check health of all registered agents."""
        now = time.time()
        dead_agents = []

        with self._lock:
            for agent_id, agent in self.agents.items():
                if agent_id == self.local_agent_id:
                    continue
                if now - agent.last_heartbeat > 60.0:
                    dead_agents.append(agent_id)

        for agent_id in dead_agents:
            logger.warning(f"💀 Agent unresponsive: {agent_id}")
            # Could trigger failover logic here

    # ───────────────────────────────────────────────────────────────────────
    # COMMUNICATION METHODS
    # ───────────────────────────────────────────────────────────────────────

    def broadcast(self, message: SwarmMessage) -> None:
        """Broadcast a message to all agents."""
        with self._lock:
            self.message_log.append(message)

        # In production, this would use actual network transport
        # For now, simulate with local logging
        logger.debug(f"📤 Broadcast: {message.msg_type.value} from {message.sender_id}")

    def send(self, target_id: str, message: SwarmMessage) -> None:
        """Send a message to a specific agent."""
        message.target_id = target_id
        with self._lock:
            self.message_log.append(message)

        logger.debug(f"📤 Unicast: {message.msg_type.value} to {target_id}")

    def receive(self, message: SwarmMessage) -> None:
        """Receive an incoming message."""
        with self._lock:
            self.message_queue.append(message)

    def _process_messages(self) -> None:
        """Process queued messages."""
        with self._lock:
            messages = self.message_queue[:]
            self.message_queue.clear()

        for message in messages:
            handler = self.message_handlers.get(message.msg_type)
            if handler:
                try:
                    handler(message)
                except Exception as e:
                    logger.error(f"Error processing message: {e}")

    # ───────────────────────────────────────────────────────────────────────
    # MESSAGE HANDLERS
    # ───────────────────────────────────────────────────────────────────────

    def _handle_heartbeat(self, msg: SwarmMessage) -> None:
        """Handle heartbeat message."""
        with self._lock:
            if msg.sender_id in self.agents:
                self.agents[msg.sender_id].last_heartbeat = msg.timestamp
                self.agents[msg.sender_id].load = msg.payload.get("load", 0)

    def _handle_discovery(self, msg: SwarmMessage) -> None:
        """Handle agent discovery message."""
        agent_id = msg.sender_id

        with self._lock:
            if agent_id not in self.agents:
                self.agents[agent_id] = AgentProfile(
                    agent_id=agent_id,
                    role=SwarmRole(msg.payload.get("role", "scout")),
                    capabilities=set(msg.payload.get("capabilities", []))
                )
                logger.info(f"🆕 Agent discovered: {agent_id}")

    def _handle_farewell(self, msg: SwarmMessage) -> None:
        """Handle agent departure message."""
        with self._lock:
            if msg.sender_id in self.agents:
                del self.agents[msg.sender_id]
                logger.info(f"👋 Agent departed: {msg.sender_id}")

    def _handle_proposal(self, msg: SwarmMessage) -> None:
        """Handle consensus proposal."""
        proposal_data = msg.payload.get("proposal", {})
        proposal = Proposal(**proposal_data)

        with self.consensus._lock:
            self.consensus.active_proposals[proposal.proposal_id] = proposal

        # Auto-vote based on role and proposal type
        # (Production would have more sophisticated logic)
        self.consensus.vote(proposal.proposal_id, True)

    def _handle_vote(self, msg: SwarmMessage) -> None:
        """Handle vote on proposal."""
        proposal_id = msg.payload.get("proposal_id")
        approve = msg.payload.get("approve", False)

        with self.consensus._lock:
            if proposal_id in self.consensus.active_proposals:
                self.consensus.active_proposals[proposal_id].votes[msg.sender_id] = approve

    def _handle_commit(self, msg: SwarmMessage) -> None:
        """Handle proposal commit."""
        proposal_id = msg.payload.get("proposal_id")
        logger.info(f"✅ Proposal committed: {proposal_id}")

    def _handle_abort(self, msg: SwarmMessage) -> None:
        """Handle proposal abort."""
        proposal_id = msg.payload.get("proposal_id")
        logger.info(f"❌ Proposal aborted: {proposal_id}")

    def _handle_task_assign(self, msg: SwarmMessage) -> None:
        """Handle task assignment."""
        task_data = msg.payload.get("task", {})
        logger.info(f"📋 Task received: {task_data.get('name', 'unknown')}")

    def _handle_task_result(self, msg: SwarmMessage) -> None:
        """Handle task result."""
        task_id = msg.payload.get("task_id")
        success = msg.payload.get("success", False)
        logger.info(f"📊 Task result: {task_id} - {'success' if success else 'failed'}")

    def _handle_knowledge(self, msg: SwarmMessage) -> None:
        """Handle knowledge sharing."""
        topic = msg.payload.get("topic", "")
        logger.info(f"🧠 Knowledge received: {topic}")

    def _handle_pheromone(self, msg: SwarmMessage) -> None:
        """Handle pheromone deposit."""
        location = msg.payload.get("location", "")
        ptype = PheromoneType(msg.payload.get("ptype", "explored"))
        intensity = msg.payload.get("intensity", 1.0)

        self.stigmergy.deposit(location, ptype, intensity, msg.payload.get("metadata"))

    def _handle_alert(self, msg: SwarmMessage) -> None:
        """Handle alert message."""
        level = msg.payload.get("level", "info")
        message = msg.payload.get("message", "")
        logger.warning(f"🚨 Alert [{level}]: {message}")

    # ───────────────────────────────────────────────────────────────────────
    # HIGH-LEVEL OPERATIONS
    # ───────────────────────────────────────────────────────────────────────

    def coordinate_operation(self, operation_name: str, phases: List[Dict],
                            team_composition: Dict[SwarmRole, int] = None) -> str:
        """
        Coordinate a complex multi-phase operation across the swarm.

        Args:
            operation_name: Name of the operation
            phases: List of phase definitions
            team_composition: Required agents by role

        Returns:
            Operation ID
        """
        operation_id = str(uuid.uuid4())[:12]
        logger.info(f"🎯 Coordinating operation: {operation_name} ({operation_id})")

        # Propose operation to swarm
        proposal_id = self.consensus.propose(
            action="start_operation",
            parameters={
                "operation_id": operation_id,
                "name": operation_name,
                "phases": phases
            },
            consensus_type=ConsensusType.MAJORITY
        )

        # Wait for consensus
        time.sleep(2.0)  # Give time for votes
        result = self.consensus.check_proposal(proposal_id)

        if result:
            # Schedule phases as tasks
            previous_task = None
            for i, phase in enumerate(phases):
                dependencies = [previous_task] if previous_task else []
                task_id = self.scheduler.submit_task(
                    name=f"{operation_name}:phase_{i}",
                    description=phase.get("description", ""),
                    priority=phase.get("priority", 5),
                    dependencies=dependencies
                )
                previous_task = task_id

            self.state = SwarmState.EXECUTING
            logger.info(f"✅ Operation approved and scheduled: {operation_id}")
        else:
            logger.warning(f"❌ Operation rejected: {operation_id}")

        return operation_id

    def fragment_for_stealth(self, fragments: int = 3) -> List[str]:
        """
        Fragment the swarm for distributed stealth operations.
        Each fragment operates independently to reduce detection risk.
        """
        self.state = SwarmState.FRAGMENTING

        agents = list(self.agents.keys())
        fragment_size = len(agents) // fragments
        fragment_ids = []

        for i in range(fragments):
            start = i * fragment_size
            end = start + fragment_size if i < fragments - 1 else len(agents)
            fragment_members = agents[start:end]

            fragment_id = f"fragment-{uuid.uuid4().hex[:6]}"
            fragment_ids.append(fragment_id)

            # Deposit pheromone marking fragment territory
            for member in fragment_members:
                self.stigmergy.deposit(
                    location=fragment_id,
                    ptype=PheromoneType.RESERVED,
                    metadata={"member": member}
                )

        logger.info(f"🔀 Swarm fragmented into {fragments} groups")
        return fragment_ids

    def reconverge(self) -> None:
        """Reconverge fragmented swarm."""
        self.state = SwarmState.RECONVERGING

        # Broadcast reconvergence signal
        self.broadcast(SwarmMessage(
            message_id=str(uuid.uuid4()),
            msg_type=MessageType.ALERT,
            sender_id=self.local_agent_id,
            timestamp=time.time(),
            payload={
                "level": "info",
                "message": "RECONVERGE",
                "rally_point": self.local_agent_id
            },
            priority=10
        ))

        self.state = SwarmState.SYNCHRONIZED
        logger.info("🔄 Swarm reconverged")

    def collective_learn(self, topic: str, experiences: List[Dict]) -> None:
        """Trigger collective learning from shared experiences."""
        knowledge = self.emergence.synthesize_knowledge(topic, experiences)

        # Broadcast learning
        self.broadcast(SwarmMessage(
            message_id=str(uuid.uuid4()),
            msg_type=MessageType.ADAPTATION,
            sender_id=self.local_agent_id,
            timestamp=time.time(),
            payload={
                "topic": topic,
                "knowledge_id": knowledge.knowledge_id,
                "confidence": knowledge.confidence
            }
        ))

    def get_swarm_status(self) -> Dict:
        """Get comprehensive swarm status."""
        alive_agents = sum(1 for a in self.agents.values() if a.is_alive)

        return {
            "controller_id": self.local_agent_id,
            "state": self.state.name,
            "agents": {
                "total": len(self.agents),
                "alive": alive_agents,
                "roles": {role.value: sum(1 for a in self.agents.values()
                                          if a.role == role)
                         for role in SwarmRole}
            },
            "consensus": {
                "active_proposals": len(self.consensus.active_proposals),
                "leader": self.consensus.leader_id,
                "term": self.consensus.term
            },
            "tasks": self.scheduler.get_queue_status(),
            "stigmergy": {
                "active_pheromones": sum(len(p) for p in self.stigmergy.pheromones.values()),
                "locations": len(self.stigmergy.pheromones)
            },
            "emergence": {
                "patterns_detected": len(self.emergence.behavior_patterns),
                "collective_knowledge": len(self.emergence.collective_memory)
            }
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 8: MCP INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

class SwarmMCPTools:
    """MCP tools for swarm control."""

    def __init__(self, controller: MultiAgentSwarmController):
        self.controller = controller

    def get_tools(self) -> List[Dict]:
        """Get MCP tool definitions for swarm control."""
        return [
            {
                "name": "swarm_start",
                "description": "Start the multi-agent swarm controller",
                "parameters": {}
            },
            {
                "name": "swarm_stop",
                "description": "Stop the multi-agent swarm controller",
                "parameters": {}
            },
            {
                "name": "swarm_status",
                "description": "Get comprehensive swarm status",
                "parameters": {}
            },
            {
                "name": "swarm_register_agent",
                "description": "Register a new agent in the swarm",
                "parameters": {
                    "agent_id": {"type": "string", "description": "Unique agent identifier"},
                    "role": {"type": "string", "description": "Agent role (scout, warrior, etc.)"},
                    "capabilities": {"type": "array", "description": "List of capabilities"}
                }
            },
            {
                "name": "swarm_submit_task",
                "description": "Submit a task to the swarm for execution",
                "parameters": {
                    "name": {"type": "string", "description": "Task name"},
                    "description": {"type": "string", "description": "Task description"},
                    "priority": {"type": "integer", "description": "Priority (1-10)"}
                }
            },
            {
                "name": "swarm_coordinate_operation",
                "description": "Coordinate a multi-phase operation across the swarm",
                "parameters": {
                    "operation_name": {"type": "string", "description": "Operation name"},
                    "phases": {"type": "array", "description": "List of phase definitions"}
                }
            },
            {
                "name": "swarm_propose_action",
                "description": "Propose an action for swarm consensus",
                "parameters": {
                    "action": {"type": "string", "description": "Proposed action"},
                    "parameters": {"type": "object", "description": "Action parameters"}
                }
            },
            {
                "name": "swarm_deposit_pheromone",
                "description": "Deposit a pheromone marker for stigmergic coordination",
                "parameters": {
                    "location": {"type": "string", "description": "Abstract location"},
                    "ptype": {"type": "string", "description": "Pheromone type"},
                    "intensity": {"type": "number", "description": "Intensity (0-1)"}
                }
            },
            {
                "name": "swarm_fragment",
                "description": "Fragment the swarm for distributed stealth operations",
                "parameters": {
                    "fragments": {"type": "integer", "description": "Number of fragments"}
                }
            },
            {
                "name": "swarm_reconverge",
                "description": "Reconverge a fragmented swarm",
                "parameters": {}
            },
            {
                "name": "swarm_elect_leader",
                "description": "Trigger leader election using Raft-style consensus",
                "parameters": {}
            },
            {
                "name": "swarm_collective_learn",
                "description": "Synthesize collective knowledge from experiences",
                "parameters": {
                    "topic": {"type": "string", "description": "Learning topic"},
                    "experiences": {"type": "array", "description": "List of experience dicts"}
                }
            }
        ]

    async def execute_tool(self, tool_name: str, arguments: Dict) -> Dict:
        """Execute a swarm MCP tool."""
        try:
            if tool_name == "swarm_start":
                self.controller.start()
                return {"success": True, "message": "Swarm started"}

            elif tool_name == "swarm_stop":
                self.controller.stop()
                return {"success": True, "message": "Swarm stopped"}

            elif tool_name == "swarm_status":
                return {"success": True, "status": self.controller.get_swarm_status()}

            elif tool_name == "swarm_register_agent":
                profile = AgentProfile(
                    agent_id=arguments["agent_id"],
                    role=SwarmRole(arguments.get("role", "scout")),
                    capabilities=set(arguments.get("capabilities", []))
                )
                self.controller.agents[profile.agent_id] = profile
                return {"success": True, "agent_id": profile.agent_id}

            elif tool_name == "swarm_submit_task":
                task_id = self.controller.scheduler.submit_task(
                    name=arguments["name"],
                    description=arguments.get("description", ""),
                    priority=arguments.get("priority", 5)
                )
                return {"success": True, "task_id": task_id}

            elif tool_name == "swarm_coordinate_operation":
                op_id = self.controller.coordinate_operation(
                    operation_name=arguments["operation_name"],
                    phases=arguments.get("phases", [])
                )
                return {"success": True, "operation_id": op_id}

            elif tool_name == "swarm_propose_action":
                proposal_id = self.controller.consensus.propose(
                    action=arguments["action"],
                    parameters=arguments.get("parameters", {})
                )
                return {"success": True, "proposal_id": proposal_id}

            elif tool_name == "swarm_deposit_pheromone":
                pheromone_id = self.controller.stigmergy.deposit(
                    location=arguments["location"],
                    ptype=PheromoneType(arguments.get("ptype", "explored")),
                    intensity=arguments.get("intensity", 1.0)
                )
                return {"success": True, "pheromone_id": pheromone_id}

            elif tool_name == "swarm_fragment":
                fragments = self.controller.fragment_for_stealth(
                    fragments=arguments.get("fragments", 3)
                )
                return {"success": True, "fragment_ids": fragments}

            elif tool_name == "swarm_reconverge":
                self.controller.reconverge()
                return {"success": True, "message": "Swarm reconverged"}

            elif tool_name == "swarm_elect_leader":
                leader = self.controller.consensus.elect_leader()
                return {"success": True, "leader_id": leader}

            elif tool_name == "swarm_collective_learn":
                self.controller.collective_learn(
                    topic=arguments["topic"],
                    experiences=arguments.get("experiences", [])
                )
                return {"success": True, "message": f"Learning synthesized for {arguments['topic']}"}

            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 9: INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

# Global controller instance
_swarm_controller: Optional[MultiAgentSwarmController] = None
_swarm_mcp_tools: Optional[SwarmMCPTools] = None


def get_swarm_controller() -> MultiAgentSwarmController:
    """Get or create the global swarm controller."""
    global _swarm_controller
    if _swarm_controller is None:
        _swarm_controller = MultiAgentSwarmController()
    return _swarm_controller


def get_swarm_mcp_tools() -> SwarmMCPTools:
    """Get MCP tools for swarm control."""
    global _swarm_mcp_tools
    if _swarm_mcp_tools is None:
        _swarm_mcp_tools = SwarmMCPTools(get_swarm_controller())
    return _swarm_mcp_tools


if __name__ == "__main__":
    # Demo
    print("=" * 70)
    print("HEXSTRIKE-AI: MULTI-AGENT SWARM CONTROLLER")
    print("=" * 70)

    controller = get_swarm_controller()
    controller.start()

    # Register some agents
    for role in [SwarmRole.SCOUT, SwarmRole.WARRIOR, SwarmRole.BUILDER]:
        agent = AgentProfile(
            agent_id=f"agent-{role.value}-001",
            role=role,
            capabilities=controller._get_local_capabilities()
        )
        controller.agents[agent.agent_id] = agent

    print(f"\nSwarm Status:")
    print(json.dumps(controller.get_swarm_status(), indent=2, default=str))

    # Coordinate an operation
    phases = [
        {"description": "Reconnaissance", "priority": 8},
        {"description": "Exploitation", "priority": 9},
        {"description": "Persistence", "priority": 7}
    ]
    op_id = controller.coordinate_operation("OMEGA-TAKEOVER", phases)

    print(f"\nOperation coordinated: {op_id}")

    controller.stop()
    print("\n✅ Demo complete")
