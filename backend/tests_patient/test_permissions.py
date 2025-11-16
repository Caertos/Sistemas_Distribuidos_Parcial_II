import pytest
from fastapi import HTTPException

from src.auth import permissions


def test_assert_not_patient_raises_401_on_none():
    with pytest.raises(HTTPException) as exc:
        permissions.assert_not_patient(None)
    assert exc.value.status_code == 401


def test_assert_not_patient_raises_403_for_patient():
    user = {"role": "patient"}
    with pytest.raises(HTTPException) as exc:
        permissions.assert_not_patient(user)
    assert exc.value.status_code == 403


def test_assert_not_patient_allows_other_roles():
    for r in ["practitioner", "admin", "staff", "doctor"]:
        # Should not raise
        permissions.assert_not_patient({"role": r})


def test_deny_patient_dependency_with_dummy_request():
    class DummyState:
        def __init__(self, user):
            self.user = user

    class DummyRequest:
        def __init__(self, user):
            self.state = DummyState(user)

    # should raise 403 for patient
    with pytest.raises(Exception) as exc:
        permissions.deny_patient_dependency(DummyRequest({"role": "patient"}))

    # should not raise for other role
    permissions.deny_patient_dependency(DummyRequest({"role": "practitioner"}))
