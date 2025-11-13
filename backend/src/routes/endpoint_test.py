from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path

router = APIRouter()

# Path to repo root -> ../.. from this file: backend/src/routes/endpoint_test.py
REPO_ROOT = Path(__file__).resolve().parents[3]
FRONTEND_DIR = REPO_ROOT / "frontend"


@router.get("/test/login")
def serve_login():
    file_path = FRONTEND_DIR / "login_test.html"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="login_test.html not found")
    return FileResponse(file_path, media_type="text/html")


@router.get("/test/muestra")
def serve_muestra():
    file_path = FRONTEND_DIR / "muestra_test.html"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="muestra_test.html not found")
    return FileResponse(file_path, media_type="text/html")


@router.get("/test/me")
def test_me(request: Request):
    # This endpoint is protected by the global AuthMiddleware and will have
    # request.state.user populated when a valid Bearer token is provided.
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return JSONResponse({"user": user})
