import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import ast
import io
from pathlib import Path
import runpy
import tokenize
import unittest
from unittest.mock import Mock, patch

import numpy as np
import pygame

from setting import control_settings, game_settings as settings
from system import app
from system.camera import HandCamera, mirrored_point
from system.controls import GameControls
from system.game import Game, GOAL, SKILLS
from test_controls import hand


class GameTests(unittest.TestCase):
    def test_start_end_replay_and_skill_selection(self):
        game = Game()
        click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=app.BUTTON.center)
        app.handle_event(click, game, False)
        self.assertEqual(game.state, "MENU")
        skill_click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=app.SKILL_BUTTONS[2].center)
        app.handle_event(skill_click, game, True)
        self.assertEqual(game.selected_skill, "โล่ประตู")
        app.handle_event(click, game, True)
        game.activate_skill()
        game.update(4)
        game.misses = settings.MAX_MISSES - 1
        game.balls = [{"x": 50, "y": 150, "progress": 0.999}]
        game.update(0.1)
        self.assertEqual(game.state, "GAME_OVER")
        score = game.score
        game.update(20)
        self.assertEqual(game.score, score)
        app.handle_event(click, game, True)
        self.assertEqual((game.state, game.score, game.misses, game.elapsed), ("PLAYING", 0, 0, 0))
        self.assertEqual(game.balls, [])
        self.assertEqual(game.gloves, {})
        self.assertEqual(game.cooldown_remaining, 0)
        self.assertFalse(game.skill_active)
        self.assertEqual(game.selected_skill, "โล่ประตู")

    def test_timer_finishes_at_round_limit(self):
        with patch.object(settings, "MAX_MISSES", 999):
            game = Game()
            game.reset()
            game.update(settings.ROUND_SECONDS + 10)
            self.assertEqual(game.state, "GAME_OVER")
            self.assertEqual(game.elapsed, settings.ROUND_SECONDS)

    def test_ball_only_resolves_at_arrival(self):
        game = Game()
        game.reset()
        command = {"gloves": {"Left": (0.5, 0.5)}, "skill": False}
        game.balls = [{"x": GOAL.centerx, "y": GOAL.centery, "progress": 0.5}]
        game.update(0.01, command)
        self.assertEqual(game.saves, 0)
        game.balls[0]["progress"] = 0.999
        game.update(0.01, command)
        self.assertEqual(game.score, settings.POINTS_PER_SAVE)
        game.update(0.01, command)
        self.assertEqual(game.saves, 1)

    def test_missing_hands_cannot_keep_old_gloves(self):
        game = Game()
        game.reset()
        game.update(0, {"gloves": {"Left": (0.5, 0.5)}, "skill": False})
        game.balls = [{"x": GOAL.centerx, "y": GOAL.centery, "progress": 0.999}]
        game.update(0.01)
        self.assertEqual(game.misses, 1)

    def test_all_skills_have_effect_duration_and_cooldown(self):
        for skill in SKILLS:
            with self.subTest(skill=skill), patch.object(settings, "FIRST_BALL_DELAY", 999):
                game = Game()
                game.reset()
                game.selected_skill = skill
                self.assertTrue(game.activate_skill())
                self.assertFalse(game.activate_skill())
                if skill == "ถุงมือใหญ่":
                    self.assertEqual(game.glove_radius, settings.GLOVE_RADIUS * settings.BIG_GLOVE_MULTIPLIER)
                    game.gloves = {"Left": (100, 200)}
                    self.assertTrue(game.catches({"x": 175, "y": 200}))
                elif skill == "ชะลอบอล":
                    game.balls = [{"x": 100, "y": 200, "progress": 0}]
                    game.update(1)
                    self.assertAlmostEqual(game.balls[0]["progress"], settings.SLOW_BALL_MULTIPLIER / settings.BALL_FLIGHT_SECONDS)
                else:
                    game.balls = [{"x": 100, "y": 200, "progress": 0.999}]
                    game.update(0.01)
                    self.assertEqual(game.saves, 1)
                game.update(settings.SKILL_DURATION)
                self.assertFalse(game.skill_active)
                self.assertEqual(game.glove_radius, settings.GLOVE_RADIUS)
                self.assertFalse(game.activate_skill())
                game.update(settings.SKILL_COOLDOWN)
                self.assertTrue(game.activate_skill())

    def test_motion_and_cooldown_are_frame_rate_independent(self):
        results = []
        for fps in (20, 60):
            game = Game()
            game.reset()
            game.selected_skill = "ชะลอบอล"
            game.activate_skill()
            game.balls = [{"x": 100, "y": 200, "progress": 0}]
            for _ in range(fps):
                game.update(1 / fps)
            results.append((game.elapsed, game.balls[0]["progress"], game.cooldown_remaining))
        for left, right in zip(*results):
            self.assertAlmostEqual(left, right)

    def test_invalid_game_settings(self):
        for values in ({"BALL_INTERVAL": 0}, {"ROUND_SECONDS": -1}, {"MAX_MISSES": 0}, {"GLOVE_RADIUS": 500}, {"DEFAULT_SKILL": "bad"}):
            with self.subTest(values=values), patch.multiple(settings, **values), self.assertRaises(ValueError):
                Game()


class AppTests(unittest.TestCase):
    def test_launcher(self):
        launcher = Path(__file__).resolve().parents[2] / "main.py"
        with patch("system.app.main") as run, patch("sys.argv", [str(launcher), "--camera", "2"]):
            runpy.run_path(str(launcher), run_name="__main__")
        run.assert_called_once_with(2)

    def test_real_loop_start_finish_replay_both_modes(self):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=app.BUTTON.center)
        quit_event = pygame.event.Event(pygame.QUIT)
        for preset in (True, False):
            states = []
            camera = Mock(error="", pose_landmarks=[])
            camera.read.return_value = (frame, [hand("Left"), hand("Right")])
            def record(screen, game, *args):
                states.append((game.state, game.elapsed, game.score, len(game.gloves), game.cooldown_remaining))
            with self.subTest(preset=preset), patch.object(control_settings, "USE_PRESET", preset), patch.object(settings, "ROUND_SECONDS", 0.1), patch("system.app.HandCamera", return_value=camera), patch("system.app.time.perf_counter", side_effect=[0, 0.01, 0.21, 0.22, 0.23]), patch("system.app.pygame.event.get", side_effect=[[click], [], [click], [quit_event]]), patch("system.app.draw_screen", side_effect=record):
                app.main()
            self.assertEqual([state[0] for state in states], ["MENU", "PLAYING", "GAME_OVER", "PLAYING"])
            self.assertEqual(states[-1][1:], (0, 0, 0, 0))
            camera.close.assert_called_once()
            self.assertFalse(pygame.get_init())

    def test_exception_closes_camera_and_pygame(self):
        camera = Mock()
        camera.read.side_effect = RuntimeError("simulated read error")
        with patch("system.app.HandCamera", return_value=camera), self.assertRaises(RuntimeError):
            app.main()
        camera.close.assert_called_once()
        self.assertFalse(pygame.get_init())

    def test_escape_exits(self):
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
        self.assertFalse(app.handle_event(event, Game(), True))


class CameraTests(unittest.TestCase):
    def test_camera_open_failure_and_idempotent_cleanup(self):
        capture = Mock()
        capture.isOpened.return_value = False
        model = Mock()
        with patch("system.camera.vision.HandLandmarker.create_from_options", return_value=model), patch("system.camera.cv2.VideoCapture", return_value=capture):
            camera = HandCamera()
        self.assertIn("Camera", camera.error)
        capture.release.assert_called_once()
        model.close.assert_called_once()
        camera.close()
        self.assertEqual(camera.read(), (None, []))

    def test_unmirrored_inference_monotonic_timestamps_mirrored_display(self):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:, :320] = (0, 0, 255)
        capture = Mock()
        capture.read.return_value = (True, frame)
        model = Mock()
        model.detect_for_video.return_value = Mock(hand_landmarks=[], handedness=[])
        with patch("system.camera.cv2.VideoCapture", return_value=capture), patch("system.camera.vision.HandLandmarker.create_from_options", return_value=model), patch("system.camera.time.perf_counter", return_value=1):
            camera = HandCamera()
            mirrored, _ = camera.read()
            camera.read()
            args = model.detect_for_video.call_args_list
            self.assertEqual(args[0].args[1], 1000)
            self.assertEqual(args[1].args[1], 1001)
            np.testing.assert_array_equal(args[0].args[0].numpy_view()[0, 0], [255, 0, 0])
            np.testing.assert_array_equal(mirrored[0, 0], [0, 0, 0])
            camera.close()
        model.close.assert_called_once()
        capture.release.assert_called_once()

    def test_disconnection_releases_resources(self):
        capture = Mock()
        capture.read.return_value = (False, None)
        model = Mock()
        with patch("system.camera.cv2.VideoCapture", return_value=capture), patch("system.camera.vision.HandLandmarker.create_from_options", return_value=model):
            camera = HandCamera()
            self.assertEqual(camera.read(), (None, []))
        self.assertIn("disconnected", camera.error)
        capture.release.assert_called_once()
        model.close.assert_called_once()


class ProjectContractTests(unittest.TestCase):
    def test_system_has_no_python_comments_or_docstrings(self):
        for path in Path("system").rglob("*.py"):
            if "artifacts" in path.parts:
                continue
            source = path.read_text(encoding="utf-8-sig")
            self.assertFalse(any(token.type == tokenize.COMMENT for token in tokenize.generate_tokens(io.StringIO(source).readline)), str(path))
            for node in ast.walk(ast.parse(source)):
                if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    self.assertIsNone(ast.get_docstring(node), str(path))

    def test_settings_are_literal_data(self):
        for path in (Path("setting/game_settings.py"), Path("setting/control_settings.py")):
            tree = ast.parse(path.read_text(encoding="utf-8-sig"))
            for node in tree.body:
                self.assertIsInstance(node, ast.Assign)
                ast.literal_eval(node.value)

    def test_local_only_files_are_ignored(self):
        import subprocess
        files = ["AGENTS.md", "PROJECT_FORMAT.md", "SKILL.md", ".codex/test", ".agents/test", "system/artifacts/test.png", "Goalkeeper-workshop.zip"]
        result = subprocess.run(["git", "check-ignore", *files], capture_output=True, text=True)
        self.assertEqual(set(result.stdout.splitlines()), set(files))


if __name__ == "__main__":
    unittest.main()
