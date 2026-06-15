"""Cashier unit tests — no display, no real API needed."""
from unittest.mock import MagicMock, patch


def test_offline_queue_enqueue_and_count(tmp_path, monkeypatch):
    """Queue writes to file; pending_count reads it."""
    import cashier.local.queue as q
    monkeypatch.setattr(q, "QUEUE_FILE", tmp_path / "queue.jsonl")
    assert q.pending_count() == 0
    q.enqueue({"transaction_uuid": "abc", "lines": []})
    q.enqueue({"transaction_uuid": "def", "lines": []})
    assert q.pending_count() == 2


def test_api_client_pin_login_success():
    """pin_login returns parsed dict on 200."""
    import cashier.api_client as api
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"access_token": "tok", "user_id": "uid", "display_name": "Ana", "permissions": []}
    with patch("cashier.api_client.httpx.Client") as MockClient:
        MockClient.return_value.__enter__.return_value.post.return_value = mock_resp
        result = api.pin_login("loc-id", "1234")
    assert result["access_token"] == "tok"


def test_api_client_pin_login_failure():
    """pin_login returns None on 401."""
    import cashier.api_client as api
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    with patch("cashier.api_client.httpx.Client") as MockClient:
        MockClient.return_value.__enter__.return_value.post.return_value = mock_resp
        result = api.pin_login("loc-id", "wrong")
    assert result is None


def test_api_client_network_error():
    """pin_login returns None on connection error."""
    import httpx

    import cashier.api_client as api
    with patch("cashier.api_client.httpx.Client") as MockClient:
        MockClient.return_value.__enter__.return_value.post.side_effect = httpx.ConnectError("down")
        result = api.pin_login("loc-id", "1234")
    assert result is None


def test_mock_printer_print(capsys):
    """Mock printer outputs to stdout without error."""
    from cashier.hardware.printer import get_printer
    printer = get_printer()
    printer.print_receipt({
        "header": "TEST",
        "lines": [{"name": "Mleko", "qty": "2", "unit_price": "1.50", "line_total": "3.00"}],
        "total": "3.00",
        "payments": [{"method": "cash", "amount": "5.00"}],
        "zoi": "abc",
        "eor": "def",
    })
    out = capsys.readouterr().out
    assert "Mleko" in out
    assert "3.00" in out


def test_set_token():
    """set_token modifies auth header."""
    import cashier.api_client as api
    api.set_token("mytoken")
    headers = api._headers()
    assert headers["Authorization"] == "Bearer mytoken"
    api.set_token(None)  # cleanup
    headers2 = api._headers()
    assert "Authorization" not in headers2 or headers2.get("Authorization") is None
