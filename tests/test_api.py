from fastapi.testclient import TestClient
import main

client = TestClient(main.app)
KEY = {"x-api-key": "mahak-pdf-tool-7k3x9q2m"}


def test_root_ok():
    r = client.get("/")
    assert r.status_code == 200


def test_status_ok():
    r = client.get("/status/")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_documents_requires_api_key():
    r = client.get("/documents/")
    assert r.status_code in (401, 403, 422)