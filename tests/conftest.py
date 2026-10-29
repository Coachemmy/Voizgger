import os
import tempfile
from pathlib import Path

import pytest

_TMP_DB = Path(tempfile.gettempdir()) / "voizgger_test.db"
os.environ["VOIZGGER_DB"] = str(_TMP_DB)


@pytest.fixture(autouse=True)
def clean_database():
    from app.core.db import delete_all_invoices
    from app.core.limits import reset_limits

    delete_all_invoices()
    reset_limits()
    yield
    delete_all_invoices()
    reset_limits()
