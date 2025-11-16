import pytest
from jose import jwt
from src.auth.jwt import create_access_token
from src.config import settings


def test_create_access_token_contains_documento_id():
    extras = {"role": "patient", "documento_id": "ABC-12345"}
    token = create_access_token(subject="user-1", extras=extras)
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    assert "documento_id" in payload
    assert payload["documento_id"] == "ABC-12345"


def test_create_access_token_does_not_allow_overwrite_reserved_claims():
    # intentar pasar sub/exp/iat en extras — deben ser ignorados
    extras = {"sub": "malicious", "iat": 0, "exp": 0, "documento_id": "XYZ"}
    token = create_access_token(subject="user-2", extras=extras)
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    # sub debe ser el sujeto correcto
    assert payload.get("sub") == "user-2"
    # documento_id preservado
    assert payload.get("documento_id") == "XYZ"
