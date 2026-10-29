from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

def _invoice(**overrides):
    payload = {
        "id": "VG-000001",
        "date": "28/10/2026, 21:00:00",
        "summary": "Sold 3 bags of rice, customer owes 5000",
        "items": ["Rice"],
        "quantity": [3],
        "amount_paid": 15000,
        "amount_owed": 5000,
    }
    payload.update(overrides)
    return payload

class TestInvoiceApi:
    def test_starts_empty(self):
        assert client.get("/api/invoices").json() == []

    def test_create_returns_persisted_list(self):
        response = client.post("/api/invoices", json=_invoice())
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["id"] == "VG-000001"
        assert body[0]["items"] == ["Rice"]
        assert body[0]["quantity"] == [3]

    def test_survives_a_fresh_read(self):
        client.post("/api/invoices", json=_invoice())
        reread = client.get("/api/invoices").json()
        assert reread[0]["amount_owed"] == 5000
        assert reread[0]["summary"].startswith("Sold 3 bags")

    def test_newest_first(self):
        client.post("/api/invoices", json=_invoice(id="VG-000001", date="01/01/2026"))
        client.post("/api/invoices", json=_invoice(id="VG-000002", date="02/01/2026"))
        ids = [row["id"] for row in client.get("/api/invoices").json()]
        assert ids[0] == "VG-000002"

    def test_duplicate_id_is_upserted_not_duplicated(self):
        client.post("/api/invoices", json=_invoice(amount_owed=5000))
        client.post("/api/invoices", json=_invoice(amount_owed=9000))
        rows = client.get("/api/invoices").json()
        assert len(rows) == 1
        assert rows[0]["amount_owed"] == 9000

    def test_blank_id_is_rejected(self):
        response = client.post("/api/invoices", json=_invoice(id="   "))
        assert response.status_code == 400

    def test_clear_removes_everything(self):
        client.post("/api/invoices", json=_invoice())
        assert client.delete("/api/invoices").json() == []
        assert client.get("/api/invoices").json() == []
