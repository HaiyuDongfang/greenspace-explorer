"""Dependency-free test runner: executes every test_* function in tests/test_*.py.

Usage (from the project root): python -m tests.run_tests
Exits non-zero if any test fails or errors; skipped tests are listed explicitly.
"""

from __future__ import annotations

import importlib
import sys
import traceback
from pathlib import Path
from unittest import SkipTest


def main() -> int:
    passed, skipped, failed = 0, [], []
    for path in sorted(Path(__file__).parent.glob("test_*.py")):
        module = importlib.import_module(f"tests.{path.stem}")
        for name in sorted(vars(module)):
            test = getattr(module, name)
            if not (name.startswith("test_") and callable(test)):
                continue
            label = f"{path.stem}::{name}"
            try:
                test()
            except SkipTest as reason:
                skipped.append(f"{label} ({reason})")
            except Exception:
                failed.append(label)
                print(f"FAIL {label}")
                traceback.print_exc()
            else:
                passed += 1
    for entry in skipped:
        print(f"SKIP {entry}")
    print(f"{passed} passed, {len(skipped)} skipped, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
