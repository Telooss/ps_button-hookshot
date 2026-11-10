"""PS Buttons installer: finds the Hookshot folder, builds the mod from the player's own game files,
and installs it in Hookshot\\mods\\PS_Buttons.   python -m ps_buttons [--game-dir PATH] [--xbox]"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .build import BNTX, MOD_NAME, build_mod
from .locate import ask_game_dir, find_game_dir

KNOWN_BUILD_ID = "e0f3ccfaf50065ae4ea01eb5aeb13b1a45da3348"  # Ocarina of Time (Switch 2), update 2.0.0


def game_version_ok(game: Path) -> bool:
    try:
        with open(Path(game) / ".hookshot_exefs" / "main", "rb") as f:
            head = f.read(0x54)
    except OSError:
        return False
    return head[:4] == b"NSO0" and head[0x40:0x54].hex() == KNOWN_BUILD_ID


def conflicting_mods(mods: Path) -> list[str]:
    """Other enabled mods replacing the same texture file (e.g. an older copy of this mod)."""
    if not Path(mods).is_dir():
        return []
    return sorted(d.name for d in Path(mods).iterdir()
                  if d.is_dir() and d.name != MOD_NAME and not d.name.startswith(("_", "-"))
                  and (d / "romfs" / (BNTX + ".zs")).is_file())


def safe_console() -> None:
    """A redirected or legacy console may not know symbols like → or ✕: print a placeholder instead of crashing."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass


def _here() -> Path:
    return Path(sys.executable).parent if getattr(sys, "frozen", False) else Path.cwd()


def _pause() -> None:
    if getattr(sys, "frozen", False):
        input("\nAppuie sur Entrée pour fermer…")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="ps-buttons-installer")
    ap.add_argument("--game-dir", type=Path)
    ap.add_argument("--xbox", action="store_true", help='disposition "Xbox / PC" ou "Swap Face" (✕ valide)')
    safe_console()
    args = ap.parse_args(argv)
    print("PS Buttons pour Hookshot — installation\n")

    appdata = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    game = find_game_dir(args.game_dir, _here(), appdata)
    if game is None:
        print("Dossier Hookshot introuvable : choisis-le dans la fenêtre qui s'ouvre")
        print("(le dossier qui contient romfs et hookshot.exe).")
        game = ask_game_dir()
    if game is None:
        print("Aucun dossier Hookshot choisi : rien n'a été installé.")
        _pause()
        return 1
    print("Jeu trouvé :", game)
    if not game_version_ok(game):
        print("\nVersion du jeu non reconnue : ce mod est fait pour la mise à jour 2.0.0 d'Ocarina of Time.")
        print("Rien n'a été installé.")
        _pause()
        return 1

    xbox = args.xbox
    if not xbox and getattr(sys, "frozen", False):
        print("\nDans le menu Hookshot (Insert ou F1), Controls → Layout preset :")
        print("  - « Nintendo » (réglage par défaut) : appuie simplement sur Entrée")
        print("  - « Xbox / PC » ou « Swap Face »   : tape X puis Entrée")
        xbox = input("> ").strip().lower() == "x"

    mods = game / "mods"
    print(f"\nFabrication du mod à partir de ta copie du jeu (disposition {'Xbox / PC' if xbox else 'Nintendo'})…")
    try:
        out = build_mod(game, mods, xbox=xbox, log=lambda msg: print("  " + msg))
    except Exception as e:
        print("\nÉchec, rien n'a été modifié :", e)
        _pause()
        return 1
    print("\nInstallé dans :", out)
    others = conflicting_mods(mods)
    if others:
        print("\nAttention : ces mods remplacent les mêmes fichiers et peuvent masquer celui-ci :")
        for name in others:
            print("  -", mods / name)
        print("Supprime-les, ou renomme-les en ajoutant _ au début de leur nom pour les désactiver.")
    print("\nC'est prêt : lance le jeu. Pour désinstaller, supprime le dossier", out)
    _pause()
    return 0


if __name__ == "__main__":
    sys.exit(main())
