"""共享领域常量：等级阈值、学期顺序与日期→学期推导。"""

from datetime import date

GRADE_LEVELS = [
    (93, "A+"), (87, "A"), (80, "A-"),
    (73, "B+"), (66, "B"), (59, "B-"),
    (52, "C+"), (45, "C"), (0, "C-"),
]


def grade_for(score: float) -> str:
    for threshold, grade in GRADE_LEVELS:
        if score >= threshold:
            return grade
    return "C-"


SEMESTER_ORDER = {"初一上": 1, "初一下": 2, "初二上": 3, "初二下": 4, "初三上": 5, "初三下": 6}

# 每学期开考科目（单一事实来源，供录入校验/网格列/生成脚本共用）。
SUBJECTS_BY_SEMESTER = {
    "初一上": ["语文", "数学", "英语", "生物", "历史", "道德与法治", "地理"],
    "初一下": ["语文", "数学", "英语", "生物", "历史", "道德与法治", "地理"],
    "初二上": ["语文", "数学", "英语", "物理", "历史", "道德与法治", "生物", "地理"],
    "初二下": ["语文", "数学", "英语", "物理", "历史", "道德与法治"],
    "初三上": ["语文", "数学", "英语", "物理", "化学", "历史", "道德与法治"],
    "初三下": ["语文", "数学", "英语", "物理", "化学", "历史", "道德与法治"],
}

# 各科满分（单一事实来源）。未收录科目默认 100 分。
MAX_SCORES = {
    "语文": 150, "数学": 150, "英语": 120, "物理": 100, "化学": 100,
    "生物": 100, "历史": 100, "道德与法治": 100, "地理": 100,
}

EXAM_TYPES = ("月考", "期中", "期末")

AWARD_LEVELS = ("校级", "区级", "市级", "省级")

QUALITY_SUBJECTS = ["音乐", "体育", "美术", "信息技术"]

# 音体美信各科评估维度（单一事实来源，供录入/生成/前端共用）。
QUALITY_DIMENSIONS = {
    "音乐": ["音乐素养", "演唱演奏", "节奏感知", "欣赏能力", "舞台表现"],
    "体育": ["体能素质", "运动技能", "协调能力", "团队协作", "体育精神"],
    "美术": ["艺术素养", "创作能力", "审美感知", "技法运用", "艺术表达"],
    "信息技术": ["信息素养", "编程能力", "操作技能", "创新应用", "数字素养"],
}


def semester_subjects(semester: str):
    """返回某学期开考科目列表；未知学期返回空列表。"""
    return SUBJECTS_BY_SEMESTER.get(semester, [])


def subject_max(subject: str) -> int:
    """返回科目满分，未知科目默认 100。"""
    return MAX_SCORES.get(subject, 100)


def semester_ranges():
    """返回全部学期起止区间（含首尾），供前端做日期/科目联动。"""
    return {sem: {"start": start.isoformat(), "end": end.isoformat()}
            for sem, (start, end) in _SEMESTER_RANGES.items()}

# 每学期起止（含首尾）。与 data/raw_data_gen.py 的 SEMESTERS 保持一致。
_SEMESTER_RANGES = {
    "初一上": (date(2025, 9, 1), date(2026, 2, 15)),
    "初一下": (date(2026, 2, 16), date(2026, 8, 31)),
    "初二上": (date(2026, 9, 1), date(2027, 2, 15)),
    "初二下": (date(2027, 2, 16), date(2027, 8, 31)),
    "初三上": (date(2027, 9, 1), date(2028, 2, 15)),
    "初三下": (date(2028, 2, 16), date(2028, 8, 31)),
}

_GRADE_FIRST_SEMESTER = {"初一": "初一上", "初二": "初二上", "初三": "初三上"}


def semester_from_date(grade: str, date: date) -> str:
    """按年级与日期推导学期。日期超出该年级学业跨度时返回 None。"""
    if not grade or not date:
        return None
    first = _GRADE_FIRST_SEMESTER.get(grade)
    if not first:
        return None
    idx = SEMESTER_ORDER[first] - 1
    order = sorted(SEMESTER_ORDER, key=lambda x: SEMESTER_ORDER[x])
    for sem in order[idx:]:
        start, end = _SEMESTER_RANGES[sem]
        if start <= date <= end:
            return sem
    return None
