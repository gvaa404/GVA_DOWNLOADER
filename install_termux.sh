#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

APP_NAME="GVA Downloader"
APP_VERSION="2.1"
REPO_URL="https://github.com/gvaa404/GVA_DOWNLOADER.git"
INSTALL_DIR="$HOME/.local/share/gva-downloader"
BIN_DIR="$PREFIX/bin"
VENV_DIR="$INSTALL_DIR/venv"
LAUNCHER="$BIN_DIR/gvad"

echo
echo "============================================"
echo "   GVA Downloader v${APP_VERSION}"
echo "       One-Click Termux Installer"
echo "============================================"
echo

echo "[1/5] Updating Termux packages..."
pkg update -y >/dev/null

echo "[2/5] Installing required packages..."
pkg install -y git python ffmpeg >/dev/null

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

echo "[3/5] Downloading GVA Downloader..."
git clone --depth 1 "$REPO_URL" "$TMP_DIR/repo" >/dev/null 2>&1

SOURCE_FILE="$(find "$TMP_DIR/repo/src" -maxdepth 1 -type f -name 'gva_downloader*.py' -print 2>/dev/null | sort -V | tail -n 1)"
[ -n "$SOURCE_FILE" ] || { echo "No GVA source found."; exit 1; }

echo "[4/5] Installing GVA..."
mkdir -p "$INSTALL_DIR" "$BIN_DIR"
cp "$SOURCE_FILE" "$INSTALL_DIR/gva_downloader.py"
cp "$TMP_DIR/repo/requirements.txt" "$INSTALL_DIR/requirements.txt"
if [ -d "$TMP_DIR/repo/img" ]; then
    rm -rf "$INSTALL_DIR/img"
    cp -a "$TMP_DIR/repo/img" "$INSTALL_DIR/img"
fi

rm -rf "$VENV_DIR"
python -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --upgrade pip >/dev/null
"$VENV_DIR/bin/python" -m pip install -r "$INSTALL_DIR/requirements.txt" >/dev/null

cat > "$LAUNCHER" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
APP_VERSION="${APP_VERSION}"
INSTALL_DIR="${INSTALL_DIR}"
VENV_DIR="${VENV_DIR}"
LAUNCHER="${LAUNCHER}"

case "\${1:-}" in
    --version|-v)
        echo "GVA Downloader v\${APP_VERSION}"
        exit 0
        ;;
    --help|-h)
        echo "GVA Downloader v\${APP_VERSION}"
        echo
        echo "  gvad                 Start GVA"
        echo "  gvad --version       Show version"
        echo "  gvad --help          Show help"
        echo "  gvad --uninstall     Uninstall GVA"
        exit 0
        ;;
    --uninstall)
        PRESERVE="\$HOME/GVA-Downloads"
        if [ -d "\$INSTALL_DIR/downloads" ]; then
            if [ -e "\$PRESERVE" ]; then
                echo "Cannot uninstall safely: \$PRESERVE already exists."
                exit 1
            fi
            mv "\$INSTALL_DIR/downloads" "\$PRESERVE"
            echo "Downloads preserved at: \$PRESERVE"
        fi
        rm -rf "\$INSTALL_DIR"
        rm -f "\$LAUNCHER"
        echo "GVA Downloader successfully uninstalled."
        exit 0
        ;;
esac

exec "\$VENV_DIR/bin/python" "\$INSTALL_DIR/gva_downloader.py" "\$@"
EOF
chmod +x "$LAUNCHER"

echo "[5/5] Setting up Android storage access..."
termux-setup-storage >/dev/null 2>&1 || true

echo
echo "============================================"
echo "   GVA Downloader installed"
echo "============================================"
echo
echo "Start:       gvad"
echo "Version:     gvad --version"
echo "Help:        gvad --help"
echo "Uninstall:   gvad --uninstall"
echo
