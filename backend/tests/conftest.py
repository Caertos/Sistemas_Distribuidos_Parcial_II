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


@pytest.fixture(autouse=True)
def ensure_module_clients_bound():
    """Before each test, ensure any module-level `client` variables in test modules
    point to a TestClient bound to the current `src.main.app` object.

    Esto mitiga el problema donde algunos tests recargan `src.main` y dejan
    variables `client` en otros módulos apuntando a una app antigua.
    """
    try:
        import sys
        import os
        import importlib
        from fastapi.testclient import TestClient
        # Reload a set of src modules to avoid cross-test import-time contamination
        # (some integration tests reload modules / change env vars). Reloading
        # here before each test helps ensure route/controller/get_db function
        # identities are consistent for app.dependency_overrides.
        modules_to_reload = [
            "src.config",
            "src.database",
            "src.auth.jwt",
            "src.auth.permissions",
            "src.middleware.auth",
            "src.controllers.patient",
            "src.routes.patient",
            "src.routes.practitioner",
            "src.main",
        ]
        for mn in modules_to_reload:
            try:
                if mn in sys.modules:
                    importlib.reload(sys.modules[mn])
            except Exception:
                # best-effort reload; ignore failures
                pass
        from src.main import app as current_app
    except Exception:
        yield
        return

    new_client = TestClient(current_app)

    # Rebind module-level `client` variables for loaded test modules under backend/tests
    for m in list(sys.modules.values()):
        try:
            mf = getattr(m, "__file__", None)
            if not mf:
                continue
            # normalize path and only touch modules inside backend/tests or backend/tests_patient
            norm = os.path.normpath(mf)
            # touch modules inside backend/tests or backend/tests_patient
            if (
                os.path.sep + "backend" + os.path.sep + "tests" + os.path.sep in norm
                or os.path.sep + "backend" + os.path.sep + "tests_patient" + os.path.sep in norm
            ):
                if hasattr(m, "client"):
                    try:
                        setattr(m, "client", new_client)
                    except Exception:
                        pass
                    # Rebind module-level `client` and `app` if present so tests that
                    # reference those names at module scope use the fresh app/client
                    if hasattr(m, "app"):
                        try:
                            setattr(m, "app", current_app)
                        except Exception:
                            pass
        except Exception:
            # ignore any inspect errors
            pass

    try:
        yield
    finally:
        # Intentionally do NOT close new_client here. Closing the TestClient while
        # tests still reference module-level `client` can cause "client closed"
        # RuntimeError inside tests when multiple fixtures/modules interact.
        # Leaving the client open for the process lifetime is acceptable for the
        # test run and prevents flakiness caused by premature closure.
        pass
