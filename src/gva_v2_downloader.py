#!/usr/bin/env python3
"""
GVA Downloader
==============

A premium terminal-based media downloader for Android/Termux.

Author   : Jeevanantham K
Engine   : yt-dlp
Language : Python
Platform : Android (Termux)
Version  : 2.0 (Enhanced UX & Dynamic Formats)
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    import requests
except ImportError:
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
except ImportError:
    print("Rich is not installed. Install it with: pip install rich")
    sys.exit(1)

try:
    import yt_dlp
except ImportError:
    yt_dlp = None  # type: ignore


# =====================================================================
# CONSTANTS
# =====================================================================

APP_NAME = "GVA Downloader"
APP_AUTHOR = "Jeevanantham K"
APP_VERSION = "2.0"
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
[bold magenta]        GVA Downloader v2.0[/bold magenta]
"""

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
        except Exception as exc:
            logger.error("Failed to open folder: %s", exc)
            return False


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
    download_folder: str = str(DEFAULT_BASE_DIR)
    default_video_quality: str = "Best Available"
    default_audio_quality: str = "Best Available"
    theme: str = "default"
    filename_format: str = "%(title)s.%(ext)s"
    overwrite_existing: bool = False


class Settings:
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

    def get_download_folder(self) -> Path:
        return Path(self.data.download_folder).expanduser()


@dataclass
class HistoryEntry:
    date: str
    title: str
    website: str
    resolution: str
    output_path: str


class History:
    def __init__(self) -> None:
        self.entries: List[HistoryEntry] = []
        self.load()

    def load(self) -> None:
        try:
            if HISTORY_FILE.exists():
                raw = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
                self.entries = [HistoryEntry(**item) for item in raw]
        except Exception as exc:
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
        except Exception as exc:
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

        self.ui.console.print(Panel(table, title="🎬 Media Information", border_style=self.ui.theme.style("primary")))
        return info


# =====================================================================
# PROGRESS HOOK BRIDGE
# =====================================================================

class ProgressHookBridge:
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
                if len(short_name) > 35:
                    short_name = short_name[:32] + "..."
                self.task_ids[key] = self.progress.add_task(
                    short_name, total=total if total else None
                )
            task_id = self.task_ids[key]
            if total:
                self.progress.update(task_id, completed=downloaded, total=total)
            else:
                self.progress.update(task_id, completed=downloaded)


# =====================================================================
# BASE DOWNLOADER
# =====================================================================

class BaseDownloader:
    def __init__(self, ui: UI, settings: Settings, history: History) -> None:
        self.ui = ui
        self.settings = settings
        self.history = history

    def check_ffmpeg(self) -> bool:
        if Utilities.which("ffmpeg") is None:
            self.ui.error("FFmpeg is not installed. Install it with: pkg install ffmpeg")
            return False
        return True

    def ask_output_folder(self) -> Path:
        default = str(self.settings.get_download_folder())
        self.ui.console.print(f"[muted]Default Folder: {default}[/]")
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


# =====================================================================
# VIDEO DOWNLOADER
# =====================================================================

class Downloader(BaseDownloader):
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
        sponsorblock = Confirm.ask("Use SponsorBlock?", default=False)
        output_folder = self.ask_output_folder()

        if embed_thumbnail or embed_metadata or sponsorblock:
            if not self.check_ffmpeg():
                return

        fmt = "bestvideo+bestaudio/best" if height is None else f"bestvideo[height<={height}]+bestaudio/best[height<={height}]/best"

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
            "embedsubtitles": subtitles,
            "postprocessors": postprocessors,
            "overwrites": self.settings.data.overwrite_existing,
        }

        with self.ui.build_progress() as progress:
            bridge = ProgressHookBridge(progress, self.ui)
            opts["progress_hooks"] = [bridge.hook]
            path, actual_info = self._execute_download(url, opts)

        if path:
            self.ui.success(f"Downloaded: {path.name}")
            self.history.add(
                title=str(actual_info.get("title", "Unknown")),
                website=str(actual_info.get("extractor_key", "Unknown")),
                resolution=label,
                output_path=str(path),
            )

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
            return None, None


# =====================================================================
# AUDIO DOWNLOADER
# =====================================================================

class AudioDownloader(BaseDownloader):
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
            "overwrites": self.settings.data.overwrite_existing,
        }

        with self.ui.build_progress() as progress:
            bridge = ProgressHookBridge(progress, self.ui)
            opts["progress_hooks"] = [bridge.hook]
            path, actual_info = self._execute_download(url, opts, fmt_choice)

        if path:
            self.ui.success(f"Downloaded Audio: {path.name}")
            self.history.add(
                title=str(actual_info.get("title", "Unknown")),
                website=str(actual_info.get("extractor_key", "Unknown")),
                resolution=f"Audio ({bitrate_label})",
                output_path=str(path),
            )

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
        
        # Display sample entries
        table = Table(box=box.SIMPLE)
        table.add_column("#", style="bold")
        table.add_column("Title")
        for idx, entry in enumerate(entries[:10], start=1):
            table.add_row(str(idx), str(entry.get("title", "Unknown")))
        if len(entries) > 10:
            table.add_row("...", f"and {len(entries) - 10} more")
        self.ui.console.print(table)

        # Playlist mode choices
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

        # MEDIA TYPE OPTION: Video vs Audio
        download_type = Prompt.ask("Download playlist as", choices=["video", "audio"], default="video")
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
            }

            self._process_playlist_loop(entries, selected_indices, opts, f"Audio ({bitrate}k)")

        else: # Video download
            quality = Prompt.ask("Preferred max video quality", choices=["1080", "720", "480", "best"], default="best")
            fmt = "bestvideo+bestaudio/best" if quality == "best" else f"bestvideo[height<={quality}]+bestaudio/best"

            opts = {
                "format": fmt,
                "outtmpl": str(output_folder / "%(playlist_index)s - %(title)s.%(ext)s"),
                "merge_output_format": "mp4",
                "quiet": True,
                "overwrites": self.settings.data.overwrite_existing,
            }

            self._process_playlist_loop(entries, selected_indices, opts, f"Video ({quality}p)")

    def _process_playlist_loop(self, entries: List[Dict[str, Any]], indices: List[int], opts: Dict[str, Any], label: str) -> None:
        success = 0
        for i in indices:
            entry = entries[i - 1]
            entry_url = entry.get("url") or entry.get("webpage_url") or entry.get("id")
            if not entry_url.startswith("http"):
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
                            self.history.add(title, "Playlist", label, str(opts["outtmpl"]))
                except Exception as exc:
                    self.ui.error(f"Failed item {i}: {exc}")

        self.ui.success(f"Playlist batch complete! {success}/{len(indices)} downloaded successfully.")

    def _extract_playlist(self, url: str) -> Optional[List[Dict[str, Any]]]:
        opts = {"quiet": True, "extract_flat": True, "skip_download": True}
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
# NEW UX COMMANDS: SEARCH & BATCH DOWNLOAD
# =====================================================================

class SearchDownloader:
    """Search YouTube directly inside Termux and download media."""

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
            opts = {"quiet": True, "extract_flat": True, "skip_download": True}
            search_target = f"ytsearch7:{query}"
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    res = ydl.extract_info(search_target, download=False)
                    entries = res.get("entries", []) if res else []
            except Exception as exc:
                self.ui.error(f"Search failed: {exc}")
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
        choice_str = Prompt.ask("Select video number to download (0 to cancel)", choices=[str(i) for i in range(len(entries) + 1)], default="1")
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
            urls = [line.strip() for line in path.read_text().splitlines() if line.strip() and Validator.is_valid_url(line.strip())]
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

        downloader = Downloader(self.ui, self.settings, self.history) if dl_type == "video" else AudioDownloader(self.ui, self.settings, self.history)

        for idx, u in enumerate(urls, start=1):
            self.ui.rule(f"Item {idx}/{len(urls)}")
            downloader.run(u)


class EngineMaintenance:
    """Update engine and manage cache."""

    def __init__(self, ui: UI) -> None:
        self.ui = ui

    def run(self) -> None:
        self.ui.rule("Engine Maintenance")
        table = Table(box=box.ROUNDED, show_header=False)
        table.add_row("1", "Update yt-dlp library")
        table.add_row("2", "Clear yt-dlp Cache")
        table.add_row("3", "Back")
        self.ui.console.print(table)

        choice = Prompt.ask("Select action", choices=["1", "2", "3"], default="1")
        if choice == "1":
            with self.ui.console.status("[bold cyan]Updating yt-dlp..."):
                try:
                    res = subprocess.run([sys.executable, "-m", "pip", "install", "-U", "yt-dlp"], capture_output=True, text=True)
                    if res.returncode == 0:
                        self.ui.success("yt-dlp updated successfully!")
                    else:
                        self.ui.error(f"Update failed: {res.stderr}")
                except Exception as exc:
                    self.ui.error(f"Error during update: {exc}")
        elif choice == "2":
            try:
                with yt_dlp.YoutubeDL({}) as ydl:
                    ydl.cache.remove()
                self.ui.success("Cache cleared successfully.")
            except Exception as exc:
                self.ui.error(f"Failed to clear cache: {exc}")


# =====================================================================
# MENU & APP CONTROLLER
# =====================================================================

class Menu:
    def __init__(self, ui: UI, settings: Settings, history: History) -> None:
        self.ui = ui
        self.settings = settings
        self.history = history

    def show_history(self) -> None:
        self.ui.rule("Download History")
        if not self.history.entries:
            self.ui.info("No download history yet.")
            return

        table = Table(box=box.ROUNDED, border_style=self.ui.theme.style("primary"))
        table.add_column("#", style="bold")
        table.add_column("Date")
        table.add_column("Title")
        table.add_column("Resolution/Bitrate")
        for idx, entry in enumerate(self.history.entries, start=1):
            table.add_row(str(idx), entry.date, entry.title, entry.resolution)
        self.ui.console.print(table)

        if Confirm.ask("Clear history?", default=False):
            self.history.clear()
            self.ui.success("History cleared.")

    def show_settings(self) -> None:
        self.ui.rule("Settings")
        table = Table(box=box.ROUNDED, show_header=False)
        table.add_row("1. Download Folder", self.settings.data.download_folder)
        table.add_row("2. Theme", self.settings.data.theme)
        table.add_row("3. Overwrite Files", str(self.settings.data.overwrite_existing))
        table.add_row("4. Back", "")
        self.ui.console.print(table)

        choice = Prompt.ask("Setting choice", choices=["1", "2", "3", "4"], default="4")
        if choice == "1":
            folder = Prompt.ask("New folder path", default=self.settings.data.download_folder)
            self.settings.data.download_folder = str(Path(folder).expanduser())
            self.settings.save()
            self.ui.success("Folder updated.")
        elif choice == "2":
            t = Prompt.ask("Theme", choices=list(Theme.THEMES.keys()), default="default")
            self.settings.data.theme = t
            self.ui.theme = Theme(t)
            self.settings.save()
            self.ui.success("Theme updated.")
        elif choice == "3":
            self.settings.data.overwrite_existing = Confirm.ask("Overwrite existing files?", default=False)
            self.settings.save()

    def show_help(self) -> None:
        self.ui.rule("Help & Info")
        self.ui.panel(
            "• Video Download: Provides real-time dynamic quality options extracted from the video link.\n"
            "• Playlist Download: Supports downloading full playlists as Video OR Audio (MP3/FLAC/M4A).\n"
            "• YouTube Search: Search keywords directly without opening a browser.\n"
            "• Engine Maintenance: Keep yt-dlp updated to prevent extraction failures.",
            title="💡 Hints & Features",
        )

    def show_about(self) -> None:
        self.ui.rule("About")
        self.ui.panel(
            f"GVA Downloader v{APP_VERSION}\nAuthor: {APP_AUTHOR}\nPlatform: {APP_PLATFORM}\nEngine: {APP_ENGINE}",
            title="📖 About App",
        )


class Application:
    def __init__(self) -> None:
        self.settings = Settings()
        self.history = History()
        self.theme = Theme(self.settings.data.theme)
        self.ui = UI(self.theme)
        self.menu = Menu(self.ui, self.settings, self.history)
        self.running = True

    def main_loop(self) -> None:
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
                elif choice == "7":
                    self.menu.show_history()
                elif choice == "8":
                    self.menu.show_settings()
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
        Utilities.ensure_dir(CONFIG_DIR)
        Utilities.ensure_dir(self.settings.get_download_folder())
        self.main_loop()


def main() -> None:
    try:
        app = Application()
        app.run()
    except KeyboardInterrupt:
        console.print("\n[bold yellow]⚠️ Exiting. Goodbye![/]")
        sys.exit(0)


if __name__ == "__main__":
    main()