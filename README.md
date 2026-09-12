<h1 align="center">
  <br>
  <a href="https://github.com/yiheinchai/notmonad/assets/76833604/afab9829-9fa8-4349-8f42-488ac21c1fde"><img src="https://github.com/yiheinchai/notmonad/assets/76833604/afab9829-9fa8-4349-8f42-488ac21c1fde" alt="NotMonad" width="200"></a>
  <br>
  NotMonad
  <br>
</h1>

<h4 align="center">Pipeline-style data transformation — and enough control flow to build a real app</h4>

<p align="center">
  <a href="#building-an-app">Building an app</a> •
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

The same machinery — interceptors, memory slots, loops, and branching — is enough to write full programs. `examples/tic_tac_toe.py` and `examples/todo.py` are complete applications built this way.

> The word *monad* here is used loosely. These are composable interceptors around each pipeline step, not category-theory monads.

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

Fork a computation, stash it, do something else, then come back:

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

`__call=True` applies the current value (a function) to a stored value — that is how nested maps stay flat.

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

Run the example apps:

```bash
python examples/tic_tac_toe.py
python examples/todo.py
```

## Motivations

Data work is often “take this value, run a series of functions, do not invent twelve names I will never reuse.” Nested calls read right-to-left. Locals pollute notebook namespaces. A pipeline reads left-to-right and only names the things you still care about.

Traditional monadic wrappers force every function to know about the wrapper. NotMonad keeps step functions ordinary: interceptors sit *between* steps, with a shared `(value, func, args, kwargs)` shape, so they compose. Error handling, logging, argument reordering, and memory are all the same kind of thing.

`while_loop` is iterative (not recursive) and has a `max_steps` guard, so application main loops are safe.

## License

MIT
