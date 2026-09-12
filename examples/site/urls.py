from examples.site import middleware, views
from notmonad import App, chain
from notmonad.web import GET, POST, router

handler = router(
    [
        GET("/", views.index),
        GET("/posts/new", views.new_post),
        POST("/posts/new", views.create_post),
        GET("/posts/:id", views.show),
        GET("/login", views.login_get),
        POST("/login", views.login_post),
        GET("/admin", views.admin),
    ],
    not_found=views.not_found,
)

app = (
    chain(handler, App)(middleware.wrap_params)(middleware.wrap_session)(
        middleware.wrap_exception
    )()
)
