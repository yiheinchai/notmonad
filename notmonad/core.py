"""Pipeline engine: partial application, monad composition, and chaining."""

from __future__ import annotations

from typing import Any, Callable, Mapping, MutableMapping, Tuple

from notmonad.exceptions import CallerConflictError

MonadResult = Tuple[Any, Any, tuple, dict]
Monad = Callable[..., MonadResult]

_DROP_STATE = frozenset({"_consumed", "_skip"})


class Partial:
    """A callable with some arguments already bound.

    This is the object returned by every unfinished pipeline step. It keeps the
    historic ``.func`` / ``.args`` / ``.keywords`` attributes so debug traces,
    logs, and memory can be read off a pipeline without unwrapping it.
    """

    __slots__ = ("func", "args", "keywords", "__name__")

    def __init__(
        self,
        func: Callable[..., Any],
        args: tuple = (),
        keywords: MutableMapping[str, Any] | None = None,
    ) -> None:
        self.func = func
        self.args = tuple(args)
        self.keywords = {} if keywords is None else keywords
        self.__name__ = getattr(func, "__name__", "partial")

    def __call__(self, *fargs: Any, **fkeywords: Any) -> Any:
        return self.func(*self.args, *fargs, **{**self.keywords, **fkeywords})

    def __repr__(self) -> str:
        value = self.args[1] if len(self.args) >= 2 else None
        return f"Pipeline(value={value!r})"

    def result(self) -> Any:
        """Unwrap the pipeline value. Same as calling the pipeline with ``()``."""
        return self()

    def expect(self) -> Any:
        """Unwrap the value, raising if a Maybe-pipeline stored an exception."""
        value = self()
        if isinstance(value, Exception):
            raise value
        return value

    @property
    def trace(self) -> list:
        return list(self.keywords.get("_debug_trace") or [])

    @property
    def log(self) -> list:
        return list(self.keywords.get("_log") or [])

    @property
    def mem(self) -> dict:
        return dict(self.keywords.get("_mem") or {})


def partial(func: Callable[..., Any], /, *args: Any, **keywords: Any) -> Partial:
    """Bind arguments to ``func``. Replaces ``functools.partial`` in this library."""
    bound = Partial(func, args, keywords)
    bound.__name__ = getattr(func, "__name__", "partial")
    return bound


def split_kwargs(
    kwargs: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Split kwargs into ``(func_params, state, actions)``.

    Convention
    ----------
    * ``foo=`` — forwarded to the step function
    * ``_foo=`` — pipeline state carried between steps (``_mem``, ``_log``, ...)
    * ``__foo=`` — one-shot interceptor actions (``__post``, ``__get``, ...)
    """
    params: dict[str, Any] = {}
    state: dict[str, Any] = {}
    actions: dict[str, Any] = {}
    for key, value in kwargs.items():
        if key.startswith("__"):
            actions[key] = value
        elif key.startswith("_"):
            state[key] = value
        else:
            params[key] = value
    return params, state, actions


def caller(monad: Monad) -> Monad:
    """Mark ``monad`` as the data-transforming interceptor in a stack.

    A composed stack may contain any number of side-effect interceptors and at
    most one caller. The caller is the interceptor that actually invokes the
    step function.
    """

    def inner(*args: Any, **kwargs: Any) -> MonadResult:
        pkwargs = {key: value for key, value in kwargs.items() if not key.startswith("_")}
        _kwargs = {key: value for key, value in kwargs.items() if key.startswith("_")}
        if _kwargs.get("_consumed"):
            raise CallerConflictError(
                "Cannot compose two caller monads together. "
                f"{getattr(monad, '__name__', monad)} is the second caller monad used. "
                "Please remove this for it to work."
            )
        new_val, new_func, new_args, new_kwargs = monad(*args, **pkwargs)
        return new_val, new_func, new_args, {**_kwargs, **new_kwargs, "_consumed": True}

    inner.__name__ = getattr(monad, "__name__", "caller")  # type: ignore[attr-defined]
    inner._is_caller = True  # type: ignore[attr-defined]
    inner.__wrapped__ = monad  # type: ignore[attr-defined]
    return inner


def compose(*monads: Monad) -> Partial:
    """Compose interceptors into a single pipeline stack.

    Side-effect monads run first (logging, memory, argument rewriting). The
    single caller monad should be last so the step function runs once.
    """
    callers = [
        getattr(monad, "__name__", "?")
        for monad in monads
        if getattr(monad, "_is_caller", False)
    ]
    if len(callers) > 1:
        raise CallerConflictError(
            "Cannot compose multiple caller monads: "
            + ", ".join(callers)
            + ". A pipeline may include at most one caller."
        )

    def combined_monad(_monads, value, func=None, *args, **kwargs):
        params, state, actions = split_kwargs(kwargs)

        # ``pipeline()`` — no step function, no extra args, no memory actions.
        if func is None and not args and not params and not actions:
            return value

        if not _monads:
            if kwargs.get("_skip") or func is not None:
                forwarded = {
                    key: value_
                    for key, value_ in state.items()
                    if key not in _DROP_STATE
                }
                return partial(combined_monad, monads, value, **forwarded)
            return value

        monad, *rest = _monads
        if kwargs.get("_skip"):
            new_val, new_func, new_args, new_kwargs = value, func, args, kwargs
        else:
            new_val, new_func, new_args, new_kwargs = monad(
                value, func, *args, **kwargs
            )
        return combined_monad(rest, new_val, new_func, *new_args, **new_kwargs)

    combined_monad.__name__ = "pipeline"
    return partial(combined_monad, monads)


def mmonad(monad_to_add: Monad) -> Partial:
    """Incrementally compose interceptors: ``mmonad(just)(log)(mem)()``."""

    def accumulate(monad_list, next_monad=None):
        if next_monad is None:
            return compose(*monad_list)
        return partial(accumulate, [*monad_list, next_monad])

    return accumulate([monad_to_add])


def monad(value: Any, monad_func: Callable[..., Any]) -> Partial:
    """Start a pipeline with ``value`` and the given interceptor stack."""
    return partial(monad_func, value)
