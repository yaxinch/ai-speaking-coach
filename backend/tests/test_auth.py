import unittest

from tests.auth_test_support import TEST_PASSWORD, TEST_USERNAME, login
from fastapi.testclient import TestClient

from app.main import app
from app.config import Settings
from app.providers.factory import get_llm_provider


class CountingLLM:
    calls = 0

    async def chat(self, messages, temperature=0.7):
        type(self).calls += 1
        return "{}"


class AuthTests(unittest.TestCase):
    def setUp(self):
        CountingLLM.calls = 0
        app.dependency_overrides[get_llm_provider] = lambda: CountingLLM()
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()

    def test_login_session_me_and_logout(self):
        response = login(self.client)
        self.assertEqual(response.json(), {"authenticated": True, "username": TEST_USERNAME})
        cookie = response.headers["set-cookie"].lower()
        self.assertIn("speaking_coach_session=", cookie)
        self.assertIn("httponly", cookie)
        self.assertIn("samesite=lax", cookie)
        self.assertIn("max-age=28800", cookie)
        self.assertNotIn("secure", cookie)

        self.assertEqual(
            self.client.get("/api/auth/me").json(),
            {"authenticated": True, "username": TEST_USERNAME},
        )
        self.assertEqual(self.client.post("/api/auth/logout").json(), {"authenticated": False})
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)

    def test_invalid_credentials_have_one_generic_response(self):
        wrong_username = self.client.post(
            "/api/auth/login", json={"username": "someone-else", "password": TEST_PASSWORD}
        )
        wrong_password = self.client.post(
            "/api/auth/login", json={"username": TEST_USERNAME, "password": "wrong"}
        )
        unicode_username = self.client.post(
            "/api/auth/login", json={"username": "错误用户", "password": TEST_PASSWORD}
        )
        self.assertEqual(wrong_username.status_code, 401)
        self.assertEqual(wrong_password.status_code, 401)
        self.assertEqual(unicode_username.status_code, 401)
        self.assertEqual(wrong_username.json(), wrong_password.json())
        self.assertEqual(wrong_username.json(), {"detail": "Invalid username or password."})

    def test_health_is_public_and_all_business_router_groups_are_protected(self):
        self.assertEqual(self.client.get("/api/health").status_code, 200)
        requests = [
            ("post", "/api/examiner/generate"),
            ("post", "/api/feedback/evaluate"),
            ("get", "/api/practices"),
            ("get", "/api/mock-tests"),
            ("post", "/api/speaking/tts"),
            ("get", "/api/speaking/audio/missing"),
            ("delete", "/api/speaking/audio/missing"),
        ]
        for method, path in requests:
            with self.subTest(path=path):
                response = self.client.request(method, path, json={} if method == "post" else None)
                self.assertEqual(response.status_code, 401)
        self.assertEqual(CountingLLM.calls, 0)

    def test_tampered_cookie_is_rejected(self):
        login(self.client)
        cookie = self.client.cookies.get("speaking_coach_session")
        self.client.cookies.set("speaking_coach_session", f"{cookie}tampered")
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)
        self.assertEqual(self.client.get("/api/practices").status_code, 401)

    def test_production_requires_secure_complete_configuration(self):
        settings = Settings(
            app_env="production",
            admin_username="admin",
            admin_password_hash="$2b$12$" + "x" * 53,
            session_secret_key="x" * 32,
            cors_origins="https://speaking.example.com",
        )
        self.assertTrue(settings.session_cookie_secure)
        settings.validate_production_security()

        with self.assertRaisesRegex(RuntimeError, "Unsafe production configuration"):
            Settings(
                app_env="production",
                session_secret_key="short",
                cors_origins="*",
            ).validate_production_security()


if __name__ == "__main__":
    unittest.main()
