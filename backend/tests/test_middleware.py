from fastapi.testclient import TestClient
from src.main import app
from src.auth.jwt import create_access_token

client = TestClient(app)

def run():
    print('\n--- Middleware tests start ---')

    # 1. No Authorization header
    r1 = client.get('/api/secure/me')
    print('NO_AUTH', r1.status_code, r1.json())

    # 2. Invalid token
    r2 = client.get('/api/secure/me', headers={'Authorization': 'Bearer invalidtoken'})
    try:
        print('INVALID', r2.status_code, r2.json())
    except Exception:
        print('INVALID', r2.status_code, r2.text)

    # 3. Validly signed token (subject may not exist in DB)
    token = create_access_token(subject='00000000-0000-0000-0000-000000000000')
    r3 = client.get('/api/secure/me', headers={'Authorization': f'Bearer {token}'})
    print('VALID_SIGNED', r3.status_code, r3.text)

    # 4. Try real login against DB (admin1/secret expected from k8s populate)
    r4 = client.post('/api/auth/token', data={'username': 'admin1', 'password': 'secret'})
    try:
        print('LOGIN', r4.status_code, r4.json())
        if r4.status_code == 200:
            t = r4.json().get('access_token')
            r5 = client.get('/api/secure/me', headers={'Authorization': f'Bearer {t}'})
            print('ME_AFTER_LOGIN', r5.status_code, r5.text)
    except Exception:
        print('LOGIN', r4.status_code, r4.text)

    print('--- Middleware tests end ---\n')

if __name__ == '__main__':
    run()
