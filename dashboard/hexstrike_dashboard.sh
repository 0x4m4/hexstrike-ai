#!/bin/bash

# HexStrike Live Dashboard Monitor
# This script continuously displays the live dashboard

HEXSTRIKE_API="http://0.0.0.0:8888"
REFRESH_INTERVAL=5

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to check if HexStrike server is running
check_server() {
    if ! curl -s "${HEXSTRIKE_API}/health" > /dev/null 2>&1; then
        echo -e "${RED}❌ HexStrike server is not responding at ${HEXSTRIKE_API}${NC}"
        echo "Please ensure the HexStrike AI server is running."
        exit 1
    fi
}

# Function to get and display dashboard
show_dashboard() {
    clear
    echo -e "${PURPLE}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${PURPLE}║${CYAN}                    HexStrike Live Monitor                    ${PURPLE}║${NC}"
    echo -e "${PURPLE}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo
    
    # Get dashboard data via API call
    RESPONSE=$(curl -s "${HEXSTRIKE_API}/api/processes/dashboard" 2>/dev/null)
    
    if [ $? -eq 0 ] && [ ! -z "$RESPONSE" ]; then
        # Parse JSON response and display visual dashboard
        echo "$RESPONSE" | jq -r '.visual_dashboard' 2>/dev/null
        
        # Display system metrics
        echo
        echo -e "${YELLOW}📊 System Metrics:${NC}"
        CPU=$(echo "$RESPONSE" | jq -r '.system_load.cpu_percent' 2>/dev/null)
        MEM=$(echo "$RESPONSE" | jq -r '.system_load.memory_percent' 2>/dev/null)
        CONN=$(echo "$RESPONSE" | jq -r '.system_load.active_connections' 2>/dev/null)
        PROCS=$(echo "$RESPONSE" | jq -r '.total_processes' 2>/dev/null)
        
        echo -e "${GREEN}CPU Usage:${NC} ${CPU}%"
        echo -e "${GREEN}Memory Usage:${NC} ${MEM}%"
        echo -e "${GREEN}Active Connections:${NC} ${CONN}"
        echo -e "${GREEN}Total Processes:${NC} ${PROCS}"
        
    else
        echo -e "${RED}❌ Failed to retrieve dashboard data${NC}"
        echo "Try checking if the HexStrike server is running and accessible."
    fi
    
    echo
    echo -e "${BLUE}Last updated: $(date)${NC}"
    echo -e "${YELLOW}Press Ctrl+C to exit | Refreshing every ${REFRESH_INTERVAL}s${NC}"
}

# Function to handle cleanup on exit
cleanup() {
    echo
    echo -e "${GREEN}👋 Dashboard monitoring stopped${NC}"
    exit 0
}

# Set up signal handling
trap cleanup SIGINT SIGTERM

# Main execution
echo -e "${GREEN}🚀 Starting HexStrike Live Dashboard Monitor...${NC}"
echo -e "${BLUE}Checking server connection...${NC}"

check_server

echo -e "${GREEN}✅ Connected to HexStrike server${NC}"
echo -e "${YELLOW}Starting live dashboard (Press Ctrl+C to exit)...${NC}"
sleep 2

# Main monitoring loop
while true; do
    show_dashboard
    sleep $REFRESH_INTERVAL
done
