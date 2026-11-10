import json

from ps_buttons.locate import find_game_dir, is_game_dir


def make_game(root):
    (root / "romfs").mkdir(parents=True)
    (root / ".hookshot_exefs").mkdir()
    return root


def builder_settings(appdata, out):
    d = appdata / "HookshotBuilder"
    d.mkdir(parents=True)
    (d / "builder-settings.json").write_text(json.dumps({"Out": str(out), "Nup": "x.nup", "Romfs": None}), "utf-8")


def test_is_game_dir(tmp_path):
    assert not is_game_dir(tmp_path)
    assert is_game_dir(make_game(tmp_path / "Hookshot"))


def test_explicit_folder_wins(tmp_path):
    game = make_game(tmp_path / "Mine")
    builder_settings(tmp_path / "appdata", make_game(tmp_path / "Other"))
    assert find_game_dir(game, tmp_path / "Downloads", tmp_path / "appdata") == game


def test_found_from_hookshot_builder_settings(tmp_path):
    game = make_game(tmp_path / "Games" / "Hookshot")
    builder_settings(tmp_path / "appdata", game)
    assert find_game_dir(None, tmp_path / "Downloads", tmp_path / "appdata") == game


def test_found_next_to_the_exe(tmp_path):
    game = make_game(tmp_path / "Hookshot")
    (game / "mods").mkdir()
    assert find_game_dir(None, game, tmp_path / "appdata") == game
    assert find_game_dir(None, game / "mods", tmp_path / "appdata") == game


def test_builder_folder_that_no_longer_exists_is_ignored(tmp_path):
    builder_settings(tmp_path / "appdata", tmp_path / "deleted")
    assert find_game_dir(None, tmp_path / "Downloads", tmp_path / "appdata") is None


def test_broken_builder_settings_are_ignored(tmp_path):
    d = tmp_path / "appdata" / "HookshotBuilder"
    d.mkdir(parents=True)
    (d / "builder-settings.json").write_text("{not json", "utf-8")
    assert find_game_dir(None, tmp_path / "Downloads", tmp_path / "appdata") is None
