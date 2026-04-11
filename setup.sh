#!/bin/bash
set -e

echo "🎼 Orchestra AI — Setup Script"
echo "================================"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Check Python
echo -e "${BLUE}[1/5] Checking Python...${NC}"
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required. Install it first."
    exit 1
fi
echo -e "${GREEN}✓ Python $(python3 --version)${NC}"

# Check Node
echo -e "${BLUE}[2/5] Checking Node.js...${NC}"
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is required. Install it first."
    exit 1
fi
echo -e "${GREEN}✓ Node $(node --version)${NC}"

# Backend setup
echo -e "${BLUE}[3/5] Setting up backend...${NC}"
cd "$PROJECT_DIR"
python3 -m pip install -r backend/requirements.txt 2>&1 | tail -1
echo -e "${GREEN}✓ Backend dependencies installed${NC}"

# Frontend setup
echo -e "${BLUE}[4/5] Setting up frontend...${NC}"
cd "$PROJECT_DIR/frontend"
npm install 2>&1 | tail -3
echo -e "${GREEN}✓ Frontend dependencies installed${NC}"

# Docker sandbox (optional)
echo -e "${BLUE}[5/5] Building Docker sandbox (optional)...${NC}"
if command -v docker &> /dev/null; then
    cd "$PROJECT_DIR"
    docker build -t orchestra-sandbox -f docker/sandbox.Dockerfile . 2>/dev/null && \
        echo -e "${GREEN}✓ Docker sandbox built${NC}" || \
        echo -e "${YELLOW}⚠ Docker build skipped (non-critical)${NC}"
else
    echo -e "${YELLOW}⚠ Docker not found — sandbox will use local execution${NC}"
fi

# Initialize database
echo ""
echo -e "${BLUE}Initializing database...${NC}"
cd "$PROJECT_DIR"
PYTHONPATH="$PROJECT_DIR" python3 -c "from backend.database import init_db; init_db()" 2>&1
echo -e "${GREEN}✓ Database initialized${NC}"

echo ""
echo "================================"
echo -e "${GREEN}🎼 Orchestra AI is ready!${NC}"
echo ""
echo "Start the system:"
echo ""
echo -e "  ${YELLOW}# Terminal 1 — Backend${NC}"
echo -e "  cd $PROJECT_DIR"
echo -e "  PYTHONPATH=. python3 -m uvicorn backend.main:app --reload --port 8000"
echo ""
echo -e "  ${YELLOW}# Terminal 2 — Frontend${NC}"
echo -e "  cd $PROJECT_DIR/frontend"
echo -e "  npm run dev"
echo ""
echo -e "  ${YELLOW}# Make sure LM Studio is running at http://127.0.0.1:1234${NC}"
echo ""
echo "Dashboard: http://localhost:3000"
echo "API Docs:  http://localhost:8000/docs"
echo ""
