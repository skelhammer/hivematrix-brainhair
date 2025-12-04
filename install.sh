#!/bin/bash
#
# HiveMatrix Template - Installation Script
# Handles setup of template module
#

set -e  # Exit on error

APP_NAME="brainhair"
APP_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PARENT_DIR="$(dirname "$APP_DIR")"
HELM_DIR="$PARENT_DIR/hivematrix-helm"

echo "=========================================="
echo "  Installing HiveMatrix Brain Hair"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check Python version
echo -e "${YELLOW}Checking Python...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 not found${NC}"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo -e "${GREEN}✓ Found Python $PYTHON_VERSION${NC}"
echo ""

# Create virtual environment
echo -e "${YELLOW}Creating virtual environment...${NC}"
if [ -d "pyenv" ]; then
    echo "  Virtual environment already exists"
else
    python3 -m venv pyenv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi
echo ""

# Activate virtual environment
source pyenv/bin/activate

# Upgrade pip
echo -e "${YELLOW}Upgrading pip...${NC}"
pip install --upgrade pip > /dev/null 2>&1
echo -e "${GREEN}✓ pip upgraded${NC}"
echo ""

# Install dependencies
if [ -f "requirements.txt" ]; then
    echo -e "${YELLOW}Installing Python dependencies...${NC}"
    pip install -r requirements.txt
    echo -e "${GREEN}✓ Dependencies installed${NC}"
    echo ""
fi

# Create instance directory if needed
if [ ! -d "instance" ]; then
    echo -e "${YELLOW}Creating instance directory...${NC}"
    mkdir -p instance
    echo -e "${GREEN}✓ Instance directory created${NC}"
    echo ""
fi

# === MODULE-SPECIFIC SETUP ===
echo -e "${YELLOW}Running module-specific setup...${NC}"

# Create .flaskenv configuration if it doesn't exist
if [ ! -f ".flaskenv" ]; then
    echo "Creating configuration file..."

    cat > .flaskenv <<EOF
FLASK_APP=run.py
FLASK_ENV=development
FLASK_RUN_PORT=5050
SERVICE_NAME=brainhair

# Core Service
CORE_SERVICE_URL=http://localhost:5000

# Helm Service
HELM_SERVICE_URL=http://localhost:5004
EOF

    echo -e "${GREEN}✓ Configuration file created${NC}"
else
    echo "  Configuration file already exists"
fi
echo ""

# Create services.json symlink to Helm's services.json if Helm is installed
if [ -d "$HELM_DIR" ] && [ -f "$HELM_DIR/services.json" ]; then
    echo "Linking to Helm's services configuration..."
    if [ -L "services.json" ]; then
        rm services.json
    fi
    ln -sf "$HELM_DIR/services.json" services.json
    echo -e "${GREEN}✓ Services configuration linked${NC}"
    echo ""
fi

echo -e "${GREEN}✓ Module-specific setup complete${NC}"
echo ""

# Check for Claude Code CLI
echo -e "${YELLOW}Checking for Claude Code CLI...${NC}"
CLAUDE_BIN=""

# Check common locations
if [ -x "$HOME/.local/bin/claude" ]; then
    CLAUDE_BIN="$HOME/.local/bin/claude"
elif command -v claude &> /dev/null; then
    CLAUDE_BIN=$(which claude)
elif [ -x "/usr/local/bin/claude" ]; then
    CLAUDE_BIN="/usr/local/bin/claude"
fi

if [ -n "$CLAUDE_BIN" ]; then
    CLAUDE_VERSION=$($CLAUDE_BIN --version 2>/dev/null || echo "unknown")
    echo -e "${GREEN}✓ Claude Code CLI found: $CLAUDE_BIN ($CLAUDE_VERSION)${NC}"
else
    echo -e "${YELLOW}⚠ Claude Code CLI not found${NC}"
    echo ""
    echo "  Brainhair requires Claude Code CLI to function."
    echo "  Install with ONE of these methods:"
    echo ""
    echo "  Option 1 - NPM (recommended):"
    echo "    npm install -g @anthropic-ai/claude-code"
    echo ""
    echo "  Option 2 - Direct download:"
    echo "    Visit https://github.com/anthropics/claude-code/releases"
    echo "    Download and place in ~/.local/bin/claude"
    echo ""
    echo "  After installing, run 'claude' once to authenticate."
fi
echo ""

echo "=========================================="
echo -e "${GREEN}  Brain Hair installed successfully!${NC}"
echo "=========================================="
echo ""
echo "Configuration:"
echo "  Port: 5050"
echo "  Core Service: http://localhost:5000"
echo "  Helm Service: http://localhost:5004"
echo ""
echo "Next steps:"
echo "  1. Ensure Claude Code CLI is installed and authenticated"
echo "  2. Ensure Core and Helm are running"
echo "  3. Start Brain Hair: python run.py"
echo "  4. Or use Helm to start the service"
echo ""
