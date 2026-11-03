"""API behaviour against the real database. Skipped automatically if the database is not running."""
import re
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import connect
from app.main import app


def _db_up() -> bool:
    try:
        with connect() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        return False


def _key() -> str:
    try:
        return get_settings().review_api_key
    except Exception:
        return ""


pytestmark = pytest.mark.skipif(not _db_up(), reason="database is not running")
client = TestClient(app)


def post_id(prefix: str) -> int:
    return next(p["id"] for p in client.get("/posts").json() if p["title"].startswith(prefix))


def image_id(filename: str) -> int:
    with connect() as conn:
        return conn.execute("SELECT id FROM images WHERE filename = %s", (filename,)).fetchone()["id"]


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_bad_id_is_422_and_missing_post_is_404():
    assert client.get("/posts/abc/images").status_code == 422
    assert client.get("/posts/999999/images").status_code == 404


def test_fox_post_gets_a_fox_image_first():
    r = client.get(f"/posts/{post_id('How red foxes survive')}/images").json()
    assert r["verdict"] == "match" and r["candidates"][0]["category"] == "fox"


def test_forced_wolf_is_rejected_with_a_category_reason():
    r = client.get(f"/posts/{post_id('How red foxes survive')}/check/{image_id('wolf_01.jpg')}").json()
    assert r["decision"]["accepted"] is False and r["decision"]["rule"] == "category"
    assert "mismatch" in r["decision"]["reason"]


def test_post_with_no_suitable_image_says_no_confident_match():
    r = client.get(f"/posts/{post_id('Eagles nesting')}/images").json()
    assert r["verdict"] == "no_confident_match" and r["best_image_id"] is None
    assert "No confident match" in r["message"]


def test_writes_need_the_api_key():
    pid = post_id("How red foxes survive")
    assert client.post(f"/posts/{pid}/suggestions").status_code in (401, 503)
    assert client.post(f"/posts/{pid}/suggestions", headers={"X-API-Key": "wrong"}).status_code in (401, 503)


@pytest.mark.skipif(not _key(), reason="REVIEW_API_KEY is not set")
def test_a_pair_the_guard_rejected_cannot_be_approved():
    headers = {"X-API-Key": _key()}
    first = client.post(f"/posts/{post_id('Eagles nesting')}/suggestions", headers=headers).json()[0]
    r = client.post(f"/suggestions/{first['id']}/review", headers=headers, json={"decision": "approved"})
    assert r.status_code == 409


def test_eval_headline_precision_is_reported_and_high():
    out = subprocess.run([sys.executable, "-m", "scripts.run_eval"], capture_output=True, text=True,
                         check=True).stdout
    m = re.search(r"HEADLINE TOP-1 PRECISION.*?: ([0-9.]+)%", out)
    assert m and float(m.group(1)) >= 90.0


def test_image_status_reports_progress_and_failures():
    r = client.get("/images/status").json()
    assert r["total"] == sum(r["counts"].values()) and r["total"] >= 50
    assert all("filename" in f for f in r["failed"])
