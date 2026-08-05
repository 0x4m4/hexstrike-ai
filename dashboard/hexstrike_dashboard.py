#!/usr/bin/env python3
"""
HexStrike AI Live Dashboard Monitor
A Python script for real-time monitoring of HexStrike security processes
"""

import requests
import json
import time
import os
import sys
from datetime import datetime
import argparse

# ANSI Color codes for beautiful terminal output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    PURPLE = '\033[0;35m'
    CYAN = '\033[0;36m'
    WHITE = '\033[1;37m'
    BOLD = '\033[1m'
    NC = '\033[0m'  # No Color

class HexStrikeDashboard:
    def __init__(self, api_base="http://0.0.0.0:8888", refresh_interval=5):
        self.api_base = api_base
        self.refresh_interval = refresh_interval
        self.session = requests.Session()
        self.session.timeout = 10
        
    def check_server_health(self):
        """Check if HexStrike server is accessible"""
        try:
            response = self.session.get(f"{self.api_base}/health")
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
    
    def get_dashboard_data(self):
        """Fetch live dashboard data from HexStrike API"""
        try:
            response = self.session.get(f"{self.api_base}/api/processes/dashbaord")
            if response.status_code == 200:
                return response.json()
            else:
                return None
        except requests.exceptions.RequestException as e:
            print(f"{Colors.RED}Error fetching dashboard data: {e}{Colors.NC}")
            return None
    
    def get_process_status(self, pid):
        """Get status of specific process"""
        try:
            response = self.session.get(f"{self.api_base}/api/processes/status/{pid}")
            if response.status_code == 200:
                return response.json()
            else:
                return None
        except requests.exceptions.RequestException:
            return None
    
    def terminate_process(self, pid):
        """Terminate a specific process"""
        try:
            response = self.session.post(f"{self.api_base}/api/processes/terminate/{pid}")
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
    
    def pause_process(self, pid):
        """Pause a specific process"""
        try:
            response = self.session.post(f"{self.api_base}/api/processes/pause/{pid}")
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
    
    def resume_process(self, pid):
        """Resume a paused process"""
        try:
            response = self.session.post(f"{self.api_base}/api/processes/resume/{pid}")
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
    
    def format_runtime(self, seconds):
        """Format runtime in human readable format"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        else:
            return f"{seconds/3600:.1f}h"
    
    def format_bytes(self, bytes_count):
        """Format bytes in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_count < 1024.0:
                return f"{bytes_count:.1f}{unit}"
            bytes_count /= 1024.0
        return f"{bytes_count:.1f}TB"
    
    def display_header(self):
        """Display dashboard header"""
        print(f"{Colors.PURPLE}╔══════════════════════════════════════════════════════════════════════════════╗{Colors.NC}")
        print(f"{Colors.PURPLE}║{Colors.CYAN}{Colors.BOLD}                           HexStrike AI Live Dashboard                        {Colors.PURPLE}║{Colors.NC}")
        print(f"{Colors.PURPLE}╚══════════════════════════════════════════════════════════════════════════════╝{Colors.NC}")
        print()
    
    def display_system_metrics(self, data):
        """Display system performance metrics"""
        system_load = data.get('system_load', {})
        cpu = system_load.get('cpu_percent', 0)
        memory = system_load.get('memory_percent', 0)
        connections = system_load.get('active_connections', 0)
        total_processes = data.get('total_processes', 0)
        
        print(f"{Colors.YELLOW}📊 System Metrics:{Colors.NC}")
        print(f"   {Colors.GREEN}CPU Usage:{Colors.NC} {cpu}%")
        print(f"   {Colors.GREEN}Memory Usage:{Colors.NC} {memory}%")
        print(f"   {Colors.GREEN}Active Connections:{Colors.NC} {connections:,}")
        print(f"   {Colors.GREEN}Total Processes:{Colors.NC} {total_processes}")
        print()
    
    def display_processes(self, processes):
        """Display detailed process information"""
        if not processes:
            print(f"{Colors.YELLOW}No active processes found.{Colors.NC}")
            return
        
        print(f"{Colors.BLUE}🔄 Active Security Processes:{Colors.NC}")
        print(f"{Colors.BLUE}{'PID':<8} {'Status':<10} {'Runtime':<10} {'Progress':<12} {'Data':<10} {'Command':<50}{Colors.NC}")
        print(f"{Colors.BLUE}{'-' * 100}{Colors.NC}")
        
        for proc in processes:
            pid = proc.get('pid', 'N/A')
            status = proc.get('status', 'unknown')
            runtime = self.format_runtime(float(proc.get('runtime', '0').rstrip('s')))
            progress = proc.get('progress_percent', '0%')
            data_processed = self.format_bytes(proc.get('bytes_processed', 0))
            command = proc.get('command', '')[:45] + '...' if len(proc.get('command', '')) > 45 else proc.get('command', '')
            
            # Color code status
            status_color = Colors.GREEN if status == 'running' else Colors.RED if status == 'failed' else Colors.YELLOW
            status_display = f"{status_color}{status}{Colors.NC}"
            
            print(f"{Colors.WHITE}{pid:<8}{Colors.NC} {status_display:<20} {runtime:<10} {progress:<12} {data_processed:<10} {command}")
        
        print()
    
    def display_visual_dashboard(self, data):
        """Display the visual dashboard from API"""
        visual_dashboard = data.get('visual_dashboard', '')
        if visual_dashboard:
            print(visual_dashboard)
            print()
    
    def display_footer(self):
        """Display dashboard footer with timestamp and controls"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{Colors.BLUE}Last updated: {timestamp}{Colors.NC}")
        print(f"{Colors.YELLOW}Press 'q' to quit, 'r' to refresh, 't <pid>' to terminate process{Colors.NC}")
        print(f"{Colors.YELLOW}Refreshing every {self.refresh_interval}s{Colors.NC}")
    
    def display_dashboard(self, data):
        """Display complete dashboard"""
        os.system('clear')
        self.display_header()
        
        if data:
            # Display visual dashboard if available
            self.display_visual_dashboard(data)
            
            # Display system metrics
            self.display_system_metrics(data)
            
            # Display process details
            processes = data.get('processes', [])
            self.display_processes(processes)
        else:
            print(f"{Colors.RED}❌ Failed to retrieve dashboard data{Colors.NC}")
            print("Please check if the HexStrike AI server is running and accessible.")
            print(f"Server URL: {self.api_base}")
            print()
        
        self.display_footer()
    
    def interactive_mode(self):
        """Run dashboard in interactive mode"""
        print(f"{Colors.GREEN}🚀 Starting HexStrike AI Live Dashboard...{Colors.NC}")
        print(f"{Colors.BLUE}Checking server connection at {self.api_base}...{Colors.NC}")
        
        if not self.check_server_health():
            print(f"{Colors.RED}❌ Cannot connect to HexStrike server at {self.api_base}{Colors.NC}")
            print("Please ensure the HexStrike AI server is running.")
            sys.exit(1)
        
        print(f"{Colors.GREEN}✅ Connected to HexStrike server{Colors.NC}")
        print(f"{Colors.YELLOW}Starting live dashboard monitoring...{Colors.NC}")
        time.sleep(2)
        
        try:
            while True:
                data = self.get_dashboard_data()
                self.display_dashboard(data)
                time.sleep(self.refresh_interval)
        except KeyboardInterrupt:
            print(f"\n{Colors.GREEN}👋 Dashboard monitoring stopped{Colors.NC}")
            sys.exit(0)
    
    def one_shot_mode(self):
        """Run dashboard once and exit"""
        print(f"{Colors.GREEN}📊 HexStrike AI Dashboard Snapshot{Colors.NC}")
        print()
        
        if not self.check_server_health():
            print(f"{Colors.RED}❌ Cannot connect to HexStrike server at {self.api_base}{Colors.NC}")
            sys.exit(1)
        
        data = self.get_dashboard_data()
        self.display_dashboard(data)

def main():
    parser = argparse.ArgumentParser(description='HexStrike AI Live Dashboard Monitor')
    parser.add_argument('--api-base', default='http://localhost:8888', 
                      help='HexStrike API base URL (default: http://localhost:8888)')
    parser.add_argument('--refresh', type=int, default=5, 
                      help='Refresh interval in seconds (default: 5)')
    parser.add_argument('--once', action='store_true', 
                      help='Run once and exit (no continuous monitoring)')
    parser.add_argument('--terminate', type=int, metavar='PID',
                      help='Terminate process with given PID')
    parser.add_argument('--pause', type=int, metavar='PID',
                      help='Pause process with given PID')
    parser.add_argument('--resume', type=int, metavar='PID',
                      help='Resume process with given PID')
    parser.add_argument('--status', type=int, metavar='PID',
                      help='Get status of process with given PID')
    
    args = parser.parse_args()
    
    dashboard = HexStrikeDashboard(api_base=args.api_base, refresh_interval=args.refresh)
    
    # Handle process management commands
    if args.terminate:
        if dashboard.terminate_process(args.terminate):
            print(f"{Colors.GREEN}✅ Process {args.terminate} terminated successfully{Colors.NC}")
        else:
            print(f"{Colors.RED}❌ Failed to terminate process {args.terminate}{Colors.NC}")
        return
    
    if args.pause:
        if dashboard.pause_process(args.pause):
            print(f"{Colors.GREEN}✅ Process {args.pause} paused successfully{Colors.NC}")
        else:
            print(f"{Colors.RED}❌ Failed to pause process {args.pause}{Colors.NC}")
        return
    
    if args.resume:
        if dashboard.resume_process(args.resume):
            print(f"{Colors.GREEN}✅ Process {args.resume} resumed successfully{Colors.NC}")
        else:
            print(f"{Colors.RED}❌ Failed to resume process {args.resume}{Colors.NC}")
        return
    
    if args.status:
        status = dashboard.get_process_status(args.status)
        if status:
            print(f"{Colors.GREEN}Process {args.status} Status:{Colors.NC}")
            print(json.dumps(status, indent=2))
        else:
            print(f"{Colors.RED}❌ Failed to get status for process {args.status}{Colors.NC}")
        return
    
    # Run dashboard
    if args.once:
        dashboard.one_shot_mode()
    else:
        dashboard.interactive_mode()

if __name__ == "__main__":
    main()
