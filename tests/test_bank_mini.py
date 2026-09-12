import runpy
from pathlib import Path

from notmonad.web import invoke

MINI = Path(__file__).resolve().parents[1] / "examples" / "bank.mini.py"
_ns = runpy.run_path(str(MINI), run_name="bank_mini")
app = _ns["app"]
reset_db = _ns["reset_db"]
seed = _ns["seed"]


def setup_function():
    reset_db()
    seed()


def _req(method, uri, form=None, headers=None):
    return invoke(
        app,
        {
            "request-method": method,
            "uri": uri,
            "form": form or {},
            "headers": headers or {},
        },
    )


def _sid(response):
    cookie = response["headers"]["Set-Cookie"]
    return cookie.split(";")[0].split("=", 1)[1]


def _auth(username, password):
    login = _req("post", "/login", {"username": username, "password": password})
    return {"cookie": f"sid={_sid(login)}"}


def test_mini_home_redirects_until_login():
    assert _req("get", "/")["status"] == 302
    page = _req("get", "/login")
    assert page["status"] == 200
    assert "NotMonad Bank" in page["body"]


def test_mini_alice_sends_bob_with_a_note():
    headers = _auth("alice", "alice")
    sent = _req(
        "post",
        "/send",
        {"to": "bob", "amount": "40", "note": "concert tickets"},
        headers,
    )
    assert sent["status"] == 302
    alice = _req("get", "/", headers=headers)
    assert "$960" in alice["body"]
    assert "concert tickets" in alice["body"]
    bob = _req("get", "/", headers=_auth("bob", "bob"))
    assert "$540" in bob["body"]
    assert "from alice" in bob["body"]


def test_mini_open_account_starts_with_one_hundred():
    created = _req(
        "post", "/register", {"username": "dave", "password": "dave"}
    )
    assert created["status"] == 302
    home = _req("get", "/", headers={"cookie": f"sid={_sid(created)}"})
    assert "$100" in home["body"]
    assert "Hello, dave" in home["body"]
