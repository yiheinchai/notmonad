from examples.site.db import seed
from examples.site.urls import app
from notmonad import App, chain, effect

chain(True, App)(effect, seed)()
