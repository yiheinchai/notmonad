"""Ring-style HTTP as ``chain(..., Seq)`` procedures (request/response dicts)."""

from __future__ import annotations

from html import escape
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

from notmonad.data import assoc, dmerge
from notmonad.monads import Seq, chain
from notmonad.ops import get, if_else, switch, tap, while_loop

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

_void = frozenset({"br", "hr", "img", "input", "meta", "link"})

_qs_map = lambda qs: (
    chain(list(parse_qs(qs, keep_blank_values=True).items()), Seq)(
        lambda items: {
            key: (vals[0] if len(vals) == 1 else vals) for key, vals in items
        }
    )()
)

_http_headers = lambda environ: (
    chain({"items": list(environ.items()), "headers": {}}, Seq)(
        while_loop,
        lambda state: {
            "items": state["items"][1:],
            "headers": {
                **state["headers"],
                state["items"][0][0][5:].lower().replace("_", "-"): state["items"][0][
                    1
                ],
            }
            if state["items"][0][0].startswith("HTTP_")
            else state["headers"],
        },
        cond=lambda state: bool(state["items"]),
    )(get, "headers")(
        lambda headers: dmerge(
            headers,
            {"content-type": environ["CONTENT_TYPE"]}
            if "CONTENT_TYPE" in environ
            else {},
        )
    )()
)

_form_from = lambda raw, headers: (
    chain(raw, Seq)(
        if_else,
        lambda body: bool(body)
        and "application/x-www-form-urlencoded"
        in (headers.get("content-type") or ""),
        lambda body: _qs_map(body.decode("utf-8", errors="replace")),
        {},
    )()
)

request_from_environ = lambda environ: (
    chain(environ, Seq)(__post="env", __retain=True)(
        lambda env: (env.get("REQUEST_METHOD") or "GET").lower()
    )(__post="method")(__get="env", __retain=True)(
        lambda env: int(env.get("CONTENT_LENGTH") or 0)
    )(__post="length")(__get="env", __retain=True)(
        lambda env: lambda length: env["wsgi.input"].read(length) if length else b""
    )(__get="length", __call=True)(__post="raw")(__get="env", __retain=True)(
        _http_headers
    )(__post="headers")(__get="raw", __retain=True)(
        lambda raw: lambda headers: _form_from(raw, headers)
    )(__get="headers", __retain=True, __call=True)(__post="form")(
        __get="env", __retain=True
    )(
        lambda env: env.get("PATH_INFO") or "/"
    )(__post="path")(__get="env", __retain=True)(
        lambda env: env.get("HTTP_HOST") or env.get("SERVER_NAME") or "localhost"
    )(__post="host")(__get="env", __retain=True)(
        lambda env: env.get("wsgi.url_scheme", "http")
    )(__post="scheme")(__get="env", __retain=True)(
        lambda env: _qs_map(env.get("QUERY_STRING", ""))
    )(__post="params")(__get="env")(
        lambda env: lambda method: lambda raw: lambda headers: lambda path: lambda host: lambda scheme: lambda form: lambda params: {
            "server-port": int(env.get("SERVER_PORT") or 80),
            "uri": path,
            "query-string": env.get("QUERY_STRING") or "",
            "request-method": method,
            "headers": headers,
            "body": raw.decode("utf-8", errors="replace") if raw else "",
            "params": params,
            "form": form,
            "scheme": scheme,
            "remote-addr": env.get("REMOTE_ADDR"),
            "url": f"{scheme}://{host}{path}",
        }
    )(__get="method", __call=True)(__get="raw", __call=True)(
        __get="headers", __call=True
    )(__get="path", __call=True)(__get="host", __call=True)(
        __get="scheme", __call=True
    )(__get="form", __call=True)(__get="params", __call=True)()
)

response = lambda status, body="", headers=None: (
    chain(status, Seq)(
        lambda code: {
            "status": int(code),
            "body": body,
            "headers": dict(headers or {}),
        }
    )()
)

redirect = lambda url, status=302, headers=None: (
    chain(dict(headers or {}), Seq)(assoc, "Location", url)(
        lambda hdrs: response(status, "", hdrs)
    )()
)

_render_element = lambda node: (
    chain(node, Seq)(__post="node", __retain=True)(lambda tree: tree[0])(
        __post="tag"
    )(__get="node", __retain=True)(
        lambda tree: tree[1]
        if len(tree) > 1 and isinstance(tree[1], dict)
        else {}
    )(__post="attrs")(__get="node")(
        lambda tree: tree[2:]
        if len(tree) > 1 and isinstance(tree[1], dict)
        else tree[1:]
    )(lambda children: "".join(html(child) for child in children))(__post="inner")(
        __get="attrs"
    )(
        lambda attrs: "".join(
            f' {key}="{escape(str(val), quote=True)}"'
            for key, val in attrs.items()
            if val is not None and val is not False
        )
    )(__post="attr_s")(__get="tag", __retain=True)(
        lambda tag: lambda attr_s: lambda inner: (
            f"<{tag}{attr_s}>" if tag in _void else f"<{tag}{attr_s}>{inner}</{tag}>"
        )
    )(__get="attr_s", __call=True)(__get="inner", __call=True)()
)

html = lambda node: switch(
    node,
    (
        (lambda tree: tree is None or tree is False, ""),
        (
            lambda tree: isinstance(tree, (str, int, float)),
            lambda tree: escape(str(tree)),
        ),
        (
            lambda tree: isinstance(tree, (list, tuple))
            and bool(tree)
            and isinstance(tree[0], str),
            _render_element,
        ),
        (
            lambda tree: isinstance(tree, (list, tuple)),
            lambda tree: "".join(html(child) for child in tree),
        ),
    ),
    lambda tree: escape(str(tree)),
)

html_response = lambda node, status=200, headers=None: (
    chain(html(node), Seq)(
        lambda body: response(
            status,
            body,
            dmerge(
                {"Content-Type": "text/html; charset=utf-8"},
                dict(headers or {}),
            ),
        )
    )()
)

_match_step = lambda state: (
    chain(state, Seq)(__post="state", __retain=True)(
        lambda item: item["p"][0]
    )(__post="pat")(__get="state", __retain=True)(lambda item: item["u"][0])(
        __post="got"
    )(__get="state")(
        lambda item: lambda pat: lambda got: {
            **item,
            "p": item["p"][1:],
            "u": item["u"][1:],
            "params": {**item["params"], pat[1:]: got},
        }
        if pat.startswith(":")
        else {**item, "p": item["p"][1:], "u": item["u"][1:]}
        if pat == got
        else {**item, "p": [], "u": [], "ok": False}
    )(__get="pat", __call=True)(__get="got", __call=True)()
)

match_path = lambda pattern, uri: (
    chain(
        {
            "p": [part for part in pattern.split("/") if part != ""],
            "u": [part for part in uri.split("?")[0].split("/") if part != ""],
            "params": {},
            "ok": True,
        },
        Seq,
    )(
        if_else,
        lambda state: len(state["p"]) != len(state["u"]),
        lambda state: {**state, "ok": False, "p": [], "u": []},
        lambda state: state,
    )(
        while_loop,
        _match_step,
        cond=lambda state: state["ok"] and bool(state["p"]),
    )(
        if_else,
        lambda state: state["ok"],
        lambda state: state["params"],
        lambda _: None,
    )()
)

route = lambda method, path, handler: (
    chain(method, Seq)(
        lambda verb: {"method": verb.lower(), "path": path, "handler": handler}
    )()
)

GET = lambda path, handler: route("get", path, handler)
POST = lambda path, handler: route("post", path, handler)

_consider_route = lambda state: (
    chain(state["routes"][0], Seq)(__post="item", __retain=True)(
        lambda item: match_path(
            str(item["path"]), str(state["request"].get("uri") or "/")
        )
    )(__post="params")(__get="item")(
        lambda item: lambda params: {
            **state,
            "routes": state["routes"][1:],
            "matched": {"handler": item["handler"], "params": params}
            if params is not None
            and str(item.get("method") or "get").lower()
            in (
                str(state["request"].get("request-method") or "get").lower(),
                "any",
            )
            else None,
        }
    )(__get="params", __call=True)()
)

router = lambda routes, not_found=None: lambda request: (
    chain(
        {"routes": list(routes), "request": request, "matched": None},
        Seq,
    )(
        while_loop,
        _consider_route,
        cond=lambda state: state["matched"] is None and bool(state["routes"]),
    )(
        if_else,
        lambda state: state["matched"] is not None,
        lambda state: state["matched"]["handler"](
            {
                **state["request"],
                "params": {
                    **(state["request"].get("params") or {}),
                    **state["matched"]["params"],
                },
                "route-params": state["matched"]["params"],
            }
        ),
        lambda _: not_found(request)
        if not_found is not None
        else response(404, "Not found"),
    )()
)

wrap = lambda handler, *middleware: (
    chain({"app": handler, "mws": list(middleware)}, Seq)(
        while_loop,
        lambda state: {
            "app": state["mws"][0](state["app"]),
            "mws": state["mws"][1:],
        },
        cond=lambda state: bool(state["mws"]),
    )(get, "app")()
)

invoke = lambda handler, request: (
    chain(request, Seq)(
        lambda req: dmerge(
            {
                "request-method": "get",
                "uri": "/",
                "params": {},
                "form": {},
                "headers": {},
                "body": "",
            },
            req,
        )
    )(handler)(
        lambda result=None: result
        if isinstance(result, dict) and "status" in result
        else response(200, result)
    )()
)

response_bytes = lambda resp: (
    chain(resp, Seq)(__post="resp", __retain=True)(
        lambda item: int(item.get("status") or 200)
    )(__post="status")(__get="resp", __retain=True)(
        lambda item: item.get("body") or ""
    )(
        lambda body: body if isinstance(body, bytes) else str(body).encode("utf-8")
    )(__post="data")(__get="resp")(
        lambda item: [(str(key), str(value)) for key, value in (item.get("headers") or {}).items()]
    )(__post="headers")(__get="headers", __retain=True)(
        lambda headers: headers
        + (
            []
            if any(key.lower() == "content-type" for key, _ in headers)
            else [("Content-Type", "text/html; charset=utf-8")]
        )
    )(lambda headers: lambda data: headers + [("Content-Length", str(len(data)))])(
        __get="data", __retain=True, __call=True
    )(__post="headers")(__get="status")(
        lambda status: lambda headers: lambda data: (
            f"{status} {_STATUS.get(status, 'OK')}",
            headers,
            data,
        )
    )(__get="headers", __call=True)(__get="data", __call=True)()
)

wsgi_app = lambda handler: lambda environ, start_response: (
    chain(environ, Seq)(request_from_environ)(
        lambda req: invoke(handler, req)
    )(response_bytes)(
        tap, lambda packed: start_response(packed[0], packed[1])
    )(lambda packed: [packed[2]])()
)

serve = lambda handler, port=8000, host="127.0.0.1": (
    chain((host, int(port), handler), Seq)(
        lambda spec: make_server(spec[0], spec[1], wsgi_app(spec[2]))
    )(
        tap,
        lambda _httpd: print(f"notmonad serving on http://{host}:{port}"),
    )(lambda httpd: httpd.serve_forever())()
)
