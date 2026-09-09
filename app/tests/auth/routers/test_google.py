from http.cookies import SimpleCookie

import pytest
from sqlalchemy import select

from app.core import settings


class TestGoogleLoginStart:
    async def test_redirects_to_google_with_state(self, client):
        response = await client.get("/auth/login/google", follow_redirects=False)

        assert response.status_code == 302
        assert response.headers["location"].startswith(settings.GOOGLE_AUTHORIZE_URL)

        jar = SimpleCookie()
        jar.load(response.headers["set-cookie"])

        assert jar["state"].value
        assert jar["state"].value in response.headers["location"]
        assert jar["state"]["httponly"]


class TestGoogleCallback:
    @pytest.fixture(autouse=True)
    def fake_google(self, monkeypatch):
        async def _exchange(token_data):
            return "newperson@gmail.com", "New Person"

        monkeypatch.setattr("app.auth.routers.callback_google.exchange_google_auth_for_token", _exchange)

    async def test_success_creates_user_and_sets_refresh_cookie(self, client, db_session):
        from app.auth.models import UserModel

        response = await client.get(
            "/auth/google/callback",
            params={"code": "google-code", "state": "matching-state"},
            headers={"Cookie": "state=matching-state"},
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert response.headers["location"] == f"{settings.FRONTEND_URL}/auth/callback"
        assert client.cookies.get("refresh")

        rows = await db_session.execute(select(UserModel).where(UserModel.email == "newperson@gmail.com"))
        user = rows.scalar_one()

        assert user.is_verified
        assert user.auth_provider == "google"

    async def test_state_mismatch_returns_400(self, client):
        response = await client.get(
            "/auth/google/callback",
            params={"code": "google-code", "state": "attacker-state"},
            headers={"Cookie": "state=cookie-state"},
            follow_redirects=False,
        )

        assert response.status_code == 400

    async def test_missing_state_cookie_returns_400(self, client):
        response = await client.get(
            "/auth/google/callback",
            params={"code": "google-code", "state": "some-state"},
            follow_redirects=True,
        )

        assert response.status_code == 400

    async def test_declined_consent_returns_400(self, client):
        response = await client.get(
            "/auth/google/callback",
            params={"error": "access_denied", "state": "matching-state"},
            headers={"Cookie": "state=matching-state"},
            follow_redirects=False,
        )

        assert response.status_code == 400
