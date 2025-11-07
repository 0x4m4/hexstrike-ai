#!/usr/bin/env python3
"""
MindSync Oracle - Demo Script

Demonstrates the key capabilities:
1. Persistent memory across sessions
2. Goal-directed autonomy
3. Multi-modal input
4. Proactive intelligence
"""

import asyncio
import logging
from pathlib import Path

from storage.memory_manager import MemoryManager
from interfaces.input_processor import MultiModalInputProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def demo_persistent_memory():
    """Demo 1: Persistent Memory"""
    print("\n" + "="*60)
    print("DEMO 1: Persistent Memory")
    print("="*60)

    memory = MemoryManager("demo_memory.db")

    # Session 1: Store patterns
    print("\n[Session 1] Storing user patterns...")

    pattern_id = memory.store_pattern(
        "tool_preference",
        {
            "tool": "nmap",
            "args": "-sV -sC",
            "reason": "User always uses version detection and default scripts"
        },
        confidence=0.85
    )
    print(f"✅ Stored pattern: {pattern_id}")

    # Session 1: Create a goal
    print("\n[Session 1] Creating goal...")
    goal_id = memory.create_goal(
        "Research CVE-2024-1234 and prepare exploit analysis",
        priority="high",
        sub_tasks=[
            "Find CVE details in NVD database",
            "Locate public exploit code",
            "Test exploit in lab environment",
            "Document findings"
        ]
    )
    print(f"✅ Created goal: {goal_id}")

    # Session 1: Store conversation
    memory.store_conversation(
        "I'm pentesting example.com, WordPress 6.2",
        "I've noted this. Based on your history, you usually start with subdomain enum. Shall I begin?"
    )

    # Session 2: Retrieve everything (simulating new session)
    print("\n[Session 2] Retrieving context (simulating new session)...")
    context = memory.get_context_summary()

    print(f"\n📊 Context Summary:")
    print(f"  - Patterns learned: {len(context['patterns'])}")
    print(f"  - Active goals: {len(context['active_goals'])}")
    print(f"  - Recent conversations: {len(context['recent_conversations'])}")

    if context['patterns']:
        print(f"\n🧠 Learned Pattern:")
        pattern = context['patterns'][0]
        print(f"  Type: {pattern['pattern_type']}")
        print(f"  Data: {pattern['pattern_data']}")
        print(f"  Confidence: {pattern['confidence']*100:.0f}%")

    if context['active_goals']:
        print(f"\n🎯 Active Goal:")
        goal = context['active_goals'][0]
        print(f"  Goal: {goal['goal_text']}")
        print(f"  Priority: {goal['priority']}")
        print(f"  Progress: {goal['progress']*100:.0f}%")
        print(f"  Sub-tasks: {len(goal['sub_tasks'])}")

    print("\n✅ Memory persists across sessions!")


async def demo_goal_autonomy():
    """Demo 2: Goal-Directed Autonomy"""
    print("\n" + "="*60)
    print("DEMO 2: Goal-Directed Autonomy")
    print("="*60)

    memory = MemoryManager("demo_memory.db")

    # Create a goal
    print("\n📝 Creating autonomous goal...")
    goal_id = memory.create_goal(
        "Complete comprehensive security assessment of target.com",
        priority="high",
        sub_tasks=[
            "Subdomain enumeration",
            "Port scanning",
            "Service version detection",
            "Vulnerability scanning",
            "Report generation"
        ]
    )

    # Simulate autonomous progress
    print(f"\n🤖 Goal {goal_id} created - autonomous engine would now:")
    print("  1. Break down goal into executable tasks")
    print("  2. Execute each task using available tools")
    print("  3. Update progress automatically")
    print("  4. Surface results when complete")

    # Simulate progress updates
    tasks = ["Subdomain enumeration", "Port scanning", "Service detection",
             "Vulnerability scan", "Report generation"]

    for i, task in enumerate(tasks):
        progress = (i + 1) / len(tasks)
        memory.update_goal_progress(goal_id, progress)
        print(f"\n  ⏳ [{int(progress*100)}%] Completed: {task}")
        await asyncio.sleep(0.5)

    # Mark complete
    memory.update_goal_progress(goal_id, 1.0, status="completed")
    print(f"\n  ✅ Goal {goal_id} completed autonomously!")

    # Get final status
    goals = memory.get_active_goals()
    print(f"\n📊 Active goals remaining: {len(goals)}")


async def demo_multimodal_input():
    """Demo 3: Multi-Modal Input"""
    print("\n" + "="*60)
    print("DEMO 3: Multi-Modal Input Processing")
    print("="*60)

    processor = MultiModalInputProcessor()

    # Text input
    print("\n📝 Processing text input...")
    text_event = processor.process_text(
        "I need to scan example.com for vulnerabilities",
        metadata={"source": "cli"}
    )
    print(f"  Type: {text_event.input_type}")
    print(f"  Content: {text_event.content[:60]}...")

    # File input
    print("\n📄 Processing file input...")
    try:
        # Create a test file
        Path("test_target_list.txt").write_text("example.com\ntest.com\ntarget.org")

        file_event = processor.process_file("test_target_list.txt")
        print(f"  Type: {file_event.input_type}")
        print(f"  File: {file_event.metadata['file_name']}")
        print(f"  Size: {file_event.metadata['file_size']} bytes")

        # Cleanup
        Path("test_target_list.txt").unlink()
    except Exception as e:
        print(f"  (Skipped: {e})")

    # Screen context input
    print("\n🖥️  Processing screen context...")
    screen_event = processor.process_screen_context({
        "active_window": "Terminal - nmap scan",
        "active_file": "/home/user/pentests/example.com/recon.txt",
        "clipboard": "192.168.1.1-254",
        "recent_commands": ["nmap -sV", "gobuster dir", "nuclei"]
    })
    print(f"  Type: {screen_event.input_type}")
    print(f"  Context captured: {len(screen_event.raw_data)} fields")

    # Structured data input
    print("\n📊 Processing structured data...")
    structured_event = processor.process_structured_data({
        "scan_results": {
            "target": "example.com",
            "open_ports": [80, 443, 8080],
            "services": {
                "80": "nginx 1.18.0",
                "443": "nginx 1.18.0",
                "8080": "Apache Tomcat 9.0"
            }
        }
    })
    print(f"  Type: {structured_event.input_type}")
    print(f"  Format: {structured_event.metadata['data_format']}")

    print("\n✅ All input modalities supported!")


async def demo_pattern_learning():
    """Demo 4: Pattern Learning"""
    print("\n" + "="*60)
    print("DEMO 4: Pattern Learning & Recognition")
    print("="*60)

    memory = MemoryManager("demo_memory.db")

    # Simulate user behavior over time
    print("\n🧠 Simulating user behavior patterns...")

    behaviors = [
        ("tool_preference", {"tool": "nmap", "flags": "-sV -sC"}, 0.7),
        ("tool_preference", {"tool": "gobuster", "wordlist": "common.txt"}, 0.6),
        ("workflow", {"step": "reconnaissance", "starts_with": "subdomain_enum"}, 0.8),
        ("workflow", {"step": "scanning", "preferred_order": ["nmap", "nuclei"]}, 0.75),
        ("blind_spot", {"area": "API_endpoints", "often_missed": True}, 0.65),
    ]

    for pattern_type, data, confidence in behaviors:
        pattern_id = memory.store_pattern(pattern_type, data, confidence)
        print(f"  ✅ Learned: {pattern_type} - {data}")

    # Retrieve and display patterns
    print("\n📊 Learned Patterns Summary:")

    all_patterns = memory.get_patterns(min_confidence=0.5)

    tool_patterns = [p for p in all_patterns if p['pattern_type'] == 'tool_preference']
    print(f"\n  Tool Preferences ({len(tool_patterns)}):")
    for p in tool_patterns:
        print(f"    - {p['pattern_data']['tool']}: {p['confidence']*100:.0f}% confidence")

    workflow_patterns = [p for p in all_patterns if p['pattern_type'] == 'workflow']
    print(f"\n  Workflow Patterns ({len(workflow_patterns)}):")
    for p in workflow_patterns:
        print(f"    - {p['pattern_data']}: {p['confidence']*100:.0f}% confidence")

    blind_spots = [p for p in all_patterns if p['pattern_type'] == 'blind_spot']
    print(f"\n  Identified Blind Spots ({len(blind_spots)}):")
    for p in blind_spots:
        print(f"    - {p['pattern_data']['area']}: {p['confidence']*100:.0f}% confidence")

    print("\n✅ AI learns and adapts to your style!")


async def demo_proactive_intelligence():
    """Demo 5: Proactive Intelligence"""
    print("\n" + "="*60)
    print("DEMO 5: Proactive Intelligence")
    print("="*60)

    memory = MemoryManager("demo_memory.db")

    # Set up a project
    print("\n📁 Creating project context...")
    project_id = memory.create_project(
        "Pentest - Acme Corp",
        "penetration_test",
        description="WordPress site on acme.com",
        metadata={
            "target": "acme.com",
            "scope": ["*.acme.com"],
            "start_date": "2025-11-07",
            "technologies": ["WordPress 6.2", "Nginx", "MySQL"]
        }
    )
    print(f"  ✅ Project created: {project_id}")

    # Create related goal
    goal_id = memory.create_goal(
        "Monitor for new WordPress 6.2 CVEs",
        priority="medium",
        context={"project_id": project_id}
    )
    print(f"  ✅ Monitoring goal created: {goal_id}")

    print("\n🤖 Proactive AI behavior:")
    print("  - Continuously monitors CVE feeds for WordPress 6.2")
    print("  - Checks target for new exposed services daily")
    print("  - Compares findings against known vulnerabilities")
    print("  - Surfaces high-priority items immediately")

    print("\n💡 Proactive notification example:")
    print("  ┌─────────────────────────────────────────┐")
    print("  │ 🚨 MindSync Alert                        │")
    print("  │                                          │")
    print("  │ New CVE for your project 'Acme Corp':   │")
    print("  │                                          │")
    print("  │ CVE-2024-XXXX (CRITICAL)                │")
    print("  │ WordPress 6.2 - SQL Injection           │")
    print("  │                                          │")
    print("  │ Your target (acme.com) is affected.     │")
    print("  │ Exploit code publicly available.        │")
    print("  │                                          │")
    print("  │ [View Details] [Test Exploit] [Ignore]  │")
    print("  └─────────────────────────────────────────┘")

    print("\n✅ AI thinks ahead and notifies you!")


async def main():
    """Run all demos."""
    print("\n🧠 MindSync Oracle - Capability Demonstrations")
    print("This demo shows what makes MindSync different from standard AI")

    await demo_persistent_memory()
    await demo_goal_autonomy()
    await demo_multimodal_input()
    await demo_pattern_learning()
    await demo_proactive_intelligence()

    print("\n" + "="*60)
    print("SUMMARY: MindSync Oracle Capabilities")
    print("="*60)
    print("✅ Persistent memory across sessions")
    print("✅ Autonomous goal pursuit")
    print("✅ Multi-modal input (text, voice, files, screen, data)")
    print("✅ Pattern learning and recognition")
    print("✅ Proactive intelligence and notifications")
    print("\n🎯 This is the architecture for AGI-like AI agents")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
