"""The whole NotMonad Press site as one chain(..., App) expression.

Helpers are memory slots (procedural locals). Nothing is declared and then
referred to by name: store, HTTP, queries, views, middleware, and routes are
stashed with __post and applied with __get / __call. HTTP helpers are not
imported: html, router, and responses are built in this same expression.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from notmonad import (
    App,
    Maybe,
    Seq,
    assoc,
    assoc_in,
    atom,
    chain,
    deref,
    dmerge,
    get,
    get_in,
    if_else,
    inc,
    recover,
    swap,
    switch,
    tap,
    when,
    while_loop,
)

app, reset_db, seed = chain(
    atom(
        {
            "users": {},
            "posts": {},
            "sessions": {},
            "ids": {"users": 0, "posts": 0, "sessions": 0},
        }
    ),
    App,
)(__post="store", __retain=True)(
    lambda _store: (
        lambda box: (
            lambda esc: (
                box.reset(
                    lambda node: switch(
                        node,
                        (
                            (lambda t: t is None or t is False, ""),
                            (
                                lambda t: isinstance(t, (str, int, float)),
                                lambda t: esc(t),
                            ),
                            (
                                lambda t: isinstance(t, (list, tuple))
                                and bool(t)
                                and isinstance(t[0], str),
                                lambda n: chain(n, Seq)(
                                    __post="n", __retain=True
                                )(lambda tree: tree[0])(__post="tag")(
                                    __get="n", __retain=True
                                )(
                                    lambda tree: tree[1]
                                    if len(tree) > 1
                                    and isinstance(tree[1], dict)
                                    else {}
                                )(__post="attrs")(__get="n")(
                                    lambda tree: tree[2:]
                                    if len(tree) > 1
                                    and isinstance(tree[1], dict)
                                    else tree[1:]
                                )(
                                    lambda children: "".join(
                                        deref(box)(child)
                                        for child in children
                                    )
                                )(__post="inner")(__get="attrs")(
                                    lambda attrs: "".join(
                                        f' {key}="{esc(val, True)}"'
                                        for key, val in attrs.items()
                                        if val is not None
                                        and val is not False
                                    )
                                )(__post="attr_s")(
                                    __get="tag", __retain=True
                                )(
                                    lambda tag: lambda attr_s: lambda inner: (
                                        f"<{tag}{attr_s}>"
                                        if tag
                                        in {
                                            "br",
                                            "hr",
                                            "img",
                                            "input",
                                            "meta",
                                            "link",
                                        }
                                        else f"<{tag}{attr_s}>{inner}</{tag}>"
                                    )
                                )(__get="attr_s", __call=True)(
                                    __get="inner", __call=True
                                )()
                            ),
                            (
                                lambda t: isinstance(t, (list, tuple)),
                                lambda t: "".join(
                                    deref(box)(child) for child in t
                                ),
                            ),
                        ),
                        lambda t: esc(t),
                    )
                ),
                {
                    "html": deref(box),
                    "response": lambda status, body="", headers=None: chain(
                        status, Seq
                    )(
                        lambda code: {
                            "status": int(code),
                            "body": body,
                            "headers": dict(headers or {}),
                        }
                    )(),
                    "html_response": lambda node, status=200, headers=None: chain(
                        deref(box)(node), Seq
                    )(
                        lambda body: {
                            "status": int(status),
                            "body": body,
                            "headers": dmerge(
                                {
                                    "Content-Type": "text/html; charset=utf-8"
                                },
                                dict(headers or {}),
                            ),
                        }
                    )(),
                    "redirect": lambda url, status=302, headers=None: chain(
                        dict(headers or {}), Seq
                    )(assoc, "Location", url)(
                        lambda hdrs: {
                            "status": int(status),
                            "body": "",
                            "headers": hdrs,
                        }
                    )(),
                    "GET": lambda path, handler: {
                        "method": "get",
                        "path": path,
                        "handler": handler,
                    },
                    "POST": lambda path, handler: {
                        "method": "post",
                        "path": path,
                        "handler": handler,
                    },
                    "router": lambda routes, not_found=None: lambda request: chain(
                        {
                            "routes": list(routes),
                            "request": request,
                            "matched": None,
                        },
                        Seq,
                    )(
                        while_loop,
                        lambda state: chain(state["routes"][0], Seq)(
                            __post="item", __retain=True
                        )(
                            lambda item: (
                                lambda pattern, uri: chain(
                                    {
                                        "p": [
                                            part
                                            for part in pattern.split("/")
                                            if part != ""
                                        ],
                                        "u": [
                                            part
                                            for part in uri.split("?")[0].split(
                                                "/"
                                            )
                                            if part != ""
                                        ],
                                        "params": {},
                                        "ok": True,
                                    },
                                    Seq,
                                )(
                                    if_else,
                                    lambda s: len(s["p"]) != len(s["u"]),
                                    lambda s: {
                                        **s,
                                        "ok": False,
                                        "p": [],
                                        "u": [],
                                    },
                                    lambda s: s,
                                )(
                                    while_loop,
                                    lambda s: chain(s, Seq)(
                                        __post="st", __retain=True
                                    )(lambda x: x["p"][0])(__post="pat")(
                                        __get="st", __retain=True
                                    )(lambda x: x["u"][0])(__post="got")(
                                        __get="st"
                                    )(
                                        lambda item: lambda pat: lambda got: (
                                            {
                                                **item,
                                                "p": item["p"][1:],
                                                "u": item["u"][1:],
                                                "params": {
                                                    **item["params"],
                                                    pat[1:]: got,
                                                },
                                            }
                                            if pat.startswith(":")
                                            else {
                                                **item,
                                                "p": item["p"][1:],
                                                "u": item["u"][1:],
                                            }
                                            if pat == got
                                            else {
                                                **item,
                                                "p": [],
                                                "u": [],
                                                "ok": False,
                                            }
                                        )
                                    )(__get="pat", __call=True)(
                                        __get="got", __call=True
                                    )(),
                                    cond=lambda s: s["ok"] and bool(s["p"]),
                                )(
                                    if_else,
                                    lambda s: s["ok"],
                                    lambda s: s["params"],
                                    lambda _: None,
                                )()
                            )(
                                str(item["path"]),
                                str(state["request"].get("uri") or "/"),
                            )
                        )(__post="params")(__get="item")(
                            lambda item: lambda params: {
                                **state,
                                "routes": state["routes"][1:],
                                "matched": {
                                    "handler": item["handler"],
                                    "params": params,
                                }
                                if params is not None
                                and str(item.get("method") or "get").lower()
                                in (
                                    str(
                                        state["request"].get("request-method")
                                        or "get"
                                    ).lower(),
                                    "any",
                                )
                                else None,
                            }
                        )(__get="params", __call=True)(),
                        cond=lambda state: state["matched"] is None
                        and bool(state["routes"]),
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
                        else {
                            "status": 404,
                            "body": "Not found",
                            "headers": {},
                        },
                    )(),
                },
            )[1]
        )(
            lambda text, quote=False: (
                str(text)
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                if quote
                else str(text)
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )
        )
    )(atom(None))
)(__post="web")(__get="store", __retain=True)(
    lambda store: (
        lambda table: chain(deref(store), App)(get_in, ["ids", table], 0)(
            inc
        )(tap, lambda ident: swap(store, assoc_in, ["ids", table], ident))()
    )
)(__post="next_id")(__get="store", __retain=True)(
    lambda store: lambda next_id: (
        lambda table, row: chain(row, App)(__post="row")(__mount=table)(
            next_id
        )(lambda ident: lambda saved: assoc(saved, "id", ident))(
            __get="row", __call=True
        )(
            tap,
            lambda saved: swap(store, assoc_in, [table, saved["id"]], saved),
        )()
    )
)(__get="next_id", __call=True)(__post="insert")(
    __get="store", __retain=True
)(
    lambda store: (
        lambda table: chain(deref(store), App)(get, table, {})(
            lambda rows: list(rows.values())
        )()
    )
)(__post="all_rows")(__get="store", __retain=True)(
    lambda store: (
        lambda table, ident: chain(
            ident if ident is not None else "", App
        )(if_else, bool, lambda key: int(key), 0)(
            lambda key: get_in(deref(store), [table, key], {})
        )()
    )
)(__post="fetch")(__get="all_rows", __retain=True)(
    lambda all_rows: (
        lambda username: chain("users", App)(all_rows)(
            lambda users: next(
                (
                    user
                    for user in users
                    if user.get("username") == username
                ),
                {},
            )
        )()
    )
)(__post="find_user")(__get="fetch", __retain=True)(
    lambda fetch: (
        lambda request: chain(request, App)(
            get_in, ["session", "user-id"], 0
        )(if_else, bool, lambda uid: fetch("users", uid), {})()
    )
)(__post="current_user")(__get="find_user", __retain=True)(
    lambda find_user: lambda insert: (
        lambda username, password: chain(username, App)(find_user)(
            __post="user", __retain=True
        )(
            if_else,
            lambda user: bool(user.get("id"))
            and user.get("password") == password,
            True,
            False,
        )(
            if_else,
            bool,
            lambda _: lambda user: insert(
                "sessions", {"user-id": user["id"]}
            ),
            lambda _: lambda user: {},
        )(__get="user", __call=True)()
    )
)(__get="insert", __retain=True, __call=True)(__post="login")(
    __get="current_user", __retain=True
)(
    lambda current_user: (
        lambda request: chain(request, App)(current_user)(get, "role", "")(
            lambda role: role == "admin"
        )()
    )
)(__post="is_admin")(
    __mount=lambda header: chain(header or "", App)(
        lambda h: [part.strip() for part in str(h).split(";") if part.strip()]
    )(
        lambda parts: [part.split("=", 1) for part in parts if "=" in part]
    )(lambda pairs: dict((key.strip(), val.strip()) for key, val in pairs))()
)(__post="parse_cookies")(
    __mount=lambda title, body: [
        "html",
        [
            "head",
            ["meta", {"charset": "utf-8"}],
            ["title", title],
            [
                "style",
                "body{font-family:Georgia,serif;max-width:42rem;margin:2rem auto;padding:0 1rem;line-height:1.5;color:#222}nav a{margin-right:1rem}article{border-bottom:1px solid #ddd;padding:0.6rem 0}form label{display:block;margin:0.6rem 0}input,textarea{width:100%;padding:0.4rem}button{padding:0.4rem 0.8rem}",
            ],
        ],
        [
            "body",
            [
                "header",
                ["h1", ["a", {"href": "/"}, "NotMonad Press"]],
                [
                    "nav",
                    ["a", {"href": "/"}, "Home"],
                    ["a", {"href": "/posts/new"}, "New post"],
                    ["a", {"href": "/login"}, "Login"],
                    ["a", {"href": "/admin"}, "Admin"],
                ],
            ],
            body,
            [
                "footer",
                ["p", "A Django-shaped app: pure Python, no def or class."],
            ],
        ],
    ]
)(__post="layout")(
    __mount=lambda: [
        "form",
        {"method": "post", "action": "/posts/new"},
        ["label", "Title", ["input", {"name": "title", "required": "required"}]],
        ["label", "Body", ["textarea", {"name": "body", "rows": "6"}]],
        ["button", {"type": "submit"}, "Publish"],
    ]
)(__post="post_form")(
    __mount=lambda: [
        "form",
        {"method": "post", "action": "/login"},
        ["label", "Username", ["input", {"name": "username"}]],
        [
            "label",
            "Password",
            ["input", {"name": "password", "type": "password"}],
        ],
        ["button", {"type": "submit"}, "Sign in"],
    ]
)(__post="login_form")(__get="all_rows", __retain=True)(
    lambda all_rows: lambda insert: (
        lambda: chain("users", App)(all_rows)(lambda rows: not rows)(
            __post="empty", __retain=True
        )(
            when,
            bool,
            lambda _: insert(
                "users",
                {"username": "admin", "password": "admin", "role": "admin"},
            ),
        )(__get="empty", __retain=True)(
            when,
            bool,
            lambda _: insert(
                "posts",
                {
                    "title": "Hello from notmonad",
                    "body": "This site is a Python library: models, views, urls, middleware — no def or class.",
                    "author": "admin",
                },
            ),
        )(__get="empty")(
            when,
            bool,
            lambda _: insert(
                "posts",
                {
                    "title": "Pipelines all the way down",
                    "body": "Request dicts flow through middleware and routes the same way data flows through chain.",
                    "author": "admin",
                },
            ),
        )()
    )
)(__get="insert", __retain=True, __call=True)(__post="seed", __retain=True)(
    tap, lambda fn: fn()
)(__get="web", __retain=True)(
    lambda web: lambda insert: lambda all_rows: lambda fetch: lambda current_user: lambda login: lambda is_admin: lambda layout: lambda post_form: lambda login_form: web["router"](
        [
            web["GET"](
                "/",
                lambda request: chain("posts", App)(all_rows)(
                    lambda posts: [
                        "div",
                        ["h2", "Posts"],
                        ["p", "No posts yet."]
                        if not posts
                        else [
                            [
                                "article",
                                [
                                    "h3",
                                    [
                                        "a",
                                        {"href": f"/posts/{post['id']}"},
                                        post["title"],
                                    ],
                                ],
                                ["p", post["body"]],
                                ["small", f"by {post['author']}"],
                            ]
                            for post in posts
                        ],
                    ]
                )(lambda body: layout("Home", body))(web["html_response"])(),
            ),
            web["GET"](
                "/posts/new",
                lambda request: chain(post_form(), App)(
                    lambda form: layout("New post", form)
                )(web["html_response"])(),
            ),
            web["POST"](
                "/posts/new",
                lambda request: chain(request, App)(
                    __post="req", __retain=True
                )(get_in, ["form", "title"], "")(__post="title")(
                    __get="req", __retain=True
                )(get_in, ["form", "body"], "")(__post="body")(__get="req")(
                    current_user
                )(__post="user")(__get="title", __retain=True)(
                    if_else, bool, 302, 400
                )(__post="status")(__get="title", __retain=True)(
                    lambda title: lambda body: lambda user: {
                        "title": title,
                        "body": body,
                        "author": user.get("username") or "anonymous",
                    }
                )(__get="body", __call=True)(__get="user", __call=True)(
                    __post="row"
                )(__get="status", __retain=True)(
                    if_else,
                    lambda status: status == 302,
                    lambda _: lambda row: insert("posts", row),
                    lambda _: lambda row: row,
                )(__get="row", __call=True)(__get="status")(
                    if_else,
                    lambda status: status == 302,
                    lambda _: web["redirect"]("/"),
                    lambda _: web["html_response"](
                        layout(
                            "New post",
                            [
                                "div",
                                ["p", "Title is required."],
                                post_form(),
                            ],
                        ),
                        400,
                    ),
                )(),
            ),
            web["GET"](
                "/posts/:id",
                lambda request: chain(request, App)(
                    get_in, ["params", "id"], ""
                )(lambda pid: fetch("posts", pid))(
                    __post="post", __retain=True
                )(if_else, lambda post: post.get("id"), 200, 404)(
                    __post="status"
                )(__get="post", __retain=True)(
                    if_else,
                    lambda post: post.get("id"),
                    lambda post: [
                        "article",
                        ["h2", post["title"]],
                        ["p", post["body"]],
                        ["p", ["small", f"by {post['author']}"]],
                        ["p", ["a", {"href": "/"}, "Back"]],
                    ],
                    ["p", "No such post."],
                )(__post="body")(__get="post")(
                    if_else,
                    lambda post: post.get("id"),
                    lambda post: post["title"],
                    "Not found",
                )(lambda title: lambda body: layout(title, body))(
                    __get="body", __call=True
                )(lambda node: lambda status: web["html_response"](node, status))(
                    __get="status", __call=True
                )(),
            ),
            web["GET"](
                "/login",
                lambda request: chain(login_form(), App)(
                    lambda form: layout("Login", form)
                )(web["html_response"])(),
            ),
            web["POST"](
                "/login",
                lambda request: chain(request, App)(get, "form", {})(
                    lambda form: login(
                        form.get("username") or "",
                        form.get("password") or "",
                    )
                )(__post="sess", __retain=True)(
                    if_else, lambda sess: sess.get("id"), 302, 401
                )(__post="status")(__get="sess")(
                    if_else,
                    lambda sess: sess.get("id"),
                    lambda sess: lambda _: web["redirect"](
                        "/",
                        headers={
                            "Set-Cookie": f"sid={sess['id']}; Path=/"
                        },
                    ),
                    lambda _: lambda status: web["html_response"](
                        layout(
                            "Login",
                            [
                                "div",
                                ["p", "Invalid credentials."],
                                login_form(),
                            ],
                        ),
                        status,
                    ),
                )(__get="status", __call=True)(),
            ),
            web["GET"](
                "/admin",
                lambda request: chain(request, App)(is_admin)(
                    if_else, bool, 200, 403
                )(__post="status")(__mount="posts")(all_rows)(__post="posts")(
                    __mount="users"
                )(all_rows)(
                    lambda users: lambda posts: [
                        "div",
                        ["h2", "Admin"],
                        ["h3", "Users"],
                        [
                            "ul",
                            *[
                                [
                                    "li",
                                    f"{user['username']} — {user['role']}",
                                ]
                                for user in users
                            ],
                        ],
                        ["h3", "Posts"],
                        [
                            "ul",
                            *[["li", post["title"]] for post in posts],
                        ],
                    ]
                )(__get="posts", __call=True)(__post="panel")(
                    __get="status", __retain=True
                )(
                    if_else,
                    lambda status: status == 200,
                    lambda _: lambda panel: web["html_response"](
                        layout("Admin", panel)
                    ),
                    lambda _: lambda panel: web["html_response"](
                        layout(
                            "Forbidden",
                            [
                                "p",
                                "Admins only. Sign in as admin/admin.",
                            ],
                        ),
                        403,
                    ),
                )(__get="panel", __call=True)(),
            ),
        ],
        not_found=lambda request: chain(
            ["p", "404 — nothing here."], App
        )(lambda body: layout("Not found", body))(web["html_response"], 404)(),
    )
)(__get="insert", __call=True)(__get="all_rows", __call=True)(__get="fetch", __retain=True, __call=True)(
    __get="current_user", __call=True
)(__get="login", __call=True)(__get="is_admin", __call=True)(
    __get="layout", __call=True
)(__get="post_form", __call=True)(__get="login_form", __call=True)(
    lambda handler: lambda request: chain(request, App)(
        lambda req: assoc(
            req,
            "params",
            dmerge(req.get("params") or {}, req.get("form") or {}),
        )
    )(handler)()
)(__post="handler")(__get="parse_cookies", __retain=True)(
    lambda parse_cookies: lambda fetch: lambda handler: (
        lambda request: chain(request, App)(__post="req", __retain=True)(
            get_in, ["headers", "cookie"], ""
        )(parse_cookies)(get, "sid", "")(lambda sid: fetch("sessions", sid))(
            lambda sess: lambda req: assoc(req, "session", sess)
        )(__get="req", __call=True)(handler)()
    )
)(__get="fetch", __call=True)(__get="handler", __call=True)(
    lambda handler: lambda request: chain(chain(request, Maybe)(handler)())(
        recover,
        lambda err: {
            "status": 500,
            "body": f"Internal error: {err}",
            "headers": {"Content-Type": "text/plain"},
        },
    )()
)(__post="app")(__get="store", __retain=True)(
    lambda store: (
        lambda: store.reset(
            {
                "users": {},
                "posts": {},
                "sessions": {},
                "ids": {"users": 0, "posts": 0, "sessions": 0},
            }
        )
    )
)(__post="reset")(__get="app")(
    lambda app: lambda seed: lambda reset_db: (app, reset_db, seed)
)(__get="seed", __call=True)(__get="reset", __call=True)()
