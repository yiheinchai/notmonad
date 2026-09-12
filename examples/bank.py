"""NotMonad Bank — send and receive funds with a note, one chain(..., App)."""

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
from notmonad.web import GET, POST, html_response, redirect, response, router, serve

app, reset_db, seed = chain(
    atom(
        {
            "users": {},
            "txs": {},
            "sessions": {},
            "ids": {"users": 0, "txs": 0, "sessions": 0},
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
                    if user.get("username") == str(username).strip()
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
    __get="store", __retain=True
)(
    lambda store: (
        lambda table, row: chain(row, App)(
            tap,
            lambda rec: swap(store, assoc_in, [table, rec["id"]], rec),
        )()
    )
)(__post="save")(
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
                "body{font-family:system-ui,sans-serif;max-width:40rem;margin:2rem auto;padding:0 1rem;background:#f4f6f1;color:#1b2416}header{display:flex;justify-content:space-between;align-items:baseline;gap:1rem}h1 a{color:#0f3d2e;text-decoration:none}nav a{margin-left:.75rem;color:#0f3d2e}.balance{font-size:2.4rem;font-weight:700;margin:.2rem 0 1rem}.tx{background:#fff;border:1px solid #d7ddcf;border-radius:8px;padding:.75rem 1rem;margin:.5rem 0}.out strong{color:#9a3412}.in strong{color:#166534}.err{background:#fee2e2;color:#991b1b;padding:.6rem .8rem;border-radius:6px}.hint{color:#4b5563;font-size:.95rem}label{display:block;margin:.55rem 0}input{width:100%;padding:.45rem;box-sizing:border-box}button{background:#0f3d2e;color:#fff;border:0;padding:.5rem .9rem;border-radius:6px;cursor:pointer;margin-top:.4rem}",
            ],
        ],
        [
            "body",
            [
                "header",
                ["h1", ["a", {"href": "/"}, "NotMonad Bank"]],
                [
                    "nav",
                    ["a", {"href": "/"}, "Account"],
                    ["a", {"href": "/login"}, "Login"],
                    ["a", {"href": "/register"}, "Open account"],
                    ["a", {"href": "/logout"}, "Log out"],
                ],
            ],
            body,
            [
                "footer",
                ["p", "Send funds to each other. Every transfer gets a note."],
            ],
        ],
    ]
)(__post="layout")(__get="all_rows", __retain=True)(
    lambda all_rows: lambda insert: (
        lambda: chain("users", App)(all_rows)(lambda rows: not rows)(
            __post="empty", __retain=True
        )(
            when,
            bool,
            lambda _: insert(
                "users",
                {
                    "username": "alice",
                    "password": "alice",
                    "balance": 1000,
                },
            ),
        )(__get="empty", __retain=True)(
            when,
            bool,
            lambda _: insert(
                "users",
                {"username": "bob", "password": "bob", "balance": 500},
            ),
        )(__get="empty")(
            when,
            bool,
            lambda _: insert(
                "users",
                {
                    "username": "carol",
                    "password": "carol",
                    "balance": 250,
                },
            ),
        )()
    )
)(__get="insert", __retain=True, __call=True)(__post="seed", __retain=True)(
    tap, lambda fn: fn()
)(__get="layout", __retain=True)(
    lambda layout: lambda all_rows: (
        lambda user, err="": layout(
            "Account",
            [
                ["p", f"Hello, {user.get('username')}"],
                ["p", {"class": "balance"}, f"${user.get('balance', 0)}"],
                ["p", {"class": "err"}, err] if err else "",
                [
                    "p",
                    {"class": "hint"},
                    "Demo logins: alice/alice, bob/bob, carol/carol.",
                ],
                ["h2", "Send money"],
                [
                    "form",
                    {"method": "post", "action": "/send"},
                    [
                        "label",
                        "To",
                        [
                            "input",
                            {
                                "name": "to",
                                "placeholder": "username",
                            },
                        ],
                    ],
                    [
                        "label",
                        "Amount",
                        [
                            "input",
                            {
                                "name": "amount",
                                "placeholder": "25",
                            },
                        ],
                    ],
                    [
                        "label",
                        "Note",
                        [
                            "input",
                            {
                                "name": "note",
                                "placeholder": "rent, coffee, thanks",
                            },
                        ],
                    ],
                    ["button", {"type": "submit"}, "Send"],
                ],
                ["h2", "Activity"],
                (
                    lambda txs: ["p", "No transactions yet."]
                    if not txs
                    else [
                        "div",
                        *[
                            [
                                "div",
                                {
                                    "class": "tx out"
                                    if tx.get("from_id") == user.get("id")
                                    else "tx in"
                                },
                                [
                                    "strong",
                                    f"-${tx['amount']}"
                                    if tx.get("from_id") == user.get("id")
                                    else f"+${tx['amount']}",
                                ],
                                [
                                    "span",
                                    f" to {tx.get('to_name')}"
                                    if tx.get("from_id") == user.get("id")
                                    else f" from {tx.get('from_name')}",
                                ],
                                ["p", tx.get("note") or ""],
                            ]
                            for tx in sorted(
                                txs, key=lambda row: row.get("id") or 0, reverse=True
                            )
                        ],
                    ]
                )(
                    [
                        tx
                        for tx in all_rows("txs")
                        if tx.get("from_id") == user.get("id")
                        or tx.get("to_id") == user.get("id")
                    ]
                ),
            ],
        )
    )
)(__get="all_rows", __retain=True, __call=True)(__post="board")(
    __get="insert", __retain=True
)(
    lambda insert: lambda current_user: lambda login: lambda find_user: lambda save: lambda board: lambda layout: router(
        [
            GET(
                "/",
                lambda request: chain(request, App)(current_user)(
                    if_else,
                    lambda user: user.get("id"),
                    lambda user: html_response(board(user)),
                    lambda _: redirect("/login"),
                )(),
            ),
            GET(
                "/login",
                lambda request: chain(
                    [
                        "form",
                        {"method": "post", "action": "/login"},
                        [
                            "p",
                            {"class": "hint"},
                            "alice/alice · bob/bob · carol/carol",
                        ],
                        [
                            "label",
                            "Username",
                            ["input", {"name": "username"}],
                        ],
                        [
                            "label",
                            "Password",
                            [
                                "input",
                                {
                                    "name": "password",
                                    "type": "password",
                                },
                            ],
                        ],
                        ["button", {"type": "submit"}, "Log in"],
                    ],
                    App,
                )(lambda form: layout("Login", form))(html_response)(),
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
                                [
                                    "p",
                                    {"class": "err"},
                                    "Invalid credentials.",
                                ],
                                [
                                    "form",
                                    {"method": "post", "action": "/login"},
                                    [
                                        "label",
                                        "Username",
                                        ["input", {"name": "username"}],
                                    ],
                                    [
                                        "label",
                                        "Password",
                                        [
                                            "input",
                                            {
                                                "name": "password",
                                                "type": "password",
                                            },
                                        ],
                                    ],
                                    [
                                        "button",
                                        {"type": "submit"},
                                        "Log in",
                                    ],
                                ],
                            ],
                        ),
                        status,
                    ),
                )(__get="status", __call=True)(),
            ),
            GET(
                "/register",
                lambda request: chain(
                    [
                        "form",
                        {"method": "post", "action": "/register"},
                        [
                            "p",
                            {"class": "hint"},
                            "New accounts start with $100.",
                        ],
                        [
                            "label",
                            "Username",
                            ["input", {"name": "username"}],
                        ],
                        [
                            "label",
                            "Password",
                            [
                                "input",
                                {
                                    "name": "password",
                                    "type": "password",
                                },
                            ],
                        ],
                        [
                            "button",
                            {"type": "submit"},
                            "Open account",
                        ],
                    ],
                    App,
                )(lambda form: layout("Open account", form))(
                    html_response
                )(),
            ),
            POST(
                "/register",
                lambda request: chain(request, App)(get, "form", {})(
                    __post="form", __retain=True
                )(get, "username", "")(
                    lambda name: str(name).strip()
                )(__post="username")(__get="form")(get, "password", "")(
                    __post="password"
                )(__get="username", __retain=True)(find_user)(
                    __post="existing"
                )(__get="username", __retain=True)(
                    lambda username: lambda password: lambda existing: (
                        "Username and password required."
                        if not username or not password
                        else "That username is taken."
                        if existing.get("id")
                        else ""
                    )
                )(__get="password", __call=True)(
                    __get="existing", __call=True
                )(__post="error")(__get="error", __retain=True)(
                    if_else,
                    lambda err: err == "",
                    lambda _: lambda username: lambda password: chain(
                        username, App
                    )(
                        lambda name: insert(
                            "users",
                            {
                                "username": name,
                                "password": password,
                                "balance": 100,
                            },
                        )
                    )(
                        lambda user: insert(
                            "sessions", {"user-id": user["id"]}
                        )
                    )(),
                    lambda _: lambda username: lambda password: {},
                )(__get="username", __call=True)(
                    __get="password", __call=True
                )(__post="sess")(__get="error", __retain=True)(
                    if_else,
                    lambda err: err == "",
                    lambda _: lambda sess: redirect(
                        "/",
                        headers={
                            "Set-Cookie": f"sid={sess['id']}; Path=/"
                        },
                    ),
                    lambda err: lambda sess: html_response(
                        layout(
                            "Open account",
                            [
                                "div",
                                [
                                    "p",
                                    {"class": "err"},
                                    err,
                                ],
                                [
                                    "form",
                                    {
                                        "method": "post",
                                        "action": "/register",
                                    },
                                    [
                                        "label",
                                        "Username",
                                        ["input", {"name": "username"}],
                                    ],
                                    [
                                        "label",
                                        "Password",
                                        [
                                            "input",
                                            {
                                                "name": "password",
                                                "type": "password",
                                            },
                                        ],
                                    ],
                                    [
                                        "button",
                                        {"type": "submit"},
                                        "Open account",
                                    ],
                                ],
                            ],
                        ),
                        400,
                    ),
                )(__get="sess", __call=True)(),
            ),
            GET(
                "/logout",
                lambda request: redirect(
                    "/login",
                    headers={"Set-Cookie": "sid=; Path=/; Max-Age=0"},
                ),
            ),
            POST(
                "/send",
                lambda request: chain(request, App)(
                    __post="req", __retain=True
                )(current_user)(__post="sender", __retain=True)(
                    __get="req", __retain=True
                )(get, "form", {})(__post="form", __retain=True)(
                    get, "to", ""
                )(lambda name: str(name).strip())(__post="to_name")(
                    __get="form", __retain=True
                )(get, "amount", "")(
                    lambda raw: int(raw)
                    if str(raw).strip().isdigit() and int(raw) > 0
                    else 0
                )(__post="amount")(__get="form")(get, "note", "")(
                    lambda note: str(note).strip() or "—"
                )(__post="note")(__get="to_name")(find_user)(
                    __post="recipient", __retain=True
                )(__get="sender", __retain=True)(
                    lambda sender: lambda recipient: lambda amount: (
                        "Sign in to send funds."
                        if not sender.get("id")
                        else "Amount must be a positive whole number."
                        if amount <= 0
                        else "No account with that name."
                        if not recipient.get("id")
                        else "You cannot send funds to yourself."
                        if recipient.get("id") == sender.get("id")
                        else "Insufficient funds."
                        if sender.get("balance", 0) < amount
                        else ""
                    )
                )(__get="recipient", __retain=True, __call=True)(
                    __get="amount", __retain=True, __call=True
                )(__post="error")(__get="error", __retain=True)(
                    if_else,
                    lambda err: err == "",
                    lambda _: lambda sender: lambda recipient: lambda amount: lambda note: chain(
                        sender, App
                    )(
                        lambda who: assoc(
                            who, "balance", who["balance"] - amount
                        )
                    )(lambda who: save("users", who))(
                        lambda _: assoc(
                            recipient,
                            "balance",
                            recipient["balance"] + amount,
                        )
                    )(lambda who: save("users", who))(
                        lambda _: insert(
                            "txs",
                            {
                                "from_id": sender["id"],
                                "to_id": recipient["id"],
                                "from_name": sender["username"],
                                "to_name": recipient["username"],
                                "amount": amount,
                                "note": note,
                            },
                        )
                    )(),
                    lambda _: lambda sender: lambda recipient: lambda amount: lambda note: {},
                )(__get="sender", __retain=True, __call=True)(
                    __get="recipient", __call=True
                )(__get="amount", __call=True)(__get="note", __call=True)(
                    __get="error"
                )(
                    if_else,
                    lambda err: err == "",
                    lambda _: lambda sender: redirect("/"),
                    lambda err: lambda sender: (
                        redirect("/login")
                        if not sender.get("id")
                        else html_response(board(sender, err), 400)
                    ),
                )(__get="sender", __call=True)(),
            ),
        ],
        not_found=lambda request: chain(
            ["p", "404 — nothing here."], App
        )(lambda body: layout("Not found", body))(html_response, 404)(),
    )
)(__get="current_user", __call=True)(__get="login", __call=True)(
    __get="find_user", __call=True
)(__get="save", __call=True)(__get="board", __call=True)(
    __get="layout", __call=True
)(
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
                "txs": {},
                "sessions": {},
                "ids": {"users": 0, "txs": 0, "sessions": 0},
            }
        )
    )
)(__post="reset")(__get="app")(
    lambda app: lambda seed: lambda reset_db: (app, reset_db, seed)
)(__get="seed", __call=True)(__get="reset", __call=True)()

chain(app, App)(serve)() if __name__ == "__main__" else None
