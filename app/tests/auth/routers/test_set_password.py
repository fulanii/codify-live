class TestSetPassword:
    async def test_success_sets_a_usable_password(self, authed_client, base_user):
        response = await authed_client.post(
            "/auth/set-password",
            json={
                "password": "SuperSecretPassword123@",
                "confirm_password": "SuperSecretPassword123@",
            },
        )

        assert response.status_code == 204
        assert base_user.verify_password("SuperSecretPassword123@")
        assert base_user.auth_provider == "google_password"

    async def test_user_can_login_with_the_new_password(self, authed_client, base_user):
        await authed_client.post(
            "/auth/set-password",
            json={
                "password": "SuperSecretPassword123@",
                "confirm_password": "SuperSecretPassword123@",
            },
        )

        response = await authed_client.post(
            "/auth/login",
            json={"email": base_user.email, "password": "SuperSecretPassword123@"},
        )

        assert response.status_code == 200

    async def test_mismatched_confirmation_returns_422(self, authed_client):
        response = await authed_client.post(
            "/auth/set-password",
            json={
                "password": "SuperSecretPassword123@",
                "confirm_password": "DifferentPassword123@",
            },
        )

        assert response.status_code == 422

    async def test_weak_password_returns_422(self, authed_client):
        response = await authed_client.post(
            "/auth/set-password",
            json={"password": "alllowercase1", "confirm_password": "alllowercase1"},
        )

        assert response.status_code == 422

    async def test_short_password_returns_422(self, authed_client):
        response = await authed_client.post(
            "/auth/set-password",
            json={"password": "Ab1@", "confirm_password": "Ab1@"},
        )

        assert response.status_code == 422

    async def test_without_token_returns_401(self, client):
        response = await client.post(
            "/auth/set-password",
            json={
                "password": "SuperSecretPassword123@",
                "confirm_password": "SuperSecretPassword123@",
            },
        )

        assert response.status_code == 401
