"""Pipeline operators: loops, branching, effects, and data helpers."""

from __future__ import annotations

import inspect
from typing import Any, Callable, Iterable, Sequence

from notmonad.core import partial
from notmonad.exceptions import LoopLimitError

_MISSING = object()
DEFAULT_MAX_STEPS = 1_000_000


def identity(value: Any) -> Any:
    return value


def const(value: Any, new_value: Any) -> Any:
    """Replace the pipeline value."""
    return new_value


def tap(value: Any, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """Run a side effect on the current value and keep the value."""
    fn(value, *args, **kwargs)
    return value


def effect(value: Any, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """Run a side effect that ignores the current value and keep the value."""
    fn(*args, **kwargs)
    return value


def _apply(then: Any, value: Any) -> Any:
    return then(value) if callable(then) else then


def if_else(value: Any, pred: Callable[[Any], Any], then: Any, else_: Any = None) -> Any:
    """Pick a branch. ``else_`` defaults to identity."""
    chosen = then if pred(value) else (identity if else_ is None else else_)
    return _apply(chosen, value)


def when(value: Any, pred: Callable[[Any], Any], then: Any) -> Any:
    """Apply ``then`` only when ``pred(value)`` is true."""
    return _apply(then, value) if pred(value) else value


def unless(value: Any, pred: Callable[[Any], Any], then: Any) -> Any:
    """Apply ``then`` only when ``pred(value)`` is false."""
    return _apply(then, value) if not pred(value) else value


def switch(value: Any, cases: Sequence[tuple[Callable[[Any], Any], Any]], default: Any = None) -> Any:
    """First matching ``(pred, then)`` wins. ``default`` is identity when omitted."""
    for pred, then in cases:
        if pred(value):
            return _apply(then, value)
    if default is None:
        return value
    return _apply(default, value)


def while_loop(
    value: Any,
    func: Callable[[Any], Any],
    cond: Any = True,
    break_cond: Callable[[Any], Any] | None = None,
    until: Callable[[Any], Any] | None = None,
    max_steps: int = DEFAULT_MAX_STEPS,
) -> Any:
    """Iteratively apply ``func`` until a condition fails.

    Parameters
    ----------
    cond:
        Bool or ``value -> bool``. Checked *before* each step. Default ``True``.
    break_cond / until:
        ``value -> bool`` checked *after* each step. Pass only one of them.
    max_steps:
        Safety limit so a runaway loop cannot blow the stack or hang forever.
    """
    if until is not None and break_cond is not None:
        raise TypeError("Pass only one of until= or break_cond=")
    stop = until if until is not None else break_cond

    should_run = cond if callable(cond) else (lambda _value: bool(cond))
    should_stop = stop if callable(stop) else (lambda _value: False)

    steps = 0
    while should_run(value):
        if steps >= max_steps:
            raise LoopLimitError(f"while_loop exceeded max_steps={max_steps}")
        value = func(value)
        steps += 1
        if should_stop(value):
            break
    return value


def until(
    value: Any,
    func: Callable[[Any], Any],
    pred: Callable[[Any], Any],
    max_steps: int = DEFAULT_MAX_STEPS,
) -> Any:
    """Apply ``func`` until ``pred(value)`` is true."""
    return while_loop(value, func, until=pred, max_steps=max_steps)


def while_(
    value: Any,
    func: Callable[[Any], tuple],
    max_steps: int = DEFAULT_MAX_STEPS,
) -> Any:
    """Loop where ``func(value) -> (new_value, done)``."""
    steps = 0
    while True:
        if steps >= max_steps:
            raise LoopLimitError(f"while_ exceeded max_steps={max_steps}")
        value, done = func(value)
        steps += 1
        if done:
            return value


def times(value: Any, n: int, func: Callable[[Any], Any]) -> Any:
    """Apply ``func`` exactly ``n`` times."""
    if n < 0:
        raise ValueError("times() n must be >= 0")
    for _ in range(n):
        value = func(value)
    return value


def loop(data: Iterable[Any], map=lambda x: x, filter=lambda x: True) -> list:
    """Map/filter over ``data``. Compatible with the historic positional API."""
    return [map(item) for item in data if filter(item)]


def foreach(value: Iterable[Any], fn: Callable[[Any], Any], pred: Callable[[Any], Any] | None = None) -> list:
    """Map ``fn`` over ``value``, optionally filtered by ``pred``."""
    if pred is None:
        return [fn(item) for item in value]
    return [fn(item) for item in value if pred(item)]


def p_loop(value: Any, *args: Any, **kwargs: Any):
    """Turn the current value into the ``map`` of a :func:`loop` (for nested maps)."""
    return partial(loop, *args, map=value, **kwargs)


def innerwrap(transform, value, pipeline):
    return transform(pipeline(value))


def wrap(pipeline, *args, **kwargs):
    """Run ``pipeline(data)`` first, then ``transform`` the result."""
    return partial(innerwrap, *args, pipeline=pipeline, **kwargs)


def outerwrap(transform, value, pipeline):
    return pipeline(transform(value))


def peel(pipeline, *args, **kwargs):
    """Transform the data first, then feed it into ``pipeline``."""
    return partial(outerwrap, *args, pipeline=pipeline, **kwargs)


def call(func, *args, **kwargs):
    return func(*args, **kwargs)


def join(value, value2):
    def inner(data):
        return [value(data), value2(data)]

    return inner


def merge(value, value2):
    def inner(data):
        return {**value(data), **value2(data)}

    return inner


def p_merge(*args):
    return partial(merge, *args)


def flatten(value: Iterable[Iterable[Any]], levels: int = 1) -> list:
    result: Any = value
    for _ in range(levels):
        result = [item for group in result for item in group]
    return result


def recover(value: Any, handler: Callable[[BaseException], Any]) -> Any:
    """Replace a captured exception with ``handler(exc)``."""
    if isinstance(value, Exception):
        return handler(value)
    return value


def or_else(value: Any, default: Any) -> Any:
    """Replace a captured exception with ``default`` (called if callable)."""
    if not isinstance(value, Exception):
        return value
    return default(value) if callable(default) else default


def unwrap(value: Any) -> Any:
    """Raise if the value is an exception, otherwise return it."""
    if isinstance(value, Exception):
        raise value
    return value


def is_error(value: Any) -> bool:
    return isinstance(value, Exception)


def getitem(value: Any, key: Any) -> Any:
    return value[key]


def get(value: Any, key: Any, default: Any = None) -> Any:
    getter = getattr(value, "get", None)
    if callable(getter):
        return getter(key, default)
    try:
        return value[key]
    except (KeyError, IndexError, TypeError):
        return default


def attr(value: Any, name: str, default: Any = _MISSING) -> Any:
    if default is _MISSING:
        return getattr(value, name)
    return getattr(value, name, default)


def invoke(value: Any, name: str, *args: Any, **kwargs: Any) -> Any:
    return getattr(value, name)(*args, **kwargs)


def set_in(value: Any, key: Any, item: Any) -> Any:
    """Return a shallow copy of a dict or list with ``key`` updated."""
    if isinstance(value, dict):
        return {**value, key: item}
    if isinstance(value, list):
        out = value[:]
        out[key] = item
        return out
    if isinstance(value, tuple):
        out = list(value)
        out[key] = item
        return type(value)(out)
    raise TypeError(f"set_in expected dict, list, or tuple, got {type(value).__name__}")


def fn(func: Callable) -> Callable:
    """Mark a callable as a function value. Identity — lets app code avoid ``def``."""
    return func


def _call_with_env(func: Any, env: dict) -> Any:
    if not callable(func):
        return func
    try:
        sig = inspect.signature(func)
    except (TypeError, ValueError):
        return func()
    params = list(sig.parameters.values())
    if not params:
        return func()
    if any(param.kind == param.VAR_KEYWORD for param in params):
        return func(**env)
    args = []
    kwargs = {}
    for param in params:
        if param.kind == param.VAR_POSITIONAL:
            continue
        if param.name in env:
            if param.kind == param.KEYWORD_ONLY:
                kwargs[param.name] = env[param.name]
            else:
                args.append(env[param.name])
        elif param.default is inspect.Parameter.empty:
            return func()
    return func(*args, **kwargs)


def let(bindings, body):
    """Sequential locals without ``def``. Callables receive bindings so far.

    ``let(["x", 1, "y", lambda x: x + 1], lambda x, y: x + y)`` → ``3``
    """
    env: dict = {}
    items = list(bindings)
    if len(items) % 2:
        raise ValueError("let bindings must come in name/value pairs")
    for i in range(0, len(items), 2):
        env[items[i]] = _call_with_env(items[i + 1], env)
    return _call_with_env(body, env)


def do(*steps: Any) -> Any:
    """Evaluate ``steps`` in order (calling thunks) and return the last result."""
    result = None
    for step in steps:
        result = step() if callable(step) else step
    return result


def thread(value: Any, *steps: Any) -> Any:
    """Clojure ``->``: each step is ``fn`` or ``(fn, *args)`` with value first."""
    for step in steps:
        if step is None:
            continue
        if callable(step):
            value = step(value)
        elif isinstance(step, (tuple, list)) and step:
            func, *args = step
            value = func(value, *args)
        else:
            raise TypeError(f"thread step must be callable or (fn, *args), got {step!r}")
    return value


def thread_last(value: Any, *steps: Any) -> Any:
    """Clojure ``->>``: value is passed as the last argument."""
    for step in steps:
        if callable(step):
            value = step(value)
        elif isinstance(step, (tuple, list)) and step:
            func, *args = step
            value = func(*args, value)
        else:
            raise TypeError(f"thread_last step must be callable or (fn, *args), got {step!r}")
    return value


def cond(*clauses, else_=None):
    """``cond((pred, then), ..., else_=...)``. Pred/then may be thunks."""
    for clause in clauses:
        pred, then = clause[0], clause[1]
        ok = pred() if callable(pred) else pred
        if ok:
            return then() if callable(then) else then
    if else_ is None:
        return None
    return else_() if callable(else_) else else_


def attempt(thunk: Callable, catch: Callable) -> Any:
    """``try`` without a ``try`` statement in application code."""
    try:
        return thunk()
    except Exception as exc:
        return catch(exc)


def inc(value: Any) -> Any:
    return value + 1


def dec(value: Any) -> Any:
    return value - 1
