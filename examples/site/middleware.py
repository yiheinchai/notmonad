from examples.site.auth import parse_cookies
from examples.site.db import fetch
from notmonad import App, Maybe, assoc, chain, dmerge, get, get_in, recover
from notmonad.web import response

wrap_exception = lambda handler: lambda request: (
    chain(chain(request, Maybe)(handler)())(
        recover,
        lambda err: response(
            500,
            f"Internal error: {err}",
            {"Content-Type": "text/plain"},
        ),
    )()
)

wrap_session = lambda handler: lambda request: (
    chain(request, App)(__post="req", __retain=True)(
        get_in, ["headers", "cookie"], ""
    )(parse_cookies)(get, "sid", "")(lambda sid: fetch("sessions", sid))(
        lambda sess: lambda req: assoc(req, "session", sess)
    )(__get="req", __call=True)(handler)()
)

wrap_params = lambda handler: lambda request: (
    chain(request, App)(
        lambda req: assoc(
            req,
            "params",
            dmerge(req.get("params") or {}, req.get("form") or {}),
        )
    )(handler)()
)
