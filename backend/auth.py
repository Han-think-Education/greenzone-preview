"""수업 시제품용 담당자 한 계정과 만료되는 서버 세션."""
import os
import secrets
import time

SESSIONS: dict[str, float] = {}
FAILED_LOGINS: dict[str, tuple[int, float]] = {}
SESSION_SECONDS = 6 * 60 * 60


def configured() -> bool:
    return len(os.getenv("ADMIN_PASSWORD", "")) >= 12


def sign_in(username: str, password: str, address: str) -> str | None:
    now = time.time()
    count, started = FAILED_LOGINS.get(address, (0, now))
    if now - started > 300:
        count, started = 0, now
    if count >= 10:
        return None
    expected_user = os.getenv("ADMIN_USERNAME", "admin")
    expected_password = os.getenv("ADMIN_PASSWORD", "")
    if not configured() or not secrets.compare_digest(username.encode(), expected_user.encode()) or not secrets.compare_digest(password.encode(), expected_password.encode()):
        FAILED_LOGINS[address] = (count + 1, started)
        return None
    FAILED_LOGINS.pop(address, None)
    for key in list(SESSIONS):
        if SESSIONS[key] < now:
            SESSIONS.pop(key, None)
    token = secrets.token_urlsafe(32)
    SESSIONS[token] = now + SESSION_SECONDS
    return token


def valid(token: str | None) -> bool:
    if not token:
        return False
    if SESSIONS.get(token, 0) <= time.time():
        SESSIONS.pop(token, None)
        return False
    return True


def sign_out(token: str | None) -> None:
    if token:
        SESSIONS.pop(token, None)
