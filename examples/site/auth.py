from examples.site.db import fetch, find_user, insert
from notmonad import App, chain, get, get_in, if_else

parse_cookies = lambda header: (
    chain(header or "", App)(
        lambda h: [part.strip() for part in str(h).split(";") if part.strip()]
    )(
        lambda parts: [part.split("=", 1) for part in parts if "=" in part]
    )(lambda pairs: dict((key.strip(), val.strip()) for key, val in pairs))()
)

current_user = lambda request: (
    chain(request, App)(get_in, ["session", "user-id"], 0)(
        if_else, bool, lambda uid: fetch("users", uid), lambda _: {}
    )()
)

login = lambda username, password: (
    chain(username, App)(find_user)(
        if_else,
        lambda user: bool(user.get("id")) and user.get("password") == password,
        lambda user: insert("sessions", {"user-id": user["id"]}),
        lambda _: {},
    )()
)

is_admin = lambda request: (
    chain(request, App)(current_user)(get, "role", "")(
        lambda role: role == "admin"
    )()
)
