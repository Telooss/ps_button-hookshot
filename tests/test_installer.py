from ps_buttons.__main__ import KNOWN_BUILD_ID, conflicting_mods, game_version_ok
from ps_buttons.build import BNTX, MOD_NAME


def nso(path, build_id: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"NSO0" + bytes(0x3C) + build_id + bytes(16))


def test_game_version_ok(tmp_path):
    nso(tmp_path / ".hookshot_exefs" / "main", bytes.fromhex(KNOWN_BUILD_ID))
    assert game_version_ok(tmp_path)
    nso(tmp_path / ".hookshot_exefs" / "main", bytes(20))
    assert not game_version_ok(tmp_path)
    assert not game_version_ok(tmp_path / "missing")


def test_console_never_crashes_on_symbols(monkeypatch):
    import io
    import sys
    from ps_buttons.__main__ import safe_console
    raw = io.BytesIO()
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(raw, encoding="cp1252"))
    safe_console()
    print("Controls → Layout preset, ✕ valide")
    sys.stdout.flush()
    assert b"Controls" in raw.getvalue()


def test_conflicting_mods(tmp_path):
    mods = tmp_path / "mods"
    for name in (MOD_NAME, "ps_button-hookshot-main", "_disabled_copy", "OtherMod"):
        (mods / name / "romfs").mkdir(parents=True)
    for name in (MOD_NAME, "ps_button-hookshot-main", "_disabled_copy"):
        f = mods / name / "romfs" / (BNTX + ".zs")
        f.parent.mkdir(parents=True)
        f.write_bytes(b"x")
    assert conflicting_mods(mods) == ["ps_button-hookshot-main"]
    assert conflicting_mods(tmp_path / "nothing") == []
