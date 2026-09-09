from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestRefreshTokenModels:
    async def test_success_refresh_token_creation(self, base_user, refresh_token):
        assert refresh_token.id is not None
        assert refresh_token.user_id == base_user.id
        assert not refresh_token.is_revoked
