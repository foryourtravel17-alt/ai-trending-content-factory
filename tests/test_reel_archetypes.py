import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import src.reel_generator as reel


class ReelArchetypeTests(unittest.TestCase):
    def test_hash_selection_is_deterministic(self):
        self.assertEqual(reel.choose_archetype("content_abc"), reel.choose_archetype("content_abc"))

    def test_repeat_guard_changes_same_pick(self):
        first = reel.choose_archetype("content_abc")
        second = reel.choose_archetype("content_abc", previous=first)
        self.assertNotEqual(first, second)

    def test_rotation_has_no_adjacent_repeats(self):
        data = json.loads(Path("config/rotation.json").read_text(encoding="utf-8"))
        order = data["archetype_order"]
        self.assertEqual(len(order), 30)
        self.assertTrue(all(a != b for a, b in zip(order, order[1:])))

    def test_rotation_mix_targets_sum_to_100(self):
        data = json.loads(Path("config/rotation.json").read_text(encoding="utf-8"))
        mix = data["target_mix"]
        self.assertEqual(sum(mix.values()), 100)
        self.assertEqual(mix, {"education": 70, "authority": 20, "conversion": 10})
        archetypes = json.loads(Path("config/card_archetypes.json").read_text(encoding="utf-8"))["archetypes"]
        actual = {"education": 0, "authority": 0, "conversion": 0}
        for name in data["archetype_order"]:
            actual[archetypes[name]["role"]] += 1
        self.assertEqual(actual, {"education": 21, "authority": 6, "conversion": 3})

    def test_all_eight_archetypes_have_required_fields(self):
        data = json.loads(Path("config/card_archetypes.json").read_text(encoding="utf-8"))
        self.assertEqual(set(data["archetypes"]), {"hook", "chartproof", "wrongright", "list", "myth", "rule", "term", "cta"})
        for item in data["archetypes"].values():
            self.assertIn("zones", item)
            self.assertIn("font_sizes", item)
            self.assertIn("accent", item)
            self.assertIn("chart_style", item)
            self.assertIn("text_max", item)

    def test_hook_frame_renders_from_body(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "hook.png"
            with patch("src.reel_generator.centered") as centered_mock:
                reel.make_frame(path, "Structure", "education", "THE HOOK",
                                "REAL HOOK TEXT", 0, "", archetype="hook")
                self.assertTrue(any(call.args[1] == "REAL HOOK TEXT" for call in centered_mock.call_args_list))
            self.assertTrue(path.exists())
            self.assertGreater(path.stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main()
