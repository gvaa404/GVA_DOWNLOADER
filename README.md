# GVA Downloader v2.0

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

## Windows Installation

```bat
git clone <repository-url> "GVA Downloader"
cd "GVA Downloader"
install_windows.bat
```

Or manually:

```bat
python -m pip install -U yt-dlp rich
python gva_downloader.py
```

Install FFmpeg on Windows by downloading a build from https://ffmpeg.org/download.html and adding its `bin` folder to your system PATH.

## Termux Installation

```bash
pkg install git -y
git clone <repository-url> "GVA Downloader"
cd "GVA Downloader"
bash install_termux.sh
```

Or manually:

```bash
pkg install python ffmpeg -y
pip install -U yt-dlp rich
termux-setup-storage
python gva_downloader.py
```

## First Run

```bash
python gva_downloader.py
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

Just run the script and use the on-screen menu:

```bash
python gva_downloader.py
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
python gva_downloader.py "https://www.youtube.com/watch?v=XXXXXXXXXXX"
python gva_downloader.py --url "https://youtu.be/XXXXXXXXXXX"
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
python gva_downloader.py --video URL      # jump straight to a video-quality prompt
python gva_downloader.py --audio URL      # jump straight to an audio-format prompt
python gva_downloader.py --info URL       # show media info only, no download
python gva_downloader.py --history        # print download history and exit
python gva_downloader.py --settings       # open the settings menu and exit
python gva_downloader.py --help           # show all options
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
GVA Downloader/
│
├── gva_downloader.py
├── README.md
├── install_windows.bat
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

Copy the entire `GVA Downloader` folder to another machine or another location, and your settings, history, and logs travel with it — nothing is stored outside this folder.

## Updating yt-dlp

From the app: **Engine Maintenance → Update yt-dlp library** (menu option 9 → 1).

Or manually:

```bash
pip install -U yt-dlp
```

Update yt-dlp regularly — YouTube and other sites change frequently, and an outdated yt-dlp is the most common cause of extraction failures.

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
