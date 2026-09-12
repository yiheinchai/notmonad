<h1 align="center">
  <br>
  <a href="https://github.com/yiheinchai/notmonad/assets/76833604/afab9829-9fa8-4349-8f42-488ac21c1fde"><img src="https://github.com/yiheinchai/notmonad/assets/76833604/afab9829-9fa8-4349-8f42-488ac21c1fde" alt="NotMonad" width="200"></a>
  <br>
  NotMonad
  <br>
</h1>

<h4 align="center">A pure functional library in Python — write entire apps with no <code>def</code> or <code>class</code></h4>

<p align="center">
  <a href="#no-declarations">No declarations</a> •
  <a href="#building-an-app">Pipelines</a> •
  <a href="#api">API</a> •
  <a href="#installation">Installation</a> •
  <a href="#license">License</a>
</p>

NotMonad lets you write left-to-right pipelines instead of nested calls or a pile of throwaway locals:

```python
from notmonad import chain
import numpy as np

chain(np.array([[1, 2, 3], [1, 2, 3]]))(np.transpose)(np.sum, axis=1)(np.mean)(
    lambda x: x / 100
)()
```

The same machinery — interceptors, memory, loops, branching, atoms — is enough to write full programs **in ordinary `.py` files**. NotMonad is not a new language. The idea is monads for everything: `chain(value, App)(func, *args)(...)()`, with `mem`, `maybe`, `if_else` / `when` / `unless`. `examples/site/` is a Django-shaped web app (models, views, urls, middleware, templates, auth) written as those pipelines.

> The word *monad* here is used loosely. These are composable interceptors around each pipeline step, not category-theory monads.

## No declarations

A view is a lambda that finishes a `chain(..., App)` pipeline — the same shape as tic-tac-toe, not a pile of `let` / `cond` helpers:

```python
from notmonad import App, chain, get_in, if_else
from notmonad.web import html_response

index = lambda request: (
    chain("posts", App)(all_rows)(post_list)(
        lambda body: layout("Home", body)
    )(html_response)()
)

show = lambda request: (
    chain(request, App)(get_in, ["params", "id"], "")(
        lambda pid: fetch("posts", pid)
    )(
        if_else,
        lambda post: post.get("id"),
        lambda post: html_response(layout(post["title"], post_detail(post))),
        lambda _: html_response(layout("Not found", ["p", "No such post."]), 404),
    )()
)
```

Run the site:

```bash
python -m examples.site
```

Login `admin` / `admin`. Tests fail the build if `examples/site/*.py` contains a `def` or `class`.

The same site as **one expression** (every helper inlined into memory slots) lives in `examples/oneline.py`.

A **bank** in the same style — users send funds to each other with a note on every transfer:

```bash
python examples/bank.py
```

Open `http://127.0.0.1:8000`. Demo logins: `alice` / `alice`, `bob` / `bob`, `carol` / `carol`. New accounts start with $100.

| Django layer | notmonad |
| --- | --- |
| `models.py` | `examples/site/db.py` (atom + queries) |
| `views.py` | `examples/site/views.py` |
| `urls.py` | `examples/site/urls.py` |
| middleware | `examples/site/middleware.py` |
| templates | `examples/site/templates.py` (hiccup lists) |
| auth | `examples/site/auth.py` |
| `wsgi.py` | `notmonad.web` |

Middleware is the same composition: `chain(handler, App)(wrap_params)(wrap_session)(wrap_exception)()`. Memory slots are the locals: `__post` / `__get` / `__call` make a handler a procedure instead of nested lambdas. Templates stay hiccup lists — data, not control flow.

## Building an app

A real program needs sequencing, state, branching, looping, IO, and errors. NotMonad ships an `App` stack (`mem` + `maybe`) that provides those as pipeline steps.

```python
from notmonad import App, chain, effect, tap, unless, while_loop

def play():
    return (
        chain(new_board(), App)
        (effect, print_instructions)
        (while_loop, turn, until=game_over)
        (tap, print_board)
        (tap, announce)
        ()
    )

def turn(board):
    return (
        chain(board, App)
        (user_move)
        (unless, game_over, computer_move)
        ()
    )
```

That is the shape of `examples/tic_tac_toe.py`: each turn is a pipeline, the game loop is `while_loop`, and IO is `tap` / `effect`.

### Errors

`Maybe` captures exceptions as the pipeline value so later steps are skipped (railway style). Recover or re-raise when you are ready:

```python
from notmonad import Maybe, chain, or_else, recover, unwrap

chain(5, Maybe)(lambda x: x / 0)(lambda x: x + 1)()          # ZeroDivisionError instance
chain(5, Maybe)(lambda x: x / 0)(or_else, 0)()              # 0
chain(5, Maybe)(lambda x: x / 0)(recover, lambda e: str(e))()
chain(5, Maybe)(lambda x: x / 0).expect()                   # raises
```

### Debugging

`debug` records every step *without running the function twice* (impure steps stay safe). Read the trace off the unfinished pipeline:

```python
from notmonad import compose, debug, maybe, monad

monad(5, compose(debug, maybe))(lambda x: x + 1)(lambda x: x / 0).trace
```

### Memory slots

The memory system is how a pipeline stays **procedural**. Named slots are locals: stash a value, do the next statement, come back. No nested `let` / `chain` / closures for intermediates.

```python
from notmonad import App, chain

(
    chain(user, App)
    (__post="user", __retain=True)
    (lambda u: u["addresses"])
    (__post="addresses")
    (__get="user")
    (lambda u: u["phones"])
    ()
)
```

`__call=True` applies the current value (a function) to a stored slot — curried steps plus memory replace nested maps and nested pipelines:

```python
(
    chain(request, App)
    (__post="req", __retain=True)
    (get_in, ["form", "title"], "")
    (__post="title")
    (__get="req")
    (current_user)
    (lambda user: lambda title: insert("posts", {"title": title, "author": user}))
    (__get="title", __call=True)
    ()
)
```

### Custom interceptors

An interceptor takes and returns `(value, func, *args, **kwargs)`. Mark it `@caller` if it is the one that actually invokes `func`. Compose at most one caller with any number of side-effect interceptors:

```python
from notmonad import caller, compose

@caller
def retry(value, func, *args, tries=3, **kwargs):
    last = None
    for _ in range(tries):
        try:
            last = func(value, *args, **kwargs)
            return last, func, args, kwargs
        except Exception as exc:
            last = exc
    return last, func, args, kwargs

Robust = compose(retry)  # retry is the caller; do not also compose `just`
```

## API

**Start a pipeline**

| Call | Stack |
| --- | --- |
| `chain(value)` / `pipe(value)` | `Just` (raise on error) |
| `chain(value, Seq)` | `mem` + `just` — procedures with memory slots that still raise |
| `chain(value, App)` | `mem` + `maybe` — default for applications |
| `chain(value, Maybe)` | railway error handling |
| `chain(value, Trace)` | `mem` + `debug` + `maybe` |
| `monad(value, compose(...))` | custom stack |

Finish with `()` or `.result()`. `.expect()` unwraps and raises if `Maybe` captured an exception. `.mem`, `.log`, and `.trace` expose interceptor state.

**Control flow** — `while_loop`, `until`, `while_`, `times`, `loop`, `foreach`, `p_loop`, `if_else`, `when`, `unless`, `switch`

**Effects** — `tap` (use the value), `effect` (ignore the value), `const`, `identity`

**Errors** — `recover`, `or_else`, `unwrap`, `is_error`

**Data** — `get`, `getitem`, `attr`, `invoke`, `set_in`, `flatten`, `wrap`, `peel`, `join`, `merge`

**Memory actions** (own step, no function call)

- `(__post="key")` / `(__post="key", __retain=True)`
- `(__get="key")` / `(__get="key", __retain=True)`
- `(__mount=data)`
- `(__delete="key")`
- `(__get="key", __call=True)` — call the current value on the loaded slot
- `(__strict=True)` — missing keys raise `MemKeyError`

Kwargs convention: `foo=` is a function argument, `_foo=` is pipeline state, `__foo=` is a one-shot interceptor action.

Imported helpers (`if_else`, `assoc`, `html_response`, `router`, …) are themselves `chain(..., Seq)` procedures, not `def`. The interceptor engine (`just`, `maybe`, `mem`, `while_loop`, `Atom`) stays ordinary Python.

## Installation

Requires Python 3.9+.

```bash
pip install git+https://github.com/yiheinchai/notmonad.git
```

From a clone:

```bash
git clone https://github.com/yiheinchai/notmonad
cd notmonad
pip install -e ".[dev]"
pytest
```

```python
from notmonad import App, chain
```

```bash
python -m examples.site
python examples/bank.py
python -c "from examples.oneline import app; from notmonad.web import serve; serve(app)"
python examples/tic_tac_toe.py
python examples/todo.py
```

## Motivations

Data work is often “take this value, run a series of functions, do not invent twelve names I will never reuse.” Nested calls read right-to-left. Locals pollute notebook namespaces. A pipeline reads left-to-right and only names the things you still care about.

Traditional monadic wrappers force every function to know about the wrapper. NotMonad keeps step functions ordinary: interceptors sit *between* steps, with a shared `(value, func, args, kwargs)` shape, so they compose. Error handling, logging, argument reordering, and memory are all the same kind of thing.

`while_loop` is iterative (not recursive) and has a `max_steps` guard, so application main loops are safe.

## License

MIT
