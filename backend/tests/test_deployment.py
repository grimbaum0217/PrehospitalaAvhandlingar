import asyncio
import tempfile
import unittest
from pathlib import Path

from fastapi import Request
from fastapi import FastAPI

from app.auth import (
    COOKIE_NAME,
    SiteAuthMiddleware,
    create_session_token,
    handle_login,
    valid_session_token,
)
from app.config import Settings, load_settings
from app.database import engine, initialize_database
from app.main import create_application


async def call_asgi(app, path, cookie=None, method="GET", body=b""):
    messages = []
    headers = []
    if cookie:
        headers.append((b"cookie", f"{COOKIE_NAME}={cookie}".encode()))
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": headers,
        "client": ("127.0.0.1", 1234),
        "server": ("test", 80),
    }

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message):
        messages.append(message)

    await app(scope, receive, send)
    return messages


async def ok_app(scope, receive, send):
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b"ok"})


def response_status(messages):
    return next(message["status"] for message in messages if message["type"] == "http.response.start")


def response_headers(messages):
    headers = next(message["headers"] for message in messages if message["type"] == "http.response.start")
    return {key.decode().lower(): value.decode() for key, value in headers}


class DeploymentTests(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        engine.dispose()

    def test_database_seed_is_copied_once_and_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            seed = root / "seed.db"
            target = root / "volume" / "app.db"
            seed.write_bytes(b"seed")

            initialize_database(target, seed)
            self.assertEqual(target.read_bytes(), b"seed")

            target.write_bytes(b"persistent-data")
            seed.write_bytes(b"new-seed")
            initialize_database(target, seed)
            self.assertEqual(target.read_bytes(), b"persistent-data")

    def test_production_fails_closed_for_missing_auth_configuration(self):
        invalid_environments = [
            {"APP_ENV": "production", "AUTH_ENABLED": "false"},
            {"APP_ENV": "production", "AUTH_ENABLED": "true", "SESSION_SECRET": "secret"},
            {"APP_ENV": "production", "AUTH_ENABLED": "true", "SITE_PASSWORD": "password"},
        ]
        for environment in invalid_environments:
            with self.subTest(environment=environment), self.assertRaises(RuntimeError):
                load_settings(environment)

    def test_development_defaults_to_auth_disabled(self):
        settings = load_settings({})
        self.assertEqual(settings.app_env, "development")
        self.assertFalse(settings.auth_enabled)

    def test_session_is_signed_expires_and_rejects_tampering(self):
        token = create_session_token("session-secret", now=100)
        self.assertTrue(valid_session_token(token, "session-secret", now=101))
        self.assertFalse(valid_session_token(token + "x", "session-secret", now=101))
        self.assertFalse(valid_session_token(token, "wrong-secret", now=101))
        self.assertFalse(valid_session_token(token, "session-secret", now=100 + 8 * 24 * 60 * 60))

    def test_auth_middleware_redirects_frontend_but_returns_json_401_for_api(self):
        settings = Settings("test", True, "password", "session-secret")
        app = SiteAuthMiddleware(ok_app, settings)

        frontend = asyncio.run(call_asgi(app, "/"))
        api = asyncio.run(call_asgi(app, "/api/theses"))
        health = asyncio.run(call_asgi(app, "/api/health"))
        token = create_session_token(settings.session_secret)
        authenticated = asyncio.run(call_asgi(app, "/api/theses", token))

        self.assertEqual(response_status(frontend), 303)
        self.assertEqual(response_status(api), 401)
        self.assertIn(b'"Unauthorized"', api[-1]["body"])
        self.assertEqual(response_status(health), 200)
        self.assertEqual(response_status(authenticated), 200)

    def test_auth_disabled_allows_frontend_and_api(self):
        app = SiteAuthMiddleware(ok_app, Settings("test", False, "", ""))
        self.assertEqual(response_status(asyncio.run(call_asgi(app, "/"))), 200)
        self.assertEqual(response_status(asyncio.run(call_asgi(app, "/api/theses"))), 200)

    def test_login_sets_http_only_cookie_and_secure_cookie_in_production(self):
        async def login(settings):
            body = b"password=test-password"
            sent = False

            async def receive():
                nonlocal sent
                if sent:
                    return {"type": "http.disconnect"}
                sent = True
                return {"type": "http.request", "body": body, "more_body": False}

            request = Request(
                {
                    "type": "http",
                    "method": "POST",
                    "path": "/login",
                    "headers": [(b"content-type", b"application/x-www-form-urlencoded")],
                    "client": ("127.0.0.1", 1234),
                    "scheme": "http",
                    "server": ("test", 80),
                    "query_string": b"",
                },
                receive=receive,
            )
            return await handle_login(request, settings)

        response = asyncio.run(login(Settings("production", True, "test-password", "secret")))
        cookie = response.headers["set-cookie"]
        self.assertIn("HttpOnly", cookie)
        self.assertIn("Secure", cookie)
        self.assertNotIn("test-password", cookie)

    def test_wrong_password_does_not_create_session(self):
        async def attempt():
            async def receive():
                return {"type": "http.request", "body": b"password=wrong", "more_body": False}

            request = Request(
                {
                    "type": "http",
                    "method": "POST",
                    "path": "/login",
                    "headers": [],
                    "client": ("192.0.2.10", 1234),
                    "scheme": "http",
                    "server": ("test", 80),
                    "query_string": b"",
                },
                receive=receive,
            )
            return await handle_login(request, Settings("test", True, "correct", "secret"))

        response = asyncio.run(attempt())
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("set-cookie", response.headers)
        self.assertNotIn("wrong", response.body.decode())

    def test_complete_login_api_asset_and_logout_flow(self):
        with tempfile.TemporaryDirectory() as directory:
            static_dir = Path(directory)
            (static_dir / "assets").mkdir()
            (static_dir / "index.html").write_text("<html>app</html>")
            (static_dir / "assets" / "app.js").write_text("console.log('app')")
            api = FastAPI()

            @api.get("/health")
            def health():
                return {"status": "ok"}

            @api.get("/data")
            def data():
                return {"value": 1}

            app = create_application(api, Settings("test", True, "test-password", "session-secret"), static_dir)

            self.assertEqual(response_status(asyncio.run(call_asgi(app, "/"))), 303)
            self.assertEqual(response_status(asyncio.run(call_asgi(app, "/api/data"))), 401)
            self.assertEqual(response_status(asyncio.run(call_asgi(app, "/api/health"))), 200)
            self.assertEqual(response_status(asyncio.run(call_asgi(app, "/assets/app.js"))), 303)

            login = asyncio.run(
                call_asgi(
                    app,
                    "/login",
                    method="POST",
                    body=b"password=test-password",
                )
            )
            set_cookie = response_headers(login)["set-cookie"]
            token = set_cookie.split(f"{COOKIE_NAME}=", 1)[1].split(";", 1)[0]
            self.assertIn("HttpOnly", set_cookie)
            self.assertEqual(response_status(asyncio.run(call_asgi(app, "/", token))), 200)
            self.assertEqual(response_status(asyncio.run(call_asgi(app, "/api/data", token))), 200)
            self.assertEqual(response_status(asyncio.run(call_asgi(app, "/assets/app.js", token))), 200)

            logout = asyncio.run(call_asgi(app, "/logout", token, method="POST"))
            self.assertEqual(response_status(logout), 303)
            self.assertIn("Max-Age=0", response_headers(logout)["set-cookie"])
            self.assertEqual(response_status(asyncio.run(call_asgi(app, "/api/data"))), 401)


if __name__ == "__main__":
    unittest.main()
