from examples.site.core import app
from notmonad import App, chain
from notmonad.web import serve

chain(app, App)(serve)()
