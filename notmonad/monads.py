"""Built-in interceptors (caller and side-effect monads)."""

from __future__ import annotations

import warnings
from typing import Any

from notmonad.core import caller, compose, monad
from notmonad.exceptions import MemKeyError

_MISSING = object()


def _call_step(value: Any, func: Any, args: tuple, kwargs: dict) -> Any:
    if not callable(func):
        raise TypeError(
            f"Pipeline step expected a callable, got {type(func).__name__}: {func!r}"
        )
    if value is None:
        return func(*args, **kwargs)
    return func(value, *args, **kwargs)


@caller
def just(value: Any, func: Any, *args: Any, **kwargs: Any):
    """Apply ``func`` and propagate exceptions to the caller."""
    return _call_step(value, func, args, kwargs), func, args, kwargs


@caller
def maybe(value: Any, func: Any = None, *args: Any, **kwargs: Any):
    """Apply ``func``, capturing exceptions as the pipeline value (railway style)."""
    if isinstance(value, Exception):
        return value, func, args, kwargs

    try:
        result = _call_step(value, func, args, kwargs)
    except Exception as exc:
        result = exc

    return result, func, args, kwargs


def debug(value: Any, func: Any, *args: Any, **kwargs: Any):
    """Record each step's call, result, and error without executing ``func`` twice.

    The step function is wrapped so the caller monad runs it once. Append to
    ``pipeline.keywords["_debug_trace"]`` (also ``pipeline.trace``).
    """
    if isinstance(value, Exception) or func is None:
        return value, func, args, kwargs

    trace = kwargs.get("_debug_trace")
    if trace is None:
        trace = []
    verbose = kwargs.get("_debug_print", True)
    original = func

    def traced(*call_args, **call_kwargs):
        errors: Any = ""
        result = None
        try:
            result = original(*call_args, **call_kwargs)
            return result
        except Exception as exc:
            errors = exc
            result = None
            raise
        finally:
            name = getattr(original, "__name__", "")
            user_kwargs = {
                key: val for key, val in call_kwargs.items() if not key.startswith("_")
            }
            entry = {
                "func": name,
                "args": call_args,
                "kwargs": user_kwargs,
                "value": result,
                "errors": repr(errors),
                "repr": f"{name}{call_args} -> {result} [{repr(errors)}]",
            }
            trace.append(entry)
            if verbose:
                print("\n======== \n", entry["repr"])

    traced.__name__ = getattr(original, "__name__", "traced")
    traced.__wrapped__ = original  # type: ignore[attr-defined]
    return value, traced, args, {**kwargs, "_debug_trace": trace}


def shout(value: Any, func: Any, *args: Any, **kwargs: Any):
    """Example side-effect monad: print the function name at every step."""
    if func is not None:
        print("I am shouting!", getattr(func, "__name__", repr(func)))
    return value, func, args, kwargs


def log(value: Any, func: Any, *args: Any, **kwargs: Any):
    """Append each step's function name to ``pipeline.keywords["_log"]``."""
    if func is None:
        return value, func, args, kwargs
    execution_log = list(kwargs.get("_log") or [])
    execution_log.append(getattr(func, "__name__", None))
    return value, func, args, {**kwargs, "_log": execution_log}


def order_args(value: Any, func: Any, *args: Any, **kwargs: Any):
    """Reorder ``(value, *args)`` using ``order=[...]`` index list."""

    def sort_args(items, order):
        return tuple(items[index] for index in order)

    order = kwargs.pop("order", None)
    if order is None:
        return value, func, args, kwargs

    value, *args = sort_args([value, *args], order)
    return value, func, args, kwargs


def assign_args(value: Any, func: Any, *args: Any, **kwargs: Any):
    """Remap positional inputs using ``order={dest: origin, ...}``.

    Integer destinations become positional args; string destinations become
    keyword args.
    """
    order = kwargs.pop("order", None)
    if order is None:
        return value, func, args, kwargs

    packed = (value, *args)
    ordered_args = tuple(
        packed[origin]
        for dest, origin in order.items()
        if isinstance(dest, int) and isinstance(origin, int)
    )
    ordered_kwargs = {
        dest: packed[origin]
        for dest, origin in order.items()
        if isinstance(dest, str) and isinstance(origin, int)
    }
    value, *args = ordered_args
    return value, func, args, {**kwargs, **ordered_kwargs}


def swap_val(value: Any, func: Any, *args: Any, **kwargs: Any):
    """Move the pipeline value into keyword ``v_key`` and promote ``args[0]``."""
    v_key = kwargs.pop("v_key", None)
    if v_key is None:
        return value, func, args, kwargs

    val_temp = value
    try:
        value = args[0]
    except IndexError as exc:
        raise IndexError(
            "To swap out the value to a kwarg, there must at least one arg to replace it."
        ) from exc
    return value, func, args[1:], {**kwargs, v_key: val_temp}


def swap_val_auto(v_key):
    warnings.warn(
        "swap_val_auto is deprecated; use swap_val with v_key=",
        DeprecationWarning,
        stacklevel=2,
    )

    @caller
    def _swap_val(value, func, *args, **kwargs):
        if v_key is None:
            return value, func, args, kwargs
        kwargs = {**kwargs, v_key: value}
        return func(*args, **kwargs), func, args[1:], kwargs

    _swap_val.__name__ = "swap_val_auto"
    return _swap_val


def swap_val_auto_optional(v_key_auto):
    warnings.warn(
        "swap_val_auto_optional is deprecated; use swap_val with v_key=",
        DeprecationWarning,
        stacklevel=2,
    )

    @caller
    def _swap_val(value, func, *args, **kwargs):
        v_key = kwargs.pop("v_key", None)
        if v_key is not None:
            kwargs = {**kwargs, v_key: value}
            return func(*args, **kwargs), func, args[1:], kwargs
        if v_key_auto is None:
            return value, func, args, kwargs
        kwargs = {**kwargs, v_key_auto: value}
        return func(*args, **kwargs), func, args[1:], kwargs

    _swap_val.__name__ = "swap_val_auto_optional"
    return _swap_val


def mem(value: Any, func: Any, *args: Any, **kwargs: Any):
    """Named slots so a pipeline can stash, restore, and apply values.

    Actions (own step, no function call)::

        (__post="key")                      store value; value becomes None
        (__post="key", __retain=True)       store value; keep it as current
        (__get="key")                       load and consume the slot
        (__get="key", __retain=True)        load without consuming
        (__mount=data)                      replace the current value
        (__delete="key")                    drop a slot
        (__get="key", __call=True)          call current value on the loaded slot
        (__strict=True)                     missing keys raise MemKeyError

    Action order: post → delete → get → mount → call.
    """
    post_key = kwargs.get("__post")
    get_key = kwargs.get("__get")
    mount = kwargs["__mount"] if "__mount" in kwargs else _MISSING
    should_call = kwargs.get("__call", False)
    should_retain = kwargs.get("__retain", False)
    delete_key = kwargs.get("__delete")
    strict = kwargs.get("__strict", False)

    has_action = any(
        key in kwargs for key in ("__post", "__get", "__mount", "__call", "__delete")
    )
    if not has_action:
        return value, func, args, {**kwargs, "_skip": False}

    incoming = value
    memory = dict(kwargs.get("_mem") or {})

    if post_key is not None:
        memory[post_key] = value
        if get_key is None and mount is _MISSING:
            value = value if should_retain else None

    if delete_key is not None:
        if delete_key in memory:
            del memory[delete_key]
        elif strict:
            raise MemKeyError(delete_key)

    if get_key is not None:
        if get_key not in memory:
            if strict:
                raise MemKeyError(get_key)
            value = None
        else:
            fetched = memory[get_key]
            if not should_retain:
                del memory[get_key]
            value = fetched

    if mount is not _MISSING:
        value = mount

    if should_call:
        if not callable(incoming):
            raise TypeError(
                "__call=True requires the current pipeline value to be callable, "
                f"got {type(incoming).__name__}"
            )
        value = incoming(value)

    return value, func, args, {**kwargs, "_mem": memory, "_skip": True}


Just = compose(just)
Maybe = compose(maybe)
ForLoops = compose(debug, swap_val, maybe)
App = compose(mem, maybe)
Trace = compose(mem, debug, maybe)


def chain(value: Any, monad_func=None) -> Any:
    """Start a pipeline. Defaults to :data:`Just`; pass :data:`App` for apps."""
    return monad(value, Just if monad_func is None else monad_func)


pipe = chain
