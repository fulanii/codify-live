from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestLogin:
    async def test_success_login(self, base_user, refresh_token): ...
