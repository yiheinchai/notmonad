from examples.bank import app, reset_db, seed
from notmonad.web import invoke


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


def test_home_redirects_until_login():
    assert _req("get", "/")["status"] == 302
    page = _req("get", "/login")
    assert page["status"] == 200
    assert "NotMonad Bank" in page["body"]


def test_alice_sends_bob_with_a_note():
    headers = _auth("alice", "alice")
    home = _req("get", "/", headers=headers)
    assert home["status"] == 200
    assert "$1000" in home["body"]
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
    assert "to bob" in alice["body"]
    bob = _req("get", "/", headers=_auth("bob", "bob"))
    assert "$540" in bob["body"]
    assert "concert tickets" in bob["body"]
    assert "from alice" in bob["body"]


def test_send_rejects_overdraft_and_unknown_user():
    headers = _auth("carol", "carol")
    poor = _req(
        "post",
        "/send",
        {"to": "alice", "amount": "9999", "note": "nope"},
        headers,
    )
    assert poor["status"] == 400
    assert "Insufficient funds" in poor["body"]
    missing = _req(
        "post",
        "/send",
        {"to": "nobody", "amount": "1", "note": "hi"},
        headers,
    )
    assert missing["status"] == 400
    assert "No account" in missing["body"]


def test_open_account_starts_with_one_hundred():
    created = _req(
        "post", "/register", {"username": "dave", "password": "dave"}
    )
    assert created["status"] == 302
    home = _req("get", "/", headers={"cookie": f"sid={_sid(created)}"})
    assert home["status"] == 200
    assert "$100" in home["body"]
    assert "Hello, dave" in home["body"]
