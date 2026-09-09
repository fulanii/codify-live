from sqlalchemy import select


async def _login(client):
    return await client.post("/auth/login", json={"email": "mike@mike.dev", "password": "SuperSecretPassword123@"})


class TestLogout:
    async def test_success_revokes_the_token(self, client, user_password, db_session):
        from app.auth.models import RefreshTokenModel

        await _login(client)

        response = await client.post("/auth/logout")

        assert response.status_code == 204

        rows = await db_session.execute(select(RefreshTokenModel).where(RefreshTokenModel.user_id == user_password.id))

        assert all(token.is_revoked for token in rows.scalars().all())

    async def test_clears_the_cookie(self, client, user_password):
        await _login(client)

        await client.post("/auth/logout")

        assert client.cookies.get("refresh") is None

    async def test_revoked_token_cannot_be_refreshed(self, client, user_password):
        login = await _login(client)
        cookie = login.cookies["refresh"]

        await client.post("/auth/logout")

        client.cookies.set("refresh", cookie)
        response = await client.post("/auth/refresh")

        assert response.status_code == 401

    async def test_without_cookie_is_not_an_error(self, client):
        response = await client.post("/auth/logout")

        assert response.status_code == 204
