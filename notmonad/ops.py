"""Pipeline operators: loops, branching, effects, and data helpers.

Public helpers are ``chain(..., Seq)`` procedures (memory slots, errors raise).
``while_loop`` / ``while_`` / ``attempt`` / ``let`` stay as Python because they
need a native loop, ``try``, or ``inspect``.
"""

from __future__ import annotations

import inspect
from typing import Any, Callable

from notmonad.core import partial
from notmonad.exceptions import LoopLimitError
from notmonad.monads import Seq, chain

_MISSING = object()
DEFAULT_MAX_STEPS = 1_000_000

_raise = lambda exc: (_ for _ in ()).throw(exc)

identity = lambda value: chain(value, Seq)()

const = lambda value, new_value: chain(value, Seq)(__mount=new_value)()

tap = lambda value, fn, *args, **kwargs: (
    chain(value, Seq)(__post="value", __retain=True)(fn, *args, **kwargs)(
        __get="value"
    )()
)

effect = lambda value, fn, *args, **kwargs: (
    chain(value, Seq)(__post="kept", __mount=fn)(
        lambda func: func(*args, **kwargs)
    )(__get="kept")()
)

_apply = lambda then, value: then(value) if callable(then) else then

if_else = lambda value, pred, then, else_=None: (
    chain(value, Seq)(__post="value", __retain=True)(
        lambda current: bool(pred(current))
    )(lambda ok: then if ok else (identity if else_ is None else else_))(
        lambda chosen: lambda current: _apply(chosen, current)
    )(__get="value", __call=True)()
)

when = lambda value, pred, then: (
    chain(value, Seq)(__post="value", __retain=True)(
        lambda current: bool(pred(current))
    )(lambda ok: then if ok else identity)(
        lambda chosen: lambda current: _apply(chosen, current)
    )(__get="value", __call=True)()
)

unless = lambda value, pred, then: (
    chain(value, Seq)(__post="value", __retain=True)(
        lambda current: bool(pred(current))
    )(lambda ok: identity if ok else then)(
        lambda chosen: lambda current: _apply(chosen, current)
    )(__get="value", __call=True)()
)

recover = lambda value, handler: (
    chain(value, Seq)(
        if_else, lambda item: isinstance(item, Exception), handler, identity
    )()
)

or_else = lambda value, default: (
    chain(value, Seq)(
        if_else,
        lambda item: not isinstance(item, Exception),
        identity,
        lambda item: default(item) if callable(default) else default,
    )()
)

unwrap = lambda value: (
    chain(value, Seq)(
        if_else,
        lambda item: isinstance(item, Exception),
        lambda item: _raise(item),
        identity,
    )()
)

is_error = lambda value: (
    chain(value, Seq)(lambda item: isinstance(item, Exception))()
)

inc = lambda value: chain(value, Seq)(lambda item: item + 1)()

dec = lambda value: chain(value, Seq)(lambda item: item - 1)()

getitem = lambda value, key: chain(value, Seq)(lambda item: item[key])()

get = lambda value, key, default=None: (
    chain(value, Seq)(lambda item: getattr(item, "get", None))(
        if_else,
        callable,
        lambda getter: getter(key, default),
        lambda _: attempt(lambda: value[key], lambda _exc: default),
    )()
)

attr = lambda value, name, default=_MISSING: (
    chain(value, Seq)(
        lambda item: getattr(item, name)
        if default is _MISSING
        else getattr(item, name, default)
    )()
)

invoke = lambda value, name, *args, **kwargs: (
    chain(value, Seq)(lambda item: getattr(item, name)(*args, **kwargs))()
)

set_in = lambda value, key, item: (
    chain(value, Seq)(
        switch,
        (
            (lambda data: isinstance(data, dict), lambda data: {**data, key: item}),
            (
                lambda data: isinstance(data, list),
                lambda data: data[:key] + [item] + data[key + 1 :],
            ),
            (
                lambda data: isinstance(data, tuple),
                lambda data: type(data)(data[:key] + (item,) + data[key + 1 :]),
            ),
        ),
        lambda data: _raise(
            TypeError(
                f"set_in expected dict, list, or tuple, got {type(data).__name__}"
            )
        ),
    )()
)


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


until = lambda value, func, pred, max_steps=DEFAULT_MAX_STEPS: (
    chain(value, Seq)(while_loop, func, until=pred, max_steps=max_steps)()
)


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


times = lambda value, n, func: (
    chain({"v": value, "n": n}, Seq)(
        if_else,
        lambda state: state["n"] < 0,
        lambda _: _raise(ValueError("times() n must be >= 0")),
        identity,
    )(
        while_loop,
        lambda state: {"v": func(state["v"]), "n": state["n"] - 1},
        cond=lambda state: state["n"] > 0,
    )(get, "v")()
)

foreach = lambda value, fn, pred=None: (
    chain({"items": list(value), "out": [], "fn": fn, "pred": pred}, Seq)(
        while_loop,
        lambda state: {
            **state,
            "items": state["items"][1:],
            "out": state["out"]
            + (
                [state["fn"](state["items"][0])]
                if state["pred"] is None or state["pred"](state["items"][0])
                else []
            ),
        },
        cond=lambda state: bool(state["items"]),
    )(get, "out")()
)

loop = lambda data, map=lambda item: item, filter=lambda item: True: (
    chain(data, Seq)(foreach, map, filter)()
)

flatten = lambda value, levels=1: (
    chain({"cur": value, "n": levels}, Seq)(
        while_loop,
        lambda state: {
            "cur": [item for group in state["cur"] for item in group],
            "n": state["n"] - 1,
        },
        cond=lambda state: state["n"] > 0,
    )(get, "cur")()
)

p_loop = lambda value, *args, **kwargs: partial(loop, *args, map=value, **kwargs)

innerwrap = lambda transform, value, pipeline: (
    chain(value, Seq)(pipeline)(transform)()
)

wrap = lambda pipeline, *args, **kwargs: partial(
    innerwrap, *args, pipeline=pipeline, **kwargs
)

outerwrap = lambda transform, value, pipeline: (
    chain(value, Seq)(transform)(pipeline)()
)

peel = lambda pipeline, *args, **kwargs: partial(
    outerwrap, *args, pipeline=pipeline, **kwargs
)

call = lambda func, *args, **kwargs: (
    chain(func, Seq)(lambda fn: fn(*args, **kwargs))()
)

join = lambda value, value2: lambda data: (
    chain(data, Seq)(__post="data", __retain=True)(value)(__post="left")(
        __get="data"
    )(value2)(lambda right: lambda left: [left, right])(
        __get="left", __call=True
    )()
)

merge = lambda value, value2: lambda data: (
    chain(data, Seq)(__post="data", __retain=True)(value)(__post="left")(
        __get="data"
    )(value2)(lambda right: lambda left: {**left, **right})(
        __get="left", __call=True
    )()
)

p_merge = lambda *args: partial(merge, *args)

_switch_step = lambda state: (
    chain(state["cases"][0], Seq)(__post="pair", __retain=True)(
        lambda pair: bool(pair[0](state["value"]))
    )(__post="ok", __retain=True)(
        lambda ok: lambda pair: {
            "value": state["value"],
            "cases": state["cases"][1:],
            "default": state["default"],
            "hit": bool(ok),
            "result": _apply(pair[1], state["value"]) if ok else state.get("result"),
        }
    )(__get="pair", __call=True)()
)

switch = lambda value, cases, default=None: (
    chain(
        {
            "value": value,
            "cases": list(cases),
            "default": default,
            "hit": False,
            "result": None,
        },
        Seq,
    )(
        while_loop,
        _switch_step,
        cond=lambda state: (not state["hit"]) and bool(state["cases"]),
    )(
        if_else,
        lambda state: state["hit"],
        lambda state: state["result"],
        lambda state: state["value"]
        if state["default"] is None
        else _apply(state["default"], state["value"]),
    )()
)

fn = lambda func: func


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


do = lambda *steps: (
    chain({"steps": list(steps), "result": None}, Seq)(
        while_loop,
        lambda state: {
            "result": state["steps"][0]()
            if callable(state["steps"][0])
            else state["steps"][0],
            "steps": state["steps"][1:],
        },
        cond=lambda state: bool(state["steps"]),
    )(get, "result")()
)

thread = lambda value, *steps: (
    chain(
        {
            "v": value,
            "steps": [step for step in steps if step is not None],
        },
        Seq,
    )(
        while_loop,
        lambda state: {
            "v": (
                state["steps"][0](state["v"])
                if callable(state["steps"][0])
                else state["steps"][0][0](state["v"], *state["steps"][0][1:])
                if isinstance(state["steps"][0], (tuple, list)) and state["steps"][0]
                else _raise(
                    TypeError(
                        "thread step must be callable or (fn, *args), "
                        f"got {state['steps'][0]!r}"
                    )
                )
            ),
            "steps": state["steps"][1:],
        },
        cond=lambda state: bool(state["steps"]),
    )(get, "v")()
)

thread_last = lambda value, *steps: (
    chain({"v": value, "steps": list(steps)}, Seq)(
        while_loop,
        lambda state: {
            "v": (
                state["steps"][0](state["v"])
                if callable(state["steps"][0])
                else state["steps"][0][0](*state["steps"][0][1:], state["v"])
                if isinstance(state["steps"][0], (tuple, list)) and state["steps"][0]
                else _raise(
                    TypeError(
                        "thread_last step must be callable or (fn, *args), "
                        f"got {state['steps'][0]!r}"
                    )
                )
            ),
            "steps": state["steps"][1:],
        },
        cond=lambda state: bool(state["steps"]),
    )(get, "v")()
)

_cond_step = lambda state: (
    chain(state["clauses"][0], Seq)(__post="clause", __retain=True)(
        lambda clause: bool(clause[0]() if callable(clause[0]) else clause[0])
    )(__post="ok", __retain=True)(
        lambda ok: lambda clause: {
            "clauses": state["clauses"][1:],
            "else_": state["else_"],
            "hit": bool(ok),
            "result": (clause[1]() if callable(clause[1]) else clause[1])
            if ok
            else None,
        }
    )(__get="clause", __call=True)()
)

cond = lambda *clauses, else_=None: (
    chain(
        {
            "clauses": list(clauses),
            "else_": else_,
            "hit": False,
            "result": None,
        },
        Seq,
    )(
        while_loop,
        _cond_step,
        cond=lambda state: (not state["hit"]) and bool(state["clauses"]),
    )(
        if_else,
        lambda state: state["hit"],
        lambda state: state["result"],
        lambda state: None
        if state["else_"] is None
        else state["else_"]()
        if callable(state["else_"])
        else state["else_"],
    )()
)


def attempt(thunk: Callable, catch: Callable) -> Any:
    """``try`` without a ``try`` statement in application code."""
    try:
        return thunk()
    except Exception as exc:
        return catch(exc)
