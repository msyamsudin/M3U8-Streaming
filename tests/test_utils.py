"""Unit tests untuk util & logika inti.

Jalankan dari root proyek:
    python -m unittest discover tests
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import src.utils as utils  # noqa: E402
from src.config import USER_AGENTS  # noqa: E402
from src.app.main_window import UA_ALIASES, KNOWN_UA_VALUES  # noqa: E402


class TestFormatting(unittest.TestCase):
    def test_format_time(self):
        self.assertEqual(utils.format_time(None), "00:00:00")
        self.assertEqual(utils.format_time(0), "00:00:00")
        self.assertEqual(utils.format_time(3661), "01:01:01")

    def test_format_clock(self):
        self.assertEqual(utils.format_clock(None), "00:00")
        self.assertEqual(utils.format_clock(-5), "00:00")
        self.assertEqual(utils.format_clock(59.7), "00:59")
        self.assertEqual(utils.format_clock(3600), "01:00:00")


class TestUAAliases(unittest.TestCase):
    def test_alias_maps_to_full_ua(self):
        for token in ("chrome", "firefox", "safari", "edge"):
            self.assertNotEqual(UA_ALIASES[token], token, "alias tidak berubah")
            self.assertIn(UA_ALIASES[token], KNOWN_UA_VALUES)
            self.assertEqual(UA_ALIASES[token], USER_AGENTS[token.capitalize()])

    def test_unknown_ua_passthrough(self):
        self.assertEqual(UA_ALIASES.get("random-string", "random-string"), "random-string")


class TestHistoryFile(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._old_cwd = os.getcwd()
        os.chdir(self._tmp.name)

    def tearDown(self):
        os.chdir(self._old_cwd)
        self._tmp.cleanup()

    def test_save_load_roundtrip_with_meta(self):
        utils.save_history(
            "http://x/1",
            name="one",
            meta={
                "referer": "http://r",
                "user_agent": USER_AGENTS["Chrome"],
                "headers": {"Referer": "http://r"},
            },
        )
        data = utils.load_history()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["referer"], "http://r")
        self.assertEqual(data[0]["user_agent"], USER_AGENTS["Chrome"])
        self.assertEqual(data[0]["headers"], {"Referer": "http://r"})

    def test_no_meta_no_extra_keys(self):
        utils.save_history("http://x/2")
        data = utils.load_history()
        self.assertNotIn("referer", data[0])

    def test_dedup_and_limit_50(self):
        for i in range(60):
            utils.save_history(f"http://x/{i}")
        data = utils.load_history()
        self.assertEqual(len(data), 50)
        self.assertEqual(data[0]["url"], "http://x/59")

    def test_atomic_write_no_tmp_leftover(self):
        utils.write_history([{"url": "a"}])
        self.assertTrue(os.path.exists(utils.HISTORY_FILE))
        self.assertFalse(os.path.exists(utils.HISTORY_FILE + ".tmp"))
        with open(utils.HISTORY_FILE, encoding="utf-8") as f:
            self.assertEqual(json.load(f)[0]["url"], "a")

    def test_corrupt_file_backed_up(self):
        with open(utils.HISTORY_FILE, "w", encoding="utf-8") as f:
            f.write("{{{ not json")
        self.assertEqual(utils.load_history(), [])
        backups = [x for x in os.listdir(".") if x.startswith("history.json.bak-")]
        self.assertTrue(backups, "backup tidak dibuat untuk file korup")


class TestPlayerStateMachine(unittest.TestCase):
    """State machine: core-idle (True saat pause manual) tidak boleh
    mengubah state PAUSED menjadi LOADING (indikator buffering palsu)."""

    def test_core_idle_ignored_while_paused(self):
        from src.app.controllers.player_controller import PlayerController, PlayerState
        pc = PlayerController(None)
        pc._set_state(PlayerState.PAUSED)
        pc._on_property_core_idle(None, True)
        self.assertEqual(pc.state, PlayerState.PAUSED)

    def test_core_idle_sets_loading_when_not_paused(self):
        from src.app.controllers.player_controller import PlayerController, PlayerState
        pc = PlayerController(None)
        pc._set_state(PlayerState.IDLE)
        pc._on_property_core_idle(None, True)
        self.assertEqual(pc.state, PlayerState.LOADING)


if __name__ == "__main__":
    unittest.main()
