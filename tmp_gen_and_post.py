from src.auth.jwt import create_access_token
from src.database import SessionLocal
from src.models.user import User
import urllib.request, json

s=SessionLocal()
try:
    u=s.query(User).filter(User.user_type=='practitioner').first()
    if not u:
        from sqlalchemy import text
        import uuid
        uid=str(uuid.uuid4())
        s.execute(text("INSERT INTO users (id, username, user_type, is_active, fhir_practitioner_id) VALUES (:id, :u, 'practitioner', true, null)"), {"id": uid, "u": "tmp_pr"})
        s.commit()
        u=s.query(User).filter(User.id==uid).first()
    token=create_access_token(u.id, expires_minutes=60, extras={'role':'practitioner','username': getattr(u,'username',None)})
    print('TOKEN:', token)
    # Do POST
    url='http://127.0.0.1:8000/api/practitioner/medications'
    payload={"nombre_medicamento":"Paracetamol","dosis":"500mg","paciente_id":1}
    req=urllib.request.Request(url, data=json.dumps(payload).encode(), headers={'Content-Type':'application/json','Authorization':f'Bearer {token}'})
    try:
        resp=urllib.request.urlopen(req)
        print('POST-OK', resp.getcode(), resp.read().decode())
    except Exception as e:
        try:
            import urllib.error
            if isinstance(e, urllib.error.HTTPError):
                print('POST-ERR', e.code, e.read().decode())
            else:
                print('POST-EXC', e)
        except Exception as ex:
            print('POST-EXC2', ex)
finally:
    s.close()
