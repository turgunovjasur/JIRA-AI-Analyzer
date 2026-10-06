"""The operator CLI must not depend on site startup importing importlib.util."""

import site
import subprocess
import sys

import pytest

pytestmark = pytest.mark.no_db


def test_driver_detection_works_in_a_fresh_python_process():
    code = (
        "import sys; sys.path.extend(" + repr(site.getsitepackages()) + "); "
        "from utils.database.runtime import is_postgres_driver_available; "
        "assert is_postgres_driver_available()"
    )
    result = subprocess.run([sys.executable, "-S", "-c", code], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
