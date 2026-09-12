"""The whole NotMonad Press site as one chain(..., App) expression.

Helpers are memory slots (procedural locals). Nothing is declared and then
referred to by name: store, queries, views, middleware, and routes are
stashed with __post and applied with __get / __call.
"""

from notmonad import (
    App,
    Maybe,
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
    tap,
    when,
)
from notmonad.web import GET, POST, html_response, redirect, response, router

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
)(__get="insert", __retain=True)(
    lambda insert: lambda all_rows: lambda fetch: lambda current_user: lambda login: lambda is_admin: lambda layout: lambda post_form: lambda login_form: router(
        [
            GET(
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
                )(lambda body: layout("Home", body))(html_response)(),
            ),
            GET(
                "/posts/new",
                lambda request: chain(post_form(), App)(
                    lambda form: layout("New post", form)
                )(html_response)(),
            ),
            POST(
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
                    lambda _: redirect("/"),
                    lambda _: html_response(
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
            GET(
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
                )(lambda node: lambda status: html_response(node, status))(
                    __get="status", __call=True
                )(),
            ),
            GET(
                "/login",
                lambda request: chain(login_form(), App)(
                    lambda form: layout("Login", form)
                )(html_response)(),
            ),
            POST(
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
                    lambda sess: lambda _: redirect(
                        "/",
                        headers={
                            "Set-Cookie": f"sid={sess['id']}; Path=/"
                        },
                    ),
                    lambda _: lambda status: html_response(
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
            GET(
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
                    lambda _: lambda panel: html_response(
                        layout("Admin", panel)
                    ),
                    lambda _: lambda panel: html_response(
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
        )(lambda body: layout("Not found", body))(html_response, 404)(),
    )
)(__get="all_rows", __call=True)(__get="fetch", __retain=True, __call=True)(
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
        lambda err: response(
            500,
            f"Internal error: {err}",
            {"Content-Type": "text/plain"},
        ),
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
