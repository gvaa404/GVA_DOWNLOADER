#!/data/data/com.termux/files/usr/bin/bash
# =====================================================================
#  GVA Downloader v2.0 - Termux Installer
#  Installs Python dependencies and prepares the application folder.
# =====================================================================
set -e

echo ""
echo "============================================"
echo "  GVA Downloader v2.0 - Termux Setup"
echo "============================================"
echo ""

echo "[1/5] Updating Termux packages..."
pkg update -y

echo "[2/5] Installing Python and FFmpeg..."
pkg install -y python ffmpeg

echo "[3/5] Upgrading pip..."
python -m pip install --upgrade pip

echo "[4/5] Installing dependencies (yt-dlp, rich)..."
python -m pip install -U yt-dlp rich

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[5/5] Creating application folders..."
python "$SCRIPT_DIR/gva_downloader.py" --history >/dev/null 2>&1 || true

echo ""
echo "Setting up storage access (needed to save downloads outside Termux)..."
termux-setup-storage || echo "  (skipped - run 'termux-setup-storage' manually if needed)"

echo ""
echo "Would you like to set up the 'Share to GVA Downloader' workflow now? (y/n)"
read -r SETUP_SHARE
if [ "$SETUP_SHARE" = "y" ] || [ "$SETUP_SHARE" = "Y" ]; then
    mkdir -p "$HOME/bin"
    cat > "$HOME/bin/termux-url-opener" << EOF
#!/data/data/com.termux/files/usr/bin/bash
python "$SCRIPT_DIR/gva_downloader.py" "\$1"
EOF
    chmod +x "$HOME/bin/termux-url-opener"
    echo "Share workflow installed: $HOME/bin/termux-url-opener"
fi

echo ""
echo "============================================"
echo "  Setup complete!"
echo "  Run GVA Downloader with:"
echo "      python gva_downloader.py"
echo "============================================"
