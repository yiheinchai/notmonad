"""Ring-style HTTP as ordinary Python functions (request/response dicts)."""

from __future__ import annotations

from html import escape
from io import BytesIO
from typing import Any, Callable
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

_STATUS = {
    200: "OK",
    201: "Created",
    302: "Found",
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    500: "Internal Server Error",
}


def request_from_environ(environ: dict) -> dict:
    method = (environ.get("REQUEST_METHOD") or "GET").lower()
    query = parse_qs(environ.get("QUERY_STRING", ""), keep_blank_values=True)
    params = {key: (vals[0] if len(vals) == 1 else vals) for key, vals in query.items()}
    length = int(environ.get("CONTENT_LENGTH") or 0)
    raw = environ["wsgi.input"].read(length) if length else b""
    headers = {}
    for key, value in environ.items():
        if key.startswith("HTTP_"):
            headers[key[5:].lower().replace("_", "-")] = value
    if "CONTENT_TYPE" in environ:
        headers["content-type"] = environ["CONTENT_TYPE"]
    form = {}
    ctype = headers.get("content-type", "")
    if raw and "application/x-www-form-urlencoded" in ctype:
        decoded = parse_qs(raw.decode("utf-8", errors="replace"), keep_blank_values=True)
        form = {key: (vals[0] if len(vals) == 1 else vals) for key, vals in decoded.items()}
    path = environ.get("PATH_INFO") or "/"
    host = environ.get("HTTP_HOST") or environ.get("SERVER_NAME") or "localhost"
    scheme = environ.get("wsgi.url_scheme", "http")
    return {
        "server-port": int(environ.get("SERVER_PORT") or 80),
        "uri": path,
        "query-string": environ.get("QUERY_STRING") or "",
        "request-method": method,
        "headers": headers,
        "body": raw.decode("utf-8", errors="replace") if raw else "",
        "params": params,
        "form": form,
        "scheme": scheme,
        "remote-addr": environ.get("REMOTE_ADDR"),
        "url": f"{scheme}://{host}{path}",
    }


def response(status: int, body: Any = "", headers: dict | None = None) -> dict:
    return {"status": int(status), "body": body, "headers": dict(headers or {})}


def redirect(url: str, status: int = 302, headers: dict | None = None) -> dict:
    hdrs = dict(headers or {})
    hdrs["Location"] = url
    return response(status, "", hdrs)


def html(node: Any) -> str:
    """Render hiccup lists: ``[\"tag\", {attrs}, children...]``."""
    if node is None or node is False:
        return ""
    if isinstance(node, (str, int, float)):
        return escape(str(node))
    if isinstance(node, (list, tuple)):
        if not node:
            return ""
        if isinstance(node[0], str):
            tag = node[0]
            rest = list(node[1:])
            attrs = rest.pop(0) if rest and isinstance(rest[0], dict) else {}
            attr_s = "".join(
                f' {key}="{escape(str(val), quote=True)}"'
                for key, val in attrs.items()
                if val is not None and val is not False
            )
            inner = "".join(html(child) for child in rest)
            if tag in {"br", "hr", "img", "input", "meta", "link"}:
                return f"<{tag}{attr_s}>"
            return f"<{tag}{attr_s}>{inner}</{tag}>"
        return "".join(html(child) for child in node)
    return escape(str(node))


def html_response(node: Any, status: int = 200, headers: dict | None = None) -> dict:
    hdrs = dict(headers or {})
    hdrs.setdefault("Content-Type", "text/html; charset=utf-8")
    return response(status, html(node), hdrs)


def match_path(pattern: str, uri: str) -> dict | None:
    p_parts = [p for p in pattern.split("/") if p != ""]
    u_parts = [p for p in uri.split("?")[0].split("/") if p != ""]
    if len(p_parts) != len(u_parts):
        return None
    params = {}
    for pat, got in zip(p_parts, u_parts):
        if pat.startswith(":"):
            params[pat[1:]] = got
        elif pat != got:
            return None
    return params


def route(method: str, path: str, handler: Callable) -> dict:
    return {"method": method.lower(), "path": path, "handler": handler}


GET = lambda path, handler: route("get", path, handler)
POST = lambda path, handler: route("post", path, handler)


def router(routes, not_found: Callable | None = None) -> Callable:
    def handler(request):
        method = str(request.get("request-method") or "get").lower()
        uri = request.get("uri") or "/"
        for item in routes:
            want = str(item.get("method") or "get").lower()
            if want not in (method, "any"):
                continue
            params = match_path(str(item["path"]), str(uri))
            if params is None:
                continue
            merged = {
                **request,
                "params": {**(request.get("params") or {}), **params},
                "route-params": params,
            }
            return item["handler"](merged)
        if not_found is not None:
            return not_found(request)
        return response(404, "Not found")

    return handler


def wrap(handler: Callable, *middleware: Callable) -> Callable:
    """``wrap(handler, mw1, mw2)`` → ``mw2(mw1(handler))`` — mw2 is outermost."""
    app = handler
    for mw in middleware:
        app = mw(app)
    return app


def invoke(handler: Callable, request: dict) -> dict:
    req = {
        "request-method": "get",
        "uri": "/",
        "params": {},
        "form": {},
        "headers": {},
        "body": "",
        **request,
    }
    result = handler(req)
    if isinstance(result, dict) and "status" in result:
        return result
    return response(200, result)


def response_bytes(resp: dict) -> tuple[str, list[tuple[str, str]], bytes]:
    status = int(resp.get("status") or 200)
    body = resp.get("body") or ""
    data = body if isinstance(body, bytes) else str(body).encode("utf-8")
    headers = []
    has_type = False
    for key, value in (resp.get("headers") or {}).items():
        if str(key).lower() == "content-type":
            has_type = True
        headers.append((str(key), str(value)))
    if not has_type:
        headers.append(("Content-Type", "text/html; charset=utf-8"))
    headers.append(("Content-Length", str(len(data))))
    return f"{status} {_STATUS.get(status, 'OK')}", headers, data


def wsgi_app(handler: Callable) -> Callable:
    def app(environ, start_response):
        resp = invoke(handler, request_from_environ(environ))
        status, headers, data = response_bytes(resp)
        start_response(status, headers)
        return [data]

    return app


def serve(handler: Callable, port: int = 8000, host: str = "127.0.0.1"):
    httpd = make_server(host, int(port), wsgi_app(handler))
    print(f"notmonad serving on http://{host}:{port}")
    httpd.serve_forever()
