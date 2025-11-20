#!/bin/bash
# ========================================
# CaseCheck Mac/Linux 启动脚本
# ========================================

set -e

echo "========================================"
echo "CaseCheck System Starting..."
echo "========================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python
echo "[1/4] Checking Python..."
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    PYTHON_VERSION=$(python3 --version)
    echo -e "      ${GREEN}${PYTHON_VERSION}${NC}"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
    PYTHON_VERSION=$(python --version)
    echo -e "      ${GREEN}${PYTHON_VERSION}${NC}"
else
    echo -e "${RED}[ERROR] Python not found!${NC}"
    echo ""
    echo "Please install Python 3.8+ first:"
    echo "  macOS: brew install python3"
    echo "  Linux: sudo apt install python3"
    echo ""
    exit 1
fi
echo ""

# Check if installed
if [ ! -f ".env" ]; then
    echo -e "${RED}[ERROR] System not installed!${NC}"
    echo ""
    echo "Please run installation first:"
    echo "  python3 setup.py"
    echo ""
    exit 1
fi

echo "[2/4] Installation verified"
echo ""

# Activate virtual environment if exists
if [ -f "venv/bin/activate" ]; then
    echo "[3/4] Activating virtual environment..."
    source venv/bin/activate
    echo ""
else
    echo "[3/4] Using system Python"
    echo ""
fi

# Start services
echo "[4/4] Starting services..."
echo ""

# Create log directory
mkdir -p data/logs

echo "========================================"
echo "Starting API Server (port 8000)..."
echo "========================================"

# Start API in background
nohup $PYTHON_CMD -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 \
    > data/logs/api.log 2>&1 &
API_PID=$!
echo "API PID: $API_PID"

# Wait for API to start
echo ""
echo "Waiting for API to initialize..."
sleep 8

# Check if API is running
if ! kill -0 $API_PID 2>/dev/null; then
    echo -e "${RED}[ERROR] API failed to start!${NC}"
    echo "Check logs: data/logs/api.log"
    exit 1
fi

echo ""
echo "========================================"
echo "Starting Web Interface (port 8501)..."
echo "========================================"

# Start Streamlit in background
nohup $PYTHON_CMD -m streamlit run src/web/app.py \
    --server.port 8501 \
    --server.address 0.0.0.0 \
    --server.headless true \
    > data/logs/web.log 2>&1 &
WEB_PID=$!
echo "Web PID: $WEB_PID"

# Wait for Web to start
sleep 5

# Check if Web is running
if ! kill -0 $WEB_PID 2>/dev/null; then
    echo -e "${RED}[ERROR] Web interface failed to start!${NC}"
    echo "Check logs: data/logs/web.log"
    kill $API_PID 2>/dev/null
    exit 1
fi

echo ""
echo "========================================"
echo -e "${GREEN}Services Started Successfully!${NC}"
echo "========================================"
echo ""
echo "Access URLs:"
echo "  Web Interface: http://localhost:8501"
echo "  API Docs:      http://localhost:8000/docs"
echo "  API Health:    http://localhost:8000/health"
echo ""
echo "Process IDs:"
echo "  API PID: $API_PID"
echo "  Web PID: $WEB_PID"
echo ""
echo "========================================"
echo "IMPORTANT NOTES:"
echo "========================================"
echo ""
echo "* First startup may take 5-10 minutes (downloading model)"
echo "* Services are running in background"
echo "* Logs are in data/logs/ directory"
echo ""
echo "To stop services:"
echo "  kill $API_PID $WEB_PID"
echo ""
echo "Or run:"
echo "  ./stop.sh"
echo ""

# Save PIDs to file for stop script
echo $API_PID > data/logs/api.pid
echo $WEB_PID > data/logs/web.pid

# Try to open browser (macOS only)
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Opening browser..."
    sleep 3
    open http://localhost:8501
fi

echo "========================================"
echo -e "${GREEN}System is ready!${NC}"
echo "========================================"
echo ""

# Keep script running to show logs (optional)
echo "Press Ctrl+C to view logs (services will keep running)"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Note: Services are still running in background"
    echo "Use './stop.sh' to stop them"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Optionally tail logs
read -p "View logs? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    tail -f data/logs/api.log data/logs/web.log
fi
