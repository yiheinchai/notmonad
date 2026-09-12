from examples.site.auth import current_user, is_admin, login
from examples.site.db import all_rows, fetch, insert
from examples.site.templates import (
    admin_panel,
    layout,
    login_form,
    post_detail,
    post_form,
    post_list,
)
from notmonad import cond, do, get_in, let
from notmonad.web import html_response, redirect

index = lambda request: html_response(
    layout("Home", post_list(all_rows("posts")))
)

show = lambda request: let(
    ["post", lambda: fetch("posts", get_in(request, ["params", "id"]))],
    lambda post: cond(
        (
            post,
            lambda: html_response(layout(post["title"], post_detail(post))),
        ),
        else_=lambda: html_response(
            layout("Not found", ["p", "No such post."]), 404
        ),
    ),
)

new_post = lambda request: html_response(layout("New post", post_form()))

create_post = lambda request: let(
    [
        "title",
        lambda: get_in(request, ["form", "title"]) or "",
        "body",
        lambda: get_in(request, ["form", "body"]) or "",
        "user",
        lambda: current_user(request),
    ],
    lambda title, body, user: cond(
        (
            title == "",
            lambda: html_response(
                layout(
                    "New post",
                    ["div", ["p", "Title is required."], post_form()],
                ),
                400,
            ),
        ),
        else_=lambda: do(
            lambda: insert(
                "posts",
                {
                    "title": title,
                    "body": body,
                    "author": (user or {}).get("username") or "anonymous",
                },
            ),
            lambda: redirect("/"),
        ),
    ),
)

login_get = lambda request: html_response(layout("Login", login_form()))

login_post = lambda request: let(
    [
        "session",
        lambda: login(
            get_in(request, ["form", "username"]),
            get_in(request, ["form", "password"]),
        ),
    ],
    lambda session: cond(
        (
            session,
            lambda: redirect(
                "/",
                headers={"Set-Cookie": f"sid={session['id']}; Path=/"},
            ),
        ),
        else_=lambda: html_response(
            layout(
                "Login",
                ["div", ["p", "Invalid credentials."], login_form()],
            ),
            401,
        ),
    ),
)

admin = lambda request: cond(
    (
        lambda: is_admin(request),
        lambda: html_response(
            layout("Admin", admin_panel(all_rows("users"), all_rows("posts")))
        ),
    ),
    else_=lambda: html_response(
        layout(
            "Forbidden",
            ["p", "Admins only. Sign in as admin/admin."],
        ),
        403,
    ),
)

not_found = lambda request: html_response(
    layout("Not found", ["p", "404 — nothing here."]), 404
)
