# ใช้ไฟล์นี้เมื่อ USE_PRESET = False
MOVE_INSTRUCTION = "เลื่อนมือซ้ายและขวาเพื่อกันบอล"
SKILL_INSTRUCTION = "กำมือข้างใดก็ได้เพื่อใช้สกิล"

# ค่ากล้องของแบบเขียนเอง ไม่อ่านค่าจาก preset
CAMERA_OPTIONS = {
    "min_detection_confidence": 0.5,
    "min_presence_confidence": 0.5,
    "min_tracking_confidence": 0.5,
}


def get_goalkeeper_command(hands, pose_landmarks=None):
    gloves = {}
    skill = False
    for hand in hands:
        if hand["confidence"] < 0.6:
            continue
        points = hand["landmarks"]
        if len(points) != 21:
            continue

        # จุด 9 คือโคนนิ้วกลาง กลับแกน x ให้ตรงภาพกระจก
        palm = points[9]
        gloves[hand["side"]] = (1 - palm.x, palm.y)

        # ปลายนิ้วทั้งสี่อยู่ใกล้ข้อมือกว่าข้อนิ้ว คือกำมือ
        wrist = points[0]
        index_closed = (points[8].x-wrist.x)**2 + (points[8].y-wrist.y)**2 < (points[6].x-wrist.x)**2 + (points[6].y-wrist.y)**2
        middle_closed = (points[12].x-wrist.x)**2 + (points[12].y-wrist.y)**2 < (points[10].x-wrist.x)**2 + (points[10].y-wrist.y)**2
        ring_closed = (points[16].x-wrist.x)**2 + (points[16].y-wrist.y)**2 < (points[14].x-wrist.x)**2 + (points[14].y-wrist.y)**2
        little_closed = (points[20].x-wrist.x)**2 + (points[20].y-wrist.y)**2 < (points[18].x-wrist.x)**2 + (points[18].y-wrist.y)**2
        if index_closed and middle_closed and ring_closed and little_closed:
            skill = True
    return {"gloves": gloves, "skill": skill}
