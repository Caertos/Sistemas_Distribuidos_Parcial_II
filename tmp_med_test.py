import urllib.request, json
from urllib.error import HTTPError
TOKEN='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIyNjQ4NWExOS02OWYxLTQwNDYtOGZjMi05ODFkYTNjZTg1M2UiLCJyb2xlIjoicHJhY3RpdGlvbmVyIiwiaWF0IjoxNzYzNjAxMTgwLCJleHAiOjE3NjM2MDQ3ODB9.m3B6Jk9LKRmkXi5sMuniou2Ec0-A8Y_h8cBu-mXQgIY'
url='http://127.0.0.1:8000/api/practitioner/medications'
payloads=[
    {"nombre_medicamento": "Paracetamol", "dosis": "500mg", "paciente_id": 1},
    {"nombre": "Paracetamol", "dosis": "500mg", "paciente_id": 1},
    {"nombre_medicamento": "Paracetamol", "dosis": "500mg", "patient_id": 1},
    {"nombre_medicamento": "Paracetamol", "dosis": "500mg"},
]
for i,p in enumerate(payloads,1):
    print('\n--- Payload', i, '---')
    print(json.dumps(p))
    req=urllib.request.Request(url,data=json.dumps(p).encode(),headers={'Content-Type':'application/json','Authorization':f'Bearer {TOKEN}'})
    try:
        resp=urllib.request.urlopen(req)
        print('OK',resp.getcode(),resp.read().decode())
    except HTTPError as e:
        print('HTTPERR',e.code)
        try:
            print('BODY:', e.read().decode())
        except Exception:
            pass
    except Exception as ex:
        print('ERR',ex)
