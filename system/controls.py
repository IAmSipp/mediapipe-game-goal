from math import exp, isfinite

from setting import control_settings as settings
from setting import hand_controls


ACTIONS = ("กำมือข้างใดก็ได้", "กำมือซ้าย", "กำมือขวา", "กำมือสองข้าง")


def distance_squared(a, b):
    return (a.x - b.x) ** 2 + (a.y - b.y) ** 2


def is_fist(points, sensitivity):
    wrist = points[0]
    return all(distance_squared(points[tip], wrist) < distance_squared(points[joint], wrist) * (0.95 + 0.1 * sensitivity) ** 2
               and distance_squared(points[joint], wrist) > 1e-10
               for tip, joint in ((8, 6), (12, 10), (16, 14), (20, 18)))


def validate_command(command):
    if not isinstance(command, dict) or type(command.get("skill")) is not bool:
        raise ValueError("hand_controls: ต้องคืน dict ที่มี gloves และ skill (True/False)")
    gloves = command.get("gloves")
    if not isinstance(gloves, dict):
        raise ValueError("hand_controls: gloves ต้องเป็น dict")
    result = {}
    for side, position in gloves.items():
        if side not in ("Left", "Right") or len(position) != 2:
            raise ValueError("hand_controls: ใช้ Left/Right และพิกัด (x, y)")
        x, y = position
        if not isfinite(x) or not isfinite(y):
            raise ValueError("hand_controls: พิกัดต้องเป็นตัวเลขที่มีค่าจำกัด")
        result[side] = (max(0.0, min(1.0, x)), max(0.0, min(1.0, y)))
    return result


class GameControls:
    def __init__(self):
        if type(settings.USE_PRESET) is not bool:
            raise ValueError("USE_PRESET ต้องเป็น True หรือ False")
        self.custom = not settings.USE_PRESET
        self.detect_hands = True
        self.detect_pose = False
        if self.custom:
            self.move_instruction = hand_controls.MOVE_INSTRUCTION
            self.skill_instruction = hand_controls.SKILL_INSTRUCTION
            self.camera_options = dict(hand_controls.CAMERA_OPTIONS)
        else:
            if settings.SKILL_ACTION not in ACTIONS:
                raise ValueError("SKILL_ACTION ไม่อยู่ในรายการท่า")
            if not 0.5 <= settings.SENSITIVITY <= 1.5:
                raise ValueError("SENSITIVITY ต้องอยู่ระหว่าง 0.5–1.5")
            if settings.HOLD_SECONDS < 0 or settings.SMOOTHING_SECONDS < 0 or settings.MOVEMENT_GAIN <= 0:
                raise ValueError("เวลาต้อง >= 0 และ MOVEMENT_GAIN > 0")
            if not 0 <= settings.MIN_HAND_CONFIDENCE <= 1:
                raise ValueError("MIN_HAND_CONFIDENCE ต้องอยู่ระหว่าง 0–1")
            self.move_instruction = "เลื่อนมือซ้ายและขวาเพื่อกันบอล"
            self.skill_instruction = settings.SKILL_ACTION + "เพื่อใช้สกิล"
            self.camera_options = {
                "min_detection_confidence": settings.MIN_DETECTION_CONFIDENCE,
                "min_presence_confidence": settings.MIN_PRESENCE_CONFIDENCE,
                "min_tracking_confidence": settings.MIN_TRACKING_CONFIDENCE,
            }
        if any(not 0 <= value <= 1 for value in self.camera_options.values()):
            raise ValueError("ค่าตรวจจับ MediaPipe ต้องอยู่ระหว่าง 0–1")
        self.reset()

    def reset(self):
        self.command = {"gloves": {}, "skill": False}
        self.filtered = {}
        self.held_seconds = 0.0
        self.pending = False
        self.armed = False
        self.release_sides = set()
        self.status = "ยกมือให้กล้องเห็น"

    def update(self, hands, pose_landmarks, delta_seconds):
        delta_seconds = max(0.0, delta_seconds)
        if self.custom:
            raw = hand_controls.get_goalkeeper_command(hands, pose_landmarks)
            gloves = validate_command(raw)
            candidate = raw["skill"]
            ready = candidate
            release_seen = bool(gloves) and not candidate
        else:
            gloves = {}
            fists = {}
            for hand in sorted(hands, key=lambda hand: hand.get("confidence", 0)):
                points = hand["landmarks"]
                side = hand["side"]
                if side not in ("Left", "Right") or len(points) != 21 or hand.get("confidence", 0) < settings.MIN_HAND_CONFIDENCE:
                    continue
                x = (1 - points[9].x - 0.5) * settings.MOVEMENT_GAIN + 0.5
                y = (points[9].y - 0.5) * settings.MOVEMENT_GAIN + 0.5
                if not isfinite(x) or not isfinite(y):
                    continue
                target = (max(0.0, min(1.0, x)), max(0.0, min(1.0, y)))
                if side in self.filtered and settings.SMOOTHING_SECONDS > 0:
                    alpha = 1 - exp(-delta_seconds / settings.SMOOTHING_SECONDS)
                    old = self.filtered[side]
                    target = (old[0] + (target[0] - old[0]) * alpha, old[1] + (target[1] - old[1]) * alpha)
                gloves[side] = target
                fists[side] = is_fist(points, settings.SENSITIVITY)
            self.filtered = dict(gloves)
            if settings.SKILL_ACTION == "กำมือซ้าย":
                candidate = fists.get("Left", False)
                release_seen = "Left" in fists and not candidate
            elif settings.SKILL_ACTION == "กำมือขวา":
                candidate = fists.get("Right", False)
                release_seen = "Right" in fists and not candidate
            elif settings.SKILL_ACTION == "กำมือสองข้าง":
                candidate = fists.get("Left", False) and fists.get("Right", False)
                release_seen = len(fists) == 2 and not candidate
            else:
                candidate = any(fists.values())
                release_seen = bool(fists) and not candidate
            if candidate:
                if self.pending:
                    self.held_seconds += delta_seconds
                else:
                    self.held_seconds = 0.0
            else:
                self.held_seconds = 0.0
            self.pending = candidate
            ready = candidate and self.held_seconds + 1e-9 >= settings.HOLD_SECONDS
        if self.release_sides and not self.release_sides.issubset(gloves):
            release_seen = False
        if release_seen:
            self.armed = True
        fired = bool(ready and self.armed)
        if fired:
            self.armed = False
            self.release_sides = set(gloves)
        self.command = {"gloves": gloves, "skill": fired}
        if not gloves:
            self.status = "ยกมือให้กล้องเห็น"
        elif fired:
            self.status = "ส่งคำสั่งสกิล"
        elif candidate and not ready:
            self.status = "ค้างท่าอีกนิด"
        elif candidate and not self.armed:
            self.status = "คลายมือเพื่อกดครั้งถัดไป"
        else:
            self.status = "พบมือสองข้าง" if len(gloves) == 2 else "พบมือหนึ่งข้าง"
        return self.command
