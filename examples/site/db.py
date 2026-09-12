from notmonad import (
    App,
    assoc,
    assoc_in,
    atom,
    chain,
    deref,
    effect,
    get,
    get_in,
    if_else,
    inc,
    swap,
    tap,
    unless,
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
    chain(table, App)(next_id)(lambda ident: assoc(row, "id", ident))(
        tap, lambda saved: swap(store, assoc_in, [table, saved["id"]], saved)
    )()
)

all_rows = lambda table: (
    chain(deref(store), App)(get, table, {})(lambda rows: list(rows.values()))()
)

fetch = lambda table, ident: (
    chain(ident if ident is not None else "", App)(
        if_else,
        bool,
        lambda key: get_in(deref(store), [table, int(key)], {}),
        lambda _: {},
    )()
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
    chain("users", App)(all_rows)(
        unless,
        bool,
        lambda _: (
            chain(True, App)(
                effect,
                insert,
                "users",
                {"username": "admin", "password": "admin", "role": "admin"},
            )(
                effect,
                insert,
                "posts",
                {
                    "title": "Hello from notmonad",
                    "body": "This site is a Python library: models, views, urls, middleware — no def or class.",
                    "author": "admin",
                },
            )(
                effect,
                insert,
                "posts",
                {
                    "title": "Pipelines all the way down",
                    "body": "Request dicts flow through middleware and routes the same way data flows through chain.",
                    "author": "admin",
                },
            )()
        ),
    )()
)
