"""Finding the player's Hookshot folder (the one holding romfs/ and .hookshot_exefs/)."""
from __future__ import annotations

import json
from pathlib import Path


def is_game_dir(p: Path | None) -> bool:
    return bool(p) and (Path(p) / "romfs").is_dir() and (Path(p) / ".hookshot_exefs").is_dir()


def _from_builder(appdata: Path) -> Path | None:
    """The Hookshot builder records where it built the game in builder-settings.json ("Out")."""
    try:
        out = json.loads((appdata / "HookshotBuilder" / "builder-settings.json").read_text("utf-8")).get("Out")
    except (OSError, ValueError, AttributeError):
        return None
    return Path(out) if out and is_game_dir(Path(out)) else None


def find_game_dir(explicit: Path | None, exe_dir: Path, appdata: Path) -> Path | None:
    """Explicit folder, else the builder's output folder, else a folder around the exe."""
    if explicit:
        return Path(explicit) if is_game_dir(explicit) else None
    found = _from_builder(Path(appdata))
    if found:
        return found
    for d in [Path(exe_dir), *Path(exe_dir).parents]:
        if is_game_dir(d):
            return d
    return None


def ask_game_dir() -> Path | None:
    """Folder picker, for when nothing was found automatically."""
    try:
        import tkinter
        from tkinter import filedialog
        root = tkinter.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        chosen = filedialog.askdirectory(title="Choisis ton dossier Hookshot (celui qui contient romfs et hookshot.exe)")
        root.destroy()
    except Exception:
        return None
    return Path(chosen) if chosen and is_game_dir(Path(chosen)) else None
