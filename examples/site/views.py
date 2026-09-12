"""Site views: one chain(..., App) per handler.

Memory slots are the locals. A handler is a procedure: stash, compute,
stash, combine with __call. Branches return values; they do not nest chain().
"""

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
from notmonad import App, chain, get, get_in, if_else
from notmonad.web import html_response, redirect

index = lambda request: (
    chain("posts", App)(all_rows)(post_list)(
        lambda body: layout("Home", body)
    )(html_response)()
)

show = lambda request: (
    chain(request, App)(get_in, ["params", "id"], "")(
        lambda pid: fetch("posts", pid)
    )(__post="post", __retain=True)(
        if_else, lambda post: post.get("id"), 200, 404
    )(__post="status")(__get="post", __retain=True)(
        if_else,
        lambda post: post.get("id"),
        post_detail,
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
    )()
)

new_post = lambda request: (
    chain(post_form(), App)(lambda form: layout("New post", form))(
        html_response
    )()
)

create_post = lambda request: (
    chain(request, App)(__post="req", __retain=True)(
        get_in, ["form", "title"], ""
    )(__post="title")(__get="req", __retain=True)(
        get_in, ["form", "body"], ""
    )(__post="body")(__get="req")(current_user)(__post="user")(
        __get="title", __retain=True
    )(if_else, bool, 302, 400)(__post="status")(
        __get="title", __retain=True
    )(
        lambda title: lambda body: lambda user: {
            "title": title,
            "body": body,
            "author": user.get("username") or "anonymous",
        }
    )(__get="body", __call=True)(__get="user", __call=True)(__post="row")(
        __get="status", __retain=True
    )(
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
                ["div", ["p", "Title is required."], post_form()],
            ),
            400,
        ),
    )()
)

login_get = lambda request: (
    chain(login_form(), App)(lambda form: layout("Login", form))(
        html_response
    )()
)

login_post = lambda request: (
    chain(request, App)(get, "form", {})(
        lambda form: login(
            form.get("username") or "", form.get("password") or ""
        )
    )(__post="sess", __retain=True)(
        if_else, lambda sess: sess.get("id"), 302, 401
    )(__post="status")(__get="sess")(
        if_else,
        lambda sess: sess.get("id"),
        lambda sess: lambda _: redirect(
            "/", headers={"Set-Cookie": f"sid={sess['id']}; Path=/"}
        ),
        lambda _: lambda status: html_response(
            layout(
                "Login",
                ["div", ["p", "Invalid credentials."], login_form()],
            ),
            status,
        ),
    )(__get="status", __call=True)()
)

admin = lambda request: (
    chain(request, App)(is_admin)(if_else, bool, 200, 403)(__post="status")(
        __mount="posts"
    )(all_rows)(__post="posts")(__mount="users")(all_rows)(
        lambda users: lambda posts: admin_panel(users, posts)
    )(__get="posts", __call=True)(__post="panel")(
        __get="status", __retain=True
    )(
        if_else,
        lambda status: status == 200,
        lambda _: lambda panel: html_response(layout("Admin", panel)),
        lambda _: lambda panel: html_response(
            layout(
                "Forbidden",
                ["p", "Admins only. Sign in as admin/admin."],
            ),
            403,
        ),
    )(__get="panel", __call=True)()
)

not_found = lambda request: (
    chain(["p", "404 — nothing here."], App)(
        lambda body: layout("Not found", body)
    )(html_response, 404)()
)
