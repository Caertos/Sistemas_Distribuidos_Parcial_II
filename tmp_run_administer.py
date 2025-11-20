from src.database import SessionLocal
from src.controllers.admission import administer_medication

s = SessionLocal()
payload = {"nombre_medicamento": "Paracetamol", "dosis": "500mg", "paciente_id": 1}
try:
    res = administer_medication(s, 'test-run', payload)
    print('RESULT:', res)
except Exception as e:
    print('EXC:', e)
finally:
    s.close()
