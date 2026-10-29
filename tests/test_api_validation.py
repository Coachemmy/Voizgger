from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

AUDIO = {"file": ("note.mp3", b"fake-audio", "audio/mpeg")}
IMAGE = {"file": ("shelf.jpg", b"fake-image", "image/jpeg")}
AUDIT_FORM = {"items": '["Rice"]', "quantities": "[3]"}

class TestAnalyzeVoiceValidation:
    def test_rejects_non_audio_extension(self):
        response = client.post(
            "/api/analyze_voice",
            files={"file": ("note.txt", b"hello", "text/plain")},
        )
        assert response.status_code == 400
        assert "Unsupported audio format" in response.json()["error"]

    def test_rejects_missing_filename(self):
        """Rejected at the multipart layer (422) before our handler runs."""
        response = client.post(
            "/api/analyze_voice",
            files={"file": ("", b"hello", "application/octet-stream")},
        )
        assert response.status_code in (400, 422)

    def test_rejects_empty_audio(self):
        response = client.post(
            "/api/analyze_voice",
            files={"file": ("note.mp3", b"", "audio/mpeg")},
        )
        assert response.status_code == 400
        assert "empty" in response.json()["error"].lower()

    def test_rejects_oversized_audio(self):
        oversized = b"0" * (25 * 1024 * 1024 + 1)
        response = client.post(
            "/api/analyze_voice",
            files={"file": ("note.mp3", oversized, "audio/mpeg")},
        )
        assert response.status_code == 400
        assert "too large" in response.json()["error"].lower()


class TestVerifyStockValidation:
    def test_rejects_non_image_extension(self):
        response = client.post(
            "/api/verify_stock",
            files={"file": ("shelf.txt", b"hello", "text/plain")},
            data=AUDIT_FORM,
        )
        assert response.status_code == 400
        assert "Unsupported image format" in response.json()["error"]

    def test_rejects_empty_image(self):
        response = client.post(
            "/api/verify_stock",
            files={"file": ("shelf.jpg", b"", "image/jpeg")},
            data=AUDIT_FORM,
        )
        assert response.status_code == 400
        assert "empty" in response.json()["error"].lower()

    def test_rejects_invalid_items_payload(self):
        response = client.post(
            "/api/verify_stock",
            files=IMAGE,
            data={"items": "not-json", "quantities": "[3]"},
        )
        assert response.status_code == 400
        assert "Invalid items payload" in response.json()["error"]


class TestAppRoutes:
    def test_dashboard_serves_html(self):
        response = client.get("/")
        assert response.status_code == 200
        assert "Voizgger" in response.text
