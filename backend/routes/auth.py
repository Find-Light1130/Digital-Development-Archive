from fastapi import APIRouter, Depends, Body, HTTPException, Header, Request
from sqlalchemy.orm import Session
import hashlib
import re
import secrets
import time
from datetime import datetime, timedelta
from backend.models import get_db, User, Student, Session as AuthSession

router = APIRouter(prefix="/api/auth", tags=["auth"])

ROLES = {"student", "teacher", "grade_leader", "admin"}
SESSION_DAYS = 7

LOGIN_MAX_FAILS = 5
LOGIN_WINDOW = 15 * 60
_login_failures: dict = {}
_last_prune = [0.0]


def _prune_login_failures():
    """周期性清理过期限流记录，避免字典无界增长。"""
    now = time.time()
    if now - _last_prune[0] < 60:
        return
    _last_prune[0] = now
    expired = [k for k, v in _login_failures.items() if now > v[1] + LOGIN_WINDOW]
    for k in expired:
        _login_failures.pop(k, None)


def _hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000).hex()
    return f"{salt}${digest}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split("$", 1)
    except ValueError:
        return False
    check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000).hex()
    return secrets.compare_digest(check, digest)


def _issue_session(db: Session, user: User) -> str:
    token = secrets.token_hex(32)
    db.add(AuthSession(
        user_id=user.id, token=token,
        created_at=datetime.now(),
        expires_at=datetime.now() + timedelta(days=SESSION_DAYS),
    ))
    db.commit()
    return token


def _user_payload(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "name": user.name,
        "student_id": user.student_id,
        "status": user.status,
        "class_name": user.class_name,
        "grade": user.grade,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def _validate_credentials(username, password):
    if not username or not str(username).strip():
        raise HTTPException(400, "用户名不能为空")
    username = str(username).strip()
    if len(username) > 32:
        raise HTTPException(400, "用户名长度不能超过 32 位")
    pwd = str(password)
    if not pwd or len(pwd) < 8:
        raise HTTPException(400, "密码长度不能少于 8 位")
    if len(pwd) > 128:
        raise HTTPException(400, "密码长度不能超过 128 位")
    if not re.search(r"[A-Za-z]", pwd) or not re.search(r"\d", pwd):
        raise HTTPException(400, "密码需同时包含字母和数字")


def _check_login_rate(request: Request, username: str):
    key = f"{request.client.host if request.client else 'unknown'}:{username}"
    fails = _login_failures.get(key)
    if fails and fails[0] >= LOGIN_MAX_FAILS and time.time() < fails[1] + LOGIN_WINDOW:
        raise HTTPException(429, "尝试次数过多，请稍后再试")


def _record_login_failure(request: Request, username: str):
    key = f"{request.client.host if request.client else 'unknown'}:{username}"
    now = time.time()
    _prune_login_failures()
    fails = _login_failures.get(key, [0, 0])
    if now > fails[1] + LOGIN_WINDOW:
        fails = [0, now]
    fails[0] += 1
    fails[1] = now
    _login_failures[key] = fails


def _reset_login_failures(request: Request, username: str):
    key = f"{request.client.host if request.client else 'unknown'}:{username}"
    _login_failures.pop(key, None)


@router.post("/register")
def register(
    username: str = Body(...), password: str = Body(...), role: str = Body(...),
    name: str = Body(None), student_id: int = Body(None),
    db: Session = Depends(get_db),
):
    username = str(username).strip()
    _validate_credentials(username, password)
    role = (role or "").strip().lower()
    if role not in ROLES:
        raise HTTPException(400, "账户类型必须为 student/teacher/grade_leader/admin")
    if role in ("grade_leader", "admin"):
        raise HTTPException(400, "管理员 / 年级组长账号仅支持由管理员创建")
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(409, "注册信息有误，请核对后重试")
    if role == "student":
        if student_id is None or int(student_id) <= 0:
            raise HTTPException(400, "学生账号需填写学生证号")
        student_id = int(student_id)
        if not db.query(Student).filter(Student.id == student_id).first():
            raise HTTPException(400, "注册信息有误，请核对后重试")
        if db.query(User).filter(User.role == "student", User.student_id == student_id).first():
            raise HTTPException(409, "注册信息有误，请核对后重试")
    else:
        student_id = None
    user = User(
        username=username,
        password_hash=_hash_password(str(password)),
        role=role,
        name=name or username,
        student_id=student_id,
        status="pending",
        created_at=datetime.now(),
    )
    db.add(user)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(409, "注册信息有误，请核对后重试")
    return {"detail": "注册成功，请等待管理员审核"}


@router.post("/login")
def login(username: str = Body(...), password: str = Body(...),
          request: Request = None, db: Session = Depends(get_db)):
    username = str(username).strip()
    _check_login_rate(request, username)
    user = db.query(User).filter(User.username == username).first()
    if not user or not _verify_password(str(password), user.password_hash):
        _record_login_failure(request, username)
        raise HTTPException(401, "用户名或密码错误")
    if user.status == "pending":
        raise HTTPException(403, "账号待审核，请等待管理员通过后登录")
    if user.status == "rejected":
        raise HTTPException(403, "账号审核未通过，无法登录")
    _reset_login_failures(request, username)
    token = _issue_session(db, user)
    return {"token": token, "user": _user_payload(user)}


def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)):
    """依赖：从 Authorization 解析当前登录用户（未登录/过期/未审核返回 None）。"""
    raw = (authorization or "").removeprefix("Bearer ").strip()
    if not raw:
        return None
    row = db.query(AuthSession).filter(AuthSession.token == raw).first()
    if not row:
        return None
    if row.expires_at and row.expires_at < datetime.now():
        db.delete(row)
        db.commit()
        return None
    user = db.query(User).filter(User.id == row.user_id).first()
    if not user or user.status != "approved":
        return None
    return user


@router.post("/logout")
def logout(authorization: str = Header(None), user=Depends(get_current_user),
           db: Session = Depends(get_db)):
    if not user:
        raise HTTPException(401, "未登录或会话已过期")
    raw = (authorization or "").removeprefix("Bearer ").strip()
    if raw:
        db.query(AuthSession).filter(
            AuthSession.token == raw, AuthSession.user_id == user.id,
        ).delete()
        db.commit()
    return {"detail": "已退出登录"}


@router.post("/change_password")
def change_password(old_password: str = Body(...), new_password: str = Body(...),
                    user=Depends(get_current_user), db: Session = Depends(get_db)):
    if not user:
        raise HTTPException(401, "未登录或会话已过期")
    if not _verify_password(str(old_password), user.password_hash):
        raise HTTPException(400, "原密码不正确")
    _validate_credentials(user.username, new_password)
    user.password_hash = _hash_password(str(new_password))
    db.query(AuthSession).filter(AuthSession.user_id == user.id).delete()
    db.commit()
    return {"detail": "密码修改成功，请重新登录"}


@router.get("/me")
def me(user=Depends(get_current_user)):
    if not user:
        raise HTTPException(401, "未登录或会话已过期")
    return _user_payload(user)


def _user_payload_admin(user: User) -> dict:
    """用户管理列表用（已含 class_name/grade 字段）。"""
    return _user_payload(user)


def user_scope(user: User) -> dict:
    """计算用户可见范围：student_ids / class_names / grades，None 表示不限制。"""
    if user.role == "student":
        return {"student_ids": [user.student_id], "class_names": None, "grades": None}
    if user.role == "teacher":
        return {"student_ids": None, "class_names": [user.class_name], "grades": None}
    if user.role == "grade_leader":
        return {"student_ids": None, "class_names": None, "grades": [user.grade]}
    return {"student_ids": None, "class_names": None, "grades": None}


def can_access_student(db: Session, user: User, student_id: int):
    """当前用户是否可查看指定学生。

    返回 True/False 表示是否越权；student_id 不存在时返回 None，
    由各路由自行返回 404（避免把"不存在"误判为 403）。
    """
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        return None
    scope = user_scope(user)
    if scope["student_ids"] is not None:
        return student.id in scope["student_ids"]
    if scope["class_names"] is not None:
        return student.class_name in scope["class_names"]
    if scope["grades"] is not None:
        return student.grade in scope["grades"]
    return True


def can_access_class(db: Session, user: User, class_name: str) -> bool:
    """当前用户是否可访问指定班级（仅校验范围，不含格式/存在性）。

    学生角色无权访问任何班级级数据。
    """
    if user.role == "student":
        return False
    scope = user_scope(user)
    if scope["class_names"] is not None:
        return class_name in scope["class_names"]
    if scope["grades"] is not None:
        return class_name.startswith(scope["grades"][0])
    return True
