"""API smoke for scrcpy status — does not spawn a window."""

from fastapi.testclient import TestClient

from control.server import app, _scrcpy_last


def test_scrcpy_status_unknown_serial():
    _scrcpy_last.pop("no-such-device", None)
    client = TestClient(app)
    r = client.get("/api/devices/no-such-device/scrcpy_status")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["running"] is False
