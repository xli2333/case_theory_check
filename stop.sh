#!/bin/bash
# ========================================
# CaseCheck Mac/Linux 停止脚本
# ========================================

echo "========================================"
echo "CaseCheck System Stopping..."
echo "========================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

# Check for PID files
if [ -f "data/logs/api.pid" ] && [ -f "data/logs/web.pid" ]; then
    API_PID=$(cat data/logs/api.pid)
    WEB_PID=$(cat data/logs/web.pid)

    echo "Stopping services..."
    echo "  API PID: $API_PID"
    echo "  Web PID: $WEB_PID"
    echo ""

    # Kill processes
    kill $API_PID 2>/dev/null && echo -e "${GREEN}✓${NC} API server stopped"
    kill $WEB_PID 2>/dev/null && echo -e "${GREEN}✓${NC} Web interface stopped"

    # Remove PID files
    rm -f data/logs/api.pid data/logs/web.pid
else
    echo "PID files not found, searching for processes..."

    # Find and kill by port
    API_PID=$(lsof -ti:8000 2>/dev/null)
    WEB_PID=$(lsof -ti:8501 2>/dev/null)

    if [ ! -z "$API_PID" ]; then
        kill $API_PID 2>/dev/null
        echo -e "${GREEN}✓${NC} API server stopped (port 8000)"
    fi

    if [ ! -z "$WEB_PID" ]; then
        kill $WEB_PID 2>/dev/null
        echo -e "${GREEN}✓${NC} Web interface stopped (port 8501)"
    fi

    if [ -z "$API_PID" ] && [ -z "$WEB_PID" ]; then
        echo "No running services found"
    fi
fi

echo ""
echo "========================================"
echo -e "${GREEN}Services Stopped${NC}"
echo "========================================"
