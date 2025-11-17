from fastapi.testclient import TestClient
from src.main import app
from src.auth.jwt import create_access_token

# Prepare token
extras = {"role": "patient", "documento_id": "1"}
token = create_access_token(subject="11111111-1111-1111-1111-111111111111", extras=extras)
headers = {"Authorization": f"Bearer {token}"}

client = TestClient(app)
# call endpoint
r = client.get("/api/patient/me", headers=headers)
print('status', r.status_code)
print('text', r.text)
print('headers', r.headers)
