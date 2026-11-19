import math
import random

import pygame

from setting import game_settings as settings


GOAL = pygame.Rect(40, 128, 440, 390)
SKILLS = ("ถุงมือใหญ่", "ชะลอบอล", "โล่ประตู")


def validate_settings():
    for name in ("ROUND_SECONDS", "BALL_INTERVAL", "BALL_FLIGHT_SECONDS", "SKILL_COOLDOWN", "SKILL_DURATION"):
        value = getattr(settings, name)
        if not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name} ต้องเป็นตัวเลขมากกว่า 0")
    if type(settings.MAX_MISSES) is not int or settings.MAX_MISSES < 1:
        raise ValueError("MAX_MISSES ต้องเป็นจำนวนเต็มอย่างน้อย 1")
    if settings.FIRST_BALL_DELAY < 0 or settings.POINTS_PER_SAVE < 0:
        raise ValueError("FIRST_BALL_DELAY และ POINTS_PER_SAVE ต้อง >= 0")
    if not 4 <= settings.BALL_RADIUS <= 60 or not 8 <= settings.GLOVE_RADIUS <= 120:
        raise ValueError("BALL_RADIUS ต้อง 4–60 และ GLOVE_RADIUS ต้อง 8–120")
    if settings.DEFAULT_SKILL not in SKILLS:
        raise ValueError("DEFAULT_SKILL ไม่อยู่ในรายการสกิล")
    if settings.BIG_GLOVE_MULTIPLIER < 1 or not 0 < settings.SLOW_BALL_MULTIPLIER <= 1:
        raise ValueError("ตัวคูณขนาดต้อง >= 1 และตัวคูณช้าต้อง > 0 ถึง 1")


class Game:
    def __init__(self):
        validate_settings()
        self.selected_skill = settings.DEFAULT_SKILL
        self.reset()
        self.state = "MENU"

    def reset(self):
        self.state = "PLAYING"
        self.elapsed = 0.0
        self.score = 0
        self.saves = 0
        self.misses = 0
        self.balls = []
        self.gloves = {}
        self.next_spawn = settings.FIRST_BALL_DELAY
        self.skill_until = 0.0
        self.cooldown_until = 0.0
        self.flash_until = 0.0
        self.feedback = ""

    @property
    def skill_active(self):
        return self.state == "PLAYING" and self.elapsed < self.skill_until - 1e-9

    @property
    def cooldown_remaining(self):
        return max(0.0, self.cooldown_until - self.elapsed)

    @property
    def glove_radius(self):
        multiplier = settings.BIG_GLOVE_MULTIPLIER if self.skill_active and self.selected_skill == "ถุงมือใหญ่" else 1
        return settings.GLOVE_RADIUS * multiplier

    def activate_skill(self):
        if self.state != "PLAYING" or self.cooldown_remaining > 1e-9 or self.skill_active:
            return False
        self.skill_until = self.elapsed + settings.SKILL_DURATION
        self.cooldown_until = self.elapsed + settings.SKILL_COOLDOWN
        return True

    def spawn_ball(self):
        radius = settings.BALL_RADIUS
        self.balls.append({"x": random.uniform(GOAL.left + radius, GOAL.right - radius),
                           "y": random.uniform(GOAL.top + radius, GOAL.bottom - radius), "progress": 0.0})

    def catches(self, ball):
        if self.skill_active and self.selected_skill == "โล่ประตู":
            return True
        for x, y in self.gloves.values():
            if math.hypot(x - ball["x"], y - ball["y"]) <= self.glove_radius + settings.BALL_RADIUS:
                return True
        return False

    def update(self, delta_seconds, command=None):
        if self.state != "PLAYING":
            return
        command = command or {"gloves": {}, "skill": False}
        self.gloves = {side: (GOAL.left + position[0] * (GOAL.width - 1),
                              GOAL.top + position[1] * (GOAL.height - 1))
                       for side, position in command["gloves"].items()}
        if command["skill"]:
            self.activate_skill()
        time_left = min(max(0.0, delta_seconds), max(0.0, settings.ROUND_SECONDS - self.elapsed))
        while time_left > 1e-9 and self.state == "PLAYING":
            step = min(time_left, 1 / 120)
            if self.elapsed < self.skill_until - 1e-9 < self.elapsed + step:
                step = self.skill_until - self.elapsed
            slow = settings.SLOW_BALL_MULTIPLIER if self.skill_active and self.selected_skill == "ชะลอบอล" else 1.0
            for ball in list(self.balls):
                ball["progress"] += step * slow / settings.BALL_FLIGHT_SECONDS
                if ball["progress"] >= 1 - 1e-9:
                    if self.catches(ball):
                        self.saves += 1
                        self.score += settings.POINTS_PER_SAVE
                        self.feedback = "เซฟ!"
                    else:
                        self.misses += 1
                        self.feedback = "เสียประตู"
                    self.flash_until = self.elapsed + 0.6
                    self.balls.remove(ball)
                    if self.misses >= settings.MAX_MISSES:
                        self.state = "GAME_OVER"
                        break
            self.elapsed += step
            if self.elapsed + 1e-9 >= settings.ROUND_SECONDS:
                self.elapsed = settings.ROUND_SECONDS
                self.state = "GAME_OVER"
            if self.state == "PLAYING" and self.elapsed + 1e-9 >= self.next_spawn:
                self.spawn_ball()
                self.next_spawn += settings.BALL_INTERVAL
            time_left -= step

    def pitch_point(self, across, depth):
        half_width = GOAL.width * (0.12 + 0.88 * depth) / 2
        return (round(GOAL.centerx + across * half_width),
                round(GOAL.top + 114 + (GOAL.height - 114) * depth ** 1.45))

    def shot_origin(self):
        x, y = self.pitch_point(0, 0.55)
        return (x + 18, y)

    def draw_stadium(self, screen):
        horizon = GOAL.top + 114
        for row in range(114):
            color = tuple(min(255, channel + round(row * 0.24)) for channel in settings.SKY_COLOR)
            pygame.draw.line(screen, color, (GOAL.left, GOAL.top + row), (GOAL.right, GOAL.top + row))
        stand = [(GOAL.left, GOAL.top + 44), (GOAL.centerx - 84, GOAL.top + 62),
                 (GOAL.centerx + 84, GOAL.top + 62), (GOAL.right, GOAL.top + 44),
                 (GOAL.right, horizon), (GOAL.left, horizon)]
        pygame.draw.polygon(screen, settings.STADIUM_COLOR, stand)
        for row in range(5):
            y = GOAL.top + 67 + row * 8
            pygame.draw.line(screen, (71, 91, 110), (GOAL.left, y + 3), (GOAL.right, y + 3))
            for column in range(55):
                x = GOAL.left + column * 8 + (row % 2) * 3
                colors = ((206, 216, 216), (225, 98, 91), (231, 194, 98), (88, 154, 178))
                pygame.draw.circle(screen, colors[(column * 7 + row * 3) % 4], (x, y), 2)
        for x in (GOAL.left + 38, GOAL.right - 38):
            pygame.draw.line(screen, (175, 191, 199), (x, GOAL.top + 24), (x, GOAL.top + 84), 3)
            pygame.draw.rect(screen, (225, 236, 232), (x - 17, GOAL.top + 19, 34, 12), border_radius=2)
            for offset in range(-12, 15, 8):
                pygame.draw.line(screen, (255, 251, 207), (x + offset, GOAL.top + 22), (x + offset, GOAL.top + 27), 3)
        pygame.draw.rect(screen, (207, 224, 217), (GOAL.left, horizon - 8, GOAL.width, 9))
        for index in range(8):
            color = (38, 104, 121) if index % 2 else (227, 195, 106)
            pygame.draw.rect(screen, color, (GOAL.left + index * 56, horizon - 7, 52, 7))
        pygame.draw.rect(screen, settings.FIELD_COLOR, (GOAL.left, horizon, GOAL.width, GOAL.bottom - horizon))
        for band in range(10):
            near = (band + 1) / 10
            far = band / 10
            top = self.pitch_point(0, far)[1]
            bottom = self.pitch_point(0, near)[1]
            color = tuple(max(0, channel - 10) for channel in settings.FIELD_COLOR) if band % 2 else settings.FIELD_COLOR
            pygame.draw.rect(screen, color, (GOAL.left, top, GOAL.width, bottom - top + 1))
        line_color = (204, 226, 196)
        for across in (-1.55, 1.55):
            pygame.draw.line(screen, line_color, self.pitch_point(across, 0), self.pitch_point(across, 1), 2)
        for width, depth in ((1.13, 0.46), (0.66, 0.78)):
            points = [self.pitch_point(-width, 1), self.pitch_point(-width, depth),
                      self.pitch_point(width, depth), self.pitch_point(width, 1)]
            pygame.draw.lines(screen, line_color, False, points, 2)
        center_y = self.pitch_point(0, 0.23)[1]
        pygame.draw.ellipse(screen, line_color, (GOAL.centerx - 32, center_y - 6, 64, 13), 2)
        pygame.draw.line(screen, line_color, self.pitch_point(-1.55, 0.23), self.pitch_point(1.55, 0.23), 2)
        pygame.draw.circle(screen, line_color, self.pitch_point(0, 0.55), 3)
        pygame.draw.line(screen, line_color, (GOAL.left, GOAL.bottom - 17), (GOAL.right, GOAL.bottom - 17), 3)
        far_goal = pygame.Rect(GOAL.centerx - 24, horizon - 19, 48, 21)
        pygame.draw.rect(screen, (31, 72, 75), far_goal)
        for offset in range(6, 48, 7):
            pygame.draw.line(screen, (119, 156, 157), (far_goal.left + offset, far_goal.top),
                             (far_goal.left + offset, far_goal.bottom))
        pygame.draw.rect(screen, (224, 236, 226), far_goal, 2)
        for across in (-0.8, 0.75):
            x, y = self.pitch_point(across, 0.28)
            pygame.draw.circle(screen, (191, 143, 109), (x, y - 29), 5)
            pygame.draw.line(screen, (226, 231, 227), (x, y - 21), (x, y - 11), 9)
            pygame.draw.line(screen, (33, 61, 76), (x - 3, y - 10), (x - 5, y), 4)
            pygame.draw.line(screen, (33, 61, 76), (x + 3, y - 10), (x + 5, y), 4)

    def draw_shooter(self, screen):
        ball_x, ground_y = self.shot_origin()
        x = ball_x - 18
        windup = max(0.0, 1 - max(0.0, self.next_spawn - self.elapsed) / 0.65)
        shot_age = self.elapsed - (self.next_spawn - settings.BALL_INTERVAL)
        following = self.next_spawn > settings.FIRST_BALL_DELAY + 1e-9 and 0 <= shot_age < 0.45
        swing = (1 - shot_age / 0.45) if following else -windup * 0.7
        lean = round(swing * 4)
        pygame.draw.ellipse(screen, (31, 89, 52), (x - 30, ground_y - 5, 64, 12))
        shorts_y = ground_y - 33
        hip = (x + lean, shorts_y)
        planted_knee = (x - 9, ground_y - 17)
        planted_foot = (x - 12, ground_y - 1)
        kicking_knee = (x + 12 + round(swing * 9), ground_y - 20 - round(max(0, swing) * 7))
        kicking_foot = (x + 17 + round(swing * 15), ground_y - 1 - round(max(0, swing) * 25))
        for knee, foot in ((planted_knee, planted_foot), (kicking_knee, kicking_foot)):
            pygame.draw.lines(screen, (194, 145, 108), False, [hip, knee, foot], 8)
            pygame.draw.line(screen, (241, 237, 219), knee, foot, 5)
            pygame.draw.ellipse(screen, (24, 34, 43), (foot[0] - 5, foot[1] - 3, 14, 6))
        pygame.draw.rect(screen, (31, 45, 64), (x - 14 + lean, shorts_y - 9, 28, 15), border_radius=3)
        shoulders_y = ground_y - 69
        jersey = [(x - 14 + lean, shoulders_y), (x + 13 + lean, shoulders_y),
                  (x + 12 + lean, shorts_y - 6), (x - 12 + lean, shorts_y - 6)]
        pygame.draw.polygon(screen, settings.SHOOTER_COLOR, jersey)
        for side in (-1, 1):
            shoulder = (x + side * 13 + lean, shoulders_y + 5)
            elbow = (x + side * 24 + lean, shoulders_y + 17 - round(swing * side * 8))
            hand = (x + side * 30 + lean, shoulders_y + 26 - round(swing * side * 12))
            pygame.draw.line(screen, settings.SHOOTER_COLOR, shoulder, elbow, 10)
            pygame.draw.line(screen, (194, 145, 108), elbow, hand, 6)
        pygame.draw.line(screen, (242, 239, 220), (x - 9 + lean, shoulders_y + 4), (x + 8 + lean, shoulders_y + 4), 2)
        pygame.draw.circle(screen, (243, 241, 226), (x + lean, shoulders_y + 16), 4, 2)
        pygame.draw.line(screen, (243, 241, 226), (x + 3 + lean, shoulders_y + 16), (x + lean, shoulders_y + 24), 2)
        pygame.draw.rect(screen, (194, 145, 108), (x - 4 + lean, shoulders_y - 9, 8, 11))
        pygame.draw.ellipse(screen, (206, 158, 120), (x - 10 + lean, shoulders_y - 27, 20, 23))
        pygame.draw.ellipse(screen, (38, 34, 34), (x - 10 + lean, shoulders_y - 29, 20, 11))
        if not following:
            center = (ball_x, ground_y - 5)
            pygame.draw.circle(screen, settings.BALL_COLOR, center, 7)
            pygame.draw.circle(screen, (37, 52, 58), center, 3)

    def draw_goal_frame(self, screen):
        color = settings.NET_COLOR
        for side in (-1, 1):
            edge = GOAL.left if side == -1 else GOAL.right - 1
            inner = edge - side * 15
            for row in range(0, GOAL.height, 26):
                pygame.draw.line(screen, color, (edge, GOAL.top + row), (inner, GOAL.top + row + 9))
            pygame.draw.line(screen, color, (inner, GOAL.top + 17), (inner, GOAL.bottom), 1)
            pygame.draw.line(screen, (166, 186, 191), (inner + side * 3, GOAL.top + 13), (inner + side * 3, GOAL.bottom), 10)
            pygame.draw.line(screen, (241, 246, 236), (inner, GOAL.top + 12), (inner, GOAL.bottom), 7)
        pygame.draw.line(screen, (166, 186, 191), (GOAL.left + 13, GOAL.top + 15), (GOAL.right - 13, GOAL.top + 15), 10)
        pygame.draw.line(screen, (244, 247, 238), (GOAL.left + 13, GOAL.top + 11), (GOAL.right - 13, GOAL.top + 11), 7)

    def draw(self, screen):
        old_clip = screen.get_clip()
        screen.set_clip(GOAL)
        self.draw_stadium(screen)
        self.draw_shooter(screen)
        if self.skill_active and self.selected_skill == "โล่ประตู":
            veil = pygame.Surface(GOAL.size, pygame.SRCALPHA)
            veil.fill((75, 190, 255, 70))
            screen.blit(veil, GOAL)
            pygame.draw.rect(screen, (130, 215, 255), GOAL.inflate(-10, -10), 5)
        for ball in self.balls:
            target = (round(ball["x"]), round(ball["y"]))
            pygame.draw.circle(screen, (153, 183, 160), target, settings.BALL_RADIUS + 6, 2)
            progress = ball["progress"]
            origin_x, origin_y = self.shot_origin()
            lift = math.sin(math.pi * progress) * 48
            center = (round(origin_x + (ball["x"] - origin_x) * progress),
                      round(origin_y + (ball["y"] - origin_y) * progress - lift))
            radius = max(5, round(settings.BALL_RADIUS * (0.3 + 0.7 * progress)))
            pygame.draw.circle(screen, (12, 38, 35), (center[0] + 3, center[1] + 5), radius)
            pygame.draw.circle(screen, settings.BALL_COLOR, center, radius)
            pygame.draw.circle(screen, (38, 54, 59), center, max(2, radius // 3))
            for angle in (0, 72, 144, 216, 288):
                end = (center[0] + math.cos(math.radians(angle)) * radius * 0.85,
                       center[1] + math.sin(math.radians(angle)) * radius * 0.85)
                pygame.draw.line(screen, (70, 84, 84), center, end, 1)
        for side, position in self.gloves.items():
            center = (round(position[0]), round(position[1]))
            radius = round(self.glove_radius)
            color = settings.LEFT_GLOVE_COLOR if side == "Left" else settings.RIGHT_GLOVE_COLOR
            pygame.draw.circle(screen, color, center, radius, 5)
            pygame.draw.circle(screen, (236, 242, 250), center, max(3, radius - 9), 2)
            pygame.draw.line(screen, color, (center[0] - radius // 2, center[1]),
                             (center[0] + radius // 2, center[1]), 3)
        self.draw_goal_frame(screen)
        screen.set_clip(old_clip)
