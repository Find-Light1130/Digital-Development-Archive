from sqlalchemy import create_engine, Column, Integer, String, Float, Date, Boolean, ForeignKey, Index, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import event
from datetime import datetime
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "school.db")
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)

@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    grade = Column(String)
    class_name = Column("class", String, index=True)
    age = Column(Integer)


class Score(Base):
    __tablename__ = "scores"
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    subject = Column(String)
    score = Column(Float)
    max_score = Column(Float)
    exam_type = Column(String)
    date = Column(Date)
    semester = Column(String)
    __table_args__ = (
        Index("ix_scores_student_semester", "student_id", "semester"),
        Index("ix_scores_student_subject_exam_date", "student_id", "subject", "exam_type", "date"),
    )


class Attendance(Base):
    __tablename__ = "attendance"
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    date = Column(Date)
    present = Column(Boolean)


class EmotionLog(Base):
    __tablename__ = "emotions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    date = Column(Date)
    emotion_level = Column(Integer)
    tags = Column(String)


class Activity(Base):
    __tablename__ = "activities"
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    type = Column(String)
    hours = Column(Float)
    date = Column(Date)
    semester = Column(String)


class Award(Base):
    __tablename__ = "awards"
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    title = Column(String)
    level = Column(String)
    date = Column(Date)


class QualityScore(Base):
    __tablename__ = "quality_scores"
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    subject = Column(String)
    semester = Column(String)
    dimension = Column(String)
    score = Column(Float)
    grade = Column(String)
    __table_args__ = (Index("ix_quality_student_semester", "student_id", "semester"),)


class SubjectStats(Base):
    """预计算统计表：按 年级×班级×学科 存储平均分（后台生成时算好存好）。"""
    __tablename__ = "subject_stats"
    id = Column(Integer, primary_key=True, autoincrement=True)
    grade = Column(String, index=True)
    class_name = Column(String, index=True)
    subject = Column(String, index=True)
    avg_score = Column(Float)
    max_score = Column(Float)
    count = Column(Integer)
    __table_args__ = (Index("ix_subject_stats_class_subject", "grade", "class_name", "subject"),)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)  # student / teacher / grade_leader / admin
    name = Column(String)
    student_id = Column(Integer, nullable=True)
    class_name = Column(String, nullable=True)  # 教师绑定班级
    grade = Column(String, nullable=True)  # 年级组长绑定年级
    status = Column(String, default="pending")  # pending / approved / rejected
    created_at = Column(DateTime, default=datetime.now)


class Session(Base):
    __tablename__ = "sessions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.now)
    expires_at = Column(DateTime)


class ExamPlan(Base):
    """考试规划：管理员下达 → 年级组长进行考试 → 教师批阅自动录入成绩。

    status: planned(待进行) → conducted(已进行) → graded(已批阅)
    """
    __tablename__ = "exam_plans"
    id = Column(Integer, primary_key=True, autoincrement=True)
    exam_type = Column(String, nullable=False)  # 月考 / 期中 / 期末
    subject = Column(String, nullable=False)
    grade = Column(String, nullable=False)  # 初一 / 初二 / 初三
    exam_date = Column(Date, nullable=False)
    semester = Column(String, nullable=False)
    status = Column(String, default="planned", nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    conducted_at = Column(DateTime, nullable=True)
    conducted_by = Column(Integer, nullable=True)
    graded_at = Column(DateTime, nullable=True)
    graded_by = Column(Integer, nullable=True)
    __table_args__ = (Index("ix_exam_plans_grade_status", "grade", "status"),)


def init_db():
    Base.metadata.create_all(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
