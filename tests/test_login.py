import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_check():
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


@pytest.mark.parametrize(
    "username,password,expected_role",
    [
        ("admin", "admin123", "管理员"),
        ("operator", "operator123", "操作员"),
        ("visitor", "visitor123", "访客"),
    ],
)
def test_login_success(username, password, expected_role):
    response = client.post(
        "/api/login",
        json={"username": username, "password": password},
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["username"] == username
    assert response.json()["role"] == expected_role


def test_login_with_wrong_password():
    response = client.post(
        "/api/login",
        json={"username": "admin", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "用户名或密码错误"


def test_login_with_empty_username():
    response = client.post(
        "/api/login",
        json={"username": "", "password": "admin123"},
    )

    assert response.status_code == 422

def test_login_with_unknown_username():
    response = client.post(
        "/api/login",
        json={"username": "unknown", "password": "admin123"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "用户名或密码错误"


def test_login_with_empty_password():
    response = client.post(
        "/api/login",
        json={"username": "admin", "password": ""},
    )

    assert response.status_code == 422


def test_login_without_password_field():
    response = client.post(
        "/api/login",
        json={"username": "admin"},
    )

    assert response.status_code == 422