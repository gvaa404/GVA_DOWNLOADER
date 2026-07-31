# 🎬 GVA Downloader

Welcome to **GVA Downloader**! This is a simple, colorful terminal application that lets you easily download videos, audio, and entire playlists straight to your phone or computer. 

Powered by `yt-dlp` and `rich`, it provides a beautiful interface with live progress bars right in your terminal.

---

## ✨ Features

* **Video & Audio:** Download in the exact quality you want (from 144p up to 4K/8K, or MP3/M4A/FLAC).
* **Playlists:** Download full playlists, specific ranges (like videos 1 through 5), or just a single video.
* **Metadata:** Automatically adds thumbnails (cover art) and video details to your downloaded files.
* **SponsorBlock:** Optionally skip or remove annoying sponsor segments from videos.
* **Beautiful Interface:** Easy-to-use numbered menus and visual progress bars.

---

## 📱 How to Install & Run on Android (Termux)

**Step 1: Install Termux**
Download the Termux app from [F-Droid](https://f-droid.org/en/packages/com.termux/). Do not use the Google Play Store version, as it is outdated.

**Step 2: Update System & Grant Storage Access**
Open Termux and run the following command. A popup will appear asking for storage access—click "Allow".
`pkg update && pkg upgrade -y && termux-setup-storage`

**Step 3: Install Required Tools**
Run this command to install the necessary system packages:
`pkg install python git ffmpeg -y`

**Step 4: Install Python Libraries**
Run this command to get the required Python modules:
`pip install rich yt-dlp requests`

**Step 5: Run the App**
Navigate to the script folder, make it executable, and start the downloader:
`chmod +x gva_downloader.py`
`python gva_downloader.py`

---

## 💻 How to Install & Run on Windows

**Step 1: Install Python**
Go to [python.org/downloads](https://www.python.org/downloads/) and download the latest installer. **CRITICAL:** Check the box that says **"Add Python to PATH"** at the bottom of the installation window before clicking install.

**Step 2: Install FFmpeg**
Click the Windows Start button, type **PowerShell**, right-click it, and select **Run as Administrator**. Run this command and close the window when it finishes:
`winget install "FFmpeg (Essentials Build)"`

**Step 3: Download the Project**
Download this project to your computer and extract the folder to your Desktop or preferred location.

**Step 4: Install Required Libraries**
Open the extracted project folder. Click on the folder address bar at the top, type `cmd`, and press Enter. In the command prompt window, run:
`pip install rich yt-dlp requests`

**Step 5: Run the App**
In the same command prompt, start the application by running:
`python gva_downloader.py`

**Step 6: Configure Windows Download Folder**
The first time you run the app, type `6` for Settings, then `1` to change your Download Folder. Type in a Windows path (like `C:\Users\YourName\Downloads`) so your files save correctly.

---

## 🎮 How to Use the Menu

Type the number of the action you want to perform and press Enter:

| Option | Name | Description |
| :--- | :--- | :--- |
| **1** | 🎬 Download Video | Paste a link and choose your video quality. |
| **2** | 🎵 Download Audio | Extract music/audio and choose your format (MP3, FLAC, etc.). |
| **3** | 📜 Playlist Download | Paste a playlist link to grab multiple files at once. |
| **4** | ℹ️ Video Information | Paste a link to see details (views, length, formats) without downloading. |
| **5** | 🕘 Download History | See a list of everything you've downloaded previously. |
| **6** | ⚙️ Settings | Change where files are saved, your default quality, or app themes. |
| **7** | ❓ Help | Check if your system has all the required tools installed. |
| **8** | 📖 About | View app version and author information. |
| **9** | 🚪 Exit | Close the downloader safely. |

---

## 🛠️ Troubleshooting & Logs

If something goes wrong or a download fails, GVA Downloader keeps log files to help you figure out why. You can find your settings and logs at these locations on your system:

* **Settings File:** `~/.gva_downloader/settings.json`
* **Error Logs:** `~/.gva_downloader/gva_downloader.log`

---

## 📄 License

This project is open-source and free to use under the MIT License.