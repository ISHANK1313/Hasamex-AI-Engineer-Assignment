"""Suite-wide guard: no test may reach the network, whatever the developer's .env contains.

The app reads .env at import time, so a real key on the machine would otherwise turn the API tests
into live model calls. Clearing the key is enough: with no key and no MOCK_LLM, `llm.available()` is
false and every path answers from verbatim evidence. Tests that need mock prose set MOCK_LLM=1
themselves, so the meaning of each test stays visible in the test file.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(autouse=True)
def no_key_by_default(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setenv("MOCK_LLM", "0")
    yield
