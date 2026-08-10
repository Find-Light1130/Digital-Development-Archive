"""数据与核心画像快速验证（真检查，失败以非零退出码反馈）

运行：python test/verify.py
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.models import init_db, SessionLocal, Student
from backend.ai_modules.analysis import compute_growth_profile

init_db()
db = SessionLocal()

total = db.query(Student).count()
print(f"Students in DB: {total}")
if total != 1050:
    print(f"FAIL: 期望 1050 名学生，实际 {total}")
    sys.exit(1)

s = db.query(Student).first()
print(f"Sample: id={s.id}, name={s.name}, grade={s.grade}, class={s.class_name}")
if not re.match(r"^[初高][一二三]\d+班$", s.class_name):
    print(f"FAIL: 班级名格式不合法: {s.class_name}")
    sys.exit(1)

profile = compute_growth_profile(1, db)
index = profile["growth_index"]
print(f"Growth index for id=1: {index}")
print(f"  Aspects: {profile['aspects']}")
print(f"  Strengths: {profile['strengths']}")
print(f"  Weakness: {profile['weakness']}")
print(f"  Warnings: {profile['warnings']}")
print(f"  Suggestions: {profile['suggestions']}")
if not (0 <= index <= 100) or not profile["aspects"]:
    print(f"FAIL: 成长画像异常: index={index}, aspects={profile['aspects']}")
    sys.exit(1)

db.close()
print("ALL CHECKS PASSED")
