"""Site views as chain(..., App) pipelines — mem, if_else, nested chains."""

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
        if_else, lambda post: post.get("id"), lambda _: 200, lambda _: 404
    )(__post="status")(__get="post")(
        if_else,
        lambda post: post.get("id"),
        post_detail,
        lambda _: ["p", "No such post."],
    )(__post="body")(__get="post")(
        if_else,
        lambda post: post.get("id"),
        lambda post: post["title"],
        lambda _: "Not found",
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
    chain(request, App)(get_in, ["form", "title"], "")(
        if_else,
        bool,
        lambda title: (
            chain(request, App)(current_user)(
                lambda user: {
                    "title": title,
                    "body": get_in(request, ["form", "body"], ""),
                    "author": user.get("username") or "anonymous",
                }
            )(lambda row: insert("posts", row))(lambda _: redirect("/"))()
        ),
        lambda _: (
            chain(
                ["div", ["p", "Title is required."], post_form()],
                App,
            )(lambda body: layout("New post", body))(html_response, 400)()
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
    )(
        if_else,
        lambda sess: sess.get("id"),
        lambda sess: redirect(
            "/", headers={"Set-Cookie": f"sid={sess['id']}; Path=/"}
        ),
        lambda _: (
            chain(
                ["div", ["p", "Invalid credentials."], login_form()],
                App,
            )(lambda body: layout("Login", body))(html_response, 401)()
        ),
    )()
)

admin = lambda request: (
    chain(request, App)(
        if_else,
        is_admin,
        lambda _: (
            chain("posts", App)(all_rows)(__post="posts")(__mount="users")(
                all_rows
            )(lambda users: lambda posts: admin_panel(users, posts))(
                __get="posts", __call=True
            )(lambda body: layout("Admin", body))(html_response)()
        ),
        lambda _: (
            chain(
                ["p", "Admins only. Sign in as admin/admin."],
                App,
            )(lambda body: layout("Forbidden", body))(html_response, 403)()
        ),
    )()
)

not_found = lambda request: (
    chain(["p", "404 — nothing here."], App)(
        lambda body: layout("Not found", body)
    )(html_response, 404)()
)
