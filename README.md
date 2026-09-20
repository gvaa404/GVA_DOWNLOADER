# GVA Downloader v2.1

A polished, terminal-based media downloader built on [yt-dlp](https://github.com/yt-dlp/yt-dlp) and [Rich](https://github.com/Textualize/rich). Fully **portable** — everything the app owns lives inside its own folder, and it runs the same way on **Windows, Linux, macOS, and Android (Termux)**.

## Features

- 🎬 Video downloads with dynamic, real quality options (up to 4K where available)
- 🎵 Audio downloads in MP3, M4A, AAC, FLAC, OGG, WAV
- 📜 Playlist downloads (entire or a custom range), as video or audio
- 🔍 In-app YouTube search
- 📁 Batch downloads (pasted URLs or a text file)
- ℹ️ Media information without downloading
- 🕘 Download history with search, delete, and "open location"
- ⚙️ Configurable download folder, quality defaults, theme, overwrite behavior
- 🛠️ Engine maintenance: update yt-dlp, clear caches
- 🔗 **Direct URL / share-to-download**: run with a URL as an argument, or share a video straight from the YouTube app on Android
- 📂 One portable application folder — copy it anywhere and it keeps working

## Requirements

- Python 3.9+
- [FFmpeg](https://ffmpeg.org/) (for merging video/audio, converting audio formats, embedding thumbnails)
- Python packages: `yt-dlp`, `rich`

## Linux Installation

### One-command installer

For Linux Mint, Ubuntu, Debian, and compatible Debian-based systems:

```bash
curl -fsSL https://raw.githubusercontent.com/gvaa404/GVA_DOWNLOADER/main/install_linux.sh | bash
```

Then start GVA:

```bash
gvad
```

Management commands:

```bash
gvad --version
gvad --help
gvad --uninstall
```

### Manual installation

```bash
git clone https://github.com/gvaa404/GVA_DOWNLOADER.git "GVA Downloader"
cd "GVA Downloader"
bash install_linux.sh
```

The Linux installer checks for Python, Python virtual-environment support, and FFmpeg, installs missing system packages, creates GVA's isolated Python environment, and installs the `gvad` command.

## Installer Files

The repository includes installers for:

- Linux: [`install_linux.sh`](./install_linux.sh)
- Windows Batch: [`install_windows.bat`](./install_windows.bat)
- Windows PowerShell: [`install_windows.ps1`](./install_windows.ps1)
- Android / Termux: [`install_termux.sh`](./install_termux.sh)

## Windows Installation

### One-command PowerShell installer

Open PowerShell and run:

```powershell
irm https://raw.githubusercontent.com/gvaa404/GVA_DOWNLOADER/main/install_windows.ps1 | iex
```

After installation, open a new PowerShell or Command Prompt window and run:

```powershell
gvad
```

Management commands:

```powershell
gvad --version
gvad --help
gvad --uninstall
```

### Double-click installer

Download [`install_windows.bat`](./install_windows.bat) and double-click it.

The `.bat` installer launches the PowerShell installer and completes the same setup.

### Manual installation

```powershell
git clone https://github.com/gvaa404/GVA_DOWNLOADER.git "GVA Downloader"
cd "GVA Downloader"
python -m pip install -U yt-dlp rich
python src\gva_downloader_2.1.py
```

FFmpeg is required. The Windows installer checks for it and installs it with WinGet when it is missing.

## Termux Installation

### One-command installer

Run:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/gvaa404/GVA_DOWNLOADER/main/install_termux.sh)
```

Then start GVA:

```bash
gvad
```

Management commands:

```bash
gvad --version
gvad --help
gvad --uninstall
```

### Manual installation

```bash
pkg install git python ffmpeg -y
git clone https://github.com/gvaa404/GVA_DOWNLOADER.git "GVA Downloader"
cd "GVA Downloader"
bash install_termux.sh
```

The installer also requests Android storage access and can configure the YouTube → Termux → GVA share workflow.

## First Run

After using an installer, start GVA with:

```bash
gvad
```

For a manual/source checkout, you can run:

```bash
python src/gva_downloader_2.1.py
```

On first run GVA automatically creates everything it needs inside the application folder:

```
downloads/videos/
downloads/audios/
config/settings.json
history/history.json
logs/gva_downloader.log
cache/
temp/
```

No manual setup is required.

## Normal Usage

After installation, run the `gvad` command and use the on-screen menu:

```bash
gvad
```

For a manual/source checkout:

```bash
python src/gva_downloader_2.1.py
```

```
1. 🎬 Download Video
2. 🎵 Download Audio
3. 📜 Playlist Download
4. 🔍 Search YouTube
5. 📁 Batch Downloads
6. ℹ️ Media Information
7. 🕘 Download History
8. ⚙️ Settings
9. 🛠️ Engine Maintenance
10. ❓ Help
11. 📖 About
12. 🚪 Exit
```

## Direct URL Usage

Pass a URL straight from the command line and skip the main menu:

```bash
gvad "https://www.youtube.com/watch?v=XXXXXXXXXXX"
gvad --url "https://youtu.be/XXXXXXXXXXX"
```

This opens a quick menu:

```
1. Download Video
2. Download Audio
3. Download Best Quality
4. View Information
5. Cancel
```

Other quick command-line options:

```bash
gvad --video URL      # jump straight to a video-quality prompt
gvad --audio URL      # jump straight to an audio-format prompt
gvad --info URL       # show media info only, no download
gvad --history        # print download history and exit
gvad --settings       # open the settings menu and exit
gvad --help           # show all options
```

Supported URL forms include standard YouTube links, `youtu.be` short links, and YouTube Shorts — anything yt-dlp's extractor system recognizes.

## YouTube Share → Termux → GVA Downloader

You can share a video directly from the YouTube app to GVA Downloader, with no copy-pasting:

1. Run `install_termux.sh` and answer **y** when asked about the share workflow (or set it up manually, below).
2. In the YouTube app, tap **Share** on any video, then choose **Termux**.
3. Termux launches `~/bin/termux-url-opener`, which passes the shared URL straight to GVA Downloader's quick download menu.

**Manual setup:**

```bash
mkdir -p ~/bin
cat > ~/bin/termux-url-opener << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash
python "/path/to/GVA Downloader/gva_downloader.py" "$1"
EOF
chmod +x ~/bin/termux-url-opener
```

Replace `/path/to/GVA Downloader` with the actual path where you cloned the project. If your downloads need to be visible outside Termux (e.g. in your phone's gallery/Downloads app), run `termux-setup-storage` once and point the **Download Folder** setting at a path under `~/storage/downloads/`.

## Changing Download Folder

Open **Settings → Download Folder** (menu option 8 → 1), or run:

```bash
python gva_downloader.py --settings
```

You can enter:

- A **relative** path (default: `downloads`) — resolved inside the GVA Downloader folder, keeping the project fully portable.
- An **absolute** path (e.g. `D:\My Downloads\GVA` or `/storage/emulated/0/Download/GVA`) — GVA will create `videos/` and `audios/` subfolders there.

Application data (`config/`, `history/`, `logs/`, `cache/`, `temp/`) **always** stays inside the GVA Downloader folder, even if you move your downloads elsewhere.

## Folder Structure

```
GVA_DOWNLOADER/
│
├── src/
│   └── gva_downloader_2.1.py
│
├── img/
│
├── README.md
├── LICENSE
├── requirements.txt
│
├── install_linux.sh
├── install_windows.bat
├── install_windows.ps1
├── install_termux.sh
│
├── downloads/
│   ├── videos/
│   └── audios/
│
├── config/
│   └── settings.json
│
├── history/
│   └── history.json
│
├── logs/
│   └── gva_downloader.log
│
├── cache/
└── temp/
```

Copy the entire GVA application folder to another location, and its settings, history, and logs travel with it. Installed copies using `gvad` keep their application data inside GVA's installation directory.

## Updating yt-dlp

From the app: **Engine Maintenance → Update yt-dlp library** (menu option 9 → 1).

Or manually:

```bash
pip install -U yt-dlp
```

Update yt-dlp regularly — YouTube and other sites change frequently, and an outdated yt-dlp is the most common cause of extraction failures.

## Uninstall

For an installed copy of GVA Downloader:

```bash
gvad --uninstall
```

On Windows the same command works from PowerShell or Command Prompt:

```powershell
gvad --uninstall
```

The uninstall process removes GVA's installed application files and launcher without removing system Python, FFmpeg, or unrelated applications.

## Troubleshooting

| Problem | Fix |
|---|---|
| `FFmpeg is not installed` | Windows: install from ffmpeg.org and add to PATH. Termux: `pkg install ffmpeg`. Linux: `sudo apt install ffmpeg`. macOS: `brew install ffmpeg`. |
| Download fails / extraction error | Update yt-dlp (Engine Maintenance → Update, or `pip install -U yt-dlp`). |
| "This video is private/age-restricted" | GVA cannot bypass authentication or access controls — you need to be authorized to access that content. |
| Files not showing on my phone | Make sure `termux-setup-storage` has been run and your Download Folder setting points to a path under `~/storage/`. |
| Duplicate file prompt keeps appearing | Turn on **Overwrite Existing Files** in Settings if you always want to overwrite. |

Technical error details are always written to `logs/gva_downloader.log`.

## Responsible Use

GVA Downloader uses yt-dlp as its download engine and performs no custom scraping. It does not bypass DRM, authentication, or paywalls. Only use it to download content you are authorized to access and download, and respect the terms of service of the sites you use it with.
