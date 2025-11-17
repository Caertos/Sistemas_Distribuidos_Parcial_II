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
    """Autouse fixture that does a light cleanup of any module-level TestClient
    objects found in loaded test modules. This avoids leaking sockets across
    tests while avoiding heavy module reloads that caused breakage.
    """
    try:
        import sys
        import os
        from fastapi.testclient import TestClient

        for m in list(sys.modules.values()):
            try:
                mf = getattr(m, "__file__", None)
                if not mf:
                    continue
                norm = os.path.normpath(mf)
                if (
                    os.path.sep + "backend" + os.path.sep + "tests" + os.path.sep in norm
                    or os.path.sep + "backend" + os.path.sep + "tests_patient" + os.path.sep in norm
                ):
                    if hasattr(m, "client"):
                        old = getattr(m, "client")
                        try:
                            close_fn = getattr(old, "close", None)
                            if callable(close_fn):
                                close_fn()
                        except Exception:
                            pass
                        try:
                            delattr(m, "client")
                        except Exception:
                            try:
                                setattr(m, "client", None)
                            except Exception:
                                pass
            except Exception:
                pass
        # Inject a shared TestClient into test modules that expect a module-level
        # `client` variable (legacy tests). Create it once per fixture run.
        try:
            from src.main import app as current_app
            shared_client = TestClient(current_app)
            for m in list(sys.modules.values()):
                try:
                    mf = getattr(m, "__file__", None)
                    if not mf:
                        continue
                    norm = os.path.normpath(mf)
                    if os.path.sep + "backend" + os.path.sep + "tests_patient" + os.path.sep in norm:
                        if not hasattr(m, "client") or getattr(m, "client") is None:
                            try:
                                setattr(m, "client", shared_client)
                            except Exception:
                                pass
                except Exception:
                    pass
        except Exception:
            # best-effort only
            pass
    except Exception:
        pass

    yield
