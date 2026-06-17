"""
TRINKER - Application Configuration
Centralizes all paths, constants, and user settings.
Uses platformdirs for cross-platform data directory resolution.
"""

import json
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name, "")
    if not raw:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


# Runtime env (Arbitragem parity) — not persisted in settings.json
RESOURCE_RAM_FRACTION = _env_float("RESOURCE_RAM_FRACTION", 0.8)
RESOURCE_GPU_FRACTION = _env_float("RESOURCE_GPU_FRACTION", 0.4)
RAM_BUDGET_MB = _env_int("RAM_BUDGET_MB", 1200)
LOW_RAM_MODE = _env_bool("LOW_RAM_MODE", False)
TRINKER_BG_TESTS = _env_bool("TRINKER_BG_TESTS", True)
OLLAMA_ENABLED = _env_bool("OLLAMA_ENABLED", True)
OLLAMA_TIMEOUT_SECONDS = _env_int("OLLAMA_TIMEOUT_SECONDS", 120)
OLLAMA_PROBE_TIMEOUT_SECONDS = _env_float("OLLAMA_PROBE_TIMEOUT_SECONDS", 1.5)

# ---------------------------------------------------------------------------
# Sandbox mode — isolated data dir for agent/dev (set TRINKER_SANDBOX=1)
# ---------------------------------------------------------------------------


def is_sandbox_mode() -> bool:
    return os.environ.get("TRINKER_SANDBOX", "").strip().lower() in ("1", "true", "yes", "on")


APP_NAME = "TRINKER_SANDBOX" if is_sandbox_mode() else "TRINKER"

# ---------------------------------------------------------------------------
# Platform-aware application directories
# ---------------------------------------------------------------------------


class _AppDirs:
    """Fallback directory resolver when platformdirs is unavailable."""

    def __init__(self, app_name: str):
        self.app_name = app_name

    @property
    def user_data_dir(self) -> str:
        if sys.platform == "win32":
            base = Path.home() / "AppData" / "Local"
        elif sys.platform == "darwin":
            base = Path.home() / "Library" / "Application Support"
        else:
            base = Path.home() / ".local" / "share"
        return str(base / self.app_name)

    @property
    def user_log_dir(self) -> str:
        return str(Path(self.user_data_dir) / "logs")

    @property
    def user_cache_dir(self) -> str:
        return str(Path(self.user_data_dir) / "cache")


def _resolve_app_dirs(app_name: str = "TRINKER") -> _AppDirs:
    """Prefer platformdirs (XDG on Linux, standard paths on macOS/Windows)."""
    try:
        from platformdirs import user_cache_dir, user_data_dir, user_log_dir

        class _PlatformDirs:
            @property
            def user_data_dir(self) -> str:
                return user_data_dir(app_name, appauthor=False)

            @property
            def user_log_dir(self) -> str:
                return user_log_dir(app_name, appauthor=False)

            @property
            def user_cache_dir(self) -> str:
                return user_cache_dir(app_name, appauthor=False)

        return _PlatformDirs()  # type: ignore[return-value]
    except ImportError:
        return _AppDirs(app_name)


APP_DIRS = _resolve_app_dirs(APP_NAME)

# ---------------------------------------------------------------------------
# Key file paths
# ---------------------------------------------------------------------------

DATA_DIR = Path(APP_DIRS.user_data_dir)
LOG_DIR = Path(APP_DIRS.user_log_dir)
CACHE_DIR = Path(APP_DIRS.user_cache_dir)
DB_PATH = DATA_DIR / "trinker.db"
BO_DIR = DATA_DIR / "build_orders"  # local build order JSON cache
EXPORT_DIR = DATA_DIR / "exports"

# Create directories on import so downstream code never has to worry about it
CORPUS_INBOX = DATA_DIR / "corpus_inbox"  # drop .aoe2record here for TRINKER dev/testing
for _d in (DATA_DIR, LOG_DIR, CACHE_DIR, BO_DIR, EXPORT_DIR, CORPUS_INBOX):
    _d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# AoE2 replay default locations (Windows-first, checked in order)
# ---------------------------------------------------------------------------

AO2_REPLAY_DIRS: list[Path] = []
if sys.platform == "win32":
    AO2_REPLAY_DIRS = [
        Path.home() / "Documents" / "My Games" / "Age of Empires 2 DE",
        Path.home() / "Games" / "Age of Empires 2 DE",
    ]
elif sys.platform == "darwin":
    AO2_REPLAY_DIRS = [
        Path.home()
        / "Library"
        / "Application Support"
        / "Steam"
        / "steamapps"
        / "common"
        / "AoE2DE"
        / "savegame",
        Path.home() / "Documents" / "My Games" / "Age of Empires 2 DE",
    ]
else:
    # Linux — Steam Proton / native paths vary; users often set replay_dirs in Settings
    AO2_REPLAY_DIRS = [
        Path.home() / ".steam" / "steam" / "steamapps" / "compatdata" / "813780" / "pfx",
        Path.home() / "Games" / "aoe2de",
    ]

# ---------------------------------------------------------------------------
# External data sources
# ---------------------------------------------------------------------------

BUILDORDERGUIDE_BASE = "https://www.buildorderguide.com"
AOE2GG_BASE = "https://aoe2.gg"
AOE2NET_BASE = "https://aoe2.net/api"

REQUEST_TIMEOUT = 15  # seconds
REQUEST_HEADERS = {
    "User-Agent": (
        "TRINKER/1.0 AoE2TrainingCompanion (https://github.com/user/trinker; contact@example.com)"
    )
}

# ---------------------------------------------------------------------------
# Application settings (persisted as JSON)
# ---------------------------------------------------------------------------

SETTINGS_FILE = DATA_DIR / "settings.json"
VERSION_FILE = Path(__file__).resolve().parent.parent.parent / "VERSION"
GITHUB_REPO = "zakksu/Trinker"


def get_app_version() -> str:
    """Read the app version from the VERSION file at project root."""
    try:
        if VERSION_FILE.exists():
            return VERSION_FILE.read_text(encoding="utf-8").strip()
    except Exception:
        pass
    return "1.0.0"


@dataclass
class AppSettings:
    """
    All user-configurable preferences.
    Saved to / loaded from SETTINGS_FILE as JSON.
    """

    theme: str = "dark"  # "dark" | "light"
    ui_style: str = "medieval"  # "medieval" | "classic"
    civ_skin: str = "default"  # default | britons | franks | chinese | byzantines | mayans
    accent_color: str = "#3498db"  # primary accent (classic dark theme)
    overlay_opacity: float = 0.88  # 0.0 – 1.0
    overlay_position: list[int] = field(default_factory=lambda: [100, 100])
    overlay_size: list[int] = field(default_factory=lambda: [300, 340])
    hotkey_next_step: str = "Ctrl+Right"
    hotkey_prev_step: str = "Ctrl+Left"
    hotkey_toggle_overlay: str = "Ctrl+Shift+O"
    hotkey_start_session: str = "Ctrl+Shift+S"
    font_size: int = 11
    auto_advance: bool = False  # auto-step on replay timer
    show_timings: bool = True
    ai_coach_enabled: bool = True
    ollama_url: str = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = os.environ.get("OLLAMA_MODEL", "llama3")
    recommended_ollama_model: str = "llama3.2"
    rag_enabled: bool = True
    global_hotkeys_enabled: bool = True
    active_drill_id: str = ""
    telemetry_opt_in: bool = False
    auto_prompt_new_replay: bool = True  # ask to import after a new game
    last_seen_replay_mtime: float = 0.0  # tracks newest replay we've seen
    last_seen_replay_path: str = ""  # path of last acknowledged replay
    auto_postgame_coach: bool = True  # run AI coach after new replay import
    overlay_coach_alert: str = ""  # pinned reminder for next overlay session
    overlay_coach_alert_bo_id: Optional[int] = None
    dashboard_kpis: list[str] = field(
        default_factory=lambda: [
            "sessions",
            "feudal",
            "quality",
            "winrate",
            "streak",
            "accuracy",
        ]
    )
    dashboard_show_charts: bool = True
    dashboard_show_patterns: bool = True
    ollama_setup_dismissed: bool = False
    pro_coach_player: str = "Hera"
    pro_coach_model: str = "trinker-hera"
    pro_corpus_built_at: str = ""
    pro_corpus_game_count: int = 0
    overlay_profile_enabled: bool = False  # log slow overlay ticks (dev)
    ocr_capture_enabled: bool = False  # live resource OCR on overlay
    ocr_resource_region: dict = field(
        default_factory=lambda: {"left": 0, "top": 0, "width": 220, "height": 48}
    )
    simple_mode: bool = True  # hide advanced Practice panels
    last_practice_bo_id: Optional[int] = None
    auto_detect_sessions: bool = True  # auto-import replays in background
    overlay_sync_game_pause: bool = True  # pause overlay timer when game is paused
    onboarding_complete: bool = True  # first-run wizard (False for brand-new installs)
    steam_id: str = ""
    replay_dirs: list[str] = field(default_factory=list)  # custom AoE2 replay roots

    def save(self) -> None:
        """Persist settings to disk."""
        SETTINGS_FILE.write_text(json.dumps(asdict(self), indent=2))

    @classmethod
    def load(cls) -> "AppSettings":
        """Load settings from disk, falling back to defaults on any error."""
        try:
            if SETTINGS_FILE.exists():
                data = json.loads(SETTINGS_FILE.read_text())
                return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        except Exception:
            pass
        inst = cls(onboarding_complete=False)
        inst.save()
        return inst


def get_replay_search_dirs() -> list[Path]:
    """Replay folders to scan — custom paths first, then defaults, then discovered."""
    dirs: list[Path] = []
    seen: set[str] = set()

    def add(p: Path) -> None:
        if not p.exists():
            return
        try:
            key = str(p.resolve())
        except OSError:
            key = str(p)
        if key not in seen:
            seen.add(key)
            dirs.append(p)

    for raw in settings.replay_dirs:
        add(Path(raw))
    for p in AO2_REPLAY_DIRS:
        add(p)
    try:
        from .replay_paths import discover_replay_roots

        for p in discover_replay_roots():
            add(p)
    except Exception:
        pass
    return dirs


# Module-level singleton
settings = AppSettings.load()
