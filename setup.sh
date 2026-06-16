#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status
set -e

# Terminal Colours
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Colour

echo -e "${BLUE}=====================================================${NC}"
echo -e "${CYAN}      LitSynthese Development Setup Script      ${NC}"
echo -e "${BLUE}=====================================================${NC}"

# Function to check command existence
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 1. Check Python 3
echo -e "\n${BLUE}[1/5] Checking Python 3 installation...${NC}"
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version 2>&1)
    echo -e "${GREEN}✓ Found Python 3: ${PYTHON_VERSION}${NC}"
else
    echo -e "${RED}✗ Python 3 is not installed. Please install Python 3 and try again.${NC}"
    exit 1
fi

# 2. Check and Install python3-pip and python3-venv (Ubuntu/Debian system dependencies)
echo -e "\n${BLUE}[2/5] Verifying system packages (pip and venv)...${NC}"
MISSING_SYS_PACKAGES=()

# Check venv and ensurepip modules
if ! python3 -c "import venv, ensurepip" >/dev/null 2>&1; then
    MISSING_SYS_PACKAGES+=("python3-venv")
fi

# Check pip command (globally or via python module)
if ! python3 -m pip --version >/dev/null 2>&1; then
    MISSING_SYS_PACKAGES+=("python3-pip")
fi

if [ ${#MISSING_SYS_PACKAGES[@]} -ne 0 ]; then
    echo -e "${YELLOW}ℹ Missing required system packages: ${MISSING_SYS_PACKAGES[*]}${NC}"
    echo -e "${YELLOW}Requesting sudo privileges to install dependencies via APT...${NC}"
    
    # Run apt update & install
    sudo apt-get update
    sudo apt-get install -y "${MISSING_SYS_PACKAGES[@]}"
    echo -e "${GREEN}✓ System packages installed successfully.${NC}"
else
    echo -e "${GREEN}✓ System packages (pip and venv) are already available.${NC}"
fi

# 3. Create Virtual Environment
echo -e "\n${BLUE}[3/5] Setting up Python virtual environment...${NC}"
VENV_DIR="venv"
if [ ! -f "$VENV_DIR/bin/activate" ]; then
    echo -e "Creating virtual environment in ${CYAN}${VENV_DIR}${NC}..."
    # If directory exists but activate script is missing, remove it first
    if [ -d "$VENV_DIR" ]; then
        echo -e "${YELLOW}ℹ Removing incomplete/broken virtual environment directory...${NC}"
        rm -rf "$VENV_DIR"
    fi
    python3 -m venv "$VENV_DIR"
    echo -e "${GREEN}✓ Virtual environment created.${NC}"
else
    echo -e "${GREEN}✓ Virtual environment already exists in ${VENV_DIR} (verified).${NC}"
fi

# 4. Activate Venv and Install Python Requirements
echo -e "\n${BLUE}[4/5] Installing dependencies inside virtual environment...${NC}"
source "${VENV_DIR}/bin/activate"

# Upgrade pip locally in virtualenv
echo "Upgrading pip..."
pip install --upgrade pip

# Install requirements
if [ -f "requirements.txt" ]; then
    echo "Installing requirements from requirements.txt..."
    pip install -r requirements.txt
    echo -e "${GREEN}✓ All Python requirements installed.${NC}"
else
    echo -e "${RED}✗ requirements.txt not found. Cannot install dependencies.${NC}"
    exit 1
fi

# 5. Check/Setup Environment Variables (.env)
echo -e "\n${BLUE}[5/5] Checking environment configuration...${NC}"
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}ℹ No .env file found.${NC}"
    read -p "Enter your GEMINI_API_KEY (leave empty to run in Demo Mock Mode): " api_key
    
    if [ -n "$api_key" ]; then
        echo "GEMINI_API_KEY=$api_key" > .env
        echo -e "${GREEN}✓ .env file created with your API key.${NC}"
    else
        echo "GEMINI_API_KEY=" > .env
        echo -e "${YELLOW}⚠ Created empty .env file. The application will run in Demo Mock Mode.${NC}"
    fi
else
    echo -e "${GREEN}✓ .env file already exists.${NC}"
fi

echo -e "\n${GREEN}=====================================================${NC}"
echo -e "${GREEN}       Setup Complete! Ready to run LitSynthese  ${NC}"
echo -e "${GREEN}=====================================================${NC}"
echo -e "\nTo start the application, run:"
echo -e "  ${CYAN}source venv/bin/activate && python3 main.py${NC}"
echo -e "\nWould you like to start the server now? (y/N)"
read -r start_server
if [[ "$start_server" =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}Starting application server...${NC}"
    python3 main.py
fi
