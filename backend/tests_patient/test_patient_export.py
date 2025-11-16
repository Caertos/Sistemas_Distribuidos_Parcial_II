import pytest

from src.controllers import patient as patient_ctrl


class FakeUser:
    def __init__(self, id="1111", username="patient1", email="p@example.com", full_name="Paciente Uno", fhir_patient_id="1"):
        self.id = id
        self.username = username
        self.email = email
        self.full_name = full_name
        self.fhir_patient_id = fhir_patient_id


def test_generate_patient_summary_export_pdf(monkeypatch):
    fake_user = FakeUser()

    # Mock the summary builder to return a predictable structure
    monkeypatch.setattr(patient_ctrl, "get_patient_summary_from_model", lambda u, db: {
        "patient": {"id": fake_user.id, "full_name": fake_user.full_name, "email": fake_user.email},
        "appointments": [],
        "encounters": [],
    })

    payload, media_type, filename = patient_ctrl.generate_patient_summary_export(fake_user, db=None, fmt="pdf")

    assert isinstance(payload, (bytes, bytearray))
    assert media_type == "application/pdf"
    assert filename.endswith(".pdf")


def test_generate_patient_summary_export_fhir(monkeypatch):
    fake_user = FakeUser()

    monkeypatch.setattr(patient_ctrl, "get_patient_summary_from_model", lambda u, db: {
        "patient": {"id": fake_user.id, "full_name": fake_user.full_name, "email": fake_user.email},
        "appointments": [],
        "encounters": [],
    })

    payload, media_type, filename = patient_ctrl.generate_patient_summary_export(fake_user, db=None, fmt="fhir")

    assert isinstance(payload, dict)
    assert media_type == "application/fhir+json"
    assert filename.endswith(".json")
