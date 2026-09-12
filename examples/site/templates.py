layout = lambda title, body: [
    "html",
    [
        "head",
        ["meta", {"charset": "utf-8"}],
        ["title", title],
        [
            "style",
            "body{font-family:Georgia,serif;max-width:42rem;margin:2rem auto;padding:0 1rem;line-height:1.5;color:#222}nav a{margin-right:1rem}article{border-bottom:1px solid #ddd;padding:0.6rem 0}form label{display:block;margin:0.6rem 0}input,textarea{width:100%;padding:0.4rem}button{padding:0.4rem 0.8rem}",
        ],
    ],
    [
        "body",
        [
            "header",
            ["h1", ["a", {"href": "/"}, "NotMonad Press"]],
            [
                "nav",
                ["a", {"href": "/"}, "Home"],
                ["a", {"href": "/posts/new"}, "New post"],
                ["a", {"href": "/login"}, "Login"],
                ["a", {"href": "/admin"}, "Admin"],
            ],
        ],
        body,
        ["footer", ["p", "A Django-shaped app: pure Python, no def or class."]],
    ],
]

post_list = lambda posts: [
    "div",
    ["h2", "Posts"],
    ["p", "No posts yet."]
    if not posts
    else [
        [
            "article",
            [
                "h3",
                ["a", {"href": f"/posts/{post['id']}"}, post["title"]],
            ],
            ["p", post["body"]],
            ["small", f"by {post['author']}"],
        ]
        for post in posts
    ],
]

post_detail = lambda post: [
    "article",
    ["h2", post["title"]],
    ["p", post["body"]],
    ["p", ["small", f"by {post['author']}"]],
    ["p", ["a", {"href": "/"}, "Back"]],
]

post_form = lambda: [
    "form",
    {"method": "post", "action": "/posts/new"},
    ["label", "Title", ["input", {"name": "title", "required": "required"}]],
    ["label", "Body", ["textarea", {"name": "body", "rows": "6"}]],
    ["button", {"type": "submit"}, "Publish"],
]

login_form = lambda: [
    "form",
    {"method": "post", "action": "/login"},
    ["label", "Username", ["input", {"name": "username"}]],
    ["label", "Password", ["input", {"name": "password", "type": "password"}]],
    ["button", {"type": "submit"}, "Sign in"],
]

admin_panel = lambda users, posts: [
    "div",
    ["h2", "Admin"],
    ["h3", "Users"],
    ["ul", *[["li", f"{user['username']} — {user['role']}"] for user in users]],
    ["h3", "Posts"],
    ["ul", *[["li", post["title"]] for post in posts]],
]
