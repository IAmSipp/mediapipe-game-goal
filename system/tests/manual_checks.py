import argparse
import json
import os
from pathlib import Path
import time
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "system" / "artifacts"
os.environ.setdefault("MPLCONFIGDIR", str(ARTIFACTS / "matplotlib"))
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import numpy as np
import pygame

from setting import control_settings as settings
from system import app
from system.camera import HandCamera, draw_hands
from system.controls import GameControls, is_fist
from system.download_model import MODEL_PATH
from system.game import Game, GOAL, SKILLS


def synthetic_hand(side, x, y):
    points = [SimpleNamespace(x=x, y=y, z=0.0) for _ in range(21)]
    points[0].y = y + 0.12
    for base, offset in ((1, -0.08), (5, -0.04), (9, 0), (13, 0.04), (17, 0.08)):
        for index in range(base, base + 4):
            points[index].x = x + offset
            points[index].y = y - (index - base) * 0.045
    return {"side": side, "landmarks": points, "confidence": 0.99}


def render_screens():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.init()
    try:
        screen = pygame.display.set_mode(app.WINDOW_SIZE)
        fonts = [pygame.font.SysFont("tahoma,leelawadeeui,arial", size, bold=size == 42) for size in (24, 20, 42)]
        hands = [synthetic_hand("Left", 0.72, 0.48), synthetic_hand("Right", 0.28, 0.42)]
        frame = np.full((480, 640, 3), (25, 38, 57), dtype=np.uint8)
        draw_hands(frame, hands)
        saved = []
        for preset in (True, False):
            with patch.object(settings, "USE_PRESET", preset):
                game = Game()
                control = GameControls()
                control.update(hands, [], 0.1)
                for state in ("MENU", "PLAYING", "GAME_OVER", "CAMERA_ERROR"):
                    if state == "PLAYING":
                        game.reset()
                        game.update(0.1, control.command)
                        game.balls = [{"x": 370, "y": 270, "progress": 0.78}]
                    elif state == "GAME_OVER":
                        game.state = "GAME_OVER"
                        game.score = 70
                        game.saves = 7
                        game.misses = 5
                    elif state == "CAMERA_ERROR":
                        game.state = "MENU"
                    error = "Camera unavailable" if state == "CAMERA_ERROR" else ""
                    app.draw_screen(screen, game, None if error else frame, hands, error, *fonts, control)
                    name = f"{'preset' if preset else 'custom'}_{state.lower()}.png"
                    pygame.image.save(screen, str(ARTIFACTS / name))
                    saved.append(name)
                for skill in SKILLS:
                    game.reset()
                    game.selected_skill = skill
                    game.update(0.1, control.command)
                    game.activate_skill()
                    game.balls = [{"x": 370, "y": 270, "progress": 0.78}]
                    app.draw_screen(screen, game, frame, hands, "", *fonts, control)
                    name = f"{'preset' if preset else 'custom'}_skill_{SKILLS.index(skill)}.png"
                    pygame.image.save(screen, str(ARTIFACTS / name))
                    saved.append(name)
        return saved
    finally:
        pygame.quit()


def static_checks(fixture_dir):
    options = vision.HandLandmarkerOptions(base_options=python.BaseOptions(model_asset_buffer=MODEL_PATH.read_bytes()),
                                          running_mode=vision.RunningMode.IMAGE, num_hands=2)
    results = {}
    with vision.HandLandmarker.create_from_options(options) as detector:
        for name in ("right_hands.jpg", "pointing_up.jpg", "fist.jpg"):
            frame = cv2.imread(str(fixture_dir / name))
            if frame is None:
                raise ValueError(f"Missing fixture: {name}")
            for flipped in (False, True):
                rgb = cv2.cvtColor(cv2.flip(frame, 1) if flipped else frame, cv2.COLOR_BGR2RGB)
                result = detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
                hands = [{"side": categories[0].category_name, "confidence": categories[0].score, "landmarks": points}
                         for points, categories in zip(result.hand_landmarks, result.handedness)]
                assert hands, name
                if name == "right_hands.jpg":
                    assert len(hands) == 2
                    assert all(hand["side"] == ("Left" if flipped else "Right") for hand in hands)
                if name == "pointing_up.jpg":
                    assert hands[0]["side"] == ("Left" if flipped else "Right")
                    assert not is_fist(hands[0]["landmarks"], 1.0)
                if name == "fist.jpg":
                    assert is_fist(hands[0]["landmarks"], 1.0)
                modes = {}
                for preset in (True, False):
                    with patch.object(settings, "USE_PRESET", preset):
                        control = GameControls()
                        control.update([synthetic_hand(hands[0]["side"], 0.5, 0.5)], [], 0)
                        command = control.update(hands, [], 0.1)
                        next_command = control.update(hands, [], 0.2)
                        assert command["gloves"]
                        if name == "fist.jpg":
                            assert command["skill"] or next_command["skill"]
                        modes[str(preset)] = {"gloves": len(command["gloves"]), "skill_pressed": command["skill"] or next_command["skill"]}
                results[name + ("_flipped" if flipped else "")] = {"sides": [hand["side"] for hand in hands], "modes": modes}
    return results


def live_checks():
    results = []
    for preset in (True, False):
        with patch.object(settings, "USE_PRESET", preset):
            control = GameControls()
            camera = HandCamera(**control.camera_options)
            count = 0
            detected_frames = 0
            previous = time.perf_counter()
            try:
                if not camera.error:
                    for _ in range(24):
                        frame, hands = camera.read()
                        now = time.perf_counter()
                        control.update(hands, [], now - previous)
                        previous = now
                        if frame is None:
                            break
                        count += 1
                        detected_frames += bool(hands)
                results.append({"preset": preset, "frames_read": count, "frames_with_hands": detected_frames, "error": camera.error})
            finally:
                camera.close()
            assert camera.capture is None and camera.landmarker is None
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture-dir", type=Path)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    report = {"screens_synthetic": render_screens()}
    if args.fixture_dir:
        report["static_model"] = static_checks(args.fixture_dir)
    if args.live:
        report["live_camera"] = live_checks()
    path = ARTIFACTS / "manual-checks.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
