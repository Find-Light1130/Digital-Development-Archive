"""数据库结构抽查（真检查，失败以非零退出码反馈）

运行：python test/check.py
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.models import init_db, SessionLocal, Student
from backend.ai_modules.analysis import compute_growth_profile

init_db()
db = SessionLocal()

classes = [c[0] for c in db.query(Student.class_name).distinct().order_by(Student.class_name).all()]
print("Classes in DB:", classes[:9])

if not all(re.match(r"^[初高][一二三]\d+班$", c) for c in classes):
    bad_classes = [c for c in classes if not re.match(r"^[初高][一二三]\d+班$", c)]
    print(f"FAIL: 存在格式不合法的班级名: {bad_classes}")
    sys.exit(1)

cnt = db.query(Student).count()
print(f"Total students: {cnt}")
if cnt < 1000:
    print("FAIL: 学生数量过少")
    sys.exit(1)

for sid in [1, 334, 667]:
    p = compute_growth_profile(sid, db)
    index = p["growth_index"]
    print(f"Student {sid}: index={index}, aspects={p['aspects']}")
    if not (0 <= index <= 100) or not p["aspects"]:
        print(f"FAIL: 学生 {sid} 画像异常")
        sys.exit(1)

db.close()
print("ALL CHECKS PASSED")
