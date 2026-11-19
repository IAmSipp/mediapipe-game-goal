# ผู้รักษาประตู

ขยับมือทั้งสองข้างให้วงถุงมือไปทับวงเป้าหมายก่อนบอลมาถึงประตู
เซฟได้ลูกละ 10 คะแนน พลาด 5 ลูกหรือครบ 60 วินาทีจบรอบ
เลือกสกิลก่อนเริ่มหรือเล่นใหม่ แล้วกำมือเพื่อใช้สกิล
คลายมือก่อนกดครั้งถัดไป คูลดาวน์เริ่มตอนกดใช้

| สกิล | ผล |
|---|---|
| ถุงมือใหญ่ | เพิ่มขนาดถุงมือ 3 วินาที |
| ชะลอบอล | บอลช้าลง 3 วินาที |
| โล่ประตู | กันบอลทั้งประตู 3 วินาที |

คูลดาวน์เริ่มต้น 8 วินาที ถ้าไม่พบมือ วงถุงมือข้างนั้นจะหายไป

## เปิดเกม (PowerShell / Python 3.13)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m system.download_model
.\.venv\Scripts\python.exe main.py
```

ถ้ามีกล้องหลายตัว ใช้ `main.py --camera 1` กด Esc เพื่อออก
มีโมเดลทางการใน `system/models/` อยู่แล้ว ไม่ต้องดาวน์โหลดซ้ำถ้าไฟล์ยังครบ

แก้ค่าที่ [setting/README.md](setting/README.md)
ใช้ `USE_PRESET = True` สำหรับสำเร็จรูป หรือ `False` เพื่อเขียนกฎเอง
แบบเขียนเองไม่ใช้ความไว เวลาค้าง การกรอง หรือค่ากล้องจาก preset

ทดสอบจำลอง: `.\.venv\Scripts\python.exe -m unittest discover -s system/tests -v`
วิธีตรวจโมเดลและกล้องจริง: [system/docs/CONTROL_DETAILS.md](system/docs/CONTROL_DETAILS.md)
