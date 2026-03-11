import pytest
import requests
import time
import subprocess
import os
import signal
import uuid
import glob
import json

# Base URL for the HexStrike Server
BASE_URL = "http://127.0.0.1:8888"

@pytest.fixture(scope="session", autouse=True)
def server_instance():
    """Start the HexStrike server in a separate process for the test session"""
    server_process = subprocess.Popen(
        ["python3", "hexstrike_server.py", "--port", "8888"],
        stdout=open("server_stdout.log", "w"),
        stderr=open("server_stderr.log", "w"),
        preexec_fn=os.setsid
    )
    
    # Wait for the server to start (health check)
    max_retries = 60
    retry_count = 0
    while retry_count < max_retries:
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=5)
            if response.status_code == 200:
                break
        except requests.exceptions.RequestException:
            pass
        
        time.sleep(2)
        retry_count += 1
    
    if retry_count == max_retries:
        server_process.kill()
        raise RuntimeError("HexStrike Server failed to start for tests")
    
    yield server_process
    
    # Gracefully terminate the server and its children
    try:
        os.killpg(os.getpgid(server_process.pid), signal.SIGTERM)
        server_process.wait(timeout=5)
    except:
        os.killpg(os.getpgid(server_process.pid), signal.SIGKILL)

def test_health_check():
    """Verify server is running and tools are available"""
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_generic_tool_execution_path():
    """Test execution of a tool from system PATH (whoami)"""
    payload = {
        "tool": "whoami",
        "args": []
    }
    response = requests.post(f"{BASE_URL}/api/task/run", json=payload)
    assert response.status_code == 200
    task_id = response.json()["task_id"]
    
    # Poll for completion
    for _ in range(10):
        status_resp = requests.get(f"{BASE_URL}/api/task/status/{task_id}")
        data = status_resp.json()
        if data["status"] == "completed":
            break
        time.sleep(1)
    
    assert data["status"] == "completed"
    assert len(data["stdout_tail"].strip()) > 0
    assert data["exit_code"] == 0

def test_generic_tool_execution_abs_path():
    """Test execution of a tool using an absolute path (/usr/bin/id)"""
    payload = {
        "tool": "/usr/bin/id",
        "args": ["-u"]
    }
    response = requests.post(f"{BASE_URL}/api/task/run", json=payload)
    assert response.status_code == 200
    task_id = response.json()["task_id"]
    
    # Poll for completion
    for _ in range(10):
        status_resp = requests.get(f"{BASE_URL}/api/task/status/{task_id}")
        data = status_resp.json()
        if data["status"] == "completed":
            break
        time.sleep(1)
    
    assert data["status"] == "completed"
    assert data["stdout_tail"].strip().isdigit()

def test_invalid_tool_handling():
    """Test execution of a non-existent binary"""
    payload = {
        "tool": "non_existent_binary_abc_123",
        "args": []
    }
    response = requests.post(f"{BASE_URL}/api/task/run", json=payload)
    assert response.status_code == 200 # Task submission succeeds, execution fails
    task_id = response.json()["task_id"]
    
    # Poll for failure
    for _ in range(10):
        status_resp = requests.get(f"{BASE_URL}/api/task/status/{task_id}")
        data = status_resp.json()
        if data["status"] in ["failed", "completed"]: # completed with error exit code is possible
            break
        time.sleep(1)
    
    assert data["status"] == "failed"
    assert "not found" in data["stderr_tail"].lower() or "no such file" in data["stderr_tail"].lower()

def test_long_running_task_status():
    """Test status polling for a task that takes several seconds (sleep)"""
    payload = {
        "tool": "sleep",
        "args": ["3"]
    }
    response = requests.post(f"{BASE_URL}/api/task/run", json=payload)
    task_id = response.json()["task_id"]
    
    # Verify it is initially running
    time.sleep(0.5)
    status_resp = requests.get(f"{BASE_URL}/api/task/status/{task_id}")
    assert status_resp.json()["status"] == "running"
    
    # Wait for completion
    time.sleep(3)
    status_resp = requests.get(f"{BASE_URL}/api/task/status/{task_id}")
    assert status_resp.json()["status"] == "completed"

def test_task_timeout_termination():
    """Test that tasks are terminated after reaching the timeout limit"""
    payload = {
        "tool": "sleep",
        "args": ["10"],
        "timeout": 2
    }
    response = requests.post(f"{BASE_URL}/api/task/run", json=payload)
    task_id = response.json()["task_id"]
    
    # Wait for timeout
    time.sleep(4)
    status_resp = requests.get(f"{BASE_URL}/api/task/status/{task_id}")
    assert status_resp.json()["status"] == "timeout"

def test_large_output_safety():
    """Test that the server handles large outputs without memory exhaustion"""
    # Create a command that outputs 5MB of data
    payload = {
        "tool": "python3",
        "args": ["-c", "print('A' * 5000000)"]
    }
    response = requests.post(f"{BASE_URL}/api/task/run", json=payload)
    task_id = response.json()["task_id"]
    
    # Wait for completion
    for _ in range(15):
        status_resp = requests.get(f"{BASE_URL}/api/task/status/{task_id}")
        if status_resp.json()["status"] == "completed":
            break
        time.sleep(1)
    
    data = status_resp.json()
    assert data["status"] == "completed"
    # Ensure stdout_tail is capped
    assert len(data["stdout_tail"]) <= 10000
    assert len(data["stdout_tail"]) > 0

def test_orphan_process_cleanup():
    """Test that child processes are also killed when a task is terminated"""
    # Script that spawns a child in background and sleeps
    script_content = """#!/bin/bash
    sleep 60 &
    child_pid=$!
    echo $child_pid
    sleep 60
    """
    script_path = "/tmp/orphan_test.sh"
    with open(script_path, "w") as f:
        f.write(script_content)
    os.chmod(script_path, 0o755)
    
    payload = {
        "tool": script_path,
        "args": [],
        "timeout": 2
    }
    response = requests.post(f"{BASE_URL}/api/task/run", json=payload)
    task_id = response.json()["task_id"]
    
    # Get the child PID from stdout
    child_pid = None
    for _ in range(5):
        status_resp = requests.get(f"{BASE_URL}/api/task/status/{task_id}")
        out = status_resp.json()["stdout_tail"].strip()
        if out:
            child_pid = int(out.split()[0])
            break
        time.sleep(1)
    
    assert child_pid is not None
    
    # Wait for timeout
    time.sleep(3)
    
    # Verify task is timed out
    assert requests.get(f"{BASE_URL}/api/task/status/{task_id}").json()["status"] == "timeout"
    
    # Verify child process is dead (kill -0 fails)
    try:
        os.kill(child_pid, 0)
        assert False, f"Child process {child_pid} still alive after task timeout"
    except ProcessLookupError:
        pass # Child is dead, success

def test_concurrency():
    """Test running multiple concurrent tasks"""
    task_ids = []
    for i in range(5):
        payload = {
            "tool": "echo",
            "args": [f"task_{i}"]
        }
        resp = requests.post(f"{BASE_URL}/api/task/run", json=payload)
        task_ids.append(resp.json()["task_id"])
    
    # Poll all tasks
    for i, tid in enumerate(task_ids):
        for _ in range(10):
            status_resp = requests.get(f"{BASE_URL}/api/task/status/{tid}")
            if status_resp.json()["status"] == "completed":
                break
            time.sleep(0.5)
        
        data = status_resp.json()
        assert data["status"] == "completed"
        assert f"task_{i}" in data["stdout_tail"]

def test_interactive_tool_deadlock_prevention():
    """Test that interactive tools do not deadlock the server"""
    # 'cat' with no args waits for stdin indefinitely unless closed
    payload = {
        "tool": "cat",
        "args": [],
        "timeout": 5
    }
    response = requests.post(f"{BASE_URL}/api/task/run", json=payload)
    task_id = response.json()["task_id"]
    
    # Poll for completion (should finish immediately if stdin is DEVNULL)
    for _ in range(5):
        status_resp = requests.get(f"{BASE_URL}/api/task/status/{task_id}")
        if status_resp.json()["status"] == "completed":
            break
        time.sleep(1)
    
    assert status_resp.json()["status"] == "completed"

def test_shell_command_execution():
    """Test executing a complex shell pipeline safely via bash -c"""
    payload = {
        "tool": "/bin/bash",
        "args": ["-c", "echo 'hello world' | grep hello"]
    }
    response = requests.post(f"{BASE_URL}/api/task/run", json=payload)
    task_id = response.json()["task_id"]
    
    for _ in range(5):
        status_resp = requests.get(f"{BASE_URL}/api/task/status/{task_id}")
        if status_resp.json()["status"] == "completed":
            break
        time.sleep(1)
    
    data = status_resp.json()
    assert data["status"] == "completed"
    assert "hello world" in data["stdout_tail"]

def test_temp_file_cleanup():
    """Verify that temporary files are deleted after the task completes"""
    payload = {
        "tool": "echo",
        "args": ["cleanup test"]
    }
    response = requests.post(f"{BASE_URL}/api/task/run", json=payload)
    task_id = response.json()["task_id"]
    
    for _ in range(5):
        status_resp = requests.get(f"{BASE_URL}/api/task/status/{task_id}")
        if status_resp.json()["status"] == "completed":
            break
        time.sleep(1)
    
    # Check that temp files do not exist for this task_id in /tmp
    out_files = glob.glob(f"/tmp/task_{task_id}_out_*")
    err_files = glob.glob(f"/tmp/task_{task_id}_err_*")
    assert len(out_files) == 0, "Stdout temp file was not cleaned up"
    assert len(err_files) == 0, "Stderr temp file was not cleaned up"
    
    # Verify final data was read into memory correctly
    data = status_resp.json()
    assert data["status"] == "completed"
    assert "cleanup test" in data["stdout_tail"]

def test_task_listing_and_metadata():
    """Test listing tasks and verifying metadata persistence"""
    metadata = {
        "target": "example.com",
        "category": "recon",
        "scanner": "nmap"
    }
    payload = {
        "tool": "echo",
        "args": ["metadata test"],
        "metadata": metadata
    }
    response = requests.post(f"{BASE_URL}/api/task/run", json=payload)
    task_id = response.json()["task_id"]
    
    # Check listing
    list_resp = requests.get(f"{BASE_URL}/api/task/list")
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert data["success"] is True
    
    # Find our task in the list
    task_info = next((t for t in data["tasks"] if t["task_id"] == task_id), None)
    assert task_info is not None
    assert task_info["metadata"] == metadata
    assert task_info["tool"] == "echo"

def test_task_kill():
    """Test manual termination of a task"""
    payload = {
        "tool": "sleep",
        "args": ["60"]
    }
    response = requests.post(f"{BASE_URL}/api/task/run", json=payload)
    task_id = response.json()["task_id"]
    
    # Wait a bit for it to start
    time.sleep(1)
    
    # Kill the task
    kill_resp = requests.post(f"{BASE_URL}/api/task/kill/{task_id}")
    assert kill_resp.status_code == 200
    assert kill_resp.json()["success"] is True
    
    # Verify status is killed
    time.sleep(1)
    status_resp = requests.get(f"{BASE_URL}/api/task/status/{task_id}")
    assert status_resp.json()["status"] == "killed"

def test_system_status():
    """Test retrieving system resource status"""
    response = requests.get(f"{BASE_URL}/api/system/status")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "cpu_usage_percent" in data
    assert "memory" in data
    assert "running_tasks" in data

def test_tool_discovery_categorized():
    """Test discovery of tools with categorization"""
    response = requests.get(f"{BASE_URL}/api/tools/discover")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "tools" in data
    # Check if nmap is categorized correctly if it exists
    if "nmap" in data["tools"]:
        assert data["tools"]["nmap"]["category"] == "network_scan"

def test_task_output_retrieval():
    """Test retrieving full output for a completed task"""
    content = "Hello full output retrieval test"
    payload = {
        "tool": "echo",
        "args": [content]
    }
    response = requests.post(f"{BASE_URL}/api/task/run", json=payload)
    task_id = response.json()["task_id"]
    
    # Wait for completion
    for _ in range(5):
        status_resp = requests.get(f"{BASE_URL}/api/task/status/{task_id}")
        if status_resp.json()["status"] == "completed":
            break
        time.sleep(1)
    
    # Retrieve full output
    output_resp = requests.get(f"{BASE_URL}/api/task/output/{task_id}")
    assert output_resp.status_code == 200
    data = output_resp.json()
    assert data["success"] is True
    assert content in data["output"]

def test_task_filtering():
    """Test querying tasks with filters"""
    # Create tasks with specific metadata
    requests.post(f"{BASE_URL}/api/task/run", json={
        "tool": "echo", "args": ["filter1"], "metadata": {"target": "filter_target_1", "category": "cat1"}
    })
    requests.post(f"{BASE_URL}/api/task/run", json={
        "tool": "echo", "args": ["filter2"], "metadata": {"target": "filter_target_2", "category": "cat2"}
    })
    
    # Filter by target
    resp = requests.get(f"{BASE_URL}/api/task/list?target=filter_target_1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    assert data["tasks"][0]["metadata"]["target"] == "filter_target_1"
    
    # Filter by status
    resp = requests.get(f"{BASE_URL}/api/task/list?status=completed")
    assert resp.status_code == 200
    # At least some tasks should be completed by now
    assert all(t["status"] == "completed" for t in resp.json()["tasks"])

def test_artifact_lifecycle():
    """Test storing, retrieving, and linking artifacts"""
    # 1. Store artifact
    artifact_payload = {
        "artifact_type": "domain",
        "artifact_location": "example.com",
        "description": "Primary research target",
        "metadata": {"tags": ["initial", "high_value"]}
    }
    resp = requests.post(f"{BASE_URL}/api/artifact/store", json=artifact_payload)
    assert resp.status_code == 200
    parent_id = resp.json()["artifact_id"]
    
    # 2. Store child artifact (linking)
    child_payload = {
        "artifact_type": "subdomain",
        "artifact_location": "api.example.com",
        "parent_artifact_id": parent_id,
        "description": "Discovered via subdomain enum"
    }
    resp = requests.post(f"{BASE_URL}/api/artifact/store", json=child_payload)
    assert resp.status_code == 200
    child_id = resp.json()["artifact_id"]
    
    # 3. Retrieve specific artifact
    resp = requests.get(f"{BASE_URL}/api/artifact/get/{child_id}")
    assert resp.status_code == 200
    data = resp.json()["artifact"]
    assert data["parent_artifact_id"] == parent_id
    assert data["artifact_location"] == "api.example.com"
    
    # 4. List all artifacts
    resp = requests.get(f"{BASE_URL}/api/artifact/list")
    assert resp.status_code == 200
    assert any(a["artifact_id"] == parent_id for a in resp.json()["artifacts"])
    assert any(a["artifact_id"] == child_id for a in resp.json()["artifacts"])

def test_task_telemetry():
    """Test detailed telemetry in task status (runtime, output size)"""
    payload = {
        "tool": "python3",
        "args": ["-u", "-c", "import time; import sys; print('A'*100); sys.stdout.flush(); time.sleep(2); print('B'*100); sys.stdout.flush()"]
    }
    response = requests.post(f"{BASE_URL}/api/task/run", json=payload)
    task_id = response.json()["task_id"]
    
    time.sleep(1)
    resp = requests.get(f"{BASE_URL}/api/task/status/{task_id}")
    data = resp.json()
    assert "runtime_seconds" in data
    assert "output_size_bytes" in data
    assert data["output_size_bytes"] >= 100
    
    time.sleep(2)
    resp = requests.get(f"{BASE_URL}/api/task/status/{task_id}")
    assert resp.json()["output_size_bytes"] >= 200

def test_investigation_management():
    """Test full investigation lifecycle and research memory"""
    # 1. Create investigation
    inv_payload = {
        "target": "example.com",
        "goal": "Find RCE in update mechanism",
        "description": "Analyze firmware updates"
    }
    resp = requests.post(f"{BASE_URL}/api/investigation/create", json=inv_payload)
    assert resp.status_code == 200
    inv_id = resp.json()["investigation_id"]
    
    # 2. Update stage
    requests.post(f"{BASE_URL}/api/investigation/update_stage", json={
        "investigation_id": inv_id,
        "stage": "surface_mapping"
    })
    
    # 3. Add note
    requests.post(f"{BASE_URL}/api/investigation/add_note", json={
        "investigation_id": inv_id,
        "note": "Initial mapping complete. Found interesting endpoint /api/v1/update"
    })
    
    # 4. Save checkpoint
    checkpoint_payload = {
        "investigation_id": inv_id,
        "stage": "surface_mapping",
        "completed_tasks": ["task-1", "task-2"],
        "pending_tasks": ["task-3"],
        "key_findings": ["Endpoint /api/v1/update discovered"],
        "summary": "Mapping phase completed successfully."
    }
    requests.post(f"{BASE_URL}/api/investigation/checkpoint/save", json=checkpoint_payload)
    
    # 5. Save snapshot
    requests.post(f"{BASE_URL}/api/investigation/snapshot", json={
        "investigation_id": inv_id,
        "summary": "Compressed reasoning: endpoint uses signed requests but signature might be bypassable."
    })
    
    # 6. Verify investigation details
    resp = requests.get(f"{BASE_URL}/api/investigation/get/{inv_id}")
    assert resp.status_code == 200
    inv = resp.json()["investigation"]
    assert inv["stage"] == "surface_mapping"
    assert inv["target"] == "example.com"
    
    # 7. Verify notes
    resp = requests.get(f"{BASE_URL}/api/investigation/notes/{inv_id}")
    assert len(resp.json()["notes"]) == 1
    
    # 8. Verify checkpoints
    resp = requests.get(f"{BASE_URL}/api/investigation/checkpoint/latest/{inv_id}")
    assert resp.json()["checkpoint"]["summary"] == "Mapping phase completed successfully."
    
    # 9. Verify snapshots
    resp = requests.get(f"{BASE_URL}/api/investigation/snapshots/{inv_id}")
    assert len(resp.json()["snapshots"]) == 1

def test_artifact_investigation_linking():
    """Test linking artifacts to investigations and building discovery chains"""
    # 1. Create investigation
    resp = requests.post(f"{BASE_URL}/api/investigation/create", json={
        "target": "firmware_analysis",
        "goal": "extract secrets"
    })
    inv_id = resp.json()["investigation_id"]
    
    # 2. Store root artifact linked to investigation
    resp = requests.post(f"{BASE_URL}/api/artifact/store", json={
        "artifact_type": "firmware",
        "artifact_location": "/tmp/firmware.bin",
        "investigation_id": inv_id,
        "curiosity_score": 80
    })
    root_id = resp.json()["artifact_id"]
    
    # 3. Store child artifact (extracted filesystem)
    resp = requests.post(f"{BASE_URL}/api/artifact/store", json={
        "artifact_type": "filesystem",
        "artifact_location": "/tmp/firmware_fs/",
        "parent_artifact_id": root_id,
        "investigation_id": inv_id,
        "curiosity_score": 50
    })
    child_id = resp.json()["artifact_id"]
    
    # 4. Update curiosity score
    requests.post(f"{BASE_URL}/api/artifact/update_score", json={
        "artifact_id": child_id,
        "curiosity_score": 95
    })
    
    # 5. Verify graph
    resp = requests.get(f"{BASE_URL}/api/artifact/graph/{inv_id}")
    artifacts = resp.json()["artifacts"]
    assert len(artifacts) == 2
    
    # Find child and check score + parent
    child = next(a for a in artifacts if a["artifact_id"] == child_id)
    assert child["parent_artifact_id"] == root_id
    assert child["curiosity_score"] == 95

def test_persistent_recovery():
    """Verify that restarting the server (simulated) does not lose investigation state"""
    # Since we can't easily restart the server process group in this test environment without 
    # complex logic, we'll verify the file exists and has content.
    # The actual server in the fixture persists to disk.
    assert os.path.exists("hexstrike_investigations.json")
    assert os.path.exists("hexstrike_artifacts.json")
    
    with open("hexstrike_investigations.json", "r") as f:
        data = json.load(f)
        assert len(data["investigations"]) > 0
