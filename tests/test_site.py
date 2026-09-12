from io import BytesIO

from examples.site.core import app
from examples.site.db import reset_db, seed
from notmonad.web import invoke, wsgi_app


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


def test_home_lists_seeded_posts():
    response = _req("get", "/")
    assert response["status"] == 200
    assert "Hello from notmonad" in response["body"]
    assert "Pipelines all the way down" in response["body"]


def test_post_detail_and_404():
    ok = _req("get", "/posts/1")
    assert ok["status"] == 200
    assert "Hello from notmonad" in ok["body"]
    missing = _req("get", "/posts/999")
    assert missing["status"] == 404


def test_create_post_then_see_it_on_home():
    created = _req(
        "post",
        "/posts/new",
        form={"title": "Lisp-shaped Python", "body": "no def"},
    )
    assert created["status"] == 302
    home = _req("get", "/")
    assert "Lisp-shaped Python" in home["body"]


def test_login_sets_cookie_and_admin_requires_auth():
    forbidden = _req("get", "/admin")
    assert forbidden["status"] == 403
    login = _req(
        "post", "/login", form={"username": "admin", "password": "admin"}
    )
    assert login["status"] == 302
    cookie = login["headers"]["Set-Cookie"]
    assert cookie.startswith("sid=")
    sid = cookie.split(";")[0].split("=", 1)[1]
    admin = _req("get", "/admin", headers={"cookie": f"sid={sid}"})
    assert admin["status"] == 200
    assert "admin" in admin["body"]


def test_wsgi_get_home():
    captured = []

    def start_response(status, headers):
        captured.append((status, headers))

    environ = {
        "REQUEST_METHOD": "GET",
        "PATH_INFO": "/",
        "QUERY_STRING": "",
        "SERVER_PORT": "80",
        "CONTENT_LENGTH": "0",
        "wsgi.input": BytesIO(),
        "wsgi.url_scheme": "http",
        "REMOTE_ADDR": "127.0.0.1",
        "SERVER_NAME": "test",
    }
    body = b"".join(wsgi_app(app)(environ, start_response))
    assert captured[0][0].startswith("200")
    assert b"NotMonad Press" in body
    assert b"Hello from notmonad" in body
