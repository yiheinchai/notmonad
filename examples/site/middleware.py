from examples.site.auth import parse_cookies
from examples.site.db import fetch
from notmonad import assoc, attempt, dmerge, get_in, let
from notmonad.web import response

wrap_exception = lambda handler: lambda request: attempt(
    lambda: handler(request),
    lambda err: response(
        500,
        f"Internal error: {err}",
        {"Content-Type": "text/plain"},
    ),
)

wrap_session = lambda handler: lambda request: handler(
    assoc(
        request,
        "session",
        let(
            [
                "cookies",
                lambda: parse_cookies(get_in(request, ["headers", "cookie"])),
                "sid",
                lambda cookies: cookies.get("sid"),
                "sess",
                lambda sid: fetch("sessions", sid) if sid else None,
            ],
            lambda sess: sess or {},
        ),
    )
)

wrap_params = lambda handler: lambda request: handler(
    assoc(
        request,
        "params",
        dmerge(request.get("params") or {}, request.get("form") or {}),
    )
)
