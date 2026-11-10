import hashlib
import os
from pathlib import Path

import pytest

from ps_buttons.build import MOD_NAME, build_mod

# Files of the released mod known to work in game (Hookshot v2.0.10, game update 2.0.0).
REFERENCE = {
    "romfs/Font2/Scalable/External.Nin_Ounce_NVN2.bfotf.zs": "7e007cda00dd5a19",
    "romfs/System/Resource/ResourceSizeTable.Product.111.Nin_Ounce_NVN2.rsizetable.zs": "cd48248a346d72a8",
    "romfs/UI/Layout2Archive/Common.Product.100.Nin_Ounce_NVN2.bntx.zs": "cb2cbf190fc23b83",
}


def test_failed_build_leaves_existing_mod_untouched(tmp_path):
    game = tmp_path / "Hookshot"
    (game / "romfs").mkdir(parents=True)  # no game files inside
    mods = game / "mods"
    old = mods / MOD_NAME / "romfs" / "keep.txt"
    old.parent.mkdir(parents=True)
    old.write_text("previous install", "utf-8")
    with pytest.raises(Exception):
        build_mod(game, mods, log=lambda *a: None)
    assert old.read_text("utf-8") == "previous install"
    assert sorted(p.name for p in mods.iterdir()) == [MOD_NAME]


FONT_REL = "romfs/Font2/Scalable/External.Nin_Ounce_NVN2.bfotf.zs"
needs_game = pytest.mark.skipif(not os.environ.get("HOOKSHOT_DIR"), reason="HOOKSHOT_DIR non défini")


@needs_game
def test_font_build_is_reproducible():
    import time
    from ps_buttons.build import FONT, _Romfs, build_font, symbols
    romfs = _Romfs(Path(os.environ["HOOKSHOT_DIR"]) / "romfs")
    first = build_font(romfs.read(FONT), symbols(False))
    time.sleep(1.1)  # fontTools would otherwise stamp a new modification time
    assert build_font(romfs.read(FONT), symbols(False)) == first


@needs_game
def test_generated_mod_matches_the_working_release(tmp_path):
    out = build_mod(Path(os.environ["HOOKSHOT_DIR"]), tmp_path / "mods", log=lambda *a: None)
    got = {p.relative_to(out).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()[:16]
           for p in out.rglob("*") if p.is_file()}
    assert got.keys() == REFERENCE.keys()
    # The released font carried the build time in its header (7 bytes); everything else must match exactly.
    assert {k: v for k, v in got.items() if k != FONT_REL} == {k: v for k, v in REFERENCE.items() if k != FONT_REL}
