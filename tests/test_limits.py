import pytest
from fastapi.testclient import TestClient

import app.core.limits as limits
from app.api import endpoints
from app.main import app

client = TestClient(app)

AUDIO = {"file": ("note.mp3", b"fake-audio", "audio/mpeg")}
IMAGE = {"file": ("shelf.jpg", b"fake-image", "image/jpeg")}
AUDIT_FORM = {"items": '["Rice"]', "quantities": "[3]"}

@pytest.fixture
def stub_ai(monkeypatch):
    """Replace the paid model calls and record how often they run."""
    calls = []

    def fake_voice(*args, **kwargs):
        calls.append("voice")
        return {"transcript": "stubbed", "items": ["Rice"]}

    monkeypatch.setattr(endpoints, "process_voice_to_ledger", fake_voice)
    monkeypatch.setattr(endpoints, "translate_ledger", lambda *a, **k: {"transcript": "stubbed"})
    monkeypatch.setattr(endpoints, "verify_inventory", lambda *a, **k: {"verdict": "consistent"})
    return calls

def _wide_open(monkeypatch):
    """Only test the daily ceiling: give the IP window plenty of room."""
    monkeypatch.setattr(limits, "IP_LIMIT", 999)

class TestHealth:
    def test_returns_ok_without_touching_the_database(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        assert client.get("/api/invoices").json() == []

class TestDailyQuota:
    def test_blocks_the_request_past_the_daily_ceiling(self, stub_ai, monkeypatch):
        _wide_open(monkeypatch)
        monkeypatch.setattr(limits, "DAILY_LIMIT", 2)

        for _ in range(2):
            assert client.post("/api/analyze_voice", files=AUDIO).status_code == 200

        blocked = client.post("/api/analyze_voice", files=AUDIO)
        assert blocked.status_code == 429
        assert "quota" in blocked.json()["error"].lower()

    def test_never_spends_credits_once_exhausted(self, stub_ai, monkeypatch):
        _wide_open(monkeypatch)
        monkeypatch.setattr(limits, "DAILY_LIMIT", 2)

        for _ in range(4):
            client.post("/api/analyze_voice", files=AUDIO)

        assert len(stub_ai) == 2

    def test_rejected_upload_does_not_spend_quota(self, stub_ai, monkeypatch):
        """Validation runs first, so bad files never consume the budget."""
        _wide_open(monkeypatch)
        monkeypatch.setattr(limits, "DAILY_LIMIT", 1)

        bad = client.post("/api/analyze_voice", files={"file": ("note.txt", b"hello", "text/plain")})
        assert bad.status_code == 400

        good = client.post("/api/analyze_voice", files=AUDIO)
        assert good.status_code == 200

    def test_translation_shares_the_same_budget(self, stub_ai, monkeypatch):
        _wide_open(monkeypatch)
        monkeypatch.setattr(limits, "DAILY_LIMIT", 1)

        payload = {"transcript": "hello", "language": "Yoruba"}
        assert client.post("/api/translate", json=payload).status_code == 200

        blocked = client.post("/api/translate", json=payload)
        assert blocked.status_code == 429
        assert "quota" in blocked.json()["error"].lower()

class TestPerIpRateLimit:
    def test_blocks_a_flood_from_one_client(self, stub_ai, monkeypatch):
        monkeypatch.setattr(limits, "IP_LIMIT", 2)
        monkeypatch.setattr(limits, "IP_WINDOW_SECONDS", 60)
        monkeypatch.setattr(limits, "DAILY_LIMIT", 999)

        for _ in range(2):
            assert client.post("/api/verify_stock", files=IMAGE, data=AUDIT_FORM).status_code == 200

        blocked = client.post("/api/verify_stock", files=IMAGE, data=AUDIT_FORM)
        assert blocked.status_code == 429
        assert "too many" in blocked.json()["error"].lower()

    def test_counts_bad_requests_too(self, monkeypatch):
        """A scanner sending junk should still be throttled."""
        monkeypatch.setattr(limits, "IP_LIMIT", 2)
        monkeypatch.setattr(limits, "IP_WINDOW_SECONDS", 60)
        monkeypatch.setattr(limits, "DAILY_LIMIT", 999)

        junk = {"file": ("note.txt", b"hello", "text/plain")}
        assert client.post("/api/analyze_voice", files=junk).status_code == 400
        assert client.post("/api/analyze_voice", files=junk).status_code == 400
        assert client.post("/api/analyze_voice", files=junk).status_code == 429

class TestGuardsCanBeDisabled:
    def test_local_development_needs_no_limits(self, stub_ai, monkeypatch):
        monkeypatch.setattr(limits, "LIMITS_ENABLED", False)
        monkeypatch.setattr(limits, "DAILY_LIMIT", 0)
        monkeypatch.setattr(limits, "IP_LIMIT", 1)

        for _ in range(3):
            assert client.post("/api/analyze_voice", files=AUDIO).status_code == 200
        assert len(stub_ai) == 3
