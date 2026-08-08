# 🎬 GVA Downloader v2.0

Welcome to **GVA Downloader**! This is a simple, colorful terminal application that lets you easily download videos, audio, and entire playlists straight to your phone or computer. 

Powered by `yt-dlp` and `rich`, it provides a beautiful interface with live progress bars right in your terminal. This new v2.0 is fully portable and supports a direct-URL command-line workflow!

---

## ✨ Features

* **Portable Application Folder:** All settings, history, logs, and downloads stay in the same folder as the script.
* **Direct URL Workflow:** Call the script directly from the command line: `python gva_downloader.py "<url>"`.
* **Video & Audio:** Download in the exact quality you want (from 144p up to 4K/8K, or MP3/M4A/FLAC).
* **Playlists & Batch:** Download full playlists, specific ranges, or batch process multiple links.
* **Metadata & SponsorBlock:** Automatically adds thumbnails (cover art) and skips sponsor segments.
* **Beautiful Interface:** Easy-to-use numbered menus and visual progress bars.

---

## 📱 How to Install & Run on Android (Termux)

**Step 1: Install Termux**
Download the Termux app from [F-Droid](https://f-droid.org/en/packages/com.termux/). Do not use the Google Play Store version, as it is outdated.

**Step 2: Run the Setup Script**
Open Termux, navigate to the folder where you saved the project, make the script executable, and run it:
`chmod +x setup_termux.sh`
`./setup_termux.sh`

This script will automatically request storage permissions, update your system, install required packages (Python, Git, FFmpeg), and install the Python libraries (`yt-dlp`, `rich`). Finally, it will launch the downloader.

**Future Runs:**
Once setup is complete, you can start the application anytime by navigating to the project folder and running:
`cd src`
`python gva_downloader_2.0.py`

---

## 💻 How to Install & Run on Windows

**Step 1: Install Python & FFmpeg**
1. **Python**: Go to [python.org/downloads](https://www.python.org/downloads/) and install the latest version. **CRITICAL:** Check the box that says **"Add Python to PATH"** before clicking install.
2. **FFmpeg**: Open PowerShell as Administrator and run: `winget install "FFmpeg (Essentials Build)"`

**Step 2: Run the Setup Batch File**
Download this project and extract it. Double-click the `setup_windows.bat` file. 

This batch file will automatically install the necessary Python libraries (`yt-dlp` and `rich`) and then launch the application for you.

**Future Runs:**
You can just double-click `setup_windows.bat` anytime to run the app, or manually run:
`cd src`
`python gva_downloader_2.0.py`

**Step 3: Configure Windows Download Folder**
By default, downloads go to the `src/downloads/` folder. You can type `8` for Settings, then `1` to change your Download Folder to an absolute path (like `C:\Users\YourName\Downloads`).

---

## 🎮 How to Use the Menu

Type the number of the action you want to perform and press Enter:

| Option | Name | Description |
| :--- | :--- | :--- |
| **1** | 🎬 Download Video | Paste a link and choose your video quality. |
| **2** | 🎵 Download Audio | Extract music/audio and choose your format (MP3, FLAC, etc.). |
| **3** | 📜 Playlist Download | Paste a playlist link to grab multiple files at once. |
| **4** | 🔍 Search YouTube & Download | Search keywords directly without opening a browser. |
| **5** | 📁 Batch Downloads | Download multiple URLs from a list or file. |
| **6** | ℹ️ Media Information | Paste a link to see details without downloading. |
| **7** | 🕘 Download History | See a list of everything you've downloaded previously. |
| **8** | ⚙️ Settings | Change where files are saved, your default quality, or app themes. |
| **9** | 🛠️ Engine Maintenance | Update yt-dlp or clear application cache. |
| **10** | ❓ Help | View helpful hints and feature descriptions. |
| **11** | 📖 About | View app version and author information. |
| **12** | 🚪 Exit | Close the downloader safely. |

---

## 🚀 Command-Line Usage

You can bypass the menu by using command-line arguments:
- `python src/gva_downloader_2.0.py "<url>"` : Opens a quick download menu for the URL.
- `python src/gva_downloader_2.0.py --video "<url>"` : Quick video download.
- `python src/gva_downloader_2.0.py --audio "<url>"` : Quick audio download.
- `python src/gva_downloader_2.0.py --info "<url>"` : Show media info only.
- `python src/gva_downloader_2.0.py --history` : Print download history and exit.
- `python src/gva_downloader_2.0.py --settings` : Open the settings menu and exit.

---

## 🛠️ Troubleshooting & Logs

If something goes wrong or a download fails, GVA Downloader keeps log files to help you figure out why. Because this is a **portable** application, you will find settings and logs in the same folder as the script:

* **Settings File:** `config/settings.json`
* **Error Logs:** `logs/gva_downloader.log`
* **History:** `history/history.json`

---

## 📄 License

This project is open-source and free to use under the MIT License.