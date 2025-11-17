from fastapi.testclient import TestClient
from src.main import app
from src.auth.jwt import create_access_token

# Instantiate TestClient per-test to avoid sharing state between tests


def token_for(role: str = "admin"):
    return {"authorization": f"Bearer {create_access_token(subject='admin1', extras={'role': role})}"}


class FakeUser:
    def __init__(self, user_id="u1", username="u1"):
        self.id = user_id
        self.username = username
        self.email = "u1@example.com"
        self.full_name = "User One"
        self.user_type = "staff"
        self.is_superuser = False

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "user_type": self.user_type,
            "is_superuser": self.is_superuser,
        }


def test_admin_create_and_get_user(monkeypatch):
    import src.routes.admin as admin_routes
    from src.database import get_db

    # Patch admin_users.create_user and get_user/list_users
    class AU:
        @staticmethod
        def create_user(db, username, email, full_name, password, user_type, is_superuser):
            import uuid
            u = FakeUser(user_id=str(uuid.uuid4()), username=username)
            # return object matching UserOut schema (id as UUID string)
            return {"id": u.id, "username": u.username, "email": u.email, "full_name": u.full_name, "user_type": u.user_type, "is_superuser": u.is_superuser}

        @staticmethod
        def get_user(db, user_id):
            import uuid
            if user_id == "not-found":
                return None
            u = FakeUser(user_id=str(uuid.uuid4()), username=f"u-{user_id}")
            return {"id": u.id, "username": u.username, "email": u.email, "full_name": u.full_name, "user_type": u.user_type, "is_superuser": u.is_superuser}

        @staticmethod
        def list_users(db, skip=0, limit=100):
            import uuid
            u1 = FakeUser(user_id=str(uuid.uuid4()), username="u1")
            u2 = FakeUser(user_id=str(uuid.uuid4()), username="u2")
            return [
                {"id": u1.id, "username": u1.username, "email": u1.email, "full_name": u1.full_name, "user_type": u1.user_type, "is_superuser": u1.is_superuser},
                {"id": u2.id, "username": u2.username, "email": u2.email, "full_name": u2.full_name, "user_type": u2.user_type, "is_superuser": u2.is_superuser},
            ]

    # Patch the object that the route module uses (admin_routes.admin_users)
    monkeypatch.setattr(admin_routes, "admin_users", AU)

    # get_db override stub
    def fake_get_db():
        return object()

    app.dependency_overrides[get_db] = fake_get_db

    headers = token_for("admin")
    payload = {"username": "newuser", "email": "new@x.com", "full_name": "New User", "password": "secretpw", "user_type": "staff", "is_superuser": False}
    client = TestClient(app)
    r = client.post("/api/admin/users", json=payload, headers=headers)
    assert r.status_code == 201
    assert r.json().get("username") == "newuser"

    # list users
    r2 = client.get("/api/admin/users", headers=headers)
    assert r2.status_code == 200
    assert isinstance(r2.json(), list) and len(r2.json()) >= 1

    # get single
    r3 = client.get("/api/admin/users/u1", headers=headers)
    assert r3.status_code == 200

    # get not found
    r4 = client.get("/api/admin/users/not-found", headers=headers)
    assert r4.status_code == 404

    # non-admin cannot access
    headers_user = token_for("patient")
    r5 = client.get("/api/admin/users", headers=headers_user)
    assert r5.status_code == 403

    app.dependency_overrides.pop(get_db, None)
    client.close()
