#!/usr/bin/env python3
"""
GVA Downloader
==============

A premium terminal-based media downloader for Windows, Linux, macOS and
Android/Termux.

Author   : Jeevanantham K
Engine   : yt-dlp
Language : Python
Platform : Windows / Linux / macOS / Android (Termux)
Version  : 2.0 (Portable Application Folder + Direct URL / Share Workflow)

--------------------------------------------------------------------------
WHAT CHANGED IN v2.0
--------------------------------------------------------------------------
* The application is now fully "portable": every file GVA owns (settings,
  history, logs, cache, temp) lives inside the same folder as this script
  (APP_DIR), instead of a hidden folder in the user's home directory.
* Downloaded videos and audio are separated into "downloads/videos" and
  "downloads/audios" (or a custom root the user picks in Settings).
* New direct-URL / command-line workflow so the script can be invoked as
  `python gva_downloader.py "<url>"` (also used by the Termux share sheet).
* Safer filename sanitizer, duplicate-file handling, startup dependency
  check, and a fixed SponsorBlock post-processor pipeline.
--------------------------------------------------------------------------
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import (
        Progress,
        BarColumn,
        TextColumn,
        TimeElapsedColumn,
        TimeRemainingColumn,
        DownloadColumn,
        TransferSpeedColumn,
    )
    from rich.prompt import Prompt, Confirm
    from rich.align import Align
    from rich.text import Text
    from rich.rule import Rule
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

try:
    import yt_dlp
    YTDLP_AVAILABLE = True
except ImportError:
    yt_dlp = None  # type: ignore
    YTDLP_AVAILABLE = False


# =====================================================================
# EARLY DEPENDENCY GUARD
# =====================================================================
# Rich is required to render anything at all, so if it's missing we print
# a plain-text message (no Rich formatting available yet) and exit instead
# of crashing with an ImportError traceback.

if not RICH_AVAILABLE:
    print("=" * 60)
    print("GVA Downloader - Missing dependency: 'rich'")
    print("=" * 60)
    print("Install dependencies with:")
    print("    pip install -U yt-dlp rich")
    print("(Termux users may need: pkg install python && pip install -U yt-dlp rich)")
    sys.exit(1)


# =====================================================================
# CONSTANTS
# =====================================================================

APP_NAME = "GVA Downloader"
APP_AUTHOR = "Jeevanantham K"
APP_VERSION = "2.0"
APP_ENGINE = "yt-dlp"
APP_LANGUAGE = "Python"
APP_PLATFORM = "Windows / Linux / macOS / Android (Termux)"

# ---------------------------------------------------------------------
# PORTABLE APPLICATION ROOT
# ---------------------------------------------------------------------
# Everything GVA Downloader owns lives inside this folder. Never write
# GVA's own config/history/logs/cache to the user's home directory or any
# OS-specific hidden folder.
APP_DIR: Path = Path(__file__).resolve().parent

CONFIG_DIR = APP_DIR / "config"
HISTORY_DIR = APP_DIR / "history"
LOGS_DIR = APP_DIR / "logs"
CACHE_DIR = APP_DIR / "cache"
TEMP_DIR = APP_DIR / "temp"
DEFAULT_DOWNLOADS_DIR = APP_DIR / "downloads"

SETTINGS_FILE = CONFIG_DIR / "settings.json"
HISTORY_FILE = HISTORY_DIR / "history.json"
LOG_FILE = LOGS_DIR / "gva_downloader.log"

APP_OWNED_DIRS = [CONFIG_DIR, HISTORY_DIR, LOGS_DIR, CACHE_DIR, TEMP_DIR, DEFAULT_DOWNLOADS_DIR]

LOGO = r"""
[bold cyan]
 ██████╗  ██╗   ██╗ █████╗
██╔════╝ ██║   ██║██╔══██╗
██║  ███╗██║   ██║███████║
██║   ██║╚██╗ ██╔╝██╔══██║
╚██████╔╝ ╚████╔╝ ██║  ██║
 ╚═════╝   ╚═══╝  ╚═╝  ╚═╝
[/bold cyan]
[bold magenta]        GVA Downloader v2.0[/bold magenta]
"""

AUDIO_FORMATS = ["MP3", "M4A", "AAC", "FLAC", "OGG", "WAV"]

# Windows reserved device names that are unsafe as filenames.
WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

console = Console()


# =====================================================================
# LOGGING
# =====================================================================

def setup_logging() -> logging.Logger:
    """Configure and return the application logger.

    Logs are written ONLY to logs/gva_downloader.log inside APP_DIR.
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logger_obj = logging.getLogger("gva_downloader")
    logger_obj.setLevel(logging.DEBUG)
    if not logger_obj.handlers:
        try:
            handler: logging.Handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        except OSError:
            handler = logging.StreamHandler(sys.stderr)
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )
        handler.setFormatter(formatter)
        logger_obj.addHandler(handler)
    return logger_obj


logger = setup_logging()
logger.info("=" * 50)
logger.info("GVA Downloader v%s starting up (APP_DIR=%s)", APP_VERSION, APP_DIR)


# =====================================================================
# UTILITIES
# =====================================================================

class Utilities:
    """A collection of static helper functions used across the app."""

    @staticmethod
    def human_size(num_bytes: Optional[float]) -> str:
        """Convert a byte count into a human-readable string."""
        if num_bytes is None:
            return "Unknown"
        try:
            num = float(num_bytes)
        except (TypeError, ValueError):
            return "Unknown"
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if num < 1024.0:
                return f"{num:.2f} {unit}"
            num /= 1024.0
        return f"{num:.2f} PB"

    @staticmethod
    def human_duration(seconds: Optional[float]) -> str:
        """Convert seconds into HH:MM:SS format."""
        if seconds is None:
            return "Unknown"
        try:
            total = int(seconds)
        except (TypeError, ValueError):
            return "Unknown"
        hours, remainder = divmod(total, 3600)
        minutes, secs = divmod(remainder, 60)
        if hours:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    @staticmethod
    def human_number(value: Optional[int]) -> str:
        """Format a large number with thousands separators."""
        if value is None:
            return "Unknown"
        try:
            return f"{int(value):,}"
        except (TypeError, ValueError):
            return "Unknown"

    @staticmethod
    def sanitize_filename(name: str, max_length: int = 150) -> str:
        """Produce a filesystem-safe filename while keeping it readable.

        Handles: reserved characters, Windows reserved device names,
        unicode, trailing dots/spaces, and overly long names.
        """
        if not name:
            return "Untitled"

        # Remove/replace characters invalid on Windows (also unsafe elsewhere).
        invalid = '<>:"/\\|?*'
        cleaned = "".join("_" if ch in invalid else ch for ch in name)

        # Strip control characters but keep unicode letters/symbols intact.
        cleaned = "".join(ch for ch in cleaned if ch.isprintable())

        # Collapse whitespace.
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        # Remove trailing dots/spaces (illegal on Windows).
        cleaned = cleaned.rstrip(". ")

        if not cleaned:
            cleaned = "Untitled"

        # Avoid Windows reserved device names (CON, PRN, COM1, ...).
        stem = cleaned.split(".")[0].upper()
        if stem in WINDOWS_RESERVED_NAMES:
            cleaned = f"_{cleaned}"

        # Enforce a sane max length while keeping the file extension if any.
        if len(cleaned) > max_length:
            if "." in cleaned[-6:]:
                name_part, _, ext_part = cleaned.rpartition(".")
                keep = max_length - len(ext_part) - 1
                cleaned = f"{name_part[:keep]}.{ext_part}"
            else:
                cleaned = cleaned[:max_length]

        return cleaned or "Untitled"

    @staticmethod
    def ensure_dir(path: Path) -> bool:
        """Create a directory (and parents) if it doesn't already exist."""
        try:
            path.mkdir(parents=True, exist_ok=True)
            return True
        except PermissionError:
            logger.error("Permission denied creating directory: %s", path)
            return False
        except OSError as exc:
            logger.error("OS error creating directory %s: %s", path, exc)
            return False

    @staticmethod
    def which(binary: str) -> Optional[str]:
        """Locate a binary on PATH, returning its path or None."""
        return shutil.which(binary)

    @staticmethod
    def open_folder(path: Path) -> bool:
        """Attempt to open a folder using the platform's file manager."""
        try:
            if Utilities.which("termux-open"):
                subprocess.run(["termux-open", str(path)], check=False)
                return True
            if sys.platform.startswith("win"):
                os.startfile(str(path))  # type: ignore[attr-defined]
                return True
            if sys.platform == "darwin" and Utilities.which("open"):
                subprocess.run(["open", str(path)], check=False)
                return True
            if Utilities.which("xdg-open"):
                subprocess.run(["xdg-open", str(path)], check=False)
                return True
            console.print(f"[yellow]Could not auto-open folder. Path: {path}[/yellow]")
            return False
        except Exception as exc:
            logger.error("Failed to open folder: %s", exc)
            return False

    @staticmethod
    def ensure_app_directories() -> None:
        """Create every folder GVA Downloader owns, if missing."""
        for d in APP_OWNED_DIRS:
            Utilities.ensure_dir(d)
        Utilities.ensure_dir(DEFAULT_DOWNLOADS_DIR / "videos")
        Utilities.ensure_dir(DEFAULT_DOWNLOADS_DIR / "audios")

    @staticmethod
    def check_dependencies() -> Dict[str, bool]:
        """Return availability status of Python, yt-dlp, Rich and FFmpeg."""
        return {
            "Python": True,
            "yt-dlp": YTDLP_AVAILABLE,
            "Rich": RICH_AVAILABLE,
            "FFmpeg": Utilities.which("ffmpeg") is not None,
        }


# =====================================================================
# THEME
# =====================================================================

class Theme:
    """Centralized color/style theme for the whole application."""

    THEMES: Dict[str, Dict[str, str]] = {
        "default": {
            "primary": "cyan",
            "secondary": "magenta",
            "accent": "yellow",
            "success": "bold green",
            "error": "bold red",
            "warning": "bold yellow",
            "info": "bold cyan",
            "muted": "grey62",
        },
        "ocean": {
            "primary": "blue",
            "secondary": "cyan",
            "accent": "bright_cyan",
            "success": "bold green",
            "error": "bold red",
            "warning": "bold yellow",
            "info": "bold blue",
            "muted": "grey62",
        },
        "sunset": {
            "primary": "red",
            "secondary": "yellow",
            "accent": "bright_magenta",
            "success": "bold green",
            "error": "bold red",
            "warning": "bold yellow",
            "info": "bold magenta",
            "muted": "grey62",
        },
    }

    def __init__(self, name: str = "default") -> None:
        self.name = name if name in self.THEMES else "default"

    @property
    def colors(self) -> Dict[str, str]:
        return self.THEMES[self.name]

    def style(self, key: str) -> str:
        return self.colors.get(key, "white")


# =====================================================================
# VALIDATOR
# =====================================================================

class Validator:
    """Validation routines for user input."""

    YOUTUBE_HOSTS = ("youtube.com", "youtu.be", "m.youtube.com", "music.youtube.com")

    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Basic structural validation for a URL string."""
        if not url or not isinstance(url, str):
            return False
        url = url.strip()
        if not (url.startswith("http://") or url.startswith("https://")):
            return False
        if " " in url:
            return False
        return True

    @staticmethod
    def is_valid_range(range_str: str, maximum: int) -> bool:
        """Validate a playlist range string like '1-5'."""
        try:
            parts = range_str.split("-")
            if len(parts) != 2:
                return False
            start, end = int(parts[0]), int(parts[1])
            return 1 <= start <= end <= maximum
        except (ValueError, IndexError):
            return False


# =====================================================================
# SETTINGS & HISTORY
# =====================================================================

@dataclass
class AppSettings:
    """Persisted user settings (config/settings.json).

    `download_folder` may be either:
      * a relative path (resolved against APP_DIR), e.g. "downloads" -> the
        default, portable behaviour, or
      * an absolute path the user picked in Settings, e.g. "D:\\My Downloads\\GVA".

    In both cases GVA creates "videos" and "audios" subfolders inside it.
    Application data (config/history/logs/cache/temp) NEVER moves — only the
    download root changes.
    """

    download_folder: str = "downloads"
    default_video_quality: str = "Best Available"
    default_audio_quality: str = "Best Available"
    theme: str = "default"
    filename_format: str = "%(title)s.%(ext)s"
    overwrite_existing: bool = False


class Settings:
    """Loads/saves settings.json inside APP_DIR/config."""

    def __init__(self) -> None:
        self.data = AppSettings()
        self.load()

    def load(self) -> None:
        try:
            if SETTINGS_FILE.exists():
                raw = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
                self.data = AppSettings(**{**asdict(AppSettings()), **raw})
            else:
                self.save()
        except Exception as exc:
            logger.error("Failed to load settings: %s", exc)
            self.data = AppSettings()

    def save(self) -> bool:
        try:
            Utilities.ensure_dir(CONFIG_DIR)
            SETTINGS_FILE.write_text(
                json.dumps(asdict(self.data), indent=2), encoding="utf-8"
            )
            return True
        except Exception as exc:
            logger.error("Failed to save settings: %s", exc)
            return False

    def reset(self) -> None:
        """Restore default settings and persist them."""
        self.data = AppSettings()
        self.save()

    def get_download_root(self) -> Path:
        """Resolve the configured download root to an absolute Path.

        A relative value (the default "downloads") is resolved against
        APP_DIR so the project stays portable. An absolute value (a custom
        folder the user picked) is used as-is.
        """
        raw = Path(self.data.download_folder).expanduser()
        if raw.is_absolute():
            return raw
        return (APP_DIR / raw).resolve()

    def get_video_dir(self) -> Path:
        path = self.get_download_root() / "videos"
        Utilities.ensure_dir(path)
        return path

    def get_audio_dir(self) -> Path:
        path = self.get_download_root() / "audios"
        Utilities.ensure_dir(path)
        return path

    def set_download_root(self, new_root: str) -> None:
        """Change the download root and make sure videos/audios exist."""
        self.data.download_folder = new_root
        self.save()
        Utilities.ensure_dir(self.get_video_dir())
        Utilities.ensure_dir(self.get_audio_dir())


@dataclass
class HistoryEntry:
    """A single download-history record (history/history.json)."""

    date: str
    title: str
    url: str
    website: str
    type: str          # "video" or "audio"
    quality: str
    format: str
    output_path: str


class History:
    """Loads/saves history.json inside APP_DIR/history."""

    def __init__(self) -> None:
        self.entries: List[HistoryEntry] = []
        self.load()

    def load(self) -> None:
        try:
            if HISTORY_FILE.exists():
                raw = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
                self.entries = [self._coerce_entry(item) for item in raw]
        except Exception as exc:
            logger.error("Failed to load history: %s", exc)
            self.entries = []

    @staticmethod
    def _coerce_entry(item: Dict[str, Any]) -> HistoryEntry:
        """Build a HistoryEntry, filling in defaults for missing fields
        (keeps compatibility with older/partial history records)."""
        defaults = {
            "date": "", "title": "Unknown", "url": "", "website": "Unknown",
            "type": "video", "quality": "", "format": "", "output_path": "",
        }
        merged = {**defaults, **item}
        return HistoryEntry(**{k: merged[k] for k in defaults})

    def save(self) -> bool:
        try:
            Utilities.ensure_dir(HISTORY_DIR)
            HISTORY_FILE.write_text(
                json.dumps([asdict(e) for e in self.entries], indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            return True
        except Exception as exc:
            logger.error("Failed to save history: %s", exc)
            return False

    def add(self, title: str, url: str, website: str, media_type: str,
             quality: str, fmt: str, output_path: str) -> None:
        entry = HistoryEntry(
            date=time.strftime("%Y-%m-%d %H:%M:%S"),
            title=title,
            url=url,
            website=website,
            type=media_type,
            quality=quality,
            format=fmt,
            output_path=output_path,
        )
        self.entries.append(entry)
        self.save()
        logger.info("History added: %s | %s | %s", title, media_type, output_path)

    def delete(self, index: int) -> bool:
        if 0 <= index < len(self.entries):
            del self.entries[index]
            self.save()
            return True
        return False

    def search(self, query: str) -> List[Tuple[int, HistoryEntry]]:
        query = query.lower().strip()
        return [
            (idx, e) for idx, e in enumerate(self.entries)
            if query in e.title.lower() or query in e.website.lower() or query in e.url.lower()
        ]

    def clear(self) -> None:
        self.entries = []
        self.save()


# =====================================================================
# UI
# =====================================================================

class UI:
    def __init__(self, theme: Theme) -> None:
        self.theme = theme
        self.console = console

    def clear(self) -> None:
        self.console.clear()

    def show_logo(self) -> None:
        self.console.print(Align.center(Text.from_markup(LOGO)))
        info = Table.grid(padding=(0, 2))
        info.add_column(justify="right", style=f"bold {self.theme.style('secondary')}")
        info.add_column(justify="left", style=self.theme.style('primary'))
        info.add_row("Author", APP_AUTHOR)
        info.add_row("Engine", APP_ENGINE)
        info.add_row("Version", APP_VERSION)
        info.add_row("App Folder", str(APP_DIR))
        self.console.print(Align.center(info))
        self.console.print()

    def panel(self, content: str, title: str = "", style: Optional[str] = None) -> None:
        style = style or self.theme.style("primary")
        self.console.print(Panel(content, title=title, border_style=style, box=box.ROUNDED))

    def success(self, message: str) -> None:
        self.console.print(f"[{self.theme.style('success')}]✅ {message}[/]")

    def error(self, message: str) -> None:
        self.console.print(f"[{self.theme.style('error')}]❌ {message}[/]")

    def warning(self, message: str) -> None:
        self.console.print(f"[{self.theme.style('warning')}]⚠️  {message}[/]")

    def info(self, message: str) -> None:
        self.console.print(f"[{self.theme.style('info')}]ℹ️  {message}[/]")

    def rule(self, title: str = "") -> None:
        self.console.print(Rule(title, style=self.theme.style("secondary")))

    def main_menu(self) -> Table:
        table = Table(
            title="✨ Main Menu ✨",
            box=box.ROUNDED,
            border_style=self.theme.style("primary"),
            title_style=f"bold {self.theme.style('accent')}",
            show_header=False,
        )
        table.add_column("Option", style=f"bold {self.theme.style('secondary')}", width=4)
        table.add_column("Description", style=self.theme.style("primary"))
        items = [
            ("1", "🎬  Download Video"),
            ("2", "🎵  Download Audio"),
            ("3", "📜  Playlist Download (Video/Audio)"),
            ("4", "🔍  Search YouTube & Download"),
            ("5", "📁  Batch Downloads (List/File)"),
            ("6", "ℹ️  Media Information"),
            ("7", "🕘  Download History"),
            ("8", "⚙️  Settings"),
            ("9", "🛠️  Engine Maintenance (Update/Cache)"),
            ("10", "❓ Help"),
            ("11", "📖 About"),
            ("12", "🚪 Exit"),
        ]
        for num, desc in items:
            table.add_row(num, desc)
        return table

    def press_enter(self) -> None:
        try:
            Prompt.ask(f"[{self.theme.style('muted')}]Press Enter to Continue[/]", default="")
        except (KeyboardInterrupt, EOFError):
            raise

    def build_progress(self) -> Progress:
        return Progress(
            TextColumn("[bold]{task.description}"),
            BarColumn(bar_width=None),
            TextColumn("[progress.percentage]{task.percentage:>3.1f}%"),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=self.console,
            transient=False,
        )

    def dependency_check_table(self, statuses: Dict[str, bool]) -> Table:
        table = Table(title="GVA Downloader Environment Check", box=box.ROUNDED,
                      border_style=self.theme.style("primary"))
        table.add_column("Component", style=f"bold {self.theme.style('secondary')}")
        table.add_column("Status")
        for name, ok in statuses.items():
            table.add_row(name, "✅" if ok else "❌")
        return table


# =====================================================================
# YT-DLP ERROR TRANSLATOR & HELPER
# =====================================================================

class YtDlpErrorTranslator:
    @staticmethod
    def translate(exc: Exception) -> str:
        text = str(exc).lower()
        if "private video" in text:
            return "This video is private and cannot be accessed."
        if "video unavailable" in text or "has been removed" in text:
            return "This video has been deleted or is unavailable."
        if "age" in text and "restrict" in text:
            return "This video is age-restricted and cannot be downloaded without authentication."
        if "unsupported url" in text:
            return "This website is not supported by yt-dlp."
        if "ffmpeg" in text and ("not found" in text or "not installed" in text):
            return "FFmpeg is not installed. Required for processing media."
        if "network" in text or "urlopen" in text or "timed out" in text:
            return "Network error. Check your internet connection and try again."
        if "permission denied" in text:
            return "Permission denied while writing the file. Check folder permissions."
        if "no space left" in text or "disk full" in text:
            return "Disk is full. Free up some space and try again."
        return f"An error occurred: {exc}"


class DynamicQualityHelper:
    """Dynamically parses yt-dlp metadata to extract only real available qualities."""

    @staticmethod
    def get_video_qualities(info: Dict[str, Any]) -> List[Tuple[str, str, Optional[int]]]:
        formats = info.get("formats") or []
        heights = sorted(
            {f.get("height") for f in formats if f.get("height") and f.get("vcodec") != "none"},
            reverse=True,
        )
        quality_list: List[Tuple[str, str, Optional[int]]] = [("1", "Best Available", None)]
        idx = 2
        for h in heights:
            label = f"{h}p"
            if h >= 2160:
                label += " (4K)"
            elif h >= 1440:
                label += " (2K)"
            elif h >= 1080:
                label += " (Full HD)"
            elif h >= 720:
                label += " (HD)"
            quality_list.append((str(idx), label, h))
            idx += 1
        return quality_list

    @staticmethod
    def get_audio_qualities(info: Dict[str, Any]) -> List[Tuple[str, str, Optional[int]]]:
        formats = info.get("formats") or []
        abrs = sorted(
            {int(f.get("abr")) for f in formats if f.get("abr") and f.get("vcodec") == "none"},
            reverse=True,
        )
        audio_list: List[Tuple[str, str, Optional[int]]] = [("1", "Best Available (320 kbps)", 320)]
        idx = 2
        for abr in abrs:
            audio_list.append((str(idx), f"{abr} kbps", abr))
            idx += 1
        if len(audio_list) == 1:
            # Fallback standard bitrates if extract flat/missing abr
            for std_abr in [320, 256, 192, 128, 64]:
                audio_list.append((str(idx), f"{std_abr} kbps", std_abr))
                idx += 1
        return audio_list


# =====================================================================
# VIDEO INFO
# =====================================================================

class VideoInfo:
    def __init__(self, ui: UI) -> None:
        self.ui = ui

    def extract(self, url: str) -> Optional[Dict[str, Any]]:
        if yt_dlp is None:
            self.ui.error("yt-dlp is not installed. Run: pip install -U yt-dlp")
            return None
        opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
            "cachedir": str(CACHE_DIR),
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(url, download=False)
        except Exception as exc:
            self.ui.error(YtDlpErrorTranslator.translate(exc))
            logger.exception("Failed to extract info for %s", url)
            return None

    def show(self, url: str) -> Optional[Dict[str, Any]]:
        with self.ui.console.status("[bold cyan]Fetching video information..."):
            info = self.extract(url)
        if not info:
            return None

        formats = info.get("formats") or []
        resolutions = sorted(
            {f.get("height") for f in formats if f.get("height")}, reverse=True
        )
        audio_formats = sorted(
            {f.get("abr") for f in formats if f.get("vcodec") == "none" and f.get("abr")},
            reverse=True,
        )

        table = Table(box=box.ROUNDED, show_header=False, border_style=self.ui.theme.style("primary"))
        table.add_column("Field", style=f"bold {self.ui.theme.style('secondary')}")
        table.add_column("Value", style=self.ui.theme.style("primary"))
        table.add_row("Title", str(info.get("title", "Unknown")))
        table.add_row("Uploader", str(info.get("uploader", "Unknown")))
        table.add_row("Duration", Utilities.human_duration(info.get("duration")))
        table.add_row("Views", Utilities.human_number(info.get("view_count")))
        table.add_row(
            "Available Resolutions",
            ", ".join(f"{r}p" for r in resolutions) if resolutions else "Unknown",
        )
        table.add_row(
            "Available Audio",
            ", ".join(f"{int(a)}kbps" for a in audio_formats) if audio_formats else "Unknown",
        )
        table.add_row("Website", str(info.get("extractor_key", "Unknown")))
        table.add_row("URL", url)

        self.ui.console.print(Panel(table, title="🎬 Media Information", border_style=self.ui.theme.style("primary")))
        return info


# =====================================================================
# PROGRESS HOOK BRIDGE
# =====================================================================

class ProgressHookBridge:
    """Bridges yt-dlp's progress_hooks into a SINGLE Rich progress line.

    A video download typically pulls a separate video-only stream and
    audio-only stream before merging them, and a playlist reuses the same
    hook across many items. Rather than creating a new task per filename
    (which stacks up multiple bars), this bridge keeps exactly one task and
    simply relabels/resets it whenever yt-dlp moves on to a new file, so the
    UI always shows a single, clean progress line.
    """

    def __init__(self, progress: Progress, ui: UI) -> None:
        self.progress = progress
        self.ui = ui
        self.task_id: Optional[Any] = None
        self.current_key: Optional[str] = None

    @staticmethod
    def _short_name(filename: str) -> str:
        short_name = Path(filename).name
        if len(short_name) > 35:
            short_name = short_name[:32] + "..."
        return short_name

    def hook(self, d: Dict[str, Any]) -> None:
        filename = d.get("filename", "download")
        status = d.get("status")

        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)

            if self.task_id is None:
                # First file of this download: create the one and only task.
                self.current_key = filename
                self.task_id = self.progress.add_task(
                    self._short_name(filename), total=total if total else None
                )
            elif filename != self.current_key:
                # A new file started (e.g. switched from video-only stream to
                # audio-only stream). Reset the SAME line instead of adding
                # another one.
                self.current_key = filename
                self.progress.reset(self.task_id, total=total if total else None)
                self.progress.update(self.task_id, description=self._short_name(filename))

            if total:
                self.progress.update(self.task_id, completed=downloaded, total=total)
            else:
                self.progress.update(self.task_id, completed=downloaded)

        elif status == "finished" and self.task_id is not None:
            # Snap to 100% so the single line reads as complete before the
            # next file (if any) resets it.
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            if total:
                self.progress.update(self.task_id, completed=total, total=total)


# =====================================================================
# BASE DOWNLOADER
# =====================================================================

class BaseDownloader:
    """Shared behaviour for all downloader flows.

    media_kind must be set by subclasses to "video" or "audio" so the
    correct app-owned subfolder (downloads/videos or downloads/audios) is
    used automatically.
    """

    media_kind: str = "video"

    def __init__(self, ui: UI, settings: Settings, history: History) -> None:
        self.ui = ui
        self.settings = settings
        self.history = history

    def check_ffmpeg(self) -> bool:
        if Utilities.which("ffmpeg") is None:
            self.ui.error("FFmpeg is not installed.")
            if sys.platform.startswith("win"):
                self.ui.info("Install FFmpeg on Windows: download from https://ffmpeg.org/download.html "
                              "and add its 'bin' folder to your PATH.")
            elif shutil.which("termux-info") or "com.termux" in os.environ.get("PREFIX", ""):
                self.ui.info("Install FFmpeg on Termux: pkg install ffmpeg")
            else:
                self.ui.info("Install FFmpeg with your package manager, e.g. 'sudo apt install ffmpeg' "
                              "or 'brew install ffmpeg'.")
            return False
        return True

    def default_output_folder(self) -> Path:
        """Return downloads/videos or downloads/audios based on media_kind."""
        if self.media_kind == "audio":
            return self.settings.get_audio_dir()
        return self.settings.get_video_dir()

    def ask_output_folder(self) -> Path:
        default = str(self.default_output_folder())
        self.ui.console.print(f"[{self.ui.theme.style('muted')}]Default Folder: {default}[/]")
        use_default = Confirm.ask("Use default folder?", default=True)
        if use_default:
            folder = Path(default)
        else:
            raw = Prompt.ask("Enter custom output folder path")
            folder = Path(raw).expanduser()
        Utilities.ensure_dir(folder)
        return folder

    def ask_dynamic_quality(self, info: Dict[str, Any]) -> Tuple[str, Optional[int]]:
        ladder = DynamicQualityHelper.get_video_qualities(info)
        table = Table(title="🎯 Dynamic Quality Selection", box=box.ROUNDED, show_header=False)
        table.add_column("Option", style=f"bold {self.ui.theme.style('secondary')}", width=4)
        table.add_column("Available Quality", style=self.ui.theme.style("primary"))
        for key, label, _ in ladder:
            table.add_row(key, label)
        self.ui.console.print(table)

        valid_choices = [item[0] for item in ladder]
        choice = Prompt.ask("Select Quality Option", choices=valid_choices, default="1")
        for key, label, height in ladder:
            if key == choice:
                return label, height
        return "Best Available", None

    def ask_dynamic_audio_quality(self, info: Dict[str, Any]) -> Tuple[str, str]:
        ladder = DynamicQualityHelper.get_audio_qualities(info)
        table = Table(title="🎧 Dynamic Audio Bitrate Selection", box=box.ROUNDED, show_header=False)
        table.add_column("Option", style=f"bold {self.ui.theme.style('secondary')}", width=4)
        table.add_column("Bitrate", style=self.ui.theme.style("primary"))
        for key, label, _ in ladder:
            table.add_row(key, label)
        self.ui.console.print(table)

        valid_choices = [item[0] for item in ladder]
        choice = Prompt.ask("Select Audio Quality Option", choices=valid_choices, default="1")
        for key, label, abr in ladder:
            if key == choice:
                return label, str(abr) if abr else "320"
        return "Best Available (320 kbps)", "320"

    def resolve_duplicate(self, folder: Path, title: str, likely_exts: List[str]) -> Optional[str]:
        """Check whether a file with this title already exists in `folder`.

        Returns:
          * a (possibly new) filename STEM to use, or
          * None if the user chose to skip/cancel this download.

        Honors settings.overwrite_existing (silently overwrites, no prompt).
        """
        stem = Utilities.sanitize_filename(title)
        existing = [folder / f"{stem}{ext}" for ext in likely_exts if (folder / f"{stem}{ext}").exists()]
        if not existing:
            return stem

        if self.settings.data.overwrite_existing:
            return stem

        self.ui.warning(f"File already exists: {existing[0].name}")
        choice = Prompt.ask(
            "1) Skip  2) Overwrite  3) Save with a new filename  4) Cancel",
            choices=["1", "2", "3", "4"],
            default="1",
        )
        if choice == "1":
            self.ui.info("Skipped (file already exists).")
            return None
        if choice == "2":
            return stem
        if choice == "3":
            new_name = Prompt.ask("Enter a new filename (without extension)", default=f"{stem} (1)")
            return Utilities.sanitize_filename(new_name)
        self.ui.info("Cancelled.")
        return None


# =====================================================================
# VIDEO DOWNLOADER
# =====================================================================

class Downloader(BaseDownloader):
    media_kind = "video"

    def run(self, input_url: Optional[str] = None) -> None:
        self.ui.rule("Download Video")
        url = input_url or Prompt.ask("Paste Video URL")
        if not Validator.is_valid_url(url):
            self.ui.error("Invalid URL.")
            return

        video_info = VideoInfo(self.ui)
        info = video_info.show(url)
        if info is None:
            return

        label, height = self.ask_dynamic_quality(info)
        subtitles = Confirm.ask("Download subtitles?", default=False)
        embed_metadata = Confirm.ask("Embed metadata?", default=True)
        embed_thumbnail = Confirm.ask("Embed thumbnail?", default=False)
        sponsorblock = Confirm.ask("Use SponsorBlock (skip sponsor segments)?", default=False)
        output_folder = self.ask_output_folder()

        if embed_thumbnail or embed_metadata or sponsorblock:
            if not self.check_ffmpeg():
                return

        title = str(info.get("title", "video"))
        stem = self.resolve_duplicate(output_folder, title, [".mp4", ".mkv", ".webm"])
        if stem is None:
            return

        fmt = "bestvideo+bestaudio/best" if height is None else f"bestvideo[height<={height}]+bestaudio/best[height<={height}]/best"

        outtmpl = str(output_folder / f"{stem}.%(ext)s")
        postprocessors: List[Dict[str, Any]] = []
        if embed_metadata:
            postprocessors.append({"key": "FFmpegMetadata"})
        if embed_thumbnail:
            postprocessors.append({"key": "EmbedThumbnail"})
            postprocessors.append({"key": "FFmpegThumbnailsConvertor", "format": "jpg"})
        if sponsorblock:
            # Fixed in this version: sponsorblock was previously asked but never applied.
            postprocessors.append({
                "key": "SponsorBlock",
                "categories": ["sponsor"],
                "api": "https://sponsor.ajay.app",
            })
            postprocessors.append({
                "key": "ModifyChapters",
                "remove_sponsor_segments": ["sponsor"],
            })

        opts: Dict[str, Any] = {
            "format": fmt,
            "outtmpl": outtmpl,
            "merge_output_format": "mp4",
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "writesubtitles": subtitles,
            "embedsubtitles": subtitles,
            "postprocessors": postprocessors,
            "overwrites": True,  # duplicate handling is already resolved above
            "cachedir": str(CACHE_DIR),
            "paths": {"temp": str(TEMP_DIR)},
        }

        with self.ui.build_progress() as progress:
            bridge = ProgressHookBridge(progress, self.ui)
            opts["progress_hooks"] = [bridge.hook]
            path, actual_info = self._execute_download(url, opts)

        if path:
            self.ui.success(f"Downloaded: {path.name}")
            self.history.add(
                title=str(actual_info.get("title", "Unknown")),
                url=url,
                website=str(actual_info.get("extractor_key", "Unknown")),
                media_type="video",
                quality=label,
                fmt=path.suffix.lstrip("."),
                output_path=str(path),
            )
            logger.info("Video download completed: %s -> %s", url, path)

    def _execute_download(self, url: str, opts: Dict[str, Any]) -> Tuple[Optional[Path], Optional[Dict[str, Any]]]:
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if not info:
                    return None, None
                filename = ydl.prepare_filename(info)
                final_path = Path(filename)
                if not final_path.exists():
                    for ext in (".mp4", ".mkv", ".webm"):
                        candidate = final_path.with_suffix(ext)
                        if candidate.exists():
                            return candidate, info
                return final_path, info
        except Exception as exc:
            self.ui.error(YtDlpErrorTranslator.translate(exc))
            logger.exception("Video download failed for %s", url)
            return None, None


# =====================================================================
# AUDIO DOWNLOADER
# =====================================================================

class AudioDownloader(BaseDownloader):
    media_kind = "audio"

    def run(self, input_url: Optional[str] = None) -> None:
        self.ui.rule("Download Audio")
        url = input_url or Prompt.ask("Paste Video/Audio URL")
        if not Validator.is_valid_url(url):
            self.ui.error("Invalid URL.")
            return

        if not self.check_ffmpeg():
            return

        video_info = VideoInfo(self.ui)
        info = video_info.show(url)
        if info is None:
            return

        bitrate_label, bitrate = self.ask_dynamic_audio_quality(info)
        fmt_choice = Prompt.ask("Output format", choices=[f.lower() for f in AUDIO_FORMATS], default="mp3")

        embed_metadata = Confirm.ask("Embed metadata?", default=True)
        embed_thumbnail = Confirm.ask("Embed thumbnail (cover art)?", default=False)
        output_folder = self.ask_output_folder()

        title = str(info.get("title", "audio"))
        stem = self.resolve_duplicate(output_folder, title, [f".{fmt_choice}"])
        if stem is None:
            return

        postprocessors: List[Dict[str, Any]] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": fmt_choice,
                "preferredquality": bitrate,
            }
        ]
        if embed_metadata:
            postprocessors.append({"key": "FFmpegMetadata"})
        if embed_thumbnail and fmt_choice in ("mp3", "m4a", "flac"):
            postprocessors.append({"key": "EmbedThumbnail"})

        outtmpl = str(output_folder / f"{stem}.%(ext)s")
        opts: Dict[str, Any] = {
            "format": "bestaudio/best",
            "outtmpl": outtmpl,
            "postprocessors": postprocessors,
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "overwrites": True,  # duplicate handling is already resolved above
            "cachedir": str(CACHE_DIR),
            "paths": {"temp": str(TEMP_DIR)},
        }

        with self.ui.build_progress() as progress:
            bridge = ProgressHookBridge(progress, self.ui)
            opts["progress_hooks"] = [bridge.hook]
            path, actual_info = self._execute_download(url, opts, fmt_choice)

        if path:
            self.ui.success(f"Downloaded Audio: {path.name}")
            self.history.add(
                title=str(actual_info.get("title", "Unknown")),
                url=url,
                website=str(actual_info.get("extractor_key", "Unknown")),
                media_type="audio",
                quality=f"{bitrate_label}",
                fmt=fmt_choice,
                output_path=str(path),
            )
            logger.info("Audio download completed: %s -> %s", url, path)

    def _execute_download(self, url: str, opts: Dict[str, Any], ext: str) -> Tuple[Optional[Path], Optional[Dict[str, Any]]]:
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if not info:
                    return None, None
                filename = ydl.prepare_filename(info)
                final_path = Path(filename).with_suffix(f".{ext}")
                if not final_path.exists() and Path(filename).exists():
                    final_path = Path(filename)
                return final_path, info
        except Exception as exc:
            self.ui.error(YtDlpErrorTranslator.translate(exc))
            logger.exception("Audio download failed for %s", url)
            return None, None


# =====================================================================
# PLAYLIST DOWNLOADER
# =====================================================================

class PlaylistDownloader(BaseDownloader):
    """Handles playlist downloads with Video or Audio download modes."""

    def run(self) -> None:
        self.ui.rule("Playlist Download")
        url = Prompt.ask("Paste Playlist URL")
        if not Validator.is_valid_url(url):
            self.ui.error("Invalid URL.")
            return

        with self.ui.console.status("[bold cyan]Detecting playlist items..."):
            entries = self._extract_playlist(url)

        if not entries:
            return

        self.ui.success(f"Playlist detected with {len(entries)} items.")

        table = Table(box=box.SIMPLE)
        table.add_column("#", style="bold")
        table.add_column("Title")
        for idx, entry in enumerate(entries[:10], start=1):
            table.add_row(str(idx), str(entry.get("title", "Unknown")))
        if len(entries) > 10:
            table.add_row("...", f"and {len(entries) - 10} more")
        self.ui.console.print(table)

        mode = Prompt.ask("Download scope", choices=["entire", "range"], default="entire")
        if mode == "range":
            range_str = Prompt.ask(f"Enter range (e.g. 1-{len(entries)})")
            if not Validator.is_valid_range(range_str, len(entries)):
                self.ui.error("Invalid range.")
                return
            start, end = (int(x) for x in range_str.split("-"))
            selected_indices = list(range(start, end + 1))
        else:
            selected_indices = list(range(1, len(entries) + 1))

        download_type = Prompt.ask("Download playlist as", choices=["video", "audio"], default="video")
        self.media_kind = download_type
        output_folder = self.ask_output_folder()

        if download_type == "audio":
            if not self.check_ffmpeg():
                return
            fmt_choice = Prompt.ask("Audio format", choices=[f.lower() for f in AUDIO_FORMATS], default="mp3")
            bitrate = Prompt.ask("Audio Quality Bitrate (kbps)", choices=["320", "256", "192", "128"], default="192")

            opts: Dict[str, Any] = {
                "format": "bestaudio/best",
                "outtmpl": str(output_folder / "%(playlist_index)s - %(title)s.%(ext)s"),
                "postprocessors": [
                    {"key": "FFmpegExtractAudio", "preferredcodec": fmt_choice, "preferredquality": bitrate},
                    {"key": "FFmpegMetadata"},
                ],
                "quiet": True,
                "overwrites": self.settings.data.overwrite_existing,
                "cachedir": str(CACHE_DIR),
                "paths": {"temp": str(TEMP_DIR)},
            }

            self._process_playlist_loop(entries, selected_indices, opts, f"Audio ({bitrate}k)", "audio", fmt_choice)

        else:  # Video download
            quality = Prompt.ask("Preferred max video quality", choices=["1080", "720", "480", "best"], default="best")
            fmt = "bestvideo+bestaudio/best" if quality == "best" else f"bestvideo[height<={quality}]+bestaudio/best"

            opts = {
                "format": fmt,
                "outtmpl": str(output_folder / "%(playlist_index)s - %(title)s.%(ext)s"),
                "merge_output_format": "mp4",
                "quiet": True,
                "overwrites": self.settings.data.overwrite_existing,
                "cachedir": str(CACHE_DIR),
                "paths": {"temp": str(TEMP_DIR)},
            }

            self._process_playlist_loop(entries, selected_indices, opts, f"Video ({quality}p)", "video", "mp4")

    def _process_playlist_loop(self, entries: List[Dict[str, Any]], indices: List[int], opts: Dict[str, Any],
                                label: str, media_type: str, fmt: str) -> None:
        success = 0
        for i in indices:
            entry = entries[i - 1]
            entry_url = entry.get("url") or entry.get("webpage_url") or entry.get("id")
            if entry_url and not str(entry_url).startswith("http"):
                entry_url = f"https://www.youtube.com/watch?v={entry_url}"

            title = entry.get("title", f"Track {i}")
            self.ui.rule(f"[{i}/{len(indices)}] {title}")

            with self.ui.build_progress() as progress:
                bridge = ProgressHookBridge(progress, self.ui)
                opts["progress_hooks"] = [bridge.hook]
                try:
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        info = ydl.extract_info(entry_url, download=True)
                        if info:
                            success += 1
                            filename = ydl.prepare_filename(info)
                            self.history.add(
                                title=title, url=str(entry_url), website="Playlist",
                                media_type=media_type, quality=label, fmt=fmt,
                                output_path=filename,
                            )
                except Exception as exc:
                    self.ui.error(f"Failed item {i}: {YtDlpErrorTranslator.translate(exc)}")
                    logger.exception("Playlist item %s failed", i)

        self.ui.success(f"Playlist batch complete! {success}/{len(indices)} downloaded successfully.")

    def _extract_playlist(self, url: str) -> Optional[List[Dict[str, Any]]]:
        opts = {"quiet": True, "extract_flat": True, "skip_download": True, "cachedir": str(CACHE_DIR)}
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if info and "entries" in info:
                    return [e for e in info["entries"] if e]
                return [info] if info else None
        except Exception as exc:
            self.ui.error(YtDlpErrorTranslator.translate(exc))
            return None


# =====================================================================
# SEARCH & BATCH DOWNLOAD
# =====================================================================

class SearchDownloader:
    """Search YouTube directly and download media."""

    def __init__(self, ui: UI, settings: Settings, history: History) -> None:
        self.ui = ui
        self.settings = settings
        self.history = history

    def run(self) -> None:
        self.ui.rule("Search YouTube")
        query = Prompt.ask("Enter search query")
        if not query.strip():
            return

        with self.ui.console.status("[bold cyan]Searching YouTube..."):
            opts = {"quiet": True, "extract_flat": True, "skip_download": True, "cachedir": str(CACHE_DIR)}
            search_target = f"ytsearch7:{query}"
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    res = ydl.extract_info(search_target, download=False)
                    entries = res.get("entries", []) if res else []
            except Exception as exc:
                self.ui.error(f"Search failed: {YtDlpErrorTranslator.translate(exc)}")
                return

        if not entries:
            self.ui.warning("No results found.")
            return

        table = Table(box=box.ROUNDED, border_style=self.ui.theme.style("primary"))
        table.add_column("#", style="bold", width=4)
        table.add_column("Title", style="cyan")
        table.add_column("Uploader", style="magenta")
        table.add_column("Duration", style="yellow")

        for idx, item in enumerate(entries, start=1):
            table.add_row(
                str(idx),
                str(item.get("title", "Unknown")),
                str(item.get("uploader", "Unknown")),
                Utilities.human_duration(item.get("duration")),
            )

        self.ui.console.print(table)
        choice_str = Prompt.ask("Select video number to download (0 to cancel)",
                                 choices=[str(i) for i in range(len(entries) + 1)], default="1")
        if choice_str == "0":
            return

        chosen = entries[int(choice_str) - 1]
        target_url = chosen.get("url") or f"https://www.youtube.com/watch?v={chosen.get('id')}"

        dl_type = Prompt.ask("Download as", choices=["video", "audio"], default="video")
        if dl_type == "video":
            Downloader(self.ui, self.settings, self.history).run(target_url)
        else:
            AudioDownloader(self.ui, self.settings, self.history).run(target_url)


class BatchDownloader:
    """Download multiple URLs from input list or file."""

    def __init__(self, ui: UI, settings: Settings, history: History) -> None:
        self.ui = ui
        self.settings = settings
        self.history = history

    def run(self) -> None:
        self.ui.rule("Batch Downloader")
        mode = Prompt.ask("Batch source", choices=["paste", "file"], default="paste")
        urls: List[str] = []

        if mode == "file":
            filepath = Prompt.ask("Enter text file path containing URLs")
            path = Path(filepath).expanduser()
            if not path.exists():
                self.ui.error("File not found.")
                return
            urls = [line.strip() for line in path.read_text().splitlines()
                    if line.strip() and Validator.is_valid_url(line.strip())]
        else:
            self.ui.info("Paste URLs separated by space or commas:")
            raw = Prompt.ask("URLs")
            raw_list = raw.replace(",", " ").split()
            urls = [u.strip() for u in raw_list if Validator.is_valid_url(u.strip())]

        if not urls:
            self.ui.warning("No valid URLs provided.")
            return

        self.ui.info(f"Found {len(urls)} valid URLs.")
        dl_type = Prompt.ask("Download all as", choices=["video", "audio"], default="video")

        downloader = Downloader(self.ui, self.settings, self.history) if dl_type == "video" \
            else AudioDownloader(self.ui, self.settings, self.history)

        for idx, u in enumerate(urls, start=1):
            self.ui.rule(f"Item {idx}/{len(urls)}")
            downloader.run(u)


# =====================================================================
# ENGINE MAINTENANCE
# =====================================================================

class EngineMaintenance:
    """Update yt-dlp and manage GVA's own cache/temp folders."""

    def __init__(self, ui: UI) -> None:
        self.ui = ui

    def run(self) -> None:
        self.ui.rule("Engine Maintenance")
        table = Table(box=box.ROUNDED, show_header=False)
        table.add_row("1", "Update yt-dlp library")
        table.add_row("2", "Clear yt-dlp Cache")
        table.add_row("3", "Clear GVA Cache && Temp Folders")
        table.add_row("4", "Back")
        self.ui.console.print(table)

        choice = Prompt.ask("Select action", choices=["1", "2", "3", "4"], default="1")
        if choice == "1":
            with self.ui.console.status("[bold cyan]Updating yt-dlp..."):
                try:
                    res = subprocess.run(
                        [sys.executable, "-m", "pip", "install", "-U", "yt-dlp", "--break-system-packages"],
                        capture_output=True, text=True,
                    )
                    if res.returncode != 0:
                        # --break-system-packages isn't valid on every pip version; retry without it.
                        res = subprocess.run(
                            [sys.executable, "-m", "pip", "install", "-U", "yt-dlp"],
                            capture_output=True, text=True,
                        )
                    if res.returncode == 0:
                        self.ui.success("yt-dlp updated successfully!")
                    else:
                        self.ui.error(f"Update failed: {res.stderr}")
                except Exception as exc:
                    self.ui.error(f"Error during update: {exc}")
        elif choice == "2":
            try:
                with yt_dlp.YoutubeDL({"cachedir": str(CACHE_DIR)}) as ydl:
                    ydl.cache.remove()
                self.ui.success("yt-dlp cache cleared successfully.")
            except Exception as exc:
                self.ui.error(f"Failed to clear cache: {exc}")
        elif choice == "3":
            cleared = 0
            for folder in (CACHE_DIR, TEMP_DIR):
                try:
                    if folder.exists():
                        for item in folder.iterdir():
                            if item.is_dir():
                                shutil.rmtree(item, ignore_errors=True)
                            else:
                                item.unlink(missing_ok=True)
                            cleared += 1
                    Utilities.ensure_dir(folder)
                except Exception as exc:
                    self.ui.error(f"Failed clearing {folder}: {exc}")
            self.ui.success(f"Cleared {cleared} item(s) from GVA cache/temp folders.")


# =====================================================================
# MENU & APP CONTROLLER
# =====================================================================

class Menu:
    def __init__(self, ui: UI, settings: Settings, history: History) -> None:
        self.ui = ui
        self.settings = settings
        self.history = history

    # ---------------------------------------------------------------
    # HISTORY MENU
    # ---------------------------------------------------------------
    def history_menu(self) -> None:
        while True:
            self.ui.rule("Download History")
            table = Table(box=box.ROUNDED, show_header=False)
            table.add_row("1", "View History")
            table.add_row("2", "Search History")
            table.add_row("3", "Open Download Location")
            table.add_row("4", "Delete History Entry")
            table.add_row("5", "Clear History")
            table.add_row("6", "Back")
            self.ui.console.print(table)

            choice = Prompt.ask("Select option", choices=["1", "2", "3", "4", "5", "6"], default="6")
            if choice == "1":
                self._render_history(self.history.entries)
            elif choice == "2":
                query = Prompt.ask("Search term")
                results = self.history.search(query)
                self._render_history([e for _, e in results])
            elif choice == "3":
                Utilities.open_folder(self.settings.get_download_root())
            elif choice == "4":
                if not self.history.entries:
                    self.ui.info("No download history yet.")
                    continue
                self._render_history(self.history.entries)
                idx_str = Prompt.ask("Entry number to delete (0 to cancel)",
                                      choices=[str(i) for i in range(len(self.history.entries) + 1)], default="0")
                if idx_str != "0":
                    if self.history.delete(int(idx_str) - 1):
                        self.ui.success("Entry deleted.")
            elif choice == "5":
                if Confirm.ask("Clear entire history?", default=False):
                    self.history.clear()
                    self.ui.success("History cleared.")
            else:
                return

    def _render_history(self, entries: List[HistoryEntry]) -> None:
        if not entries:
            self.ui.info("No matching history entries.")
            return
        table = Table(box=box.ROUNDED, border_style=self.ui.theme.style("primary"))
        table.add_column("#", style="bold")
        table.add_column("Date")
        table.add_column("Title")
        table.add_column("Type")
        table.add_column("Quality")
        table.add_column("Output Path", overflow="fold")
        for idx, entry in enumerate(entries, start=1):
            table.add_row(str(idx), entry.date, entry.title, entry.type, entry.quality, entry.output_path)
        self.ui.console.print(table)

    # ---------------------------------------------------------------
    # SETTINGS MENU
    # ---------------------------------------------------------------
    def settings_menu(self) -> None:
        while True:
            self.ui.rule("Settings")
            table = Table(box=box.ROUNDED, show_header=False)
            table.add_row("1. Download Folder", str(self.settings.get_download_root()))
            table.add_row("2. Video Quality", self.settings.data.default_video_quality)
            table.add_row("3. Audio Quality", self.settings.data.default_audio_quality)
            table.add_row("4. Theme", self.settings.data.theme)
            table.add_row("5. Overwrite Existing Files", str(self.settings.data.overwrite_existing))
            table.add_row("6. Reset Settings", "")
            table.add_row("7. Back", "")
            self.ui.console.print(table)

            choice = Prompt.ask("Setting choice", choices=[str(i) for i in range(1, 8)], default="7")
            if choice == "1":
                self.ui.console.print(f"[{self.ui.theme.style('muted')}]Current: {self.settings.get_download_root()}[/]")
                folder = Prompt.ask("Enter new download folder (relative or absolute path)",
                                     default=self.settings.data.download_folder)
                self.settings.set_download_root(folder)
                self.ui.success(f"Download folder updated. videos/ and audios/ created under: "
                                 f"{self.settings.get_download_root()}")
            elif choice == "2":
                q = Prompt.ask("Default video quality label (e.g. 'Best Available', '1080p')",
                                default=self.settings.data.default_video_quality)
                self.settings.data.default_video_quality = q
                self.settings.save()
                self.ui.success("Default video quality updated.")
            elif choice == "3":
                q = Prompt.ask("Default audio quality label (e.g. 'Best Available', '192 kbps')",
                                default=self.settings.data.default_audio_quality)
                self.settings.data.default_audio_quality = q
                self.settings.save()
                self.ui.success("Default audio quality updated.")
            elif choice == "4":
                t = Prompt.ask("Theme", choices=list(Theme.THEMES.keys()), default="default")
                self.settings.data.theme = t
                self.ui.theme = Theme(t)
                self.settings.save()
                self.ui.success("Theme updated.")
            elif choice == "5":
                self.settings.data.overwrite_existing = Confirm.ask("Overwrite existing files?", default=False)
                self.settings.save()
            elif choice == "6":
                if Confirm.ask("Reset all settings to defaults?", default=False):
                    self.settings.reset()
                    self.ui.theme = Theme(self.settings.data.theme)
                    self.ui.success("Settings reset to defaults.")
            else:
                return

    def show_help(self) -> None:
        self.ui.rule("Help & Info")
        self.ui.panel(
            "• Video Download: Provides real-time dynamic quality options extracted from the video link.\n"
            "• Playlist Download: Supports downloading full playlists as Video OR Audio (MP3/FLAC/M4A).\n"
            "• YouTube Search: Search keywords directly without opening a browser.\n"
            "• Direct URL: python gva_downloader.py \"<url>\" opens a quick download menu.\n"
            "• Engine Maintenance: Keep yt-dlp updated to prevent extraction failures.",
            title="💡 Hints & Features",
        )

    def show_about(self) -> None:
        self.ui.rule("About")
        self.ui.panel(
            f"GVA Downloader v{APP_VERSION}\nAuthor: {APP_AUTHOR}\nPlatform: {APP_PLATFORM}\n"
            f"Engine: {APP_ENGINE}\nApp Folder: {APP_DIR}",
            title="📖 About App",
        )


class Application:
    def __init__(self) -> None:
        Utilities.ensure_app_directories()
        self.settings = Settings()
        self.history = History()
        self.theme = Theme(self.settings.data.theme)
        self.ui = UI(self.theme)
        self.menu = Menu(self.ui, self.settings, self.history)
        self.running = True

    def startup_check(self) -> None:
        statuses = Utilities.check_dependencies()
        if not all(statuses.values()):
            self.ui.console.print(self.ui.dependency_check_table(statuses))
            if not statuses["yt-dlp"]:
                self.ui.error("yt-dlp is required. Install it with: pip install -U yt-dlp")
            if not statuses["FFmpeg"]:
                self.ui.warning("FFmpeg is required for video merging/audio conversion/thumbnail embedding.")
            self.ui.press_enter()

    def main_loop(self) -> None:
        choice = None
        while self.running:
            try:
                self.ui.clear()
                self.ui.show_logo()
                self.ui.console.print(self.ui.main_menu())
                choice = Prompt.ask("Select an option", choices=[str(i) for i in range(1, 13)], show_choices=False)

                if choice == "1":
                    Downloader(self.ui, self.settings, self.history).run()
                elif choice == "2":
                    AudioDownloader(self.ui, self.settings, self.history).run()
                elif choice == "3":
                    PlaylistDownloader(self.ui, self.settings, self.history).run()
                elif choice == "4":
                    SearchDownloader(self.ui, self.settings, self.history).run()
                elif choice == "5":
                    BatchDownloader(self.ui, self.settings, self.history).run()
                elif choice == "6":
                    url = Prompt.ask("Paste URL")
                    if Validator.is_valid_url(url):
                        VideoInfo(self.ui).show(url)
                    else:
                        self.ui.error("Invalid URL.")
                elif choice == "7":
                    self.menu.history_menu()
                elif choice == "8":
                    self.menu.settings_menu()
                elif choice == "9":
                    EngineMaintenance(self.ui).run()
                elif choice == "10":
                    self.menu.show_help()
                elif choice == "11":
                    self.menu.show_about()
                elif choice == "12":
                    self.ui.panel("Thank you for using GVA Downloader! 👋")
                    self.running = False

            except KeyboardInterrupt:
                self.ui.warning("Cancelled.")
            except Exception as exc:
                logger.exception("Main loop error")
                self.ui.error(f"Error: {exc}")

            if self.running and choice != "12":
                self.ui.press_enter()

    def run(self) -> None:
        self.startup_check()
        self.main_loop()


# =====================================================================
# DIRECT URL MODE / COMMAND-LINE WORKFLOW
# =====================================================================
# This is what makes `python gva_downloader.py "<url>"` work, and what
# powers the Termux "Share -> GVA Downloader" workflow (see README.md).

def _build_app_context() -> Tuple[UI, Settings, History]:
    """Prepare folders + settings/history/UI without starting the menu loop."""
    Utilities.ensure_app_directories()
    settings = Settings()
    history = History()
    theme = Theme(settings.data.theme)
    ui = UI(theme)
    return ui, settings, history


def handle_direct_url(url: str) -> None:
    """Show the quick 'URL detected' menu for a URL passed on the command line."""
    ui, settings, history = _build_app_context()
    ui.clear()

    if not Validator.is_valid_url(url):
        ui.error(f"'{url}' is not a valid URL.")
        return

    ui.console.print(Panel(
        Align.center(Text.from_markup(f"[bold cyan]{APP_NAME}[/bold cyan]\n\n[bold]URL detected[/bold]")),
        box=box.DOUBLE, border_style=ui.theme.style("primary"),
    ))

    info_fetcher = VideoInfo(ui)
    with ui.console.status("[bold cyan]Fetching title..."):
        info = info_fetcher.extract(url)

    title = str(info.get("title", "Unknown")) if info else "Unknown"
    ui.console.print(f"\n[bold]🎬 Title:[/bold]\n{title}\n")

    table = Table(box=box.ROUNDED, show_header=False)
    table.add_row("1", "Download Video")
    table.add_row("2", "Download Audio")
    table.add_row("3", "Download Best Quality")
    table.add_row("4", "View Information")
    table.add_row("5", "Cancel")
    ui.console.print(table)

    choice = Prompt.ask("Choose", choices=["1", "2", "3", "4", "5"], default="1")
    if choice == "1":
        Downloader(ui, settings, history).run(url)
    elif choice == "2":
        AudioDownloader(ui, settings, history).run(url)
    elif choice == "3":
        # "Best Quality" = video downloader forced onto the Best Available rung.
        downloader = Downloader(ui, settings, history)
        if info is None:
            ui.error("Could not fetch media information.")
            return
        label, height = "Best Available", None
        output_folder = downloader.ask_output_folder()
        stem = downloader.resolve_duplicate(output_folder, title, [".mp4", ".mkv", ".webm"])
        if stem is None:
            return
        opts = {
            "format": "bestvideo+bestaudio/best",
            "outtmpl": str(output_folder / f"{stem}.%(ext)s"),
            "merge_output_format": "mp4",
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "postprocessors": [{"key": "FFmpegMetadata"}],
            "overwrites": True,
            "cachedir": str(CACHE_DIR),
            "paths": {"temp": str(TEMP_DIR)},
        }
        with ui.build_progress() as progress:
            bridge = ProgressHookBridge(progress, ui)
            opts["progress_hooks"] = [bridge.hook]
            path, actual_info = downloader._execute_download(url, opts)
        if path:
            ui.success("Download completed!")
            ui.console.print(f"\n[bold]File:[/bold]\n{path.name}\n\n[bold]Location:[/bold]\n{path}")
            history.add(title=str(actual_info.get("title", "Unknown")), url=url,
                        website=str(actual_info.get("extractor_key", "Unknown")),
                        media_type="video", quality=label, fmt=path.suffix.lstrip("."),
                        output_path=str(path))
    elif choice == "4":
        if info:
            info_fetcher.show(url)
        else:
            ui.error("Could not fetch media information.")
    else:
        ui.info("Cancelled.")


def quick_video(url: str) -> None:
    """`--video URL` flow: minimal quality prompt, download straight to videos/."""
    ui, settings, history = _build_app_context()
    if not Validator.is_valid_url(url):
        ui.error(f"'{url}' is not a valid URL.")
        return
    ui.info("URL detected. Fetching information...")
    Downloader(ui, settings, history).run(url)


def quick_audio(url: str) -> None:
    """`--audio URL` flow: minimal format prompt, download straight to audios/."""
    ui, settings, history = _build_app_context()
    if not Validator.is_valid_url(url):
        ui.error(f"'{url}' is not a valid URL.")
        return
    ui.info("URL detected. Fetching information...")
    AudioDownloader(ui, settings, history).run(url)


def quick_info(url: str) -> None:
    """`--info URL` flow: show media info only, no download."""
    ui, settings, history = _build_app_context()
    if not Validator.is_valid_url(url):
        ui.error(f"'{url}' is not a valid URL.")
        return
    VideoInfo(ui).show(url)


def cli_history() -> None:
    """`--history` flow: print history and exit."""
    ui, settings, history = _build_app_context()
    Menu(ui, settings, history)._render_history(history.entries)


def cli_settings() -> None:
    """`--settings` flow: open the interactive settings menu and exit."""
    ui, settings, history = _build_app_context()
    Menu(ui, settings, history).settings_menu()


# =====================================================================
# ENTRY POINT
# =====================================================================

def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gva_downloader.py",
        description=f"{APP_NAME} v{APP_VERSION} - portable, cross-platform media downloader (powered by yt-dlp).",
    )
    parser.add_argument("url", nargs="?", default=None,
                         help="Direct URL to download or share (opens the quick download menu).")
    parser.add_argument("--url", dest="url_flag", default=None, help="Same as passing the URL directly.")
    parser.add_argument("--video", dest="video_url", default=None, help="Quick video download for URL.")
    parser.add_argument("--audio", dest="audio_url", default=None, help="Quick audio download for URL.")
    parser.add_argument("--info", dest="info_url", default=None, help="Show media information for URL only.")
    parser.add_argument("--history", action="store_true", help="Print download history and exit.")
    parser.add_argument("--settings", action="store_true", help="Open the settings menu and exit.")
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    try:
        if args.video_url:
            quick_video(args.video_url)
        elif args.audio_url:
            quick_audio(args.audio_url)
        elif args.info_url:
            quick_info(args.info_url)
        elif args.history:
            cli_history()
        elif args.settings:
            cli_settings()
        elif args.url_flag:
            handle_direct_url(args.url_flag)
        elif args.url:
            handle_direct_url(args.url)
        else:
            app = Application()
            app.run()
    except KeyboardInterrupt:
        console.print("\n[bold yellow]⚠️ Exiting. Goodbye![/]")
        sys.exit(0)
    except Exception as exc:
        logger.exception("Fatal error")
        console.print(f"[bold red]❌ Fatal error: {exc}[/]")
        console.print(f"[grey62]See {LOG_FILE} for details.[/]")
        sys.exit(1)


if __name__ == "__main__":
    main()
