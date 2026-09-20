#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# GVA Downloader v2.0 - Linux Installer
# Linux Mint / Ubuntu / Debian based systems
# ============================================================

APP_NAME="GVA Downloader"
APP_VERSION="2.0"

INSTALL_DIR="${HOME}/.local/share/gva-downloader"
BIN_DIR="${HOME}/.local/bin"
VENV_DIR="${INSTALL_DIR}/venv"
LAUNCHER="${BIN_DIR}/gvad"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_FILE="${SCRIPT_DIR}/src/gva_downloader_2.0.py"
REQUIREMENTS_FILE="${SCRIPT_DIR}/requirements.txt"

# ---------- Colors ----------
if [[ -t 1 ]]; then
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    RED='\033[0;31m'
    CYAN='\033[0;36m'
    RESET='\033[0m'
else
    GREEN=''
    YELLOW=''
    RED=''
    CYAN=''
    RESET=''
fi

info() {
    printf "%b\n" "${CYAN}$1${RESET}"
}

ok() {
    printf "%b\n" "${GREEN}✔ $1${RESET}"
}

warn() {
    printf "%b\n" "${YELLOW}⚠ $1${RESET}"
}

fail() {
    printf "%b\n" "${RED}✘ $1${RESET}" >&2
    exit 1
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

echo
echo "============================================"
echo "      GVA Downloader v${APP_VERSION}"
echo "          Official Linux Installer"
echo "============================================"
echo

# ---------- Check OS ----------
if [[ ! -f /etc/os-release ]]; then
    fail "Cannot identify the Linux distribution."
fi

. /etc/os-release

case "${ID:-}" in
    linuxmint|ubuntu|debian|pop|elementary)
        ;;
    *)
        warn "This installer is designed for Linux Mint/Ubuntu/Debian-based systems."
        warn "Detected: ${PRETTY_NAME:-unknown}"
        ;;
esac

# ---------- Check architecture ----------
ARCH="$(uname -m)"

case "$ARCH" in
    x86_64|amd64)
        ARCH_NAME="Linux x86_64"
        ;;
    aarch64|arm64)
        ARCH_NAME="Linux ARM64"
        ;;
    armv7l)
        ARCH_NAME="Linux ARMv7"
        ;;
    *)
        warn "Unrecognized architecture: $ARCH"
        ARCH_NAME="Linux $ARCH"
        ;;
esac

ok "Environment ready (${ARCH_NAME})"

# ---------- Check project files ----------
[[ -f "$SOURCE_FILE" ]] || fail "GVA source file not found: $SOURCE_FILE"
[[ -f "$REQUIREMENTS_FILE" ]] || fail "requirements.txt not found: $REQUIREMENTS_FILE"

# ---------- Check sudo ----------
if ! command_exists sudo; then
    fail "sudo is required to install system packages."
fi

# ---------- System dependencies ----------
echo
info "[1/5] Checking system dependencies..."

APT_PACKAGES=()

command_exists python3 || APT_PACKAGES+=("python3")
command_exists ffmpeg || APT_PACKAGES+=("ffmpeg")

if ! python3 -m venv --help >/dev/null 2>&1; then
    APT_PACKAGES+=("python3-venv")
fi

if (( ${#APT_PACKAGES[@]} > 0 )); then
    info "Installing: ${APT_PACKAGES[*]}"
    sudo apt-get update
    sudo apt-get install -y "${APT_PACKAGES[@]}"
fi

ok "Python and FFmpeg are ready"

# ---------- Create directories ----------
echo
info "[2/5] Preparing GVA installation..."

mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"

# Copy GVA source
cp "$SOURCE_FILE" "${INSTALL_DIR}/gva_downloader.py"

# Copy requirements
cp "$REQUIREMENTS_FILE" "${INSTALL_DIR}/requirements.txt"

# Copy images if available
if [[ -d "${SCRIPT_DIR}/img" ]]; then
    rm -rf "${INSTALL_DIR}/img"
    cp -a "${SCRIPT_DIR}/img" "${INSTALL_DIR}/img"
fi

ok "Application files installed"

# ---------- Python virtual environment ----------
echo
info "[3/5] Creating Python environment..."

if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
    rm -rf "$VENV_DIR"
    python3 -m venv "$VENV_DIR"
fi

"${VENV_DIR}/bin/python" -m pip install --upgrade pip

# Install project dependencies
"${VENV_DIR}/bin/python" -m pip install \
    -r "${INSTALL_DIR}/requirements.txt"

# Make sure the main dependencies are available
"${VENV_DIR}/bin/python" -m pip install \
    --upgrade yt-dlp rich

ok "yt-dlp and Rich installed"

# ---------- Create gvad command ----------
echo
info "[4/5] Creating 'gvad' command..."

cat > "$LAUNCHER" <<EOF
#!/usr/bin/env bash
set -euo pipefail

APP_NAME="GVA Downloader"
APP_VERSION="${APP_VERSION}"
INSTALL_DIR="${INSTALL_DIR}"
VENV_DIR="${VENV_DIR}"
LAUNCHER="${LAUNCHER}"
BIN_DIR="${BIN_DIR}"

remove_gva() {
    echo
    echo "============================================"
    echo "       Uninstalling GVA Downloader"
    echo "============================================"
    echo

    if [[ ! -d "\$INSTALL_DIR" && ! -f "\$LAUNCHER" ]]; then
        echo "GVA Downloader is not installed."
        exit 0
    fi

    echo "Removing GVA installation:"
    echo "  \$INSTALL_DIR"
    echo

    rm -rf "\$INSTALL_DIR"

    # Remove the launcher itself.
    rm -f "\$LAUNCHER"

    # Remove only the PATH lines added by the GVA installer.
    for rc in "\$HOME/.bashrc" "\$HOME/.zshrc" "\$HOME/.profile" "\$HOME/.config/fish/config.fish"; do
        if [[ -f "\$rc" ]]; then
            sed -i '/# GVA Downloader/d' "\$rc"
            sed -i '/export PATH="\$HOME\/\.local\/bin:\$PATH"/d' "\$rc"
            sed -i '/set -gx PATH \$HOME\/\.local\/bin \$PATH/d' "\$rc"
        fi
    done

    echo
    echo "============================================"
    echo "  GVA Downloader successfully uninstalled"
    echo "============================================"
    echo
    echo "System Python, FFmpeg, and other applications"
    echo "were not removed."
    echo
}

show_help() {
    echo "GVA Downloader v\$APP_VERSION"
    echo
    echo "Usage:"
    echo "  gvad                 Start GVA Downloader"
    echo "  gvad --version       Show GVA version"
    echo "  gvad --uninstall     Uninstall GVA Downloader"
    echo "  gvad --help          Show this help"
    echo
    echo "Downloader options:"
    echo "  gvad --url URL"
    echo "  gvad --video URL"
    echo "  gvad --audio URL"
    echo "  gvad --info URL"
    echo "  gvad --history"
    echo "  gvad --settings"
}

case "\${1:-}" in
    --uninstall)
        remove_gva
        exit 0
        ;;
    --version|-v)
        echo "GVA Downloader v\$APP_VERSION"
        exit 0
        ;;
    --help|-h)
        show_help
        exit 0
        ;;
esac

exec "\$VENV_DIR/bin/python" \
    "\$INSTALL_DIR/gva_downloader.py" "\$@"
EOF

chmod +x "$LAUNCHER"

ok "Launcher installed: ${LAUNCHER}"

# ---------- PATH ----------
echo
info "[5/5] Configuring PATH..."

if [[ ":${PATH}:" != *":${BIN_DIR}:"* ]]; then

    SHELL_NAME="$(basename "${SHELL:-bash}")"

    case "$SHELL_NAME" in
        bash)
            RC_FILE="${HOME}/.bashrc"
            ;;
        zsh)
            RC_FILE="${HOME}/.zshrc"
            ;;
        fish)
            RC_FILE="${HOME}/.config/fish/config.fish"
            ;;
        *)
            RC_FILE="${HOME}/.profile"
            ;;
    esac

    if [[ "$SHELL_NAME" == "fish" ]]; then

        mkdir -p "$(dirname "$RC_FILE")"

        if ! grep -Fq \
            'set -gx PATH $HOME/.local/bin $PATH' \
            "$RC_FILE" 2>/dev/null; then

            printf '\n# GVA Downloader\nset -gx PATH $HOME/.local/bin $PATH\n' \
                >> "$RC_FILE"
        fi

    else

        if ! grep -Fq \
            'export PATH="$HOME/.local/bin:$PATH"' \
            "$RC_FILE" 2>/dev/null; then

            printf '\n# GVA Downloader\nexport PATH="$HOME/.local/bin:$PATH"\n' \
                >> "$RC_FILE"
        fi
    fi

    export PATH="${BIN_DIR}:${PATH}"

    ok "Added ${BIN_DIR} to ${RC_FILE}"

else
    ok "${BIN_DIR} is already in PATH"
fi

# ---------- Verify installation ----------
echo
info "Verifying installation..."

# Verify Python packages
"${VENV_DIR}/bin/python" -c \
    "import yt_dlp; import rich" \
    || fail "Python dependency verification failed."

# Verify FFmpeg
command_exists ffmpeg \
    || fail "FFmpeg verification failed."

# Verify GVA launcher
[[ -x "$LAUNCHER" ]] \
    || fail "GVA launcher was not created."

# Verify GVA management commands
VERSION_OUTPUT="$("$LAUNCHER" --version 2>&1)"
[[ "$VERSION_OUTPUT" == "GVA Downloader v${APP_VERSION}" ]] \
    || fail "GVA version command verification failed."

HELP_OUTPUT="$("$LAUNCHER" --help 2>&1)"
printf '%s\n' "$HELP_OUTPUT" | grep -Fq "gvad --uninstall" \
    || fail "GVA help command verification failed."

# Get versions
PYTHON_VERSION="$(
    "${VENV_DIR}/bin/python" --version 2>&1
)"

YTDLP_VERSION="$(
    "${VENV_DIR}/bin/python" -c \
    'import yt_dlp; print(yt_dlp.version.__version__)'
)"

FFMPEG_VERSION="$(
    ffmpeg -version 2>/dev/null \
    | head -n 1
)"

ok "Installation verified"

# ---------- Final output ----------
echo
echo "============================================"
echo "  ${APP_NAME} v${APP_VERSION}"
echo "       successfully installed!"
echo "============================================"
echo
echo "  • Command:     gvad"
echo "  • Install:     ${INSTALL_DIR}"
echo "  • Python:      ${PYTHON_VERSION}"
echo "  • yt-dlp:      ${YTDLP_VERSION}"
echo "  • FFmpeg:      ${FFMPEG_VERSION}"
echo
echo "Start GVA Downloader with:"
echo
echo "    gvad"
echo
echo "Management commands:"
echo
echo "    gvad --version"
echo "    gvad --help"
echo "    gvad --uninstall"
echo

if [[ ":${PATH}:" != *":${BIN_DIR}:"* ]]; then
    echo "If 'gvad' is not found, run:"
    echo
    echo "    source ~/.bashrc"
    echo
    echo "Then:"
    echo
    echo "    gvad"
    echo
fi

echo "============================================"
echo "          GVA Downloader Ready"
echo "============================================"
echo

