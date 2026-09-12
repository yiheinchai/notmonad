"""Immutable-ish data helpers and atoms — Clojure-style, still Python.

``Atom`` is the mutable box (needs a class). Everything apps import is a
``chain(..., Seq)`` procedure.
"""

from __future__ import annotations

from typing import Any, Callable

from notmonad.monads import Seq, chain
from notmonad.ops import attempt, get, if_else, unless, while_loop


class Atom:
    """Synchronous mutable box. Swap/reset return the new value."""

    __slots__ = ("state",)

    def __init__(self, state: Any) -> None:
        self.state = state

    def deref(self) -> Any:
        return self.state

    def reset(self, value: Any) -> Any:
        self.state = value
        return value

    def swap(self, fn: Callable, *args: Any) -> Any:
        self.state = fn(self.state, *args)
        return self.state

    def __repr__(self) -> str:
        return f"Atom({self.state!r})"


atom = lambda state=None: chain(Atom, Seq)(lambda cls: cls(state))()

deref = lambda box: chain(box, Seq)(lambda item: item.deref())()

reset = lambda box, value: chain(box, Seq)(lambda item: item.reset(value))()

swap = lambda box, fn, *args: (
    chain(box, Seq)(lambda item: item.swap(fn, *args))()
)

assoc = lambda mapping, *kvs: (
    chain(
        {
            "out": dict(mapping or {}),
            "pairs": [(kvs[i], kvs[i + 1]) for i in range(0, len(kvs), 2)],
        },
        Seq,
    )(
        while_loop,
        lambda state: {
            "out": {
                **state["out"],
                state["pairs"][0][0]: state["pairs"][0][1],
            },
            "pairs": state["pairs"][1:],
        },
        cond=lambda state: bool(state["pairs"]),
    )(get, "out")()
)

dissoc = lambda mapping, *keys: (
    chain(
        {
            "items": list(dict(mapping or {}).items()),
            "drop": set(keys),
            "out": {},
        },
        Seq,
    )(
        while_loop,
        lambda state: {
            **state,
            "items": state["items"][1:],
            "out": state["out"]
            if state["items"][0][0] in state["drop"]
            else {
                **state["out"],
                state["items"][0][0]: state["items"][0][1],
            },
        },
        cond=lambda state: bool(state["items"]),
    )(get, "out")()
)

_get_in_step = lambda state: (
    chain(state, Seq)(
        if_else,
        lambda item: item["cur"] is None,
        lambda item: {**item, "miss": True, "rest": []},
        lambda item: chain(item, Seq)(
            if_else,
            lambda cur_state: callable(getattr(cur_state["cur"], "get", None)),
            lambda cur_state: {
                **cur_state,
                "miss": True,
                "rest": [],
                "cur": cur_state["default"],
            }
            if cur_state["rest"][0] not in cur_state["cur"]
            else {
                **cur_state,
                "cur": cur_state["cur"][cur_state["rest"][0]],
                "rest": cur_state["rest"][1:],
            },
            lambda cur_state: attempt(
                lambda: {
                    **cur_state,
                    "cur": cur_state["cur"][cur_state["rest"][0]],
                    "rest": cur_state["rest"][1:],
                },
                lambda _: {
                    **cur_state,
                    "miss": True,
                    "rest": [],
                    "cur": cur_state["default"],
                },
            ),
        )(),
    )()
)

get_in = lambda mapping, path, default=None: (
    chain(
        {
            "cur": mapping,
            "rest": list(path),
            "default": default,
            "miss": False,
        },
        Seq,
    )(
        while_loop,
        _get_in_step,
        cond=lambda state: (not state["miss"]) and bool(state["rest"]),
    )(
        if_else,
        lambda state: state["miss"],
        lambda state: state["default"],
        lambda state: state["cur"],
    )()
)

assoc_in = lambda mapping, path, value: (
    chain(
        {"mapping": mapping, "path": list(path), "value": value, "out": None},
        Seq,
    )(
        if_else,
        lambda state: not state["path"],
        lambda state: {**state, "out": state["value"], "done": True},
        lambda state: {**state, "done": False},
    )(
        unless,
        lambda state: state["done"],
        lambda state: {
            **state,
            "out": assoc(state["mapping"], state["path"][0], state["value"])
            if len(state["path"]) == 1
            else assoc(
                state["mapping"],
                state["path"][0],
                assoc_in(
                    (state["mapping"] or {}).get(state["path"][0])
                    if isinstance(state["mapping"], dict)
                    else None,
                    state["path"][1:],
                    state["value"],
                ),
            ),
            "done": True,
        },
    )(get, "out")()
)

update = lambda mapping, key, fn, *args: (
    chain(mapping, Seq)(
        lambda item: None
        if item is None
        else item.get(key)
        if hasattr(item, "get")
        else None
    )(lambda current: assoc(mapping, key, fn(current, *args)))()
)

update_in = lambda mapping, path, fn, *args: (
    chain(
        {
            "mapping": mapping,
            "path": list(path),
            "fn": fn,
            "args": args,
            "out": None,
        },
        Seq,
    )(
        if_else,
        lambda state: not state["path"],
        lambda state: {
            **state,
            "out": state["fn"](state["mapping"], *state["args"]),
            "done": True,
        },
        lambda state: {**state, "done": False},
    )(
        unless,
        lambda state: state["done"],
        lambda state: {
            **state,
            "out": update(
                state["mapping"], state["path"][0], state["fn"], *state["args"]
            )
            if len(state["path"]) == 1
            else assoc(
                state["mapping"],
                state["path"][0],
                update_in(
                    (state["mapping"] or {}).get(state["path"][0])
                    if isinstance(state["mapping"], dict)
                    else None,
                    state["path"][1:],
                    state["fn"],
                    *state["args"],
                ),
            ),
            "done": True,
        },
    )(get, "out")()
)

dmerge = lambda *maps: (
    chain({"maps": list(maps), "out": {}}, Seq)(
        while_loop,
        lambda state: {
            "maps": state["maps"][1:],
            "out": {**state["out"], **state["maps"][0]}
            if state["maps"][0]
            else state["out"],
        },
        cond=lambda state: bool(state["maps"]),
    )(get, "out")()
)
