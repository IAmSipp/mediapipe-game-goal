import math
import time

import pygame

from system.controls import GameControls
from setting import game_settings as settings
from system.camera import HandCamera
from system.game import Game, SKILLS


WINDOW_SIZE = (1120, 760)
BUTTON = pygame.Rect(100, 530, 320, 58)
SKILL_BUTTONS = tuple(pygame.Rect(52 + index * 144, 414, 136, 48) for index in range(3))
BACKGROUND = (16, 24, 39)
WHITE = (236, 242, 250)
MUTED = (160, 178, 200)
TEAL = (58, 209, 199)
SKILL_DETAILS = {
    "ถุงมือใหญ่": "เพิ่มขนาดถุงมือชั่วคราว",
    "ชะลอบอล": "บอลเข้าประตูช้าลงชั่วคราว",
    "โล่ประตู": "ป้องกันบอลได้ทั่วประตู",
}


def text(screen, font, message, position, color=WHITE):
    screen.blit(font.render(message, True, color), position)


def handle_event(event, game, camera_ready):
    if event.type == pygame.QUIT:
        return False
    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
        return False
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and game.state != "PLAYING":
        for rect, skill in zip(SKILL_BUTTONS, SKILLS):
            if rect.collidepoint(event.pos):
                game.selected_skill = skill
        if BUTTON.collidepoint(event.pos) and camera_ready:
            game.reset()
    return True


def draw_screen(screen, game, camera_frame, hands, camera_error, font, small_font, title_font, control):
    screen.fill(BACKGROUND)
    text(screen, title_font, settings.GAME_TITLE, (40, 20))
    camera_rect = pygame.Rect(540, 128, 520, 390)
    if camera_frame is not None:
        height, width = camera_frame.shape[:2]
        image = pygame.image.frombuffer(camera_frame.tobytes(), (width, height), "RGB")
        screen.blit(pygame.transform.smoothscale(image, camera_rect.size), camera_rect)
    else:
        pygame.draw.rect(screen, (25, 38, 57), camera_rect)
    if camera_error:
        status = "เปิดกล้องไม่ได้" if "camera" in camera_error.lower() else "แจ้งผู้สอนเพื่อตรวจการตั้งค่า"
    elif camera_frame is None:
        status = "กำลังเปิดกล้อง…"
    else:
        status = control.status
    text(screen, font, status, (540, 542))

    if game.state == "PLAYING":
        text(screen, font, f"คะแนน {game.score}   พลาด {game.misses}/{settings.MAX_MISSES}", (540, 28))
        remaining = max(0, math.ceil(settings.ROUND_SECONDS - game.elapsed))
        text(screen, small_font, f"เหลือ {remaining} วินาที", (540, 76), MUTED)
        game.draw(screen)
        if game.skill_active:
            skill_status = "กำลังใช้ " + game.selected_skill
        elif game.cooldown_remaining > 0:
            skill_status = f"{game.selected_skill} อีก {math.ceil(game.cooldown_remaining)} วิ"
        else:
            skill_status = game.selected_skill + " พร้อมใช้"
        text(screen, font, skill_status, (40, 554), TEAL)
        fraction = 1 - min(1.0, game.cooldown_remaining / settings.SKILL_COOLDOWN)
        pygame.draw.rect(screen, (44, 59, 77), (40, 598, 440, 6), border_radius=3)
        if fraction > 0:
            pygame.draw.rect(screen, TEAL, (40, 598, round(440 * fraction), 6), border_radius=3)
        if game.elapsed < game.flash_until:
            text(screen, font, game.feedback, (40, 640))
    else:
        if game.state == "MENU":
            text(screen, font, "วิธีเล่น", (80, 174))
            text(screen, small_font, control.move_instruction, (80, 228))
            text(screen, small_font, control.skill_instruction, (80, 266))
            text(screen, small_font, f"พลาด {settings.MAX_MISSES} ลูก หรือครบ {settings.ROUND_SECONDS:g} วิ จบรอบ", (80, 312), MUTED)
            button_label = "เริ่มเกม"
        else:
            text(screen, font, "จบเกม", (80, 174))
            text(screen, title_font, f"คะแนน {game.score}", (80, 230))
            text(screen, small_font, f"เซฟ {game.saves} ลูก   พลาด {game.misses} ลูก", (80, 306), MUTED)
            button_label = "เล่นใหม่"
        text(screen, small_font, "เลือกสกิล", (52, 370), MUTED)
        for rect, skill in zip(SKILL_BUTTONS, SKILLS):
            selected = skill == game.selected_skill
            pygame.draw.rect(screen, TEAL if selected else (37, 53, 72), rect, border_radius=5)
            label = small_font.render(skill, True, BACKGROUND if selected else WHITE)
            screen.blit(label, label.get_rect(center=rect.center))
        text(screen, small_font, SKILL_DETAILS[game.selected_skill], (70, 478), MUTED)
        ready = camera_frame is not None and not camera_error
        pygame.draw.rect(screen, TEAL if ready else (83, 98, 115), BUTTON, border_radius=4)
        label = font.render(button_label if ready else "ยังไม่พร้อม", True, BACKGROUND)
        screen.blit(label, label.get_rect(center=BUTTON.center))
    if game.state != "MENU":
        text(screen, small_font, control.move_instruction, (540, 604), MUTED)
        text(screen, small_font, control.skill_instruction, (540, 640), MUTED)
    text(screen, small_font, "คลายมือก่อนกดสกิลครั้งถัดไป", (540, 676), MUTED)


def main(camera_index=0):
    pygame.init()
    camera = None
    try:
        screen = pygame.display.set_mode(WINDOW_SIZE)
        pygame.display.set_caption(settings.GAME_TITLE)
        font_names = "tahoma,leelawadeeui,notosansthai,thonburi,arial"
        font = pygame.font.SysFont(font_names, 24)
        small_font = pygame.font.SysFont(font_names, 20)
        title_font = pygame.font.SysFont(font_names, 42, bold=True)
        clock = pygame.time.Clock()
        game = Game()
        control = GameControls()
        draw_screen(screen, game, None, [], "", font, small_font, title_font, control)
        pygame.display.flip()
        camera = HandCamera(camera_index, detect_hands=control.detect_hands,
                            detect_pose=control.detect_pose, **control.camera_options)
        reported_error = ""
        previous_time = time.perf_counter()
        running = True
        while running:
            clock.tick(60)
            camera_frame, hands = camera.read()
            now = time.perf_counter()
            delta_seconds = now - previous_time
            previous_time = now
            ready = camera_frame is not None and not camera.error
            state_before_events = game.state
            for event in pygame.event.get():
                if not handle_event(event, game, ready):
                    running = False
            if not running:
                break
            if state_before_events != "PLAYING" and game.state == "PLAYING":
                control.reset()
            else:
                control.update(hands, camera.pose_landmarks, delta_seconds)
            if camera.error:
                control.reset()
                game.gloves = {}
                if camera.error != reported_error:
                    print(f"Camera/model: {camera.error}")
                    reported_error = camera.error
            elif state_before_events == "PLAYING" and game.state == "PLAYING":
                game.update(delta_seconds, control.command)
            draw_screen(screen, game, camera_frame, hands, camera.error, font, small_font, title_font, control)
            pygame.display.flip()
    finally:
        try:
            if camera is not None:
                camera.close()
        finally:
            pygame.quit()
