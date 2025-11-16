from datetime import datetime, timedelta

import pytest

from src.controllers import patient as patient_ctrl


class FakeResult:
    def __init__(self, rows):
        self._rows = rows or []

    def mappings(self):
        return self

    def all(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None


class FakeDB:
    def __init__(self, rows_map=None):
        # rows_map: mapping from query marker to rows
        self.rows_map = rows_map or {}

    def execute(self, q, params=None):
        # Very small heuristic: use params to pick rows
        key = None
        if params and "pid" in params and "cid" in params:
            key = f"pid:{params.get('pid')}-cid:{params.get('cid')}"
        elif params and "pid" in params:
            key = f"pid:{params.get('pid')}"
        else:
            key = "default"
        rows = self.rows_map.get(key, [])
        return FakeResult(rows)


def make_row(fecha_hora: datetime, duracion_minutos: int, estado: str = "programada", cid: int = 1):
    return {"cita_id": cid, "fecha_hora": fecha_hora, "duracion_minutos": duracion_minutos, "estado": estado}


def test_is_timeslot_available_conflict():
    pid = 1
    existing = [make_row(datetime.utcnow() + timedelta(hours=10), 60, "programada", cid=11)]
    db = FakeDB({f"pid:{pid}": existing})

    # new appointment overlapping existing (start 10:30)
    new_start = existing[0]["fecha_hora"] + timedelta(minutes=30)
    assert patient_ctrl.is_timeslot_available(db, pid, new_start, 30) is False


def test_is_timeslot_available_no_conflict():
    pid = 2
    existing = [make_row(datetime.utcnow() + timedelta(hours=10), 60, "programada", cid=21)]
    db = FakeDB({f"pid:{pid}": existing})

    # new appointment after existing end
    new_start = existing[0]["fecha_hora"] + timedelta(hours=2)
    assert patient_ctrl.is_timeslot_available(db, pid, new_start, 30) is True


def test_can_cancel_appointment_window_enforced():
    pid = 3
    # cita in 2 hours -> cannot cancel for 24h window
    cita_id = 31
    row = {"fecha_hora": datetime.utcnow() + timedelta(hours=2), "estado": "programada"}
    db = FakeDB({f"pid:{pid}-cid:{cita_id}": [row]})
    assert patient_ctrl.can_cancel_appointment(db, pid, cita_id, min_hours_before_cancel=24) is False

    # cita in 48 hours -> can cancel
    cita_id2 = 32
    row2 = {"fecha_hora": datetime.utcnow() + timedelta(hours=48), "estado": "programada"}
    db2 = FakeDB({f"pid:{pid}-cid:{cita_id2}": [row2]})
    assert patient_ctrl.can_cancel_appointment(db2, pid, cita_id2, min_hours_before_cancel=24) is True


def test_create_patient_appointment_respects_availability(monkeypatch):
    # Monkeypatch is_timeslot_available to return False -> create should return None
    fake_user = type("U", (), {"fhir_patient_id": "4"})
    fake_db = FakeDB({"pid:4": []})
    monkeypatch.setattr(patient_ctrl, "is_timeslot_available", lambda db, pid, fh, dm: False)

    res = patient_ctrl.create_patient_appointment(fake_user, fake_db, datetime.utcnow() + timedelta(days=1), 30, "motivo")
    assert res is None
