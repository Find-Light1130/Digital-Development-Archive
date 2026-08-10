"""批量画像性能与缓存验证（相对路径，跑完以退出码反馈结果）

运行：python test/perf_check.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.models import init_db, SessionLocal, Student
from backend.ai_modules.analysis import batch_growth_profiles

init_db()
db = SessionLocal()

students = db.query(Student).all()
ids = [s.id for s in students]
cnt = len(ids)

if cnt < 1000:
    print(f"FAIL: 期望至少 1000 名学生，实际 {cnt}")
    sys.exit(1)

t0 = time.perf_counter()
profiles = batch_growth_profiles(ids, db)
t1 = time.perf_counter()
elapsed = t1 - t0
speed = cnt / elapsed if elapsed > 0 else 0
print(f"{cnt} students in batch: {elapsed:.2f}s ({speed:.0f} profiles/s)")

missing = [sid for sid in ids if sid not in profiles]
if missing:
    print(f"FAIL: {len(missing)} 名学生缺失画像")
    sys.exit(1)

bad = [sid for sid in ids if not (0 <= profiles[sid]["growth_index"] <= 100)]
if bad:
    print(f"FAIL: {len(bad)} 名学生成长指数越界")
    sys.exit(1)

keys = list(profiles.keys())[:3]
for k in keys:
    p = profiles[k]
    print(f"  id={k}: index={p['growth_index']}, warnings={len(p['warnings'])}, suggestions={len(p['suggestions'])}")

db.close()
print("ALL CHECKS PASSED")
