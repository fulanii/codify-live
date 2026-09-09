import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.main import app

client = TestClient(app)


class TestUserModels:
    async def test_success_user_creation(self, base_user):
        assert base_user.id is not None
        assert base_user.name == "Yassine"
        assert base_user.email == "yassine@yassinecodes.dev"

    async def test_create_duplicate_unique_field_raises_integrity_error(self, base_user, db_session):
        from app.auth.models import UserModel

        with pytest.raises(IntegrityError):
            user = UserModel(name="Yassine", email="yassine@yassinecodes.dev", is_verified=True)

            db_session.add(user)

            await db_session.commit()
