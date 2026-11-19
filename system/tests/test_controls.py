import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from setting import control_settings as settings, hand_controls
from system.controls import GameControls, is_fist
from system.game import Game, GOAL


def hand(side="Left", closed=False, x=0.7, y=0.5):
    points = [SimpleNamespace(x=x, y=y, z=0.0) for _ in range(21)]
    points[0].y = y + 0.3
    for joint, tip in ((6, 8), (10, 12), (14, 16), (18, 20)):
        points[joint].y = y
        points[tip].y = y + 0.15 if closed else y - 0.2
    return {"side": side, "landmarks": points, "confidence": 0.99}


class ControlTests(unittest.TestCase):
    def test_two_gloves_mirror_and_move_independently_in_both_modes(self):
        for preset in (True, False):
            with self.subTest(preset=preset), patch.object(settings, "USE_PRESET", preset), patch.object(settings, "MOVEMENT_GAIN", 1.0), patch.object(settings, "SMOOTHING_SECONDS", 0):
                control = GameControls()
                command = control.update([hand("Left", x=0.8, y=0.2), hand("Right", x=0.2, y=0.7)], [], 0.1)
                self.assertAlmostEqual(command["gloves"]["Left"][0], 0.2)
                self.assertAlmostEqual(command["gloves"]["Right"][0], 0.8)
                self.assertEqual(command["gloves"]["Left"][1], 0.2)
                command = control.update([hand("Right", x=0.3)], [], 0.1)
                self.assertNotIn("Left", command["gloves"])
                self.assertAlmostEqual(command["gloves"]["Right"][0], 0.7)

    def test_fist_dwell_release_loss_and_replay(self):
        for preset in (True, False):
            with self.subTest(preset=preset), patch.object(settings, "USE_PRESET", preset):
                control = GameControls()
                self.assertFalse(control.update([hand(closed=True)], [], 1)["skill"])
                control.update([hand()], [], 0.1)
                first = control.update([hand(closed=True)], [], 0.1)
                self.assertEqual(first["skill"], not preset)
                second = control.update([hand(closed=True)], [], 0.16)
                self.assertEqual(second["skill"], preset)
                self.assertFalse(control.update([hand(closed=True)], [], 10)["skill"])
                control.update([], [], 1)
                self.assertFalse(control.update([hand(closed=True)], [], 1)["skill"])
                control.update([hand()], [], 0.1)
                fired = control.update([hand(closed=True)], [], 0)
                fired_after_hold = control.update([hand(closed=True)], [], 0.2)
                self.assertTrue(fired["skill"] or fired_after_hold["skill"])
                control.reset()
                self.assertEqual(control.filtered, {})
                self.assertFalse(control.update([hand(closed=True)], [], 1)["skill"])

    def test_each_skill_gesture(self):
        cases = [
            ("กำมือซ้าย", [hand("Left", True)], True),
            ("กำมือซ้าย", [hand("Right", True)], False),
            ("กำมือขวา", [hand("Right", True)], True),
            ("กำมือขวา", [hand("Left", True)], False),
            ("กำมือสองข้าง", [hand("Left", True)], False),
            ("กำมือสองข้าง", [hand("Left", True), hand("Right", True)], True),
            ("กำมือข้างใดก็ได้", [hand("Left", True), hand("Right", True)], True),
        ]
        for action, hands, expected in cases:
            with self.subTest(action=action, expected=expected), patch.multiple(settings, USE_PRESET=True, SKILL_ACTION=action, HOLD_SECONDS=0):
                control = GameControls()
                control.update([hand("Left"), hand("Right")], [], 0)
                self.assertEqual(control.update(hands, [], 0)["skill"], expected)

    def test_custom_ignores_every_preset_value(self):
        invalid = {name: None for name in vars(settings) if name.isupper() and name != "USE_PRESET"}
        with patch.multiple(settings, USE_PRESET=False, **invalid), patch.object(hand_controls, "get_goalkeeper_command", return_value={"gloves": {"Left": (0.2, 0.3)}, "skill": False}) as custom:
            control = GameControls()
            self.assertEqual(control.update([], [], 0)["gloves"], {"Left": (0.2, 0.3)})
            custom.assert_called_once_with([], [])

    def test_preset_never_calls_custom_rules(self):
        with patch.object(settings, "USE_PRESET", True), patch.object(hand_controls, "get_goalkeeper_command", side_effect=AssertionError):
            self.assertTrue(GameControls().update([hand()], [], 0)["gloves"])

    def test_settings_validation(self):
        for values in ({"USE_PRESET": "True"}, {"SKILL_ACTION": "unknown"}, {"SENSITIVITY": 0}, {"MIN_TRACKING_CONFIDENCE": 2}):
            with self.subTest(values=values), patch.multiple(settings, **values), self.assertRaises(ValueError):
                GameControls()

    def test_zero_length_fingers_and_low_confidence_do_not_trigger(self):
        points = [SimpleNamespace(x=0.5, y=0.5) for _ in range(21)]
        self.assertFalse(is_fist(points, 1))
        low = hand()
        low["confidence"] = 0.1
        self.assertEqual(GameControls().update([low], [], 1)["gloves"], {})

    def test_smoothing_uses_elapsed_time(self):
        with patch.multiple(settings, USE_PRESET=True, MOVEMENT_GAIN=1, SMOOTHING_SECONDS=0.1):
            positions = []
            for fps in (20, 60):
                control = GameControls()
                control.update([hand(x=0.8)], [], 0)
                for _ in range(fps):
                    command = control.update([hand(x=0.2)], [], 1 / fps)
                positions.append(command["gloves"]["Left"][0])
            self.assertAlmostEqual(*positions)

    def test_both_modes_feed_real_game_and_score(self):
        for preset in (True, False):
            for side in ("Left", "Right"):
                with self.subTest(preset=preset, side=side), patch.multiple(settings, USE_PRESET=preset, MOVEMENT_GAIN=1.0):
                    game = Game()
                    game.reset()
                    control = GameControls()
                    command = control.update([hand(side, x=0.7, y=0.4)], [], 0.1)
                    game.balls = [{"x": GOAL.left + 0.3 * (GOAL.width - 1), "y": GOAL.top + 0.4 * (GOAL.height - 1), "progress": 0.999}]
                    game.update(0.02, command)
                    self.assertEqual(game.saves, 1)
