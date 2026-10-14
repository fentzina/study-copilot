import copy
import io
import json

import pytest

import app as app_module
import llm_client

FAKE_PDF = b"%PDF-1.4 fake content for tests"

GOOD = {
    "summary": [{"text": f"Σημείο {i}", "page": i} for i in range(1, 7)],
    "flashcards": [{"front": f"Ε{i}", "back": f"Α{i}"} for i in range(10)],
    "quiz": [{"question": f"Ερώτηση {i}", "options": ["α", "β", "γ", "δ"],
              "correct_index": 1, "explanation": "Επεξήγηση", "page": 1} for i in range(5)],
}


@pytest.fixture
def client(monkeypatch):
    app_module.CACHE.clear()
    calls = []

    def fake(pdf_bytes, private=False):
        calls.append(private)
        return GOOD

    monkeypatch.setattr(llm_client, "generate_study_material", fake)
    c = app_module.app.test_client()
    c.calls = calls
    return c


def upload(client, data=FAKE_PDF, name="l.pdf", private="0"):
    return client.post("/api/analyze", data={"pdf": (io.BytesIO(data), name), "private": private},
                       content_type="multipart/form-data")


def test_index_loads(client):
    assert client.get("/").status_code == 200


def test_no_file(client):
    assert client.post("/api/analyze").status_code == 400


def test_rejects_non_pdf(client):
    assert upload(client, b"hello", "x.txt").status_code == 400


def test_returns_all_three_sections(client):
    body = upload(client).get_json()
    assert len(body["flashcards"]) == 10 and len(body["quiz"]) == 5 and body["summary"]


def test_cache_calls_model_once(client):
    upload(client)
    upload(client)
    assert client.calls == [False]


def test_private_flag_is_passed(client):
    upload(client, private="1")
    assert client.calls == [True]


def test_model_failure_is_friendly(client, monkeypatch):
    def boom(*a, **k):
        raise ValueError("bad json")
    monkeypatch.setattr(llm_client, "generate_study_material", boom)
    r = upload(client)
    assert r.status_code == 422 and "error" in r.get_json()


def test_quota_error_maps_to_429(client, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("429 quota exceeded")
    monkeypatch.setattr(llm_client, "generate_study_material", boom)
    assert upload(client).status_code == 429


def test_ollama_connection_error_maps_to_503(client, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("<urlopen error [WinError 10061] Connection refused>")
    monkeypatch.setattr(llm_client, "generate_study_material", boom)
    res = upload(client, private="1")
    assert res.status_code == 503
    assert "Ollama" in res.get_json()["error"]


def test_parse_valid_material():
    assert llm_client.parse_material(json.dumps(GOOD))["flashcards"][0]["front"] == "Ε0"


def test_parse_rejects_broken_json():
    with pytest.raises(ValueError):
        llm_client.parse_material("not json at all")


def test_parse_rejects_bad_correct_index():
    bad = copy.deepcopy(GOOD)
    bad["quiz"][0]["correct_index"] = 9
    with pytest.raises(ValueError):
        llm_client.parse_material(json.dumps(bad))
