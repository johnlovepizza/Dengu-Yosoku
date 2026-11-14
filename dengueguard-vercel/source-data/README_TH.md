# Source data

โฟลเดอร์นี้เก็บ CSV/GeoJSON ต้นฉบับจาก Streamlit project และไฟล์ Python เดิมเพื่อใช้เป็นแหล่งอ้างอิงระหว่างการย้ายระบบ

ไฟล์ที่หน้าเว็บเรียกใช้งานจริงอยู่ใน `public/data/` ในรูป JSON เพื่อให้ Next.js client โหลดผ่าน static URL ได้

เมื่อมี CSV ใหม่จาก Google Colab ให้นำมาแทนที่ไฟล์ใน `source-data/data/` หรือ `source-data/questionnaire/` แล้วรัน `python scripts/convert_data.py` จาก project root

**ห้ามเก็บข้อมูลผู้ป่วยที่ระบุตัวบุคคลได้ หรือ credentials/API keys ในโฟลเดอร์นี้**
