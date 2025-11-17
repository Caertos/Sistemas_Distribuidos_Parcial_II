import pytest

try:
    # import app for dependency_overrides cleanup
    from src.main import app
except Exception:
    app = None


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    """Fixture autouse que limpia app.dependency_overrides después de cada test.

    Esto previene contaminación entre tests que olvidan restaurar overrides.
    """
    # clear before the test as well, to avoid carrying overrides from earlier failures
    if app is not None:
        try:
            app.dependency_overrides.clear()
        except Exception:
            pass
    yield
    if app is not None:
        try:
            app.dependency_overrides.clear()
        except Exception:
            # no-op: si algo falla, no romper la limpieza de tests
            pass


@pytest.fixture
def client():
    """Provide a fresh TestClient for tests.

    Tests should accept the `client` fixture instead of creating a module-level
    TestClient(app). This prevents resource leakage and cross-test
    contamination.
    """
    from fastapi.testclient import TestClient
    from src.main import app as current_app

    with TestClient(current_app) as c:
        yield c
