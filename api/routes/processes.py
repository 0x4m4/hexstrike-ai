"""
Process Management API Routes
Handles process listing, status, control (pause/resume/terminate), and dashboard
"""

import time
import logging
import psutil
from datetime import datetime
from flask import Blueprint, jsonify
from core.visual import ModernVisualEngine

logger = logging.getLogger(__name__)

# Create blueprint
processes_bp = Blueprint('processes', __name__, url_prefix='/api/processes')

# Dependencies will be injected via init_app
process_manager = None

def init_app(proc_manager):
    """Initialize blueprint with dependencies"""
    global process_manager
    process_manager = proc_manager


@processes_bp.route("/list", methods=["GET"])
def list_processes():
    """List all active processes"""
    try:
        processes = process_manager.list_active_processes()

        # Add calculated fields for each process
        for pid, info in processes.items():
            runtime = time.time() - info["start_time"]
            info["runtime_formatted"] = f"{runtime:.1f}s"

            if info["progress"] > 0:
                eta = (runtime / info["progress"]) * (1.0 - info["progress"])
                info["eta_formatted"] = f"{eta:.1f}s"
            else:
                info["eta_formatted"] = "Unknown"

        return jsonify({
            "success": True,
            "active_processes": processes,
            "total_count": len(processes)
        })
    except Exception as e:
        logger.error(f"💥 Error listing processes: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@processes_bp.route("/status/<int:pid>", methods=["GET"])
def get_process_status(pid):
    """Get status of a specific process"""
    try:
        process_info = process_manager.get_process_status(pid)

        if process_info:
            # Add calculated fields
            runtime = time.time() - process_info["start_time"]
            process_info["runtime_formatted"] = f"{runtime:.1f}s"

            if process_info["progress"] > 0:
                eta = (runtime / process_info["progress"]) * (1.0 - process_info["progress"])
                process_info["eta_formatted"] = f"{eta:.1f}s"
            else:
                process_info["eta_formatted"] = "Unknown"

            return jsonify({
                "success": True,
                "process": process_info
            })
        else:
            return jsonify({
                "success": False,
                "error": f"Process {pid} not found"
            }), 404

    except Exception as e:
        logger.error(f"💥 Error getting process status: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@processes_bp.route("/terminate/<int:pid>", methods=["POST"])
def terminate_process(pid):
    """Terminate a specific process"""
    try:
        success = process_manager.terminate_process(pid)

        if success:
            logger.info(f"🛑 Process {pid} terminated successfully")
            return jsonify({
                "success": True,
                "message": f"Process {pid} terminated successfully"
            })
        else:
            return jsonify({
                "success": False,
                "error": f"Failed to terminate process {pid} or process not found"
            }), 404

    except Exception as e:
        logger.error(f"💥 Error terminating process {pid}: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@processes_bp.route("/pause/<int:pid>", methods=["POST"])
def pause_process(pid):
    """Pause a specific process"""
    try:
        success = process_manager.pause_process(pid)

        if success:
            logger.info(f"⏸️ Process {pid} paused successfully")
            return jsonify({
                "success": True,
                "message": f"Process {pid} paused successfully"
            })
        else:
            return jsonify({
                "success": False,
                "error": f"Failed to pause process {pid} or process not found"
            }), 404

    except Exception as e:
        logger.error(f"💥 Error pausing process {pid}: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@processes_bp.route("/resume/<int:pid>", methods=["POST"])
def resume_process(pid):
    """Resume a paused process"""
    try:
        success = process_manager.resume_process(pid)

        if success:
            logger.info(f"▶️ Process {pid} resumed successfully")
            return jsonify({
                "success": True,
                "message": f"Process {pid} resumed successfully"
            })
        else:
            return jsonify({
                "success": False,
                "error": f"Failed to resume process {pid} or process not found"
            }), 404

    except Exception as e:
        logger.error(f"💥 Error resuming process {pid}: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@processes_bp.route("/dashboard", methods=["GET"])
def process_dashboard():
    """Get enhanced process dashboard with visual status using ModernVisualEngine"""
    try:
        processes = process_manager.list_active_processes()
        current_time = time.time()

        # Create beautiful dashboard using ModernVisualEngine
        dashboard_visual = ModernVisualEngine.create_live_dashboard(processes)

        dashboard = {
            "timestamp": datetime.now().isoformat(),
            "total_processes": len(processes),
            "visual_dashboard": dashboard_visual,
            "processes": [],
            "system_load": {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "active_connections": len(psutil.net_connections())
            }
        }

        for pid, info in processes.items():
            runtime = current_time - info["start_time"]
            progress_fraction = info.get("progress", 0)

            # Create beautiful progress bar using ModernVisualEngine
            progress_bar = ModernVisualEngine.render_progress_bar(
                progress_fraction,
                width=25,
                style='cyber',
                eta=info.get("eta", 0)
            )

            process_status = {
                "pid": pid,
                "command": info["command"][:60] + "..." if len(info["command"]) > 60 else info["command"],
                "status": info["status"],
                "runtime": f"{runtime:.1f}s",
                "progress_percent": f"{progress_fraction * 100:.1f}%",
                "progress_bar": progress_bar,
                "eta": f"{info.get('eta', 0):.0f}s" if info.get('eta', 0) > 0 else "Calculating...",
                "bytes_processed": info.get("bytes_processed", 0),
                "last_output": info.get("last_output", "")[:100]
            }
            dashboard["processes"].append(process_status)

        return jsonify(dashboard)

    except Exception as e:
        logger.error(f"💥 Error getting process dashboard: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500
