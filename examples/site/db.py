from notmonad import (
    App,
    assoc,
    assoc_in,
    atom,
    chain,
    deref,
    get,
    get_in,
    if_else,
    inc,
    swap,
    tap,
    when,
)

store = atom(
    {
        "users": {},
        "posts": {},
        "sessions": {},
        "ids": {"users": 0, "posts": 0, "sessions": 0},
    }
)

blank_state = lambda: {
    "users": {},
    "posts": {},
    "sessions": {},
    "ids": {"users": 0, "posts": 0, "sessions": 0},
}

reset_db = lambda: (
    chain(store, App)(lambda box: box.reset(blank_state()))()
)

next_id = lambda table: (
    chain(deref(store), App)(get_in, ["ids", table], 0)(inc)(
        tap, lambda ident: swap(store, assoc_in, ["ids", table], ident)
    )()
)

insert = lambda table, row: (
    chain(row, App)(__post="row")(__mount=table)(next_id)(
        lambda ident: lambda saved: assoc(saved, "id", ident)
    )(__get="row", __call=True)(
        tap, lambda saved: swap(store, assoc_in, [table, saved["id"]], saved)
    )()
)

all_rows = lambda table: (
    chain(deref(store), App)(get, table, {})(lambda rows: list(rows.values()))()
)

fetch = lambda table, ident: (
    chain(ident if ident is not None else "", App)(
        if_else, bool, lambda key: int(key), 0
    )(lambda key: get_in(deref(store), [table, key], {}))()
)

find_user = lambda username: (
    chain("users", App)(all_rows)(
        lambda users: next(
            (user for user in users if user.get("username") == username),
            {},
        )
    )()
)

seed = lambda: (
    chain("users", App)(all_rows)(lambda rows: not rows)(
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
