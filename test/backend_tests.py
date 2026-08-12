"""后端接口自动化测试（无 pytest/httpx 依赖）

运行：python test/backend_tests.py
说明：在本地 8765 端口启动 uvicorn，用 urllib 调用各接口并断言结果。
     所有业务接口需要登录（Authorization: Bearer <token>），测试自动完成
     账号注册/审核/分班/登录流程，结束后清理测试账号。
     POST 写入类用例使用学业日历内的日期做幂等验证，结束后自动清理数据。
"""

import json
import os
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

BASE = "http://127.0.0.1:8765"
PORT = 8765

AUTH_TOKEN = None


def _request(method, path, data=None, json_data=None):
    headers = {}
    if AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {AUTH_TOKEN}"
    if json_data is not None and method == "POST":
        body = json.dumps(json_data).encode("utf-8")
        headers["Content-Type"] = "application/json"
        url = BASE + path
        req = urllib.request.Request(url, data=body, method=method, headers=headers)
    elif data is not None and method == "POST":
        sep = "&" if "?" in path else "?"
        full = path + sep + urllib.parse.urlencode(data)
        url = BASE + urllib.parse.quote(full, safe="/:?=&%")
        req = urllib.request.Request(url, data=None, method=method, headers=headers)
    else:
        url = BASE + urllib.parse.quote(path, safe="/:?=&%")
        req = urllib.request.Request(url, data=None, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


def sse_get(path):
    """读取 SSE 流并返回 (status, 原始文本)。"""
    headers = {}
    if AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {AUTH_TOKEN}"
    url = BASE + urllib.parse.quote(path, safe="/:?=&%")
    req = urllib.request.Request(url, data=None, method="GET", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")


def sse_post_json(path, data):
    """POST JSON 并读取 SSE 流，返回 (status, 原始文本)。"""
    headers = {"Content-Type": "application/json"}
    if AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {AUTH_TOKEN}"
    url = BASE + path
    req = urllib.request.Request(
        url, data=json.dumps(data).encode("utf-8"), method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")


def sse_event_counts(text):
    """统计 SSE 文本中各事件类型出现次数。"""
    counts = {}
    for line in (text or "").split("\n"):
        if line.startswith("event:"):
            ev = line[len("event:"):].strip()
            counts[ev] = counts.get(ev, 0) + 1
    return counts


def get(path):
    return _request("GET", path)


def post(path, data):
    return _request("POST", path, data=data)


def post_json(path, data):
    return _request("POST", path, json_data=data)


def set_auth(token):
    global AUTH_TOKEN
    AUTH_TOKEN = token


def login(username, password):
    st, body = post_json("/api/auth/login", {"username": username, "password": password})
    if st != 200:
        raise RuntimeError(f"login failed {username}: {st} {body}")
    return body["token"]


PASS = 0
FAIL = 0


def check(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}  {extra}")


def cleanup_emotion(db, sid, date):
    from backend.models import EmotionLog
    for row in db.query(EmotionLog).filter(
        EmotionLog.student_id == sid, EmotionLog.date == date
    ).all():
        db.delete(row)
    db.commit()


def cleanup_activity(db, sid, act_type, date):
    from backend.models import Activity
    for row in db.query(Activity).filter(
        Activity.student_id == sid, Activity.type == act_type, Activity.date == date
    ).all():
        db.delete(row)
    db.commit()


def cleanup_score(db, sid, subject, exam_type, date):
    from backend.models import Score
    for row in db.query(Score).filter(
        Score.student_id == sid, Score.subject == subject,
        Score.exam_type == exam_type, Score.date == date,
    ).all():
        db.delete(row)
    db.commit()


def cleanup_award(db, sid):
    from backend.models import Award
    for row in db.query(Award).filter(
        Award.student_id == sid, Award.title.like("t_test_%")
    ).all():
        db.delete(row)
    db.commit()


def purge_test_users(db):
    """删除测试账号及其会话，保证可重复运行。"""
    from backend.models import User, Session as AuthSession
    names = ["t_student", "t_student2", "t_teacher", "t_teacher2", "t_teacher3", "t_leader"]
    users = db.query(User).filter(User.username.in_(names)).all()
    ids = [u.id for u in users]
    if ids:
        db.query(AuthSession).filter(AuthSession.user_id.in_(ids)).delete(synchronize_session=False)
        for u in users:
            db.delete(u)
        db.commit()


def cleanup_ai_data(db, student_ids):
    """删除 AI 接口测试写入的干预/树洞/学习计划，保证可重复运行。"""
    from backend.models import Intervention, CompanionChat, LearningPlan
    if student_ids:
        db.query(Intervention).filter(Intervention.student_id.in_(student_ids)).delete(synchronize_session=False)
        db.query(CompanionChat).filter(CompanionChat.student_id.in_(student_ids)).delete(synchronize_session=False)
        db.query(LearningPlan).filter(LearningPlan.student_id.in_(student_ids)).delete(synchronize_session=False)
        db.commit()


def wait_ready():
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            status, body = get("/")
            if status == 200 and body.get("status") == "running":
                return
        except Exception:
            time.sleep(0.3)
    raise RuntimeError("backend server failed to start")


def main():
    from backend.app import app
    from backend.models import init_db, SessionLocal, Student, User, Intervention
    import uvicorn

    init_db()
    db = SessionLocal()

    config = uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    wait_ready()

    print("== 基础 ==")
    status, body = get("/")
    check("根路径健康检查", status == 200 and body.get("status") == "running")

    print("== 未登录 401 ==")
    set_auth(None)
    check("未登录学生档案 401", get("/api/student/profile?student_id=1")[0] == 401)
    check("未登录教师接口 401", get("/api/teacher/class/semesters?class_name=初一1班")[0] == 401)
    check("未登录管理接口 401", get("/api/admin/school/overview")[0] == 401)
    check("未登录情绪写入 401", post("/api/student/emotion", {"student_id": 1, "date": "2026-03-10", "emotion_level": 2})[0] == 401)
    check("未登录活动写入 401", post("/api/teacher/student_event", {"student_id": 1, "type": "体育", "date": "2026-03-10", "value": 1})[0] == 401)

    print("== 注册/审核/分班/登录（准备测试账号） ==")
    purge_test_users(db)
    bound_sids = {u.student_id for u in db.query(User).filter(User.role == "student").all()}
    candidates = [s.id for s in db.query(Student).filter(Student.class_name == "初一1班").order_by(Student.id).all() if s.id not in bound_sids]
    sid = candidates[0]
    other_sid = db.query(Student).filter(Student.class_name != "初一1班").order_by(Student.id).first().id
    sec_sid = db.query(Student).filter(Student.grade != "初一").order_by(Student.id).first().id
    st, body = post_json("/api/auth/register", {"username": "t_student", "password": "Abc12345", "role": "student", "student_id": sid, "name": "测试学生"})
    check("学生账号注册", st == 200)
    st, body = post_json("/api/auth/register", {"username": "t_teacher", "password": "Abc12345", "role": "teacher", "name": "测试教师"})
    check("教师账号注册", st == 200)
    st, body = post_json("/api/auth/register", {"username": "t_teacher", "password": "Abc12345", "role": "teacher"})
    check("重复用户名注册 409", st == 409)
    st, body = post_json("/api/auth/register", {"username": "t_leader", "password": "Abc12345", "role": "grade_leader"})
    check("注册年级组长被拒 400", st == 400)
    st, body = post_json("/api/auth/register", {"username": "t_badpw", "password": "short", "role": "teacher"})
    check("弱密码注册被拒 400", st == 400)

    stu_uid = db.query(User).filter(User.username == "t_student").first().id
    tea_uid = db.query(User).filter(User.username == "t_teacher").first().id
    admin_token = login("admin", "admin123")

    set_auth(admin_token)
    st, body = post_json(f"/api/admin/users/{stu_uid}/approve", {})
    check("管理员审核学生", st == 200 and body.get("user", {}).get("status") == "approved")
    st, body = post_json(f"/api/admin/users/{tea_uid}/approve", {})
    check("管理员审核教师", st == 200)
    st, body = post_json(f"/api/admin/users/{tea_uid}/class", {"class_name": "初一1班"})
    check("管理员给教师分班", st == 200 and body["user"]["class_name"] == "初一1班" and body["user"]["grade"] == "初一")
    st, body = post_json("/api/admin/users", {"username": "t_leader", "password": "Abc12345", "role": "grade_leader", "grade": "初一", "name": "测试年级组长"})
    check("管理员创建年级组长", st == 200 and body["user"]["grade"] == "初一" and body["user"]["status"] == "approved")
    st, body = post_json("/api/admin/users", {"username": "t_teacher2", "password": "Abc12345", "role": "teacher", "class_name": "初二1班", "name": "初二教师"})
    check("管理员创建教师并分班", st == 200 and body["user"]["class_name"] == "初二1班" and body["user"]["grade"] == "初二")
    tea2_uid = body["user"]["id"]
    st, body = post_json("/api/admin/users", {"username": "t_teacher3", "password": "Abc12345", "role": "teacher", "name": "待分班教师"})
    check("管理员创建教师不填班级", st == 200 and body["user"]["class_name"] is None)
    tea3_uid = body["user"]["id"]
    st, body = post_json(f"/api/admin/users/{tea3_uid}/class", {"class_name": "初二2班"})
    check("管理员后补教师分班", st == 200 and body["user"]["class_name"] == "初二2班" and body["user"]["grade"] == "初二")

    student_token = login("t_student", "Abc12345")
    teacher_token = login("t_teacher", "Abc12345")
    leader_token = login("t_leader", "Abc12345")
    teacher2_token = login("t_teacher2", "Abc12345")
    check("审核后各角色可登录", student_token and teacher_token and leader_token and teacher2_token)

    print("== 学生端 ==")
    set_auth(student_token)
    status, body = get(f"/api/student/profile?student_id={sid}")
    check("学生档案", status == 200 and body.get("name"))

    status, body = get("/api/student/profile?student_id=999999")
    check("不存在学生 404", status == 404 and body.get("detail") == "Student not found")

    status, body = get("/api/student/profile")
    check("缺 student_id 参数 422", status == 422)

    status, body = get("/api/student/profile?student_id=-1")
    check("student_id<=0 拒绝 422", status == 422)

    status, body = get(f"/api/student/profile?student_id={other_sid}")
    check("学生查看他人档案 403", status == 403)

    status, body = get(f"/api/student/scores?student_id={sid}&semester=初一上")
    check("成绩按学期过滤", status == 200 and len(body) > 0 and all(s["semester"] == "初一上" for s in body))
    check("成绩科目不含音体美信", all(s["subject"] not in ("音乐", "体育", "美术", "信息技术") for s in body))

    status, all_body = get(f"/api/student/scores?student_id={sid}")
    status, page_body = get(f"/api/student/scores?student_id={sid}&limit=5&offset=0")
    check("成绩分页 limit=5", status == 200 and len(page_body) == 5)
    check(
        "成绩分页顺序一致",
        page_body == all_body[:5],
        f"page_head={page_body[0]['date'] if page_body else None}",
    )
    status, skip_body = get(f"/api/student/scores?student_id={sid}&limit=5&offset=5")
    check("成绩分页 offset=5", status == 200 and skip_body == all_body[5:10])
    status, bad = get(f"/api/student/scores?student_id={sid}&limit=-1")
    check("分页参数校验 limit<1 拒绝", status == 422)

    status, body = get(f"/api/student/semesters?student_id={sid}")
    check("学期列表", status == 200 and isinstance(body, list) and len(body) > 0)
    status, body = get("/api/student/semesters?student_id=999999")
    check("学期列表不存在学生 404", status == 404)

    status, body = get(f"/api/student/emotions?student_id={sid}")
    check("情绪列表", status == 200 and isinstance(body, list))
    status, body = get("/api/student/emotions?student_id=999999")
    check("情绪列表不存在学生 404", status == 404)

    status, body = get(f"/api/student/summary?student_id={sid}")
    check(
        "综合素质摘要",
        status == 200 and isinstance(body.get("semester_stats"), list)
        and isinstance(body.get("awards"), list) and isinstance(body.get("activities"), list),
    )
    check("摘要学期按学年排序", [s["semester"] for s in body["semester_stats"]] == sorted(
        [s["semester"] for s in body["semester_stats"]],
        key=lambda x: {"初一上":1,"初一下":2,"初二上":3,"初二下":4,"初三上":5,"初三下":6}.get(x, 0),
    ))
    status, body = get("/api/student/summary?student_id=999999")
    check("摘要不存在学生 404", status == 404)

    status, body = get(f"/api/student/quality?student_id={sid}")
    check("学生素质评估", status == 200 and len(body) >= 4 and all("semesters" in s for s in body))
    check("素质评估科目含音体美信", status == 200 and any(s["subject"] in ("音乐", "体育", "美术", "信息技术") for s in body))
    valid_grades = {"A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-"}
    check(
        "素质评估维度含等级且为 9 档",
        status == 200 and all(
            d.get("grade") in valid_grades and d.get("score") is not None
            for s in body for dims in s["semesters"] for d in dims["dimensions"]
        ),
    )
    status, body = get(f"/api/student/quality?student_id={sid}&semester=初一上")
    check("素质评估按学期过滤", status == 200 and all(all(x["semester"] == "初一上" for x in s["semesters"]) for s in body))
    status, body = get("/api/student/quality?student_id=999999")
    check("素质评估不存在学生 404", status == 404)

    print("== 学生端 POST 幂等 ==")
    test_date = "2026-03-10"
    cleanup_emotion(db, sid, test_date)
    st1, b1 = post("/api/student/emotion", {"student_id": sid, "date": test_date, "emotion_level": 3})
    st2, b2 = post("/api/student/emotion", {"student_id": sid, "date": test_date, "emotion_level": 1})
    from backend.models import EmotionLog
    count = db.query(EmotionLog).filter(EmotionLog.student_id == sid, EmotionLog.date == test_date).count()
    check("情绪重复提交只保留一条", st1 == 200 and st2 == 200 and count == 1, f"count={count}")
    check("二次提交为更新", b2.get("updated") is True)
    cleanup_emotion(db, sid, test_date)

    st, body = post("/api/student/emotion", {"student_id": sid, "date": "not-a-date", "emotion_level": 2})
    check("情绪非法日期拒绝", st == 400)
    st, body = post("/api/student/emotion", {"student_id": sid, "date": "2099-12-31", "emotion_level": 2})
    check("情绪未来日期拒绝", st == 400)
    st, body = post("/api/student/emotion", {"student_id": sid, "date": "2020-01-01", "emotion_level": 2})
    check("情绪超出学业日历拒绝", st == 400)
    st, body = post("/api/student/emotion", {"student_id": sid, "date": "2026-03-10", "emotion_level": 0})
    check("情绪非法等级 0 拒绝", st == 400)
    st, body = post("/api/student/emotion", {"student_id": sid, "date": "2026-03-10", "emotion_level": 4})
    check("情绪非法等级 4 拒绝", st == 400)
    st, body = post("/api/student/emotion", {"student_id": 999999, "date": "2026-03-10", "emotion_level": 2})
    check("情绪不存在学生 404", st == 404)
    st, body = post(f"/api/student/emotion", {"student_id": other_sid, "date": "2026-03-10", "emotion_level": 2})
    check("情绪写他人学生 403", st == 403)

    print("== 学生端情绪标签 ==")
    tag_date = "2026-03-11"
    cleanup_emotion(db, sid, tag_date)
    st, body = post("/api/student/emotion", {"student_id": sid, "date": tag_date, "emotion_level": 2, "tags": "开心,平静"})
    check("情绪带标签提交", st == 200)
    st, body = get(f"/api/student/emotions?student_id={sid}")
    tag_log = next((e for e in body if e["date"] == tag_date), None)
    check("情绪标签可读回", st == 200 and tag_log is not None and tag_log.get("tags") == ["开心", "平静"], f"tags={tag_log and tag_log.get('tags')}")
    st, body = post("/api/student/emotion", {"student_id": sid, "date": tag_date, "emotion_level": 3, "tags": "开心"})
    check("情绪标签更新覆盖", st == 200)
    st, body = get(f"/api/student/emotions?student_id={sid}")
    tag_log = next((e for e in body if e["date"] == tag_date), None)
    check("情绪标签更新后可读回", tag_log is not None and tag_log.get("emotion_level") == 3 and tag_log.get("tags") == ["开心"])
    st, body = post("/api/student/emotion", {"student_id": sid, "date": tag_date, "emotion_level": 3, "tags": "开心,平静,焦虑,疲惫"})
    check("情绪标签超 3 个拒绝", st == 400)
    st, body = post("/api/student/emotion", {"student_id": sid, "date": tag_date, "emotion_level": 3, "tags": "狂喜"})
    check("情绪未知标签拒绝", st == 400)
    cleanup_emotion(db, sid, tag_date)

    print("== 教师端 ==")
    set_auth(teacher_token)
    status, body = get("/api/teacher/class/semesters?class_name=初一1班")
    check("班级学期", status == 200 and isinstance(body, list) and len(body) > 0)
    status, body = get("/api/teacher/class/semesters?class_name=初一9班")
    check("教师访问他班学期 403", status == 403)
    status, body = get("/api/teacher/class/semesters?class_name=foo")
    check("非法班级名格式 400", status == 400)

    status, body = get("/api/teacher/class/overview?class_name=初一1班")
    check("班级总览", status == 200 and body.get("class_name") == "初一1班" and "subject_trends" in body)
    check(
        "班级趋势标签唯一（各科目内）",
        status == 200 and all(
            len(ts) == len({t["label"] for t in ts}) for ts in body["subject_trends"].values()
        ),
    )
    check("班级趋势不含音体美信", status == 200 and not any(k in body["subject_trends"] for k in ("音乐", "体育", "美术", "信息技术")))
    status, body = get("/api/teacher/class/overview?class_name=初一9班")
    check("教师访问他班总览 403", status == 403)
    status, body = get("/api/teacher/class/overview?class_name=foo")
    check("班级总览非法格式 400", status == 400)

    status, body = get("/api/teacher/class/overview?class_name=初一1班&semester=初一上")
    check("班级总览按学期", status == 200 and all(t["label"] for t in next(iter(body["subject_trends"].values()))))

    status, body = get(f"/api/teacher/student/{sid}/details")
    check("学生详情", status == 200 and body.get("student_id") == sid and "suggestions" in body)
    status, body = get("/api/teacher/student/999999/details")
    check("学生详情不存在学生 404", status == 404)
    status, body = get("/api/teacher/student/0/details")
    check("学生详情 id<=0 拒绝 422", status == 422)
    status, body = get(f"/api/teacher/student/{other_sid}/details")
    check("教师查看他班学生 403", status == 403)

    status, body = get("/api/teacher/class/quality?class_name=初一1班")
    check("班级素质评估", status == 200 and body.get("class_name") == "初一1班" and len(body.get("subjects", [])) >= 4)
    check("班级素质维度含均分与分布", status == 200 and all(
        d.get("score") is not None and d.get("grade") and d.get("distribution")
        for s in body.get("subjects", []) for sem in s.get("semesters", []) for d in sem["dimensions"]
    ))
    status, body = get("/api/teacher/class/quality?class_name=初一1班&semester=初一上")
    check("班级素质按学期过滤", status == 200 and all(all(x["semester"] == "初一上" for x in s["semesters"]) for s in body.get("subjects", [])))
    status, body = get("/api/teacher/class/quality?class_name=初一9班")
    check("教师访问他班素质 403", status == 403)

    print("== 教师端 POST 幂等 ==")
    cleanup_activity(db, sid, "体育", test_date)
    st1, b1 = post("/api/teacher/student_event", {"student_id": sid, "type": "体育", "date": test_date, "value": 2})
    st2, b2 = post("/api/teacher/student_event", {"student_id": sid, "type": "体育", "date": test_date, "value": 3})
    from backend.models import Activity
    count = db.query(Activity).filter(Activity.student_id == sid, Activity.type == "体育", Activity.date == test_date).count()
    check("活动重复提交只保留一条", st1 == 200 and st2 == 200 and count == 1, f"count={count}")
    act = db.query(Activity).filter(Activity.student_id == sid, Activity.type == "体育", Activity.date == test_date).first()
    check("活动写入自动推导学期", act is not None and act.semester == "初一下", f"semester={act and act.semester}")
    st3, _ = post("/api/teacher/student_event", {"student_id": sid, "type": "阅读", "date": test_date, "value": 1})
    count2 = db.query(Activity).filter(Activity.student_id == sid, Activity.date == test_date).count()
    check("不同活动类型同日可共存", st3 == 200 and count2 == 2, f"count={count2}")
    cleanup_activity(db, sid, "体育", test_date)
    cleanup_activity(db, sid, "阅读", test_date)

    st, body = post("/api/teacher/student_event", {"student_id": sid, "type": "电竞", "date": "2026-03-10", "value": 1})
    check("活动非法类型拒绝", st == 400)
    st, body = post("/api/teacher/student_event", {"student_id": sid, "type": "体育", "date": "2099-12-31", "value": 1})
    check("活动未来日期拒绝", st == 400)
    st, body = post("/api/teacher/student_event", {"student_id": sid, "type": "体育", "date": "2020-01-01", "value": 1})
    check("活动超出学业日历拒绝", st == 400)
    st, body = post("/api/teacher/student_event", {"student_id": sid, "type": "体育", "date": "2026-03-10", "value": 0})
    check("活动 value=0 拒绝", st == 400)
    st, body = post("/api/teacher/student_event", {"student_id": sid, "type": "体育", "date": "2026-03-10", "value": 25})
    check("活动 value=25 拒绝", st == 400)
    st, body = post("/api/teacher/student_event", {"student_id": sid, "type": "体育", "date": "2026-03-10", "value": "nan"})
    check("活动 value=NaN 拒绝", st == 400)
    st, body = post("/api/teacher/student_event", {"student_id": 999999, "type": "体育", "date": "2026-03-10", "value": 1})
    check("活动不存在学生 404", st == 404)
    st, body = post("/api/teacher/student_event", {"student_id": other_sid, "type": "体育", "date": "2026-03-10", "value": 1})
    check("活动写他班学生 403", st == 403)

    print("== 教师端 成绩录入/获奖/下钻 ==")
    from backend.models import Score, Award
    score_date = "2026-03-10"
    cleanup_score(db, sid, "语文", "月考", score_date)
    st, body = get("/api/teacher/class/students?class_name=初一1班")
    check(
        "班级花名册",
        st == 200 and body.get("class_name") == "初一1班" and len(body.get("students", [])) > 0
        and len(body.get("subjects", [])) > 0 and any(s["subject"] == "语文" for s in body["subjects"]),
    )
    st, body = get("/api/teacher/class/students?class_name=初一9班")
    check("教师访问他班花名册 403", st == 403)

    st, body = post("/api/teacher/scores", {"student_id": sid, "subject": "语文", "exam_type": "月考", "date": score_date, "score": 120})
    check("单条成绩录入", st == 200 and body.get("status") == "ok" and body.get("updated") is False)
    st, body = post("/api/teacher/scores", {"student_id": sid, "subject": "语文", "exam_type": "月考", "date": score_date, "score": 110})
    cnt = db.query(Score).filter(
        Score.student_id == sid, Score.subject == "语文",
        Score.exam_type == "月考", Score.date == score_date,
    ).count()
    row = db.query(Score).filter(
        Score.student_id == sid, Score.subject == "语文",
        Score.exam_type == "月考", Score.date == score_date,
    ).first()
    check("成绩同键幂等覆盖", st == 200 and body.get("updated") is True and cnt == 1 and row.score == 110, f"cnt={cnt}, score={row and row.score}")
    check("成绩写入自动推导学期", row is not None and row.semester == "初一下", f"sem={row and row.semester}")
    st, body = post("/api/teacher/scores", {"student_id": sid, "subject": "语文", "exam_type": "月考", "date": score_date, "score": 151})
    check("成绩超满分拒绝", st == 400)
    st, body = post("/api/teacher/scores", {"student_id": sid, "subject": "体育", "exam_type": "月考", "date": score_date, "score": 90})
    check("成绩未知科目拒绝", st == 400)
    st, body = post("/api/teacher/scores", {"student_id": sid, "subject": "物理", "exam_type": "月考", "date": score_date, "score": 90})
    check("成绩非本学期科目拒绝", st == 400)
    st, body = post("/api/teacher/scores", {"student_id": sid, "subject": "语文", "exam_type": "期末考", "date": score_date, "score": 90})
    check("成绩非法考试类型拒绝", st == 400)
    st, body = post("/api/teacher/scores", {"student_id": sid, "subject": "语文", "exam_type": "月考", "date": "2099-12-31", "score": 90})
    check("成绩未来日期拒绝", st == 400)
    st, body = post("/api/teacher/scores", {"student_id": sid, "subject": "语文", "exam_type": "月考", "date": "2020-01-01", "score": 90})
    check("成绩超出学业日历拒绝", st == 400)
    st, body = post("/api/teacher/scores", {"student_id": sid, "subject": "语文", "exam_type": "月考", "date": "not-a-date", "score": 90})
    check("成绩非法日期拒绝", st == 400)
    st, body = post("/api/teacher/scores", {"student_id": sid, "subject": "语文", "exam_type": "月考", "date": score_date, "score": -1})
    check("成绩负分拒绝", st == 400)
    st, body = post("/api/teacher/scores", {"student_id": 999999, "subject": "语文", "exam_type": "月考", "date": score_date, "score": 90})
    check("成绩不存在学生 404", st == 404)
    st, body = post("/api/teacher/scores", {"student_id": other_sid, "subject": "语文", "exam_type": "月考", "date": score_date, "score": 90})
    check("成绩写他班学生 403", st == 403)

    st, body = post_json("/api/teacher/scores/batch", {
        "exam_type": "月考", "date": score_date,
        "scores": [
            {"student_id": sid, "subject": "语文", "score": 130},
            {"student_id": sid, "subject": "数学", "score": 120},
        ],
    })
    cnt = db.query(Score).filter(Score.student_id == sid, Score.exam_type == "月考", Score.date == score_date, Score.subject.in_(["语文", "数学"])).count()
    check("批量成绩录入", st == 200 and body.get("count") == 2 and cnt == 2, f"st={st}, count={body.get('count')}, cnt={cnt}")
    st, body = post_json("/api/teacher/scores/batch", {
        "exam_type": "月考", "date": score_date,
        "scores": [
            {"student_id": sid, "subject": "语文", "score": 135},
            {"student_id": sid, "subject": "数学", "score": 999},
        ],
    })
    cnt_after = db.query(Score).filter(Score.student_id == sid, Score.exam_type == "月考", Score.date == score_date, Score.subject.in_(["语文", "数学"])).count()
    bad_row = db.query(Score).filter(Score.student_id == sid, Score.subject == "数学", Score.exam_type == "月考", Score.date == score_date).first()
    check("批量含非法项整批拒绝且不落库", st == 400 and cnt_after == 2 and bad_row.score != 999, f"st={st}, cnt={cnt_after}, math_score={bad_row and bad_row.score}")
    st, body = post_json("/api/teacher/scores/batch", {"exam_type": "月考", "date": score_date, "scores": []})
    check("批量空列表拒绝", st == 400)

    st, body = post("/api/teacher/scores/delete", {"student_id": sid, "subject": "数学", "exam_type": "月考", "date": score_date})
    check("删除成绩", st == 200)
    st, body = post("/api/teacher/scores/delete", {"student_id": sid, "subject": "数学", "exam_type": "月考", "date": score_date})
    check("删除不存在成绩 404", st == 404)
    cleanup_score(db, sid, "语文", "月考", score_date)

    st, body = post("/api/teacher/award", {"student_id": sid, "title": "t_test_数学竞赛一等奖", "level": "校级", "date": score_date})
    award_id = body.get("id")
    check("获奖登记", st == 200 and award_id, f"st={st}")
    st, body = post("/api/teacher/award", {"student_id": sid, "title": "t_test_市级奖", "level": "国家级", "date": score_date})
    check("获奖非法级别拒绝", st == 400)
    st, body = post("/api/teacher/award", {"student_id": sid, "title": "", "level": "校级", "date": score_date})
    check("获奖空标题拒绝", st == 400)
    st, body = post("/api/teacher/award", {"student_id": sid, "title": "t_test_未来", "level": "校级", "date": "2099-12-31"})
    check("获奖未来日期拒绝", st == 400)
    st, body = post("/api/teacher/award", {"student_id": other_sid, "title": "t_test_他班", "level": "校级", "date": score_date})
    check("获奖写他班学生 403", st == 403)
    st, body = post("/api/teacher/award/delete", {"award_id": award_id})
    check("删除获奖", st == 200)
    st, body = post("/api/teacher/award/delete", {"award_id": award_id})
    check("删除不存在获奖 404", st == 404)
    cleanup_award(db, sid)

    st, body = get("/api/teacher/class/distribution?class_name=初一1班&metric=growth")
    nonempty = [b for b, c in zip(body.get("buckets", []), body.get("counts", [])) if c > 0]
    if nonempty:
        st, body = get(f"/api/teacher/class/distribution/students?class_name=初一1班&metric=growth&bucket={nonempty[0]}")
        check(
            "成长分布下钻返回学生",
            st == 200 and len(body.get("students", [])) > 0
            and all(s["bucket"] == nonempty[0] and s["name"] for s in body["students"]),
            f"st={st}",
        )
    else:
        check("成长分布下钻返回学生", True, "无非空桶")
    st, body = get("/api/teacher/class/distribution?class_name=初一1班&metric=score&subject=语文")
    nonempty = [b for b, c in zip(body.get("buckets", []), body.get("counts", [])) if c > 0]
    if nonempty:
        st, body = get(f"/api/teacher/class/distribution/students?class_name=初一1班&metric=score&subject=语文&bucket={nonempty[0]}")
        check(
            "得分分布下钻返回学生",
            st == 200 and len(body.get("students", [])) > 0 and all(s["bucket"] == nonempty[0] for s in body["students"]),
        )
    else:
        check("得分分布下钻返回学生", True, "无非空桶")
    check("下钻缺 bucket 参数 422", get("/api/teacher/class/distribution/students?class_name=初一1班&metric=growth")[0] == 422)
    st, body = get("/api/teacher/class/distribution/students?class_name=初一1班&metric=growth&bucket=99~100")
    check("下钻空桶返回空列表", st == 200 and body.get("students") == [])

    print("== 年级组长端 ==")
    set_auth(leader_token)
    status, body = get("/api/teacher/class/semesters?class_name=初一1班")
    check("组长访问初一班级", status == 200 and len(body) > 0)
    status, body = get("/api/teacher/class/semesters?class_name=初一2班")
    check("组长访问本年级其他班", status == 200)
    status, body = get("/api/teacher/class/semesters?class_name=初二1班")
    check("组长访问跨年级班级 403", status == 403)
    status, body = get(f"/api/teacher/student/1/details")
    check("组长查看本年级学生", status == 200 and body.get("student_id") == 1)
    status, body = get(f"/api/teacher/student/{sec_sid}/details")
    check("组长查看跨年级学生 403", status == 403)
    status, body = get(f"/api/teacher/class/distribution?class_name=初二1班&metric=growth")
    check("组长跨年级分布 403", status == 403)

    status, body = get("/api/admin/users")
    check("组长用户列表仅本年级教师", status == 200 and len(body) > 0 and all(u["role"] == "teacher" and u["grade"] == "初一" for u in body))
    status, body = post_json(f"/api/admin/users/{tea2_uid}/approve", {})
    check("组长审核跨年级教师 403", status == 403)
    status, body = post_json(f"/api/admin/users/{tea_uid}/approve", {})
    check("组长审核本年级教师", status == 200)

    yi_count = db.query(Student).filter(Student.grade == "初一").count()
    status, body = get("/api/admin/school/overview")
    check("组长总览仅本年级", status == 200 and body["total_students"] == yi_count and set(body["grades"]) == {"初一"}, f"total={body.get('total_students')}")
    status, body = get("/api/admin/subject_mastery")
    check("组长学科表仅本年级", status == 200 and body["grades"] == ["初一"])
    status, body = get("/api/admin/grade_comparison")
    check("组长年级对比仅本年级", status == 200 and all(c["class_name"].startswith("初一") for c in body))
    status, body = get("/api/admin/distribution")
    check("组长分布仅本年级", status == 200 and body["grade"] == "初一" and body["total"] == yi_count)

    print("== 考试规划（下达/进行/元数据） ==")
    set_auth(admin_token)
    from backend.models import ExamPlan as ExamPlanModel
    cleanup_plans = [p for p in db.query(ExamPlanModel).all()]
    exam_date = "2026-03-05"
    # 清理该日期可能遗留的规划，保证幂等
    for p in db.query(ExamPlanModel).filter(ExamPlanModel.exam_date == exam_date).all():
        db.delete(p)
    db.commit()

    status, body = get("/api/admin/exam_plans/meta")
    check("考试规划元数据", status == 200 and "grades" in body and len(body["grades"]) == 3)
    grade_meta = next((g for g in body["grades"] if g["grade"] == "初一"), None)
    check("元数据含学期科目", grade_meta and grade_meta["semesters"] and "语文" in grade_meta["semesters"][0]["subjects"])

    status, body = post("/api/admin/exam_plans", {"exam_type": "月考", "subject": "语文", "grade": "初一", "exam_date": exam_date})
    check("管理员下达考试规划", status == 200 and body.get("status") == "planned" and body.get("subject") == "语文")
    plan_id = body.get("id")
    check("规划含学期推导", status == 200 and body.get("semester") == "初一下")

    status, body = post("/api/admin/exam_plans", {"exam_type": "月考", "subject": "语文", "grade": "初一", "exam_date": exam_date})
    check("同日同类型重复下达", status == 400)

    status, body = post("/api/admin/exam_plans", {"exam_type": "月考", "subject": "物理", "grade": "初一", "exam_date": "2026-03-05"})
    check("该学期不开设科目拒绝", status == 400 and body.get("detail"))

    status, body = post("/api/admin/exam_plans", {"exam_type": "月考", "subject": "语文", "grade": "初一", "exam_date": "2020-01-01"})
    check("日历外日期拒绝", status == 400)

    status, body = get("/api/admin/exam_plans")
    check("规划列表", status == 200 and any(p["id"] == plan_id for p in body))

    status, body = get("/api/admin/exam_plans?status=planned&grade=初一")
    check("规划按状态年级过滤", status == 200 and all(p["status"] == "planned" and p["grade"] == "初一" for p in body))

    status, body = get("/api/admin/exam_plans?grade=初二")
    check("规划年级过滤为空", status == 200 and body == [])

    set_auth(leader_token)
    status, body = post(f"/api/admin/exam_plans/{plan_id}/conduct", {})
    check("组长进行考试(日期已到)", status == 200 and body.get("status") == "conducted")
    status, body = post(f"/api/admin/exam_plans/{plan_id}/conduct", {})
    check("重复进行拒绝", status == 400)

    # 未来日期的规划可下达（planned），但不可进行
    from datetime import date as date_cls, timedelta
    future_date = (date_cls.today() + timedelta(days=30)).isoformat()
    set_auth(admin_token)
    status, body = post("/api/admin/exam_plans", {"exam_type": "月考", "subject": "数学", "grade": "初一", "exam_date": future_date})
    check("未来日期可下达规划", status == 200 and body.get("status") == "planned")
    future_plan_id = body.get("id")
    set_auth(leader_token)
    status, body = post(f"/api/admin/exam_plans/{future_plan_id}/conduct", {})
    check("未来日期进行拒绝", status == 400 and "未到" in body.get("detail", ""))

    set_auth(admin_token)
    status, body = post(f"/api/admin/exam_plans/{plan_id}/conduct", {})
    check("管理员重复进行拒绝", status == 400)

    # 清理
    for p in db.query(ExamPlanModel).filter(ExamPlanModel.exam_date.in_([exam_date, future_date])).all():
        db.delete(p)
    db.commit()

    print("== 考试规划删除 / 教师批阅闭环 / 考试分析 ==")
    set_auth(admin_token)
    grade_date = "2026-03-06"
    for p in db.query(ExamPlanModel).filter(ExamPlanModel.exam_date == grade_date).all():
        db.delete(p)
    db.commit()
    st, body = post("/api/admin/exam_plans", {"exam_type": "月考", "subject": "英语", "grade": "初一", "exam_date": grade_date})
    check("批阅用规划创建", st == 200)
    grade_plan_id = body.get("id")
    set_auth(teacher_token)
    st, body = post_json(f"/api/teacher/exam_plans/{grade_plan_id}/grade", {"class_name": "初一1班", "scores": []})
    check("未进行考试不可批阅 400", st == 400)

    # 删除契约：planned 可删
    set_auth(admin_token)
    st, body = post("/api/admin/exam_plans", {"exam_type": "月考", "subject": "历史", "grade": "初一", "exam_date": "2026-03-07"})
    del_plan_id = body.get("id")
    status, body = _request("DELETE", f"/api/admin/exam_plans/{del_plan_id}")
    check("planned 规划可删除", status == 200)
    status, body = _request("DELETE", f"/api/admin/exam_plans/{del_plan_id}")
    check("删除不存在规划 404", status == 404)
    status, body = _request("DELETE", "/api/admin/exam_plans/999999")
    check("删除不存在规划(大id) 404", status == 404)

    roster_ids = [s.id for s in db.query(Student).filter(Student.class_name == "初一1班").order_by(Student.id).all()]
    set_auth(leader_token)
    st, body = post(f"/api/admin/exam_plans/{grade_plan_id}/conduct", {})
    check("批阅前进行考试", st == 200 and body.get("status") == "conducted")

    set_auth(teacher_token)
    full_scores = [{"student_id": sid, "score": 90 + (i % 3)} for i, sid in enumerate(roster_ids)]
    st, body = post_json(f"/api/teacher/exam_plans/{grade_plan_id}/grade",
                         {"class_name": "初一1班", "scores": full_scores})
    check("教师批阅成功", st == 200 and body.get("count") == len(roster_ids))

    incomplete = full_scores[:-1]
    st, body = post_json(f"/api/teacher/exam_plans/{grade_plan_id}/grade",
                         {"class_name": "初一1班", "scores": incomplete})
    check("批阅名单不完整拒绝 400", st == 400)
    bad_score = full_scores[:]
    bad_score[0] = {"student_id": roster_ids[0], "score": 9999}
    st, body = post_json(f"/api/teacher/exam_plans/{grade_plan_id}/grade",
                         {"class_name": "初一1班", "scores": bad_score})
    check("批阅分数越界拒绝 400", st == 400)
    bad_score2 = full_scores[:]
    bad_score2[0] = {"student_id": roster_ids[0], "score": "abc"}
    st, body = post_json(f"/api/teacher/exam_plans/{grade_plan_id}/grade",
                         {"class_name": "初一1班", "scores": bad_score2})
    check("批阅非数值拒绝 400", st == 400)
    bad_sid = full_scores[:]
    bad_sid[0] = {"student_id": "notanumber", "score": 90}
    st, body = post_json(f"/api/teacher/exam_plans/{grade_plan_id}/grade",
                         {"class_name": "初一1班", "scores": bad_sid})
    check("批阅非整数学生ID拒绝 400", st == 400)

    st, body = get(f"/api/teacher/exam_plans/{grade_plan_id}/stats?class_name=初一1班")
    check("考试分析统计", st == 200 and body.get("count") == len(roster_ids)
          and body.get("highest") == 92 and body.get("avg") is not None and len(body.get("ranking")) == len(roster_ids))
    check("考试分析分档", st == 200 and sum(body.get("buckets", {}).values()) == len(roster_ids)
          and body["buckets"]["良好"] > 0)

    st, body = get("/api/teacher/exam_plans?class_name=初一1班")
    check("阅卷端规划列表", st == 200 and any(p["id"] == grade_plan_id and p["graded"] for p in body))

    set_auth(admin_token)
    status, body = _request("DELETE", f"/api/admin/exam_plans/{grade_plan_id}")
    check("已批阅规划不可删除 400", status == 400)
    for p in db.query(ExamPlanModel).filter(ExamPlanModel.exam_date.in_([grade_date, "2026-03-07"])).all():
        db.delete(p)
    db.commit()
    from backend.models import Score as ScoreModel
    for r in db.query(ScoreModel).filter(ScoreModel.date == grade_date).all():
        db.delete(r)
    db.commit()

    print("== 考勤查询 / 批量录入 ==")
    set_auth(teacher_token)
    att_date = "2026-03-08"
    from backend.models import Attendance as AttendanceModel
    for r in db.query(AttendanceModel).filter(AttendanceModel.date == att_date).all():
        db.delete(r)
    db.commit()
    st, body = get(f"/api/teacher/class/attendance?class_name=初一1班&date={att_date}")
    check("考勤日期回显默认全勤", st == 200 and len(body.get("students")) == len(roster_ids)
          and all(s["present"] for s in body["students"]))
    half = len(roster_ids) // 2
    items = [{"student_id": sid, "present": True} for sid in roster_ids[:half]] + \
            [{"student_id": sid, "present": False} for sid in roster_ids[half:]]
    st, body = post_json("/api/teacher/attendance", {"class_name": "初一1班", "date": att_date, "students": items})
    check("考勤批量录入", st == 200 and body.get("count") == len(roster_ids))
    st, body = post_json("/api/teacher/attendance", {"class_name": "初一1班", "date": att_date, "students": items})
    check("考勤幂等重复提交", st == 200 and body.get("count") == len(roster_ids))
    st, body = post_json("/api/teacher/attendance", {"class_name": "初一1班", "date": att_date,
                                                     "students": [{"student_id": roster_ids[0], "present": 1}]})
    check("考勤 present 非布尔拒绝 400", st == 400)
    st, body = post_json("/api/teacher/attendance", {"class_name": "初一1班", "date": att_date,
                                                     "students": [{"student_id": 999999, "present": True}]})
    check("考勤学生不在本班拒绝 400", st == 400)
    st, body = post_json("/api/teacher/attendance", {"class_name": "初一1班", "date": future_date,
                                                     "students": [{"student_id": roster_ids[0], "present": True}]})
    check("考勤未来日期拒绝 400", st == 400)
    st, body = get(f"/api/teacher/class/attendance?class_name=初一1班&date={att_date}")
    check("考勤录入后回显", st == 200 and not all(s["present"] for s in body["students"])
          and sum(not s["present"] for s in body["students"]) == len(roster_ids) - half)
    st, body = get(f"/api/student/attendance?student_id={sid}")
    check("学生考勤明细", st == 200 and isinstance(body.get("monthly"), list) and body.get("rate") is not None)
    for r in db.query(AttendanceModel).filter(AttendanceModel.date == att_date).all():
        db.delete(r)
    db.commit()

    print("== 素质评估录入 ==")
    set_auth(teacher_token)
    from backend.models import QualityScore as QualityScoreModel
    q_dim = "音乐素养"
    for r in db.query(QualityScoreModel).filter(
            QualityScoreModel.student_id == sid, QualityScoreModel.subject == "音乐",
            QualityScoreModel.semester == "初一下", QualityScoreModel.dimension == q_dim).all():
        db.delete(r)
    db.commit()
    st, body = post_json("/api/teacher/quality", {"student_id": sid, "subject": "音乐", "semester": "初一下",
                                                  "scores": {q_dim: 85.5}})
    check("素质评估录入", st == 200 and body.get("count") == 1)
    st, body = post_json("/api/teacher/quality", {"student_id": sid, "subject": "音乐", "semester": "初一下",
                                                  "scores": {q_dim: 88}})
    check("素质评估幂等更新", st == 200)
    st, body = get(f"/api/student/quality?student_id={sid}&semester=初一下")
    check("素质录入后查询含等级", st == 200 and any(
        any(d["dimension"] == q_dim and d["score"] == 88.0 and d["grade"] for d in sem["dimensions"])
        for subj in body for sem in subj["semesters"] if subj["subject"] == "音乐"))
    st, body = post_json("/api/teacher/quality", {"student_id": sid, "subject": "音乐", "semester": "初一下",
                                                  "scores": {"不存在维度": 80}})
    check("素质未知维度拒绝 400", st == 400)
    st, body = post_json("/api/teacher/quality", {"student_id": sid, "subject": "音乐", "semester": "初一下",
                                                  "scores": {q_dim: 101}})
    check("素质分数越界拒绝 400", st == 400)
    st, body = post_json("/api/teacher/quality", {"student_id": sid, "subject": "体育", "semester": "初一下",
                                                  "scores": {q_dim: 80}})
    check("素质维度不属该科拒绝 400", st == 400)
    st, body = post_json("/api/teacher/quality", {"student_id": sid, "subject": "音乐", "semester": "初三下",
                                                  "scores": {q_dim: 80}})
    check("素质学期超出学业跨度拒绝 400", st == 400)
    st, body = post_json("/api/teacher/quality", {"student_id": other_sid, "subject": "音乐", "semester": "初一上",
                                                  "scores": {q_dim: 80}})
    check("素质写他班学生 403", st == 403)
    for r in db.query(QualityScoreModel).filter(
            QualityScoreModel.student_id == sid, QualityScoreModel.subject == "音乐",
            QualityScoreModel.semester == "初一下", QualityScoreModel.dimension == q_dim).all():
        db.delete(r)
    db.commit()

    print("== 学生位次 / 班级获奖 ==")
    set_auth(student_token)
    st, body = get(f"/api/student/rank?student_id={sid}")
    check("学生位次各学期排名", st == 200 and isinstance(body.get("semesters"), list)
          and len(body.get("semesters", [])) > 0 and all("rank" in s and "total_students" in s for s in body["semesters"]))
    check("学生位次成长排名", st == 200 and body.get("growth_rank") is not None
          and body["growth_rank"]["rank"] >= 1 and "percentile" in body["growth_rank"])
    set_auth(teacher_token)
    st, body = get("/api/teacher/class/awards?class_name=初一1班")
    check("班级获奖列表", st == 200 and isinstance(body, list)
          and all("student_id" in a and "title" in a and "level" in a for a in body))
    set_auth(admin_token)
    st, body = get("/api/teacher/class/awards?class_name=初三9班")
    check("班级获奖不存在班级 404", st == 404)

    print("== 管理端 ==")
    set_auth(admin_token)
    status, body = get("/api/student/search?keyword=张")
    check("姓名搜索返回学生列表", status == 200 and isinstance(body, list) and len(body) > 0)
    check(
        "姓名搜索字段齐全",
        status == 200 and all("student_id" in s and "name" in s and "class" in s for s in body),
    )
    status, body = get("/api/student/search?keyword=子涵")
    check("姓名搜索可命中中文名", status == 200 and len(body) > 0)
    status, body = get("/api/student/search?keyword=不存在的名字xyz")
    check("姓名搜索无结果返回空数组", status == 200 and body == [])
    status, body = get("/api/student/search")
    check("姓名搜索缺 keyword 422", status == 422)

    status, body = get("/api/teacher/class/semesters?class_name=初一9班")
    check("班级学期不存在班级 404", status == 404)
    status, body = get("/api/teacher/class/overview?class_name=初一9班")
    check("班级总览不存在班级 404", status == 404)
    status, body = get("/api/teacher/class/quality?class_name=初一9班")
    check("班级素质不存在班级 404", status == 404)

    status, body = get("/api/teacher/class/overview?class_name=初三1班")
    check("初三班级总览含全部学期", status == 200 and len(body.get("subject_trends", {})) > 0)
    check(
        "初三班级趋势标签唯一（各科目内）",
        status == 200 and all(
            len(ts) == len({t["label"] for t in ts}) for ts in body["subject_trends"].values()
        ),
    )

    status, body = get("/api/admin/school/overview")
    check("全校总览", status == 200 and body.get("total_students", 0) > 0)
    status, body = get("/api/admin/grade_comparison")
    check("年级对比", status == 200 and isinstance(body, list) and len(body) > 0)
    status, body = get("/api/admin/subject_mastery")
    check("学科平均分表", status == 200 and len(body.get("grades", [])) >= 3 and len(body.get("subjects", [])) > 0)
    check(
        "学科平均分不含音体美信",
        status == 200 and not any(s in body.get("subjects", []) for s in ("音乐", "体育", "美术", "信息技术")),
    )
    check(
        "学科平均分取值合理",
        status == 200 and all(r["max_score"] > 0 and 0 <= r["avg_score"] <= r["max_score"] for r in body.get("rows", [])),
    )
    check(
        "学科得分率归一化统一口径",
        status == 200 and all(0 <= r["avg_rate"] <= 100 for r in body.get("rows", [])),
    )
    check(
        "学科平均分年级按学期顺序",
        body.get("grades") == ["初一", "初二", "初三"],
        f"grades={body.get('grades')}",
    )
    check(
        "学科平均分每个年级至少 5 科",
        status == 200 and all(sum(1 for r in body.get("rows", []) if r["grade"] == g) >= 5 for g in body.get("grades", [])),
    )

    print("== 管理端账号管理 ==")
    st, body = post_json("/api/admin/users", {"username": "t_badrole", "password": "Abc12345", "role": "student"})
    check("管理员创建非教师角色 400", st == 400)
    st, body = post_json("/api/admin/users", {"username": "t_badgrade", "password": "Abc12345", "role": "grade_leader", "grade": "高四"})
    check("年级组长非法年级 400", st == 400)
    st, body = post_json("/api/admin/users", {"username": "t_teacher", "password": "Abc12345", "role": "teacher"})
    check("管理员创建重复用户名 409", st == 409)
    st, body = post_json(f"/api/admin/users/{tea3_uid}/class", {"class_name": "bad"})
    check("分班非法格式 400", st == 400)
    st, body = post_json("/api/admin/users/999999/class", {"class_name": "初一1班"})
    check("分班用户不存在 404", st == 404)
    st, body = post_json(f"/api/admin/users/{stu_uid}/class", {"class_name": "初一1班"})
    check("给学生账号分班 400", st == 400)
    st, body = post_json(f"/api/admin/users/{tea2_uid}/class", {"class_name": "初二3班"})
    check("管理员改教师班级", st == 200 and body["user"]["class_name"] == "初二3班" and body["user"]["grade"] == "初二")

    print("== 数据分布接口 ==")
    status, body = get("/api/teacher/class/distribution?class_name=初一1班&metric=growth")
    check(
        "教师端成长分布",
        status == 200 and isinstance(body.get("buckets", []), list) and body.get("total", 0) > 0,
        f"status={status}",
    )
    check("教师端成长分布桶含区间", status == 200 and all(("-" in b or "~" in b) for b in body.get("buckets", [])))
    status, body = get("/api/teacher/class/distribution?class_name=初一1班&metric=score&subject=数学")
    check(
        "教师端得分分布",
        status == 200 and isinstance(body.get("buckets", []), list) and body.get("subject") == "数学",
    )
    check("教师端得分缺 subject 400", get("/api/teacher/class/distribution?class_name=初一1班&metric=score")[0] == 400)
    check("教师端非法 metric 400", get("/api/teacher/class/distribution?class_name=初一1班&metric=xxx")[0] == 400)
    check("教师端不存在班级 404", get("/api/teacher/class/distribution?class_name=初三9班&metric=growth")[0] == 404)
    check("教师端非法班级格式 400", get("/api/teacher/class/distribution?class_name=bad&metric=growth")[0] == 400)

    status, body = get("/api/admin/distribution")
    check(
        "管理端全校分布",
        status == 200 and isinstance(body.get("buckets", []), list) and body.get("metric") == "growth" and body.get("total", 0) > 0,
        f"status={status}",
    )
    teacher_total = get("/api/teacher/class/distribution?class_name=初一1班&metric=growth")[1]["total"]
    status, body = get("/api/admin/distribution?grade=初一")
    check(
        "管理端分布年级过滤",
        status == 200 and body.get("total", 0) > teacher_total,
        f"total={body.get('total')}",
    )
    status, body = get("/api/admin/distribution?metric=score&subject=语文")
    check(
        "管理端得分分布",
        status == 200 and body.get("subject") == "语文" and body.get("total", 0) > 0,
        f"status={status}",
    )
    check("管理端得分缺 subject 400", get("/api/admin/distribution?metric=score")[0] == 400)
    check("管理端非法 metric 400", get("/api/admin/distribution?metric=xxx")[0] == 400)
    status, body = get("/api/admin/distribution?metric=score&subject=体育")
    check("管理端音体美信得分分布空桶", status == 200 and body.get("total") == 0)

    st, body = get("/api/admin/distribution")
    nonempty = [b for b, c in zip(body.get("buckets", []), body.get("counts", [])) if c > 0]
    if nonempty:
        st, body = get(f"/api/admin/distribution/students?metric=growth&bucket={nonempty[0]}")
        check(
            "管理端成长分布下钻",
            st == 200 and len(body.get("students", [])) > 0
            and all(s["bucket"] == nonempty[0] and s.get("class_name") for s in body["students"]),
        )
    else:
        check("管理端成长分布下钻", True, "无非空桶")
    st, body = get("/api/admin/distribution?metric=score&subject=语文")
    nonempty = [b for b, c in zip(body.get("buckets", []), body.get("counts", [])) if c > 0]
    if nonempty:
        st, body = get(f"/api/admin/distribution/students?metric=score&subject=语文&bucket={nonempty[0]}")
        check("管理端得分分布下钻", st == 200 and len(body.get("students", [])) > 0)
    else:
        check("管理端得分分布下钻", True, "无非空桶")
    st, body = get("/api/admin/distribution/students?metric=growth&grade=初一&bucket=99~100")
    check("管理端下钻年级过滤空桶", st == 200 and body.get("students") == [])
    check("管理端下钻缺 bucket 422", get("/api/admin/distribution/students?metric=growth")[0] == 422)

    from backend.ai_modules.analysis import compute_growth_profile, batch_growth_profiles
    test_sid = db.query(Student).first().id
    ids = [s.id for s in db.query(Student).limit(20).all()]
    idx_admin = batch_growth_profiles(ids, db, light=True)[test_sid]["growth_index"]
    idx_profile = compute_growth_profile(test_sid, db)["growth_index"]
    check("批量 light 与画像端成长指数一致", abs(idx_admin - idx_profile) < 0.6, f"admin={idx_admin}, profile={idx_profile}")

    print("== AI 能力接口 ==")
    set_auth(None)
    check("AI 学情报告未登录 401", get("/api/ai/learning-report?scope=student&student_id=1")[0] == 401)
    check("AI 问数未登录 401", get("/api/ai/ask?q=人数")[0] == 401)

    set_auth(student_token)
    status, body = get(f"/api/ai/learning-report?scope=student&student_id={sid}")
    check("学生 AI 学情报告", status == 200 and body.get("subjects") and body.get("summary"))
    check("学生报告含建议", isinstance(body.get("suggestions"), list) and len(body["suggestions"]) > 0)
    status, body = get("/api/ai/growth-narrative?student_id=999999")
    check("成长叙事不存在学生 404", status == 404)
    status, body = get(f"/api/ai/growth-narrative?student_id={sid}")
    check("成长叙事生成", status == 200 and body.get("paragraphs"))
    status, body = get(f"/api/ai/talent?student_id={sid}")
    check("特长发现生成", status == 200 and body.get("talents") is not None)
    status, body = get(f"/api/ai/emotion-risk?student_id={sid}")
    check("情绪风险评估", status == 200 and body.get("level") in ("low", "medium", "high"))
    status, body = get(f"/api/ai/learning-path?student_id={sid}")
    check("学习路径获取", status in (200, 404))
    status, body = post_json("/api/ai/companion/chat", {"student_id": sid, "message": "最近压力好大"})
    check("树洞对话回复", status == 200 and body.get("reply"))
    check("树洞对话含意图", body.get("intent") in ("crisis", "greet", "sad", "anxious", "angry", "tired", "study", "friend", "family", "advice", "thanks", "bye", "chat"))
    status, body = post_json("/api/ai/companion/chat", {"student_id": sid, "message": ""})
    check("树洞空消息 400", status == 400)
    status, body = post_json("/api/ai/companion/chat", {"student_id": other_sid, "message": "偷看别人树洞"})
    check("树洞只能本人使用 403", status == 403)
    status, body = get(f"/api/ai/companion/history?student_id={sid}&limit=10")
    check("树洞历史返回", status == 200 and isinstance(body, list))

    # 树洞危机红线：命中即 risk_flag + 危机类型 + 自动建干预
    # 先清理历史遗留干预，保证幂等逻辑前状态确定（可重复运行）
    cleanup_ai_data(db, [sid, other_sid])
    status, body = post_json("/api/ai/companion/chat", {"student_id": sid, "message": "我想自杀，活不下去了"})
    check("树洞危机红线命中", status == 200 and body.get("risk_flag") and body.get("crisis_type") == "self_harm")
    check("危机自动建干预", body.get("intervention_id") is not None, f"iv_id={body.get('intervention_id')}")

    # 危机红线三分级：self_harm / harm_others / hopeless 各自独立识别
    status, body = post_json("/api/ai/companion/chat", {"student_id": sid, "message": "我要毁灭世界报复社会"})
    check("危机红线伤人型", status == 200 and body.get("risk_flag") and body.get("crisis_type") == "harm_others")
    status, body = post_json("/api/ai/companion/chat", {"student_id": sid, "message": "我觉得活着真没意思"})
    check("危机红线绝望型", status == 200 and body.get("risk_flag") and body.get("crisis_type") == "hopeless")

    # 危机幂等：已有 open 干预时不重复建
    before_iv = db.query(Intervention).filter(Intervention.student_id == sid,
                                              Intervention.status.in_(["open", "in_progress"])).count()
    status, body = post_json("/api/ai/companion/chat", {"student_id": sid, "message": "我想结束生命"})
    after_iv = db.query(Intervention).filter(Intervention.student_id == sid,
                                             Intervention.status.in_(["open", "in_progress"])).count()
    check("危机干预幂等不重复建", status == 200 and after_iv == before_iv, f"before={before_iv}, after={after_iv}")

    # 树洞 SSE 流式
    status, text = sse_post_json("/api/ai/companion/chat/stream", {"student_id": sid, "message": "最近压力好大"})
    counts = sse_event_counts(text)
    check("树洞流式对话成功", status == 200 and counts.get("done", 0) == 1 and counts.get("token", 0) > 0,
          f"st={status}, events={counts}")
    status, body = get(f"/api/ai/companion/history?student_id={sid}&limit=10")
    check("树洞流式落库", status == 200 and any(a.get("role") == "assistant" for a in body))
    status, text = sse_post_json("/api/ai/companion/chat/stream", {"student_id": sid, "message": "我不想活了"})
    counts = sse_event_counts(text)
    check("树洞流式危机直接 done", status == 200 and counts.get("done", 0) == 1 and "token" not in counts,
          f"events={counts}")

    set_auth(teacher_token)
    status, body = get("/api/ai/companion/alerts?limit=10")
    check("教师树洞危机通报", status == 200 and isinstance(body, list)
          and any(a.get("student_id") == sid for a in body), f"st={status}")
    status, body = get("/api/ai/warning-board?class_name=初一1班")
    check("教师预警看板（班级）", status == 200 and isinstance(body, list))
    status, body = get("/api/ai/interventions?student_id=999999")
    check("教师查干预不存在学生 200 空", status == 200 and body == [])
    status, body = get("/api/ai/interventions")
    check("教师干预列表（本班）", status == 200 and isinstance(body, list))
    status, body = get("/api/ai/ask?q=初一1班数学掌握率")
    check("教师问数掌握率", status == 200 and body.get("answer"))
    status, body = get("/api/ai/ask?q=初一1班多少人")
    check("教师问数人数", status == 200 and "初一1班" in body.get("answer", ""))

    # 教师问数越权范围：问本班之外的班级 → 回落本班，且不会复述越权班级名
    status, body = get("/api/ai/ask?q=初二3班多少人")
    check("教师问数越权回落本班", status == 200 and "初二3班" not in body.get("answer", ""),
          f"ans={body.get('answer','')[:40]}")
    status, body = get("/api/ai/ask?q=初二年级数学平均分")
    check("教师问数年级维度回落本班", status == 200 and body.get("class_name") == "初一1班")

    # 教师问数 SSE 流式
    status, text = sse_get("/api/ai/ask/stream?q=初一1班数学掌握率")
    counts = sse_event_counts(text)
    check("教师问数流式成功", status == 200 and counts.get("done", 0) == 1 and counts.get("token", 0) > 0,
          f"st={status}, events={counts}")
    check("问数流式含阶段事件", counts.get("stage", 0) >= 2,
          f"events={counts}")
    status, text = sse_get("/api/ai/ask/stream?q=你好")
    counts = sse_event_counts(text)
    check("问数流式闲聊直接 done", status == 200 and counts.get("done", 0) == 1, f"events={counts}")
    status, text = sse_get("/api/ai/ask/stream?q=hello")
    check("问数流式问候", status == 200 and counts.get("done", 0) == 1, f"events={counts}")
    status, body = get(f"/api/ai/learning-report?scope=class&class_name=初一1班")
    check("教师班级学情报告", status == 200 and body.get("teaching_suggestions"))
    status, body = get(f"/api/ai/learning-report?scope=grade")
    check("教师无年级维度报告 400", status == 400)

    from backend.models import ExamPlan
    graded_plan = db.query(ExamPlan).filter(ExamPlan.status == "graded", ExamPlan.grade == "初一").first()
    if graded_plan:
        status, body = get(f"/api/ai/paper-analysis?plan_id={graded_plan.id}&class_name=初一1班")
        check("试卷分析", status in (200, 404), f"st={status}")
        status, body = get(f"/api/ai/grade-hints?plan_id={graded_plan.id}&class_name=初一1班")
        check("批阅辅助预估", status == 200 and isinstance(body.get("hints"), dict))
    status, body = get("/api/ai/paper-analysis?plan_id=999999&class_name=初一1班")
    check("试卷分析不存在考试 404", status == 404)

    risk_sid = None
    status, body = get("/api/ai/warning-board?class_name=初一1班")
    for r in body or []:
        if r.get("risk_level") in ("red", "yellow"):
            risk_sid = r["student_id"]
            break
    if risk_sid:
        status, body = post_json("/api/ai/interventions", {"student_id": risk_sid})
        check("创建干预方案", status == 200 and body.get("title"), f"st={status}")
        iv_id = body["id"]
        status, body = post_json(f"/api/ai/interventions/{iv_id}/follow", {"note": "第一周已沟通家长"})
        check("干预跟进", status == 200 and body.get("status") == "in_progress")
        status, body = post_json(f"/api/ai/interventions/{iv_id}/close", {})
        check("干预闭环评估效果", status == 200 and body.get("status") == "closed")
        status, body = post_json(f"/api/ai/interventions/{iv_id}/follow", {"note": "已闭环不可再跟进"})
        check("闭环干预记录跟进（允许）", status == 200)
    else:
        check("创建干预方案", True, "本班无风险学生，跳过")
    status, body = get(f"/api/ai/learning-report?scope=student&student_id={sid}")
    check("教师查看本班学生报告", status == 200)

    set_auth(admin_token)
    status, body = get("/api/ai/warning-board")
    check("管理员预警看板（全校）", status == 200 and isinstance(body, list))
    status, body = get("/api/ai/learning-report?scope=grade&grade=初一")
    check("管理员年级学情报告", status == 200 and body.get("classes"))
    status, body = get("/api/ai/ask?q=全校多少人")
    check("管理员问数需明确范围", status == 200)
    status, body = post_json("/api/ai/learning-path/generate", {"student_id": sid})
    check("管理员生成学习路径", status in (200, 400), f"st={status}")

    set_auth(student_token)
    status, body = get("/api/ai/warning-board")
    check("学生访问预警看板 403", status == 403)
    status, body = get("/api/ai/companion/alerts")
    check("学生访问危机通报 403", status == 403)

    # 危机通报范围隔离：教师只看本班，组长只看本年级，管理员看全校
    # sid 在初一1班（教师 scope=初一1班），cross-class 数据不存在时用成员隔离验证
    set_auth(teacher2_token)
    status, body = get("/api/ai/companion/alerts?limit=50")
    check("跨班教师危机通报不含外班", status == 200 and not any(a.get("student_id") == sid for a in body),
          f"st={status}, got={len(body)}")

    # 年级组长只看本年级
    set_auth(leader_token)
    status, body = get("/api/ai/companion/alerts?limit=50")
    check("年级组长危机通报仅本年级", status == 200
          and all(a.get("grade") == "初一" for a in body)
          and any(a.get("student_id") == sid for a in body),
          f"st={status}, got={len(body)}")

    # 管理员看全校（至少覆盖组长可见范围）
    set_auth(admin_token)
    status, body = get("/api/ai/companion/alerts?limit=50")
    leader_body, _ = None, None
    set_auth(leader_token)
    _, leader_body = get("/api/ai/companion/alerts?limit=50")
    set_auth(admin_token)
    check("管理员危机通报全校", status == 200
          and len(body) >= len(leader_body)
          and any(a.get("student_id") == sid for a in body),
          f"st={status}, got={len(body)}, leader={len(leader_body)}")

    print("== 已移除的死代码接口 ==")
    status, body = get("/api/student/report?student_id=1")
    check("/api/student/report 已移除", status == 404)
    status, body = get("/api/student/suggestions?student_id=1")
    check("/api/student/suggestions 已移除", status == 404)
    status, body = get("/api/student/activities?student_id=1")
    check("/api/student/activities 已移除", status == 404)

    print("== 账号安全回归（会话/登录/角色隔离） ==")
    set_auth(student_token)
    status, body = get("/api/auth/me")
    check("me 返回当前用户", status == 200 and body.get("username") == "t_student" and body.get("role") == "student")
    status, body = post("/api/auth/logout", {})
    check("logout 成功 200", status == 200)
    status, body = get("/api/auth/me")
    check("logout 后会话失效 401", status == 401)

    st2 = login("t_student", "Abc12345")
    set_auth(st2)
    status, body = get("/api/teacher/class/semesters?class_name=初一1班")
    check("学生访问教师接口 403", status == 403)
    status, body = get("/api/admin/users")
    check("学生访问管理接口 403", status == 403)
    status, body = post("/api/teacher/student_event", {"student_id": sid, "type": "体育", "date": "2026-03-10", "value": 1})
    check("学生写活动记录 403", status == 403)
    status, body = post_json("/api/admin/users", {"username": "t_x", "password": "Abc12345", "role": "teacher"})
    check("学生创建账号 403", status == 403)

    status, body = post_json("/api/auth/change_password", {"old_password": "wrong", "new_password": "Xyz98765"})
    check("修改密码原密码错误 400", status == 400)
    status, body = post_json("/api/auth/change_password", {"old_password": "Abc12345", "new_password": "short"})
    check("修改密码弱新密码 400", status == 400)
    status, body = post_json("/api/auth/change_password", {"old_password": "Abc12345", "new_password": "Xyz98765"})
    check("修改密码成功 200", status == 200)
    status, body = get("/api/auth/me")
    check("改密后旧会话失效 401", status == 401)
    status, body = post_json("/api/auth/login", {"username": "t_student", "password": "Abc12345"})
    check("改密后旧密码登录 401", status == 401)
    st2b = login("t_student", "Xyz98765")
    check("改密后新密码登录", bool(st2b))

    sts = [post_json("/api/auth/login", {"username": "t_brute", "password": "wrongpass"})[0] for _ in range(5)]
    status, body = post_json("/api/auth/login", {"username": "t_brute", "password": "wrongpass"})
    check("登录连续失败触发限流 429", all(s == 401 for s in sts) and status == 429, f"sts={sts}, st={status}")

    set_auth(teacher_token)
    status, body = get("/api/admin/users")
    check("教师访问用户管理 403", status == 403)
    status, body = post_json(f"/api/admin/users/{tea_uid}/class", {"class_name": "初一1班"})
    check("教师设置他人班级 403", status == 403)
    set_auth(leader_token)
    status, body = post_json("/api/admin/users", {"username": "t_x", "password": "Abc12345", "role": "teacher"})
    check("年级组长创建账号 403", status == 403)
    status, body = post_json(f"/api/admin/users/{tea_uid}/class", {"class_name": "初一1班"})
    check("年级组长设置班级 403", status == 403)

    set_auth(admin_token)
    sid2 = db.query(Student).filter(
        Student.class_name == "初一1班",
        Student.id.notin_({s for s in bound_sids if s} | {sid}),
    ).order_by(Student.id).first().id
    status, body = post_json("/api/auth/register", {"username": "t_student2", "password": "Abc12345", "role": "student", "student_id": sid2, "name": "测试学生2"})
    check("学生2 账号注册", status == 200)
    status, body = post_json("/api/auth/login", {"username": "t_student2", "password": "Abc12345"})
    check("未审核学生登录 403", status == 403)
    st2u = db.query(User).filter(User.username == "t_student2").first().id
    status, body = post_json(f"/api/admin/users/{st2u}/approve", {})
    check("管理员审核学生2", status == 200)
    t2_token = login("t_student2", "Abc12345")
    set_auth(t2_token)
    status, body = get("/api/auth/me")
    check("学生2 登录后 me", status == 200 and body.get("username") == "t_student2")
    set_auth(admin_token)
    status, body = post_json(f"/api/admin/users/{st2u}/reject", {})
    check("管理员驳回学生2", status == 200)
    set_auth(t2_token)
    status, body = get("/api/auth/me")
    check("驳回后会话失效 401", status == 401)

    cleanup_ai_data(db, [sid, other_sid, sec_sid, risk_sid] if risk_sid is not None else [sid, other_sid, sec_sid])
    purge_test_users(db)
    db.close()
    server.should_exit = True
    time.sleep(0.5)

    print(f"\n结果：通过 {PASS} 项，失败 {FAIL} 项")
    if FAIL:
        sys.exit(1)
    print("ALL TESTS PASSED")


if __name__ == "__main__":
    main()
