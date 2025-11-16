#!/usr/bin/env python3
"""
Run patient endpoint tests without pytest by importing the test module and running functions.
Exits with code 0 if all tests pass, non-zero otherwise.
"""
import sys
import traceback
import os

# Ensure repo root and backend/src are importable
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC_PATH = os.path.join(ROOT, "backend", "src")
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

import importlib.util

TEST_PATH = os.path.join(os.path.dirname(__file__), "test_patient.py")
spec = importlib.util.spec_from_file_location("test_patient", TEST_PATH)
tp = importlib.util.module_from_spec(spec)
sys.modules["test_patient"] = tp
spec.loader.exec_module(tp)

failures = 0

for name in [n for n in dir(tp) if n.startswith('test_')]:
    fn = getattr(tp, name)
    print(f"Running {name}...")
    try:
        fn()
    except AssertionError as e:
        failures += 1
        print(f"FAILED: {name}: {e}")
        traceback.print_exc()
    except Exception as e:
        failures += 1
        print(f"ERROR running {name}: {e}")
        traceback.print_exc()
    else:
        print(f"OK: {name}")

if failures:
    print(f"{failures} tests failed")
    sys.exit(2)
print("All tests passed")
sys.exit(0)
