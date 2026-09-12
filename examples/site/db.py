from notmonad import assoc, assoc_in, atom, cond, deref, do, get_in, inc, let, swap

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

reset_db = lambda: store.reset(blank_state())

next_id = lambda table: let(
    ["ident", lambda: inc(get_in(deref(store), ["ids", table], 0))],
    lambda ident: do(
        lambda: swap(store, lambda st: assoc_in(st, ["ids", table], ident)),
        lambda: ident,
    ),
)

insert = lambda table, row: let(
    [
        "ident",
        lambda: next_id(table),
        "saved",
        lambda ident: assoc(row, "id", ident),
    ],
    lambda ident, saved: do(
        lambda: swap(store, lambda st: assoc_in(st, [table, ident], saved)),
        lambda: saved,
    ),
)

all_rows = lambda table: list((deref(store).get(table) or {}).values())

fetch = lambda table, ident: get_in(deref(store), [table, int(ident)]) if ident is not None else None

find_user = lambda username: next(
    (user for user in all_rows("users") if user.get("username") == username),
    None,
)

seed = lambda: cond(
    (
        lambda: not all_rows("users"),
        lambda: do(
            lambda: insert(
                "users",
                {"username": "admin", "password": "admin", "role": "admin"},
            ),
            lambda: insert(
                "posts",
                {
                    "title": "Hello from notmonad",
                    "body": "This site is a Python library: models, views, urls, middleware — no def or class.",
                    "author": "admin",
                },
            ),
            lambda: insert(
                "posts",
                {
                    "title": "Pipelines all the way down",
                    "body": "Request dicts flow through middleware and routes the same way data flows through chain.",
                    "author": "admin",
                },
            ),
        ),
    )
)
