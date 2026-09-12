import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from examples.site.core import app
from notmonad import App, chain
from notmonad.web import serve

chain(app, App)(serve)()
