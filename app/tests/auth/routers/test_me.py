async def _login(client):
    return await client.post("/auth/login", json={"email": "mike@mike.dev", "password": "SuperSecretPassword123@"})


class TestMe:
    async def test_success_returns_current_user(self, client, user_password):
        login = await _login(client)
        access_token = login.json()["access_token"]

        response = await client.get("/auth/me", headers={"Authorization": f"Bearer {access_token}"})

        assert response.status_code == 200
        assert response.json()["id"] == str(user_password.id)
        assert response.json()["email"] == user_password.email

    async def test_password_hash_is_never_returned(self, client, user_password):
        login = await _login(client)

        response = await client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {login.json()['access_token']}"},
        )

        assert "password_hash" not in response.json()

    async def test_refresh_token_rejected_as_bearer(self, client, user_password):
        login = await _login(client)
        refresh_cookie = login.cookies["refresh"]

        response = await client.get("/auth/me", headers={"Authorization": f"Bearer {refresh_cookie}"})

        assert response.status_code == 401

    async def test_expired_token_returns_401(self, client, user_password):
        from datetime import UTC, datetime, timedelta

        import jwt

        from app.core import settings

        expired = jwt.encode(
            {
                "sub": str(user_password.id),
                "iat": datetime.now(UTC) - timedelta(hours=2),
                "exp": datetime.now(UTC) - timedelta(hours=1),
                "type": "access",
            },
            settings.SECRET_KEY.get_secret_value(),
            algorithm=settings.ALGORITHM,
        )

        response = await client.get("/auth/me", headers={"Authorization": f"Bearer {expired}"})

        assert response.status_code == 401

    async def test_without_token_is_rejected(self, client):
        response = await client.get("/auth/me")

        assert response.status_code == 401
