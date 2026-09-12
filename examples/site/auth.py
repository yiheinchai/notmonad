from examples.site.db import fetch, find_user, insert
from notmonad import cond, get_in, let

parse_cookies = lambda header: (
    {}
    if not header
    else dict(
        (
            lambda kv: (
                kv[0].strip(),
                kv[1].strip() if len(kv) > 1 else "",
            )
        )(part.split("=", 1))
        for part in str(header).split(";")
    )
)

current_user = lambda request: let(
    ["uid", lambda: get_in(request, ["session", "user-id"])],
    lambda uid: fetch("users", uid) if uid else None,
)

login = lambda username, password: let(
    ["user", lambda: find_user(username)],
    lambda user: cond(
        (
            user is not None and user.get("password") == password,
            lambda: insert("sessions", {"user-id": user["id"]}),
        )
    ),
)

is_admin = lambda request: (current_user(request) or {}).get("role") == "admin"
