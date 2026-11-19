# True ใช้สำเร็จรูป / False เขียนกฎใน hand_controls.py
USE_PRESET = True

# เลื่อนมือทั้งสองข้างเพื่อขยับถุงมือเสมอ
# เลือก: กำมือข้างใดก็ได้ / กำมือซ้าย / กำมือขวา / กำมือสองข้าง
SKILL_ACTION = "กำมือข้างใดก็ได้"
SENSITIVITY = 1.0  # 0.5–1.5 ค่ามากกำมือได้ง่ายขึ้น
HOLD_SECONDS = 0.15  # ค้างท่าก่อนใช้สกิล
MOVEMENT_GAIN = 1.25  # ค่ามากขยับมือน้อยลง
SMOOTHING_SECONDS = 0.06  # 0 คือไม่กรองการสั่น
MIN_HAND_CONFIDENCE = 0.6

# ค่าตรวจจับ MediaPipe เฉพาะสำเร็จรูป: 0.0–1.0
MIN_DETECTION_CONFIDENCE = 0.5
MIN_PRESENCE_CONFIDENCE = 0.5
MIN_TRACKING_CONFIDENCE = 0.5
