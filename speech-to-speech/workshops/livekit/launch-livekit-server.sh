#!/usr/bin/env bash

# This is only required by the instructor-led workshop

# install HomeBrew (works for x86)
if command -v brew >/dev/null 2>&1; then
    echo "Homebrew is installed."
else
    sudo dnf groupinstall "Development Tools" -y
    sudo dnf install curl file git gcc bzip2 tar -y
    echo | /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
    source ~/.bashrc
fi

# install LiveKit and CLI
brew install livekit livekit-cli

# install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# start virtual environment
python3 -m venv .venv
source .venv/bin/activate

# install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# start LiveKit Server
livekit-server --dev
