from http.cookies import SimpleCookie

import jwt
from sqlalchemy import select

from app.core import settings


def _refresh_cookie(response):
    jar = SimpleCookie()
    jar.load(response.headers["set-cookie"])
    return jar["refresh"].value


async def _login(client):
    return await client.post("/auth/login", json={"email": "mike@mike.dev", "password": "SuperSecretPassword123@"})


class TestRefresh:
    async def test_success_returns_a_usable_access_token(self, client, user_password):
        await _login(client)

        response = await client.post("/auth/refresh")

        assert response.status_code == 200

        payload = jwt.decode(
            response.json()["access_token"],
            settings.SECRET_KEY.get_secret_value(),
            algorithms=[settings.ALGORITHM],
        )

        assert payload["sub"] == str(user_password.id)
        assert payload["type"] == "access"

    async def test_rotates_the_refresh_cookie(self, client, user_password):
        login = await _login(client)
        old_cookie = _refresh_cookie(login)

        response = await client.post("/auth/refresh")

        assert _refresh_cookie(response) != old_cookie

    async def test_presented_token_is_revoked(self, client, user_password, db_session):
        from app.auth.models import RefreshTokenModel

        await _login(client)
        await client.post("/auth/refresh")

        rows = await db_session.execute(select(RefreshTokenModel).where(RefreshTokenModel.user_id == user_password.id))
        tokens = rows.scalars().all()

        assert len(tokens) == 2
        assert sum(token.is_revoked for token in tokens) == 1

    async def test_replayed_token_revokes_every_session(self, client, user_password, db_session):
        from app.auth.models import RefreshTokenModel

        login = await _login(client)
        old_cookie = _refresh_cookie(login)

        await client.post("/auth/refresh")

        client.cookies.set("refresh", old_cookie)
        response = await client.post("/auth/refresh")

        assert response.status_code == 401

        rows = await db_session.execute(select(RefreshTokenModel).where(RefreshTokenModel.user_id == user_password.id))

        assert all(token.is_revoked for token in rows.scalars().all())

    async def test_missing_cookie_returns_401(self, client):
        response = await client.post("/auth/refresh")

        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid or expired session."

    async def test_unknown_token_returns_401(self, client):
        client.cookies.set("refresh", "not-a-real-token")
        response = await client.post("/auth/refresh")

        assert response.status_code == 401
