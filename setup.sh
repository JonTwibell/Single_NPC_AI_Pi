#!/usr/bin/env bash

set -e

echo "=== Raspberry Pi Audio AI Setup Script ==="

# 1. Update package list
echo "[+] Updating system package index..."
sudo apt-get update -y

# 2. Install ALSA, PortAudio, and Audio Players
echo "[+] Installing system audio libraries and drivers..."
sudo apt-get install -y \
    python3-dev \
    python3-pip \
    python3-venv \
    portaudio19-dev \
    libasound2-dev \
    alsa-utils \
    mpg123 \
    ffmpeg

# 3. Create virtual environment
if [ ! -d "venv" ]; then
    echo "[+] Creating Python virtual environment (venv)..."
    python3 -m venv venv
fi

# 4. Activate VENV & Upgrade Pip
echo "[+] Activating virtual environment & updating pip..."
source venv/bin/activate
pip install --upgrade pip

# 5. Install Required Python Libraries
echo "[+] Installing required Python packages..."
pip install pyaudio python-dotenv groq elevenlabs

# 6. Setup Directory Structure
echo "[+] Setting up pre-roll directories..."
mkdir -p statement question

# 7. Setup .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "[+] Generating default .env template..."
    cat <<EOT > .env
GROQ_API_KEY=your_groq_api_key_here
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
EOT
    echo "[!] Created .env file. Please populate it with your actual API keys before running."
fi

echo "=================================================="
echo "Setup complete!"
echo "To run your assistant:"
echo " 1. Edit .env with your keys: nano .env"
echo " 2. Activate virtual environment: source venv/bin/activate"
echo " 3. Run the application: python3 SingleCharacter.py"
echo "=================================================="