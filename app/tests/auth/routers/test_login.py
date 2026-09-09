from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_login():
    response = client.post("/login")
    assert response.status_code == 404
