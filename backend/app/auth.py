from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from collections import defaultdict, deque
from urllib.parse import parse_qs

from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.config import Settings


COOKIE_NAME = "prehospital_session"
SESSION_MAX_AGE = 7 * 24 * 60 * 60
LOGIN_WINDOW_SECONDS = 5 * 60
MAX_FAILED_LOGINS = 5
_failed_logins: dict[str, deque[float]] = defaultdict(deque)


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def create_session_token(secret: str, now: int | None = None) -> str:
    issued_at = int(time.time() if now is None else now)
    payload = _encode(json.dumps({"iat": issued_at, "exp": issued_at + SESSION_MAX_AGE}).encode())
    signature = _encode(hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{signature}"


def valid_session_token(token: str | None, secret: str, now: int | None = None) -> bool:
    if not token or not secret or "." not in token:
        return False
    try:
        payload, supplied_signature = token.split(".", 1)
        expected_signature = _encode(
            hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest()
        )
        if not secrets.compare_digest(supplied_signature, expected_signature):
            return False
        data = json.loads(_decode(payload))
        current_time = int(time.time() if now is None else now)
        return int(data["iat"]) <= current_time < int(data["exp"])
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        return False


def login_page(error: bool = False) -> HTMLResponse:
    message = '<p class="error">Fel lösenord. Försök igen.</p>' if error else ""
    return HTMLResponse(
        f"""<!doctype html>
<html lang="sv"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Logga in</title><style>
body{{font-family:system-ui,sans-serif;background:#f4f1eb;color:#172033;margin:0;display:grid;min-height:100vh;place-items:center}}
main{{background:#fff;border:1px solid #ddd8ce;border-radius:8px;box-sizing:border-box;max-width:420px;padding:28px;width:calc(100% - 32px)}}
h1{{font-family:Georgia,serif;font-size:1.8rem;margin:0 0 20px}}label{{display:grid;gap:7px}}
input{{border:1px solid #b9b2a7;border-radius:6px;font:inherit;padding:10px}}button{{background:#233348;border:0;border-radius:6px;color:#fff;font:inherit;margin-top:16px;padding:10px 16px;width:100%}}
.error{{background:#fff2ef;border:1px solid #d5a69a;border-radius:6px;color:#7b2f24;padding:9px}}
</style></head><body><main><h1>Prehospitala Avhandlingar</h1>{message}
<form method="post" action="/login"><label>Lösenord<input name="password" type="password" autocomplete="current-password" required></label><button type="submit">Logga in</button></form>
</main></body></html>"""
    )


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
    return forwarded or (request.client.host if request.client else "unknown")


def login_is_limited(ip: str, now: float | None = None) -> bool:
    current = time.time() if now is None else now
    attempts = _failed_logins[ip]
    while attempts and attempts[0] <= current - LOGIN_WINDOW_SECONDS:
        attempts.popleft()
    return len(attempts) >= MAX_FAILED_LOGINS


async def handle_login(request: Request, settings: Settings):
    ip = client_ip(request)
    if login_is_limited(ip):
        return HTMLResponse("För många försök. Vänta några minuter.", status_code=429)
    body = (await request.body()).decode("utf-8", errors="replace")
    password = parse_qs(body).get("password", [""])[0]
    if not secrets.compare_digest(password.encode("utf-8"), settings.site_password.encode("utf-8")):
        _failed_logins[ip].append(time.time())
        return login_page(error=True)

    _failed_logins.pop(ip, None)
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        COOKIE_NAME,
        create_session_token(settings.session_secret),
        httponly=True,
        secure=settings.production,
        samesite="lax",
        max_age=SESSION_MAX_AGE,
        path="/",
    )
    return response


class SiteAuthMiddleware:
    def __init__(self, app, settings: Settings):
        self.app = app
        self.settings = settings

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not self.settings.auth_enabled:
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in {"/login", "/api/health"}:
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        if valid_session_token(request.cookies.get(COOKIE_NAME), self.settings.session_secret):
            await self.app(scope, receive, send)
            return

        if path == "/logout":
            response = RedirectResponse("/login", status_code=303)
        elif path == "/api" or path.startswith("/api/"):
            response = JSONResponse({"detail": "Unauthorized"}, status_code=401)
        else:
            response = RedirectResponse("/login", status_code=303)
        await response(scope, receive, send)
