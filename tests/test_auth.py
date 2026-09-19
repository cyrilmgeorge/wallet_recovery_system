import pytest

from app import create_app
from app.extensions import db
from app.models import User


@pytest.fixture
def app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": False,
            "SECRET_KEY": "test-secret-key",
        }
    )

    with app.app_context():
        db.drop_all()
        db.create_all()

    yield app

    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def test_register_user(client):

    response = client.post(
        "/auth/register",
        data={
            "username": "testuser",
            "email": "test@example.com",
            "password": "TestPassword123",
            "confirm_password": "TestPassword123",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    with client.application.app_context():

        user = User.query.filter_by(
            email="test@example.com"
        ).first()

        assert user is not None

        assert user.password_hash != (
            "TestPassword123"
        )


def test_login_success(client):

    client.post(
        "/auth/register",
        data={
            "username": "testuser",
            "email": "test@example.com",
            "password": "TestPassword123",
            "confirm_password": "TestPassword123",
        },
    )

    response = client.post(
        "/auth/login",
        data={
            "email": "test@example.com",
            "password": "TestPassword123",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Welcome back" in response.data


def test_login_invalid_password(client):

    client.post(
        "/auth/register",
        data={
            "username": "testuser",
            "email": "test@example.com",
            "password": "TestPassword123",
            "confirm_password": "TestPassword123",
        },
    )

    response = client.post(
        "/auth/login",
        data={
            "email": "test@example.com",
            "password": "WrongPassword123",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Invalid email or password." in response.data


def test_dashboard_requires_login(client):

    response = client.get(
        "/dashboard",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]