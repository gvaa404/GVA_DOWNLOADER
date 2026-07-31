#!/usr/bin/env python3
"""
GVA Downloader
==============

A premium terminal-based media downloader for Android/Termux.

Author   : Jeevanantham K
Engine   : yt-dlp
Language : Python
Platform : Android (Termux)
Version  : 1.0

This single-file application wraps yt-dlp with a rich, colorful terminal
UI to make downloading video/audio content simple, safe, and pleasant
to use on a phone running Termux.

Dependencies:
    rich
    yt-dlp
    requests
    ffmpeg (system binary, used by yt-dlp for merging/conversion)
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None  # type: ignore

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
except ImportError:  # pragma: no cover
    print("Rich is not installed. Install it with: pip install rich")
    sys.exit(1)

try:
    import yt_dlp
except ImportError:  # pragma: no cover
    yt_dlp = None  # type: ignore


# =====================================================================
# CONSTANTS
# =====================================================================

APP_NAME = "GVA Downloader"
APP_AUTHOR = "Jeevanantham K"
APP_VERSION = "1.0"
APP_ENGINE = "yt-dlp"
APP_LANGUAGE = "Python"
APP_PLATFORM = "Android (Termux)"

DEFAULT_BASE_DIR = Path.home() / "storage" / "downloads" / "GVA Downloader"
CONFIG_DIR = Path.home() / ".gva_downloader"
SETTINGS_FILE = CONFIG_DIR / "settings.json"
HISTORY_FILE = CONFIG_DIR / "history.json"
LOG_FILE = CONFIG_DIR / "gva_downloader.log"

LOGO = r"""
[bold cyan]
 ██████╗  ██╗   ██╗ █████╗
██╔════╝ ██║   ██║██╔══██╗
██║  ███╗██║   ██║███████║
██║   ██║╚██╗ ██╔╝██╔══██║
╚██████╔╝ ╚████╔╝ ██║  ██║
 ╚═════╝   ╚═══╝  ╚═╝  ╚═╝
[/bold cyan]
[bold magenta]        GVA Downloader[/bold magenta]
"""

QUALITY_LADDER: List[Tuple[str, str, Optional[int]]] = [
    ("1", "144p", 144),
    ("2", "240p", 240),
    ("3", "360p", 360),
    ("4", "480p", 480),
    ("5", "720p (HD)", 720),
    ("6", "1080p (Full HD)", 1080),
    ("7", "2K", 1440),
    ("8", "4K", 2160),
    ("9", "8K", 4320),
    ("10", "Best Available", None),
]

AUDIO_QUALITY_LADDER: List[Tuple[str, str, str]] = [
    ("1", "Low (64 kbps)", "64"),
    ("2", "Medium (128 kbps)", "128"),
    ("3", "High (192 kbps)", "192"),
    ("4", "Very High (256 kbps)", "256"),
    ("5", "Best (320 kbps)", "320"),
]

AUDIO_FORMATS = ["MP3", "M4A", "AAC", "FLAC", "OGG", "WAV"]

console = Console()


# =====================================================================
# LOGGING
# =====================================================================

def setup_logging() -> logging.Logger:
    """Configure and return the application logger."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("gva_downloader")
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        try:
            handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        except OSError:
            handler = logging.StreamHandler(sys.stderr)
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


logger = setup_logging()


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
    def sanitize_filename(name: str) -> str:
        """Remove characters unsafe for filesystem paths."""
        invalid = '<>:"/\\|?*'
        for ch in invalid:
            name = name.replace(ch, "_")
        return name.strip()

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
        """Attempt to open a folder using termux-open or xdg-open."""
        try:
            if Utilities.which("termux-open"):
                subprocess.run(["termux-open", str(path)], check=False)
                return True
            if Utilities.which("xdg-open"):
                subprocess.run(["xdg-open", str(path)], check=False)
                return True
            console.print(f"[yellow]Could not auto-open folder. Path: {path}[/yellow]")
            return False
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to open folder: %s", exc)
            return False

    @staticmethod
    def safe_input(prompt_text: str, default: Optional[str] = None) -> str:
        """Wrap Rich Prompt.ask with graceful Ctrl+C / EOF handling."""
        try:
            return Prompt.ask(prompt_text, default=default) if default else Prompt.ask(prompt_text)
        except (KeyboardInterrupt, EOFError):
            raise


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
        if "." not in url.split("//", 1)[-1]:
            return False
        return True

    @staticmethod
    def is_valid_choice(choice: str, valid_choices: List[str]) -> bool:
        """Check whether a menu choice is within the valid set."""
        return choice in valid_choices

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
# SETTINGS
# =====================================================================

@dataclass
class AppSettings:
    """Application settings persisted to settings.json."""

    download_folder: str = str(DEFAULT_BASE_DIR)
    default_video_quality: str = "720p (HD)"
    default_audio_quality: str = "High (192 kbps)"
    theme: str = "default"
    filename_format: str = "%(title)s.%(ext)s"
    overwrite_existing: bool = False
    concurrent_downloads: int = 1


class Settings:
    """Manages loading, saving, and editing of application settings."""

    def __init__(self) -> None:
        self.data = AppSettings()
        self.load()

    def load(self) -> None:
        """Load settings from disk, falling back to defaults on failure."""
        try:
            if SETTINGS_FILE.exists():
                raw = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
                self.data = AppSettings(**{**asdict(AppSettings()), **raw})
            else:
                self.save()
        except (json.JSONDecodeError, OSError, TypeError) as exc:
            logger.error("Failed to load settings, using defaults: %s", exc)
            self.data = AppSettings()

    def save(self) -> bool:
        """Persist current settings to disk."""
        try:
            Utilities.ensure_dir(CONFIG_DIR)
            SETTINGS_FILE.write_text(
                json.dumps(asdict(self.data), indent=2), encoding="utf-8"
            )
            return True
        except OSError as exc:
            logger.error("Failed to save settings: %s", exc)
            return False

    def get_download_folder(self) -> Path:
        return Path(self.data.download_folder).expanduser()


# =====================================================================
# HISTORY
# =====================================================================

@dataclass
class HistoryEntry:
    date: str
    title: str
    website: str
    resolution: str
    output_path: str


class History:
    """Manages the persisted download history log."""

    def __init__(self) -> None:
        self.entries: List[HistoryEntry] = []
        self.load()

    def load(self) -> None:
        try:
            if HISTORY_FILE.exists():
                raw = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
                self.entries = [HistoryEntry(**item) for item in raw]
        except (json.JSONDecodeError, OSError, TypeError) as exc:
            logger.error("Failed to load history: %s", exc)
            self.entries = []

    def save(self) -> bool:
        try:
            Utilities.ensure_dir(CONFIG_DIR)
            HISTORY_FILE.write_text(
                json.dumps([asdict(e) for e in self.entries], indent=2),
                encoding="utf-8",
            )
            return True
        except OSError as exc:
            logger.error("Failed to save history: %s", exc)
            return False

    def add(self, title: str, website: str, resolution: str, output_path: str) -> None:
        entry = HistoryEntry(
            date=time.strftime("%Y-%m-%d %H:%M:%S"),
            title=title,
            website=website,
            resolution=resolution,
            output_path=output_path,
        )
        self.entries.append(entry)
        self.save()

    def delete(self, index: int) -> bool:
        if 0 <= index < len(self.entries):
            del self.entries[index]
            self.save()
            return True
        return False

    def clear(self) -> None:
        self.entries = []
        self.save()


# =====================================================================
# UI
# =====================================================================

class UI:
    """Rendering helpers built on top of Rich for a consistent look."""

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
        info.add_row("Language", APP_LANGUAGE)
        info.add_row("Platform", APP_PLATFORM)
        info.add_row("Version", APP_VERSION)
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
            ("3", "📜  Playlist Download"),
            ("4", "ℹ️  Video Information"),
            ("5", "🕘  Download History"),
            ("6", "⚙️  Settings"),
            ("7", "❓  Help"),
            ("8", "📖  About"),
            ("9", "🚪  Exit"),
        ]
        for num, desc in items:
            table.add_row(num, desc)
        return table

    def quality_menu(self) -> Table:
        table = Table(
            title="🎯 Select Quality",
            box=box.ROUNDED,
            border_style=self.theme.style("primary"),
            show_header=False,
        )
        table.add_column("Option", style=f"bold {self.theme.style('secondary')}", width=4)
        table.add_column("Quality", style=self.theme.style("primary"))
        for key, label, _ in QUALITY_LADDER:
            table.add_row(key, label)
        return table

    def audio_quality_menu(self) -> Table:
        table = Table(
            title="🎧 Select Audio Quality",
            box=box.ROUNDED,
            border_style=self.theme.style("primary"),
            show_header=False,
        )
        table.add_column("Option", style=f"bold {self.theme.style('secondary')}", width=4)
        table.add_column("Bitrate", style=self.theme.style("primary"))
        for key, label, _ in AUDIO_QUALITY_LADDER:
            table.add_row(key, label)
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


# =====================================================================
# YT-DLP ERROR TRANSLATION
# =====================================================================

class YtDlpErrorTranslator:
    """Translates raw yt-dlp / network exceptions into friendly messages."""

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
            return "This website is not supported by the downloader engine."
        if "sign in" in text or "login" in text:
            return "This content requires a login and cannot be accessed."
        if any(k in text for k in ("temporary failure", "name or service not known",
                                    "network is unreachable", "connection refused",
                                    "max retries exceeded")):
            return "No internet connection or the website could not be reached."
        if "permission denied" in text:
            return "Permission denied while writing files. Check storage permissions."
        if "no space left" in text:
            return "Storage is full. Free up space and try again."
        if "ffmpeg" in text and ("not found" in text or "not installed" in text):
            return "FFmpeg is not installed. Required for merging/converting media."
        return f"An error occurred: {exc}"


# =====================================================================
# VIDEO INFO
# =====================================================================

class VideoInfo:
    """Fetches and displays metadata about a video without downloading it."""

    def __init__(self, ui: UI) -> None:
        self.ui = ui

    def _extract(self, url: str) -> Optional[Dict[str, Any]]:
        if yt_dlp is None:
            self.ui.error("yt-dlp is not installed.")
            return None
        opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(url, download=False)
        except Exception as exc:  # noqa: BLE001
            self.ui.error(YtDlpErrorTranslator.translate(exc))
            logger.exception("Failed to extract info for %s", url)
            return None

    def show(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch and print a full metadata panel for the given URL."""
        with self.ui.console.status("[bold cyan]Fetching video information..."):
            info = self._extract(url)
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
        subtitles = list((info.get("subtitles") or {}).keys())
        auto_subs = list((info.get("automatic_captions") or {}).keys())

        table = Table(box=box.ROUNDED, show_header=False, border_style=self.ui.theme.style("primary"))
        table.add_column("Field", style=f"bold {self.ui.theme.style('secondary')}")
        table.add_column("Value", style=self.ui.theme.style("primary"))
        table.add_row("Title", str(info.get("title", "Unknown")))
        table.add_row("Uploader", str(info.get("uploader", "Unknown")))
        table.add_row("Duration", Utilities.human_duration(info.get("duration")))
        table.add_row("Views", Utilities.human_number(info.get("view_count")))
        description = (info.get("description") or "No description available.")
        if len(description) > 300:
            description = description[:300] + "..."
        table.add_row("Description", description)
        table.add_row("Thumbnail", str(info.get("thumbnail", "Unknown")))
        table.add_row(
            "Available Resolutions",
            ", ".join(f"{r}p" for r in resolutions) if resolutions else "Unknown",
        )
        table.add_row(
            "Available Audio",
            ", ".join(f"{int(a)}kbps" for a in audio_formats) if audio_formats else "Unknown",
        )
        table.add_row("Subtitles", ", ".join(subtitles) if subtitles else "None")
        table.add_row("Auto Captions", ", ".join(auto_subs[:10]) if auto_subs else "None")
        table.add_row("Live Stream", "Yes" if info.get("is_live") else "No")
        table.add_row("Age Restricted", "Yes" if info.get("age_limit", 0) else "No")
        table.add_row("Website", str(info.get("extractor_key", "Unknown")))

        self.ui.panel_table = table
        self.ui.console.print(Panel(table, title="🎬 Video Information", border_style=self.ui.theme.style("primary")))
        return info

    def show_basic(self, info: Dict[str, Any]) -> None:
        """Display a compact summary panel (used before downloading)."""
        table = Table(box=box.SIMPLE, show_header=False)
        table.add_column(style=f"bold {self.ui.theme.style('secondary')}")
        table.add_column(style=self.ui.theme.style("primary"))
        table.add_row("Title", str(info.get("title", "Unknown")))
        table.add_row("Uploader", str(info.get("uploader", "Unknown")))
        table.add_row("Duration", Utilities.human_duration(info.get("duration")))
        table.add_row("Views", Utilities.human_number(info.get("view_count")))
        table.add_row("Upload Date", str(info.get("upload_date", "Unknown")))
        table.add_row("Website", str(info.get("extractor_key", "Unknown")))
        table.add_row("Thumbnail URL", str(info.get("thumbnail", "Unknown")))
        self.ui.console.print(Panel(table, title="📄 Details", border_style=self.ui.theme.style("primary")))


# =====================================================================
# PROGRESS HOOK BRIDGE
# =====================================================================

class ProgressHookBridge:
    """Bridges yt-dlp's progress_hooks callbacks into a Rich Progress bar."""

    def __init__(self, progress: Progress, ui: UI) -> None:
        self.progress = progress
        self.ui = ui
        self.task_ids: Dict[str, Any] = {}

    def hook(self, d: Dict[str, Any]) -> None:
        filename = d.get("filename", "download")
        key = filename
        status = d.get("status")

        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)
            if key not in self.task_ids:
                short_name = Path(filename).name
                if len(short_name) > 40:
                    short_name = short_name[:37] + "..."
                self.task_ids[key] = self.progress.add_task(
                    short_name, total=total if total else None
                )
            task_id = self.task_ids[key]
            if total:
                self.progress.update(task_id, completed=downloaded, total=total)
            else:
                self.progress.update(task_id, completed=downloaded)
        elif status == "finished":
            if key in self.task_ids:
                task_id = self.task_ids[key]
                self.progress.update(task_id, completed=self.progress.tasks[
                    [t.id for t in self.progress.tasks].index(task_id)
                ].total or 0)
        elif status == "error":
            self.ui.warning(f"Error while downloading: {filename}")


# =====================================================================
# BASE DOWNLOADER
# =====================================================================

class BaseDownloader:
    """Shared logic for all downloader subclasses."""

    def __init__(self, ui: UI, settings: Settings, history: History) -> None:
        self.ui = ui
        self.settings = settings
        self.history = history

    def check_ffmpeg(self) -> bool:
        if Utilities.which("ffmpeg") is None:
            self.ui.error(
                "FFmpeg is not installed. Install it with: pkg install ffmpeg"
            )
            return False
        return True

    def ask_output_folder(self) -> Path:
        default = str(self.settings.get_download_folder())
        self.ui.console.print(f"[muted]Default: {default}[/]")
        use_default = Confirm.ask("Use default output folder?", default=True)
        if use_default:
            folder = Path(default)
        else:
            raw = Prompt.ask("Enter output folder path")
            folder = Path(raw).expanduser()
        Utilities.ensure_dir(folder)
        return folder

    def ask_quality(self) -> Tuple[str, Optional[int]]:
        self.ui.console.print(self.ui.quality_menu())
        valid = [q[0] for q in QUALITY_LADDER]
        choice = Prompt.ask("Select quality", choices=valid, default="5")
        for key, label, height in QUALITY_LADDER:
            if key == choice:
                return label, height
        return "720p (HD)", 720

    def ask_yes_no(self, question: str, default: bool = False) -> bool:
        return Confirm.ask(question, default=default)

    def build_format_string(self, height: Optional[int]) -> str:
        if height is None:
            return "bestvideo+bestaudio/best"
        return (
            f"bestvideo[height<={height}]+bestaudio/best[height<={height}]/"
            f"best[height<={height}]/best"
        )

    def build_ydl_opts(
        self,
        output_folder: Path,
        fmt: str,
        subtitles: bool,
        embed_metadata: bool,
        embed_thumbnail: bool,
        sponsorblock: bool,
        progress_hook: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        outtmpl = str(output_folder / self.settings.data.filename_format)
        postprocessors: List[Dict[str, Any]] = []
        if embed_metadata:
            postprocessors.append({"key": "FFmpegMetadata"})
        if embed_thumbnail:
            postprocessors.append({"key": "EmbedThumbnail"})
            postprocessors.append({"key": "FFmpegThumbnailsConvertor", "format": "jpg"})

        opts: Dict[str, Any] = {
            "format": fmt,
            "outtmpl": outtmpl,
            "merge_output_format": "mp4",
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "writesubtitles": subtitles,
            "writeautomaticsub": subtitles,
            "embedsubtitles": subtitles,
            "postprocessors": postprocessors,
            "overwrites": self.settings.data.overwrite_existing,
            "writethumbnail": embed_thumbnail,
            "ignoreerrors": False,
            "retries": 5,
            "fragment_retries": 5,
        }
        if progress_hook:
            opts["progress_hooks"] = [progress_hook]
        if sponsorblock:
            opts["postprocessors"].append(
                {
                    "key": "SponsorBlock",
                    "categories": ["sponsor", "selfpromo", "interaction"],
                }
            )
            opts["postprocessors"].append(
                {
                    "key": "ModifyChapters",
                    "remove_sponsor_segments": ["sponsor", "selfpromo", "interaction"],
                }
            )
        return opts


# =====================================================================
# VIDEO DOWNLOADER
# =====================================================================

class Downloader(BaseDownloader):
    """Handles single video downloads."""

    def run(self) -> None:
        self.ui.rule("Download Video")
        url = Prompt.ask("Paste Video URL")
        if not Validator.is_valid_url(url):
            self.ui.error("Invalid URL. Please provide a valid http(s) link.")
            return

        video_info = VideoInfo(self.ui)
        info = video_info.show(url)
        if info is None:
            return
        video_info.show_basic(info)

        if info.get("is_live"):
            self.ui.warning("This is a live stream. Downloading may capture only the current segment.")

        label, height = self.ask_quality()
        subtitles = self.ask_yes_no("Download subtitles?", default=False)
        embed_metadata = self.ask_yes_no("Embed metadata?", default=True)
        embed_thumbnail = self.ask_yes_no("Embed thumbnail?", default=False)
        sponsorblock = self.ask_yes_no("Use SponsorBlock if available?", default=False)
        output_folder = self.ask_output_folder()

        if embed_thumbnail or embed_metadata or sponsorblock:
            if not self.check_ffmpeg():
                return

        fmt = self.build_format_string(height)

        with self.ui.build_progress() as progress:
            bridge = ProgressHookBridge(progress, self.ui)
            opts = self.build_ydl_opts(
                output_folder,
                fmt,
                subtitles,
                embed_metadata,
                embed_thumbnail,
                sponsorblock,
                progress_hook=bridge.hook,
            )
            result_path, actual_info = self._download(url, opts)

        if result_path is None:
            return

        self._show_success(result_path, label, actual_info)
        self.history.add(
            title=str(actual_info.get("title", "Unknown")) if actual_info else "Unknown",
            website=str(actual_info.get("extractor_key", "Unknown")) if actual_info else "Unknown",
            resolution=label,
            output_path=str(result_path),
        )

        if self.ask_yes_no("Open Folder?", default=False):
            Utilities.open_folder(result_path.parent)

    def _download(
        self, url: str, opts: Dict[str, Any]
    ) -> Tuple[Optional[Path], Optional[Dict[str, Any]]]:
        if yt_dlp is None:
            self.ui.error("yt-dlp is not installed.")
            return None, None
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if info is None:
                    self.ui.error("Download failed: no information returned.")
                    return None, None
                filename = ydl.prepare_filename(info)
                final_path = Path(filename)
                if not final_path.exists():
                    for ext in (".mp4", ".mkv", ".webm"):
                        candidate = final_path.with_suffix(ext)
                        if candidate.exists():
                            final_path = candidate
                            break
                return final_path, info
        except yt_dlp.utils.DownloadError as exc:  # type: ignore[union-attr]
            self.ui.error(YtDlpErrorTranslator.translate(exc))
            logger.exception("Download error for %s", url)
            return None, None
        except KeyboardInterrupt:
            self.ui.warning("Download cancelled by user.")
            raise
        except Exception as exc:  # noqa: BLE001
            self.ui.error(YtDlpErrorTranslator.translate(exc))
            logger.exception("Unexpected error downloading %s", url)
            return None, None

    def _show_success(
        self, path: Path, resolution: str, info: Optional[Dict[str, Any]]
    ) -> None:
        size = path.stat().st_size if path.exists() else None
        table = Table(box=box.SIMPLE, show_header=False)
        table.add_column(style=f"bold {self.ui.theme.style('secondary')}")
        table.add_column(style=self.ui.theme.style("primary"))
        table.add_row("Filename", path.name)
        table.add_row("Resolution", resolution)
        table.add_row("Size", Utilities.human_size(size))
        table.add_row("Location", str(path.parent))
        self.ui.console.print(
            Panel(table, title="✅ Download Successful", border_style=self.ui.theme.style("success"))
        )


# =====================================================================
# AUDIO DOWNLOADER
# =====================================================================

class AudioDownloader(BaseDownloader):
    """Handles audio-only downloads with format/bitrate conversion."""

    def run(self) -> None:
        self.ui.rule("Download Audio")
        url = Prompt.ask("Paste Video/Audio URL")
        if not Validator.is_valid_url(url):
            self.ui.error("Invalid URL. Please provide a valid http(s) link.")
            return

        if not self.check_ffmpeg():
            return

        video_info = VideoInfo(self.ui)
        with self.ui.console.status("[bold cyan]Fetching information..."):
            info = video_info._extract(url)
        if info is None:
            return
        video_info.show_basic(info)

        self.ui.console.print(self.ui.audio_quality_menu())
        valid = [q[0] for q in AUDIO_QUALITY_LADDER]
        choice = Prompt.ask("Select audio quality", choices=valid, default="3")
        bitrate_label, bitrate = "High (192 kbps)", "192"
        for key, label, br in AUDIO_QUALITY_LADDER:
            if key == choice:
                bitrate_label, bitrate = label, br

        fmt_choice = Prompt.ask(
            "Output format",
            choices=[f.lower() for f in AUDIO_FORMATS],
            default="mp3",
        )

        embed_metadata = self.ask_yes_no("Embed metadata?", default=True)
        embed_thumbnail = self.ask_yes_no("Embed thumbnail (cover art)?", default=False)
        output_folder = self.ask_output_folder()

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

        outtmpl = str(output_folder / self.settings.data.filename_format)
        opts: Dict[str, Any] = {
            "format": "bestaudio/best",
            "outtmpl": outtmpl,
            "postprocessors": postprocessors,
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "writethumbnail": embed_thumbnail,
            "overwrites": self.settings.data.overwrite_existing,
            "retries": 5,
            "fragment_retries": 5,
        }

        with self.ui.build_progress() as progress:
            bridge = ProgressHookBridge(progress, self.ui)
            opts["progress_hooks"] = [bridge.hook]
            result_path, actual_info = self._download(url, opts, fmt_choice)

        if result_path is None:
            return

        self._show_success(result_path, bitrate_label)
        self.history.add(
            title=str(actual_info.get("title", "Unknown")) if actual_info else "Unknown",
            website=str(actual_info.get("extractor_key", "Unknown")) if actual_info else "Unknown",
            resolution=f"Audio {bitrate_label}",
            output_path=str(result_path),
        )

        if self.ask_yes_no("Open Folder?", default=False):
            Utilities.open_folder(result_path.parent)

    def _download(
        self, url: str, opts: Dict[str, Any], ext: str
    ) -> Tuple[Optional[Path], Optional[Dict[str, Any]]]:
        if yt_dlp is None:
            self.ui.error("yt-dlp is not installed.")
            return None, None
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if info is None:
                    self.ui.error("Download failed: no information returned.")
                    return None, None
                filename = ydl.prepare_filename(info)
                final_path = Path(filename).with_suffix(f".{ext}")
                if not final_path.exists():
                    stem_path = Path(filename)
                    if stem_path.exists():
                        final_path = stem_path
                return final_path, info
        except yt_dlp.utils.DownloadError as exc:  # type: ignore[union-attr]
            self.ui.error(YtDlpErrorTranslator.translate(exc))
            logger.exception("Audio download error for %s", url)
            return None, None
        except KeyboardInterrupt:
            self.ui.warning("Download cancelled by user.")
            raise
        except Exception as exc:  # noqa: BLE001
            self.ui.error(YtDlpErrorTranslator.translate(exc))
            logger.exception("Unexpected error downloading audio %s", url)
            return None, None

    def _show_success(self, path: Path, bitrate_label: str) -> None:
        size = path.stat().st_size if path.exists() else None
        table = Table(box=box.SIMPLE, show_header=False)
        table.add_column(style=f"bold {self.ui.theme.style('secondary')}")
        table.add_column(style=self.ui.theme.style("primary"))
        table.add_row("Filename", path.name)
        table.add_row("Bitrate", bitrate_label)
        table.add_row("Size", Utilities.human_size(size))
        table.add_row("Location", str(path.parent))
        self.ui.console.print(
            Panel(table, title="✅ Download Successful", border_style=self.ui.theme.style("success"))
        )


# =====================================================================
# PLAYLIST DOWNLOADER
# =====================================================================

class PlaylistDownloader(BaseDownloader):
    """Handles playlist detection and batch downloads."""

    def run(self) -> None:
        self.ui.rule("Playlist Download")
        url = Prompt.ask("Paste Playlist URL")
        if not Validator.is_valid_url(url):
            self.ui.error("Invalid URL. Please provide a valid http(s) link.")
            return

        with self.ui.console.status("[bold cyan]Detecting playlist..."):
            entries = self._extract_playlist(url)

        if entries is None:
            return

        if len(entries) <= 1:
            self.ui.info("This does not appear to be a playlist. Downloading as a single video.")
            Downloader(self.ui, self.settings, self.history).run()
            return

        self.ui.success(f"Playlist detected with {len(entries)} videos.")
        table = Table(box=box.SIMPLE)
        table.add_column("#", style="bold")
        table.add_column("Title")
        for idx, entry in enumerate(entries[:15], start=1):
            table.add_row(str(idx), str(entry.get("title", "Unknown")))
        if len(entries) > 15:
            table.add_row("...", f"and {len(entries) - 15} more")
        self.ui.console.print(table)

        mode = Prompt.ask(
            "Download",
            choices=["entire", "range", "single"],
            default="entire",
        )

        selected_indices: List[int]
        if mode == "entire":
            selected_indices = list(range(1, len(entries) + 1))
        elif mode == "range":
            range_str = Prompt.ask(f"Enter range (e.g. 1-{len(entries)})")
            if not Validator.is_valid_range(range_str, len(entries)):
                self.ui.error("Invalid range.")
                return
            start, end = (int(x) for x in range_str.split("-"))
            selected_indices = list(range(start, end + 1))
        else:
            single_str = Prompt.ask(f"Enter video number (1-{len(entries)})")
            try:
                single = int(single_str)
                if not (1 <= single <= len(entries)):
                    raise ValueError
            except ValueError:
                self.ui.error("Invalid video number.")
                return
            selected_indices = [single]

        label, height = self.ask_quality()
        subtitles = self.ask_yes_no("Download subtitles?", default=False)
        embed_metadata = self.ask_yes_no("Embed metadata?", default=True)
        embed_thumbnail = self.ask_yes_no("Embed thumbnail?", default=False)
        sponsorblock = self.ask_yes_no("Use SponsorBlock if available?", default=False)
        output_folder = self.ask_output_folder()

        if embed_thumbnail or embed_metadata or sponsorblock:
            if not self.check_ffmpeg():
                return

        fmt = self.build_format_string(height)
        success_count = 0

        for i in selected_indices:
            entry = entries[i - 1]
            entry_url = entry.get("url") or entry.get("webpage_url")
            if not entry_url:
                continue
            self.ui.rule(f"Video {i}/{len(entries)}: {entry.get('title', 'Unknown')}")
            with self.ui.build_progress() as progress:
                bridge = ProgressHookBridge(progress, self.ui)
                opts = self.build_ydl_opts(
                    output_folder,
                    fmt,
                    subtitles,
                    embed_metadata,
                    embed_thumbnail,
                    sponsorblock,
                    progress_hook=bridge.hook,
                )
                downloader = Downloader(self.ui, self.settings, self.history)
                result_path, actual_info = downloader._download(entry_url, opts)
            if result_path:
                success_count += 1
                self.history.add(
                    title=str(actual_info.get("title", "Unknown")) if actual_info else "Unknown",
                    website=str(actual_info.get("extractor_key", "Unknown")) if actual_info else "Unknown",
                    resolution=label,
                    output_path=str(result_path),
                )

        self.ui.success(f"Playlist download complete: {success_count}/{len(selected_indices)} succeeded.")
        if self.ask_yes_no("Open Folder?", default=False):
            Utilities.open_folder(output_folder)

    def _extract_playlist(self, url: str) -> Optional[List[Dict[str, Any]]]:
        if yt_dlp is None:
            self.ui.error("yt-dlp is not installed.")
            return None
        opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "skip_download": True,
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if info is None:
                    self.ui.error("Could not retrieve playlist information.")
                    return None
                if "entries" in info and info["entries"]:
                    return [e for e in info["entries"] if e]
                return [info]
        except Exception as exc:  # noqa: BLE001
            self.ui.error(YtDlpErrorTranslator.translate(exc))
            logger.exception("Failed to extract playlist %s", url)
            return None


# =====================================================================
# MENU (screens for History / Settings / Help / About)
# =====================================================================

class Menu:
    """Handles the non-downloader informational/interactive screens."""

    def __init__(self, ui: UI, settings: Settings, history: History) -> None:
        self.ui = ui
        self.settings = settings
        self.history = history

    # ---------------- History ----------------

    def show_history(self) -> None:
        self.ui.rule("Download History")
        if not self.history.entries:
            self.ui.info("No download history yet.")
            return

        table = Table(box=box.ROUNDED, border_style=self.ui.theme.style("primary"))
        table.add_column("#", style="bold")
        table.add_column("Date")
        table.add_column("Title", overflow="fold")
        table.add_column("Website")
        table.add_column("Resolution")
        table.add_column("Path", overflow="fold")
        for idx, entry in enumerate(self.history.entries, start=1):
            table.add_row(
                str(idx), entry.date, entry.title, entry.website,
                entry.resolution, entry.output_path,
            )
        self.ui.console.print(table)

        action = Prompt.ask(
            "Action",
            choices=["none", "delete", "clear"],
            default="none",
        )
        if action == "delete":
            idx_str = Prompt.ask("Enter entry number to delete")
            try:
                idx = int(idx_str) - 1
            except ValueError:
                self.ui.error("Invalid entry number.")
                return
            if self.history.delete(idx):
                self.ui.success("Entry deleted.")
            else:
                self.ui.error("Entry not found.")
        elif action == "clear":
            if Confirm.ask("Are you sure you want to clear all history?", default=False):
                self.history.clear()
                self.ui.success("History cleared.")

    # ---------------- Settings ----------------

    def show_settings(self) -> None:
        self.ui.rule("Settings")
        table = Table(box=box.ROUNDED, show_header=False, border_style=self.ui.theme.style("primary"))
        table.add_column(style=f"bold {self.ui.theme.style('secondary')}")
        table.add_column(style=self.ui.theme.style("primary"))
        table.add_row("1. Download Folder", self.settings.data.download_folder)
        table.add_row("2. Default Video Quality", self.settings.data.default_video_quality)
        table.add_row("3. Default Audio Quality", self.settings.data.default_audio_quality)
        table.add_row("4. Theme", self.settings.data.theme)
        table.add_row("5. Filename Format", self.settings.data.filename_format)
        table.add_row("6. Overwrite Existing Files", str(self.settings.data.overwrite_existing))
        table.add_row("7. Concurrent Downloads", str(self.settings.data.concurrent_downloads))
        table.add_row("8. Back", "")
        self.ui.console.print(table)

        choice = Prompt.ask(
            "Select setting to change",
            choices=[str(i) for i in range(1, 9)],
            default="8",
        )
        if choice == "1":
            new_folder = Prompt.ask("Enter new download folder", default=self.settings.data.download_folder)
            self.settings.data.download_folder = str(Path(new_folder).expanduser())
        elif choice == "2":
            valid = [q[1] for q in QUALITY_LADDER]
            new_q = Prompt.ask("Enter default video quality", choices=valid, default=self.settings.data.default_video_quality)
            self.settings.data.default_video_quality = new_q
        elif choice == "3":
            valid = [q[1] for q in AUDIO_QUALITY_LADDER]
            new_q = Prompt.ask("Enter default audio quality", choices=valid, default=self.settings.data.default_audio_quality)
            self.settings.data.default_audio_quality = new_q
        elif choice == "4":
            new_theme = Prompt.ask("Enter theme", choices=list(Theme.THEMES.keys()), default=self.settings.data.theme)
            self.settings.data.theme = new_theme
            self.ui.theme = Theme(new_theme)
        elif choice == "5":
            new_fmt = Prompt.ask("Enter filename format", default=self.settings.data.filename_format)
            self.settings.data.filename_format = new_fmt
        elif choice == "6":
            self.settings.data.overwrite_existing = Confirm.ask(
                "Overwrite existing files?", default=self.settings.data.overwrite_existing
            )
        elif choice == "7":
            new_val = Prompt.ask("Enter number of concurrent downloads", default=str(self.settings.data.concurrent_downloads))
            try:
                self.settings.data.concurrent_downloads = max(1, int(new_val))
            except ValueError:
                self.ui.error("Invalid number.")
        else:
            return

        if self.settings.save():
            self.ui.success("Settings saved.")
        else:
            self.ui.error("Failed to save settings.")

    # ---------------- Help ----------------

    def show_help(self) -> None:
        self.ui.rule("Help")
        checks = [
            ("Python", sys.version.split()[0], True),
            ("yt-dlp", getattr(yt_dlp, "version", None) and getattr(yt_dlp.version, "__version__", "Unknown") if yt_dlp else None, yt_dlp is not None),
            ("FFmpeg", self._ffmpeg_version(), Utilities.which("ffmpeg") is not None),
            ("Rich", self._pkg_version("rich"), True),
            ("Requests", self._pkg_version("requests"), requests is not None),
        ]
        table = Table(box=box.ROUNDED, border_style=self.ui.theme.style("primary"))
        table.add_column("Component", style="bold")
        table.add_column("Status")
        table.add_column("Version")
        install_hints = {
            "yt-dlp": "pip install -U yt-dlp",
            "FFmpeg": "pkg install ffmpeg",
            "Rich": "pip install rich",
            "Requests": "pip install requests",
        }
        for name, version, installed in checks:
            status = "[bold green]Installed[/]" if installed else "[bold red]Missing[/]"
            table.add_row(name, status, str(version) if version else "N/A")
            if not installed and name in install_hints:
                self.ui.warning(f"Install {name} with: {install_hints[name]}")
        self.ui.console.print(table)
        self.ui.panel(
            "GVA Downloader supports downloading video/audio from any site "
            "supported by yt-dlp. Use the Main Menu to get started. "
            "For issues, check the log file at:\n" + str(LOG_FILE),
            title="📚 Usage Tips",
        )

    @staticmethod
    def _ffmpeg_version() -> Optional[str]:
        path = Utilities.which("ffmpeg")
        if not path:
            return None
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"], capture_output=True, text=True, timeout=5
            )
            first_line = result.stdout.splitlines()[0] if result.stdout else ""
            return first_line.split(" ")[2] if len(first_line.split(" ")) > 2 else "Unknown"
        except Exception:  # noqa: BLE001
            return "Unknown"

    @staticmethod
    def _pkg_version(pkg_name: str) -> Optional[str]:
        try:
            import importlib.metadata as md
            return md.version(pkg_name)
        except Exception:  # noqa: BLE001
            return None

    # ---------------- About ----------------

    def show_about(self) -> None:
        self.ui.rule("About")
        content = (
            f"[bold]{APP_NAME}[/bold]\n\n"
            f"Author   : {APP_AUTHOR}\n"
            f"Backend  : {APP_ENGINE}\n"
            f"Platform : {APP_PLATFORM}\n"
            f"Language : {APP_LANGUAGE}\n"
            f"Version  : {APP_VERSION}"
        )
        self.ui.panel(content, title="📖 About", style=self.ui.theme.style("secondary"))


# =====================================================================
# APPLICATION
# =====================================================================

class Application:
    """Top-level application controller that ties everything together."""

    def __init__(self) -> None:
        self.settings = Settings()
        self.history = History()
        self.theme = Theme(self.settings.data.theme)
        self.ui = UI(self.theme)
        self.menu = Menu(self.ui, self.settings, self.history)
        self.running = True

    def check_dependencies(self) -> bool:
        """Verify critical dependencies are present before starting."""
        missing = []
        if yt_dlp is None:
            missing.append("yt-dlp (pip install -U yt-dlp)")
        if requests is None:
            missing.append("requests (pip install requests)")
        if missing:
            self.ui.error("Missing required dependencies:")
            for item in missing:
                self.ui.console.print(f"  - {item}")
            return False
        return True

    def splash(self) -> None:
        self.ui.clear()
        self.ui.show_logo()
        self.ui.press_enter()

    def main_loop(self) -> None:
        while self.running:
            try:
                self.ui.clear()
                self.ui.show_logo()
                self.ui.console.print(self.ui.main_menu())
                choice = Prompt.ask(
                    "Select an option",
                    choices=[str(i) for i in range(1, 10)],
                    show_choices=False,
                )
                self.dispatch(choice)
            except KeyboardInterrupt:
                self.ui.console.print()
                self.ui.warning("Operation cancelled (Ctrl+C).")
                if Confirm.ask("Exit GVA Downloader?", default=False):
                    self.running = False
                continue
            except EOFError:
                self.running = False
                continue
            except Exception as exc:  # noqa: BLE001
                logger.exception("Unhandled exception in main loop")
                self.ui.error(f"An unexpected error occurred: {exc}")
                self.ui.console.print("[muted]The error has been logged. Returning to main menu.[/]")

            if self.running and choice != "9":
                self.ui.console.print()
                self.ui.press_enter()

    def dispatch(self, choice: str) -> None:
        """Route the user's main-menu choice to the correct handler."""
        handlers: Dict[str, Callable[[], None]] = {
            "1": lambda: Downloader(self.ui, self.settings, self.history).run(),
            "2": lambda: AudioDownloader(self.ui, self.settings, self.history).run(),
            "3": lambda: PlaylistDownloader(self.ui, self.settings, self.history).run(),
            "4": self._video_information,
            "5": self.menu.show_history,
            "6": self.menu.show_settings,
            "7": self.menu.show_help,
            "8": self.menu.show_about,
            "9": self._exit,
        }
        handler = handlers.get(choice)
        if handler:
            handler()

    def _video_information(self) -> None:
        self.ui.rule("Video Information")
        url = Prompt.ask("Paste Video URL")
        if not Validator.is_valid_url(url):
            self.ui.error("Invalid URL. Please provide a valid http(s) link.")
            return
        VideoInfo(self.ui).show(url)

    def _exit(self) -> None:
        self.ui.console.print()
        self.ui.panel(
            "Thank you for using GVA Downloader! 👋",
            title="Goodbye",
            style=self.ui.theme.style("secondary"),
        )
        self.running = False

    def run(self) -> None:
        """Entry point: verify environment, show splash, run main loop."""
        Utilities.ensure_dir(CONFIG_DIR)
        Utilities.ensure_dir(self.settings.get_download_folder())

        if not self.check_dependencies():
            sys.exit(1)

        try:
            self.splash()
            self.main_loop()
        except KeyboardInterrupt:
            self.ui.console.print()
            self.ui.warning("Interrupted. Exiting GVA Downloader.")
        except Exception as exc:  # noqa: BLE001
            logger.exception("Fatal unhandled exception")
            self.ui.error(f"A fatal error occurred: {exc}")
            self.ui.console.print("[muted]Check the log file for details:[/] " + str(LOG_FILE))
            sys.exit(1)


# =====================================================================
# ENTRY POINT
# =====================================================================

def main() -> None:
    """Application entry point."""
    try:
        app = Application()
        app.run()
    except KeyboardInterrupt:
        console.print("\n[bold yellow]⚠️  Exiting GVA Downloader. Goodbye![/]")
        sys.exit(0)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Fatal error during startup")
        console.print(f"[bold red]❌ Fatal error: {exc}[/]")
        console.print(f"[grey62]Details logged to: {LOG_FILE}[/]")
        sys.exit(1)


if __name__ == "__main__":
    main()
