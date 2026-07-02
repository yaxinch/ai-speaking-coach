import os

import bcrypt


TEST_USERNAME = "test-admin"
TEST_PASSWORD = "correct horse battery staple"
TEST_SESSION_SECRET = "test-session-secret-that-is-longer-than-32-characters"
TEST_PASSWORD_HASH = bcrypt.hashpw(TEST_PASSWORD.encode(), bcrypt.gensalt(rounds=4)).decode()

os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("ADMIN_USERNAME", TEST_USERNAME)
os.environ.setdefault("ADMIN_PASSWORD_HASH", TEST_PASSWORD_HASH)
os.environ.setdefault("SESSION_SECRET_KEY", TEST_SESSION_SECRET)


def login(client):
    response = client.post(
        "/api/auth/login",
        json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
    )
    if response.status_code != 200:
        raise AssertionError(f"Test login failed: {response.status_code} {response.text}")
    return response
