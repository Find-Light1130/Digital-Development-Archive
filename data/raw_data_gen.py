"""
模拟数据生成脚本（初中版）
生成 ~1000 名学生数据，涵盖成绩、考勤、情绪、活动记录
班级规模 40-50 人，科目：语数英+政史地物化生
"""

import numpy as np
from datetime import datetime, timedelta
import random
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from backend.models import (
    init_db, SessionLocal, Student, Score, Attendance, EmotionLog, Activity, Award, QualityScore,
    SubjectStats, User,
)
from backend.routes.auth import _hash_password
from backend.constants import grade_for, SUBJECTS_BY_SEMESTER, MAX_SCORES, QUALITY_SUBJECTS, QUALITY_DIMENSIONS, AWARD_LEVELS

NUM_STUDENTS = 1050
GRADES = ["初一", "初二", "初三"]
CLASSES_PER_GRADE = 7
DAYS = 180
START_DATE = datetime(2026, 2, 16)
TODAY = datetime.combine(datetime.now().date(), datetime.min.time())

np.random.seed(42)
random.seed(42)

SUBJECTS_CHUYI = SUBJECTS_BY_SEMESTER["初一上"]
SUBJECTS_CHUER_SHANG = SUBJECTS_BY_SEMESTER["初二上"]
SUBJECTS_CHUER_XIA = SUBJECTS_BY_SEMESTER["初二下"]
SUBJECTS_CHUSAN = SUBJECTS_BY_SEMESTER["初三上"]

EXAM_WEEKS = [4, 8, 10, 14, 18]

SEMESTERS = [
    {"name": "初一上", "grade": "初一", "start": datetime(2025, 9, 1), "subjects": SUBJECTS_CHUYI},
    {"name": "初一下", "grade": "初一", "start": datetime(2026, 2, 16), "subjects": SUBJECTS_CHUYI},
    {"name": "初二上", "grade": "初二", "start": datetime(2026, 9, 1), "subjects": SUBJECTS_CHUER_SHANG},
    {"name": "初二下", "grade": "初二", "start": datetime(2027, 2, 16), "subjects": SUBJECTS_CHUER_XIA},
    {"name": "初三上", "grade": "初三", "start": datetime(2027, 9, 1), "subjects": SUBJECTS_CHUSAN},
    {"name": "初三下", "grade": "初三", "start": datetime(2028, 2, 16), "subjects": SUBJECTS_CHUSAN},
]

GRADE_SEMESTERS = {
    "初一": ["初一上", "初一下"],
    "初二": ["初一上", "初一下", "初二上", "初二下"],
    "初三": ["初一上", "初一下", "初二上", "初二下", "初三上", "初三下"],
}


def generate_students():
    students = []
    last_names = "张李王刘陈杨赵黄周吴徐孙马朱胡林郭何高罗郑梁谢宋唐许韩冯邓曹彭曾萧田董潘袁蔡蒋余于杜叶程苏魏吕丁"
    first_names = ["子涵", "梓涵", "浩宇", "一诺", "欣怡", "宇轩", "梓轩", "思远",
                   "雨桐", "明哲", "静怡", "博文", "雅婷", "俊杰", "思琪", "天佑",
                   "佳琪", "文博", "诗涵", "志远"]
    ages = {"初一": 13, "初二": 14, "初三": 15}

    for i in range(NUM_STUDENTS):
        grade = GRADES[i * len(GRADES) // NUM_STUDENTS]
        grade_idx = i * len(GRADES) // NUM_STUDENTS
        per_grade = NUM_STUDENTS // len(GRADES)
        class_no = (i - grade_idx * per_grade) // (per_grade // CLASSES_PER_GRADE) + 1
        class_no = min(class_no, CLASSES_PER_GRADE)
        class_name = f"{grade}{class_no}班"
        name = random.choice(last_names) + random.choice(first_names)
        age = ages[grade] + random.randint(-1, 1)
        students.append(Student(name=name, grade=grade, class_name=class_name, age=age))
    return students


def generate_scores(student_ids, students_by_id):
    records = []
    for sid in student_ids:
        student = students_by_id[sid]
        grade = student.grade
        for sem_name in GRADE_SEMESTERS[grade]:
            sem = next(s for s in SEMESTERS if s["name"] == sem_name)
            base_pct = np.random.normal(0.72, 0.10)

            for subject in sem["subjects"]:
                max_s = MAX_SCORES[subject]
                subj_bias = np.random.normal(0, 0.05)

                for week in EXAM_WEEKS:
                    exam_date = sem["start"] + timedelta(weeks=week)
                    if exam_date > TODAY:
                        continue

                    pct = base_pct + subj_bias + week * 0.004 + np.random.normal(0, 0.06)
                    pct = max(0.15, min(0.98, pct))
                    score = round(pct * max_s)

                    if week == 10:
                        exam_type = "期中"
                    elif week == 18:
                        exam_type = "期末"
                    else:
                        exam_type = "月考"

                    records.append(Score(
                        student_id=sid, subject=subject, score=score,
                        max_score=max_s, exam_type=exam_type,
                        date=exam_date, semester=sem_name,
                    ))
    return records


def generate_quality_scores(student_ids, students_by_id):
    """生成音体美信科目的多维评估（每科 5 维度，每学期一档评分，ABC+/− 九档等级）。"""
    records = []
    for sid in student_ids:
        student = students_by_id[sid]
        base_ability = np.random.normal(0.72, 0.10)
        for sem_name in GRADE_SEMESTERS[student.grade]:
            sem = next(s for s in SEMESTERS if s["name"] == sem_name)
            if sem["start"] > TODAY:
                continue
            for subject in QUALITY_SUBJECTS:
                subj_bias = np.random.normal(0, 0.06)
                for dim in QUALITY_DIMENSIONS[subject]:
                    dim_bias = np.random.normal(0, 0.08)
                    pct = base_ability + subj_bias + dim_bias + np.random.normal(0, 0.06)
                    pct = max(0.15, min(0.98, pct))
                    score = round(pct * 100, 1)
                    records.append(QualityScore(
                        student_id=sid, subject=subject, semester=sem_name,
                        dimension=dim, score=score, grade=grade_for(score),
                    ))
    return records


def generate_attendance(student_ids):
    records = []
    for sid in student_ids:
        absences = set(random.sample(range(DAYS), max(0, int(np.random.poisson(6)))))
        for d in range(DAYS):
            date = START_DATE + timedelta(days=d)
            if date.weekday() >= 5 or date > TODAY:
                continue
            present = d not in absences
            records.append(Attendance(student_id=sid, date=date, present=present))
    return records


def generate_emotions(student_ids):
    records = []
    emo_probs = {s: np.random.dirichlet([2, 6, 2]) for s in student_ids}
    for sid in student_ids:
        probs = emo_probs[sid]
        for week in range(26):
            date = START_DATE + timedelta(weeks=week, days=random.randint(0, 4))
            if date > TODAY:
                continue
            emo = np.random.choice([1, 2, 3], p=probs)
            records.append(EmotionLog(student_id=sid, date=date, emotion_level=int(emo)))
    return records


def generate_activities(student_ids, students_by_id):
    records = []
    types = ["体育", "社团", "阅读", "实践"]
    type_weights = [0.35, 0.20, 0.20, 0.25]
    for sid in student_ids:
        student = students_by_id[sid]
        grade = student.grade
        semesters = GRADE_SEMESTERS[grade]
        num = random.randint(8, 18)
        chosen = random.choices(types, weights=type_weights, k=num)
        for act_type in chosen:
            sem_name = random.choice(semesters)
            sem = next(s for s in SEMESTERS if s["name"] == sem_name)
            date = sem["start"] + timedelta(days=random.randint(0, 140))
            if date > TODAY:
                continue
            hours = round(max(0.3, np.random.exponential(1.5) + 0.5), 1)
            records.append(Activity(
                student_id=sid, type=act_type, hours=hours,
                date=date, semester=sem_name,
            ))
    return records


AWARD_TITLES = ["学科竞赛一等奖", "作文比赛二等奖", "科技节创新奖", "运动会冠军",
                "优秀志愿者", "艺术节金奖", "英语演讲比赛三等奖"]


def generate_awards(student_ids, students_by_id):
    records = []
    for sid in student_ids:
        student = students_by_id[sid]
        grade = student.grade
        semesters = GRADE_SEMESTERS[grade]
        num = random.randint(0, 3)
        for _ in range(num):
            sem_name = random.choice(semesters)
            sem = next(s for s in SEMESTERS if s["name"] == sem_name)
            date = sem["start"] + timedelta(days=random.randint(0, 140))
            if date > TODAY:
                continue
            records.append(Award(
                student_id=sid,
                title=random.choice(AWARD_TITLES),
                level=random.choice(AWARD_LEVELS),
                date=date,
            ))
    return records


def populate_subject_stats(db):
    """按 年级×班级×学科 预计算平均分并存入 subject_stats 表。"""
    from sqlalchemy import func
    stats = db.query(
        Student.grade, Student.class_name, Score.subject,
        func.avg(Score.score), func.max(Score.max_score), func.count(Score.id),
    ).join(Student, Student.id == Score.student_id).filter(
        Score.score != None, Score.max_score != None, Score.max_score > 0,
    ).group_by(Student.grade, Student.class_name, Score.subject).all()

    db.query(SubjectStats).delete()
    db.add_all([
        SubjectStats(grade=g, class_name=c, subject=s,
                     avg_score=round(avg, 1), max_score=max_s, count=n)
        for g, c, s, avg, max_s, n in stats
    ])
    db.commit()
    print(f"  Created {len(stats)} subject stats records")


def export_csv():
    import csv
    os.makedirs(os.path.join(os.path.dirname(__file__), "sample_data"), exist_ok=True)
    db = SessionLocal()
    attr_map = {
        Student: ["id", "name", "grade", "class_name", "age"],
        Score: ["id", "student_id", "subject", "score", "max_score", "exam_type", "date", "semester"],
        Attendance: ["id", "student_id", "date", "present"],
        EmotionLog: ["id", "student_id", "date", "emotion_level"],
        Activity: ["id", "student_id", "type", "hours", "date", "semester"],
        Award: ["id", "student_id", "title", "level", "date"],
        QualityScore: ["id", "student_id", "subject", "semester", "dimension", "score", "grade"],
        SubjectStats: ["id", "grade", "class_name", "subject", "avg_score", "max_score", "count"],
    }
    for table, filename in [
        (Student, "students.csv"),
        (Score, "scores.csv"),
        (Attendance, "attendance.csv"),
        (EmotionLog, "emotions.csv"),
        (Activity, "activities.csv"),
        (Award, "awards.csv"),
        (QualityScore, "quality_scores.csv"),
        (SubjectStats, "subject_stats.csv"),
    ]:
        rows = db.query(table).all()
        if rows:
            columns = [c.name for c in table.__table__.columns]
            attrs = attr_map[table]
            path = os.path.join(os.path.dirname(__file__), "sample_data", filename)
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(columns)
                for r in rows:
                    writer.writerow([getattr(r, a) for a in attrs])
            print(f"Exported {len(rows)} rows to {filename}")
    db.close()


def main():
    print("Initializing database...")
    from backend.models import Base, engine
    Base.metadata.drop_all(engine)
    init_db()
    db = SessionLocal()

    print("Generating students...")
    students = generate_students()
    db.add_all(students)
    db.commit()
    student_ids = [s.id for s in students]
    print(f"  Created {len(students)} students")

    class_sizes = {}
    for s in students:
        key = s.class_name
        class_sizes[key] = class_sizes.get(key, 0) + 1
    for cls, cnt in sorted(class_sizes.items()):
        print(f"    {cls}: {cnt}人")

    print("Generating scores...")
    students_dict = {s.id: s for s in students}
    scores = generate_scores(student_ids, students_dict)
    db.add_all(scores)
    db.commit()
    print(f"  Created {len(scores)} score records")

    print("Generating attendance...")
    attendance = generate_attendance(student_ids)
    db.add_all(attendance)
    db.commit()
    print(f"  Created {len(attendance)} attendance records")

    print("Generating emotion logs...")
    emotions = generate_emotions(student_ids)
    db.add_all(emotions)
    db.commit()
    print(f"  Created {len(emotions)} emotion records")

    print("Generating activities...")
    activities = generate_activities(student_ids, students_dict)
    db.add_all(activities)
    db.commit()
    print(f"  Created {len(activities)} activity records")

    print("Generating awards...")
    awards = generate_awards(student_ids, students_dict)
    db.add_all(awards)
    db.commit()
    print(f"  Created {len(awards)} award records")

    print("Generating quality scores...")
    quality = generate_quality_scores(student_ids, students_dict)
    db.add_all(quality)
    db.commit()
    print(f"  Created {len(quality)} quality score records")

    print("Generating subject stats...")
    populate_subject_stats(db)

    print("Seeding demo accounts...")
    seed_demo_accounts(db)

    db.close()
    export_csv()
    print("All data generated successfully!")


def seed_demo_accounts(db):
    """种子化演示账号（已通过审核，含班级/年级绑定）。"""
    demo_accounts = [
        {"username": "stu_demo", "password": "Student123", "role": "student",
         "name": "演示学生", "student_id": 1, "class_name": None, "grade": None},
        {"username": "teacher_demo", "password": "Teacher123", "role": "teacher",
         "name": "演示教师", "student_id": None, "class_name": "初一1班", "grade": "初一"},
        {"username": "grade_leader_demo", "password": "Leader123", "role": "grade_leader",
         "name": "演示年级组长", "student_id": None, "class_name": None, "grade": "初一"},
    ]
    existing = {u.username for u in db.query(User).all()}
    for acc in demo_accounts:
        if acc["username"] in existing:
            continue
        db.add(User(
            username=acc["username"],
            password_hash=_hash_password(acc["password"]),
            role=acc["role"],
            name=acc["name"],
            student_id=acc["student_id"],
            class_name=acc["class_name"],
            grade=acc["grade"],
            status="approved",
            created_at=datetime.now(),
        ))
    db.commit()
    print(f"  Demo accounts ready: {', '.join(a['username'] for a in demo_accounts)}")


if __name__ == "__main__":
    main()
