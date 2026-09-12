"""Immutable-ish data helpers and atoms — Clojure-style, still Python."""

from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence


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


def atom(state: Any = None) -> Atom:
    return Atom(state)


def deref(box: Atom) -> Any:
    return box.deref()


def reset(box: Atom, value: Any) -> Any:
    return box.reset(value)


def swap(box: Atom, fn: Callable, *args: Any) -> Any:
    return box.swap(fn, *args)


def assoc(mapping: Mapping | None, *kvs: Any) -> dict:
    out = dict(mapping or {})
    for i in range(0, len(kvs), 2):
        out[kvs[i]] = kvs[i + 1]
    return out


def dissoc(mapping: Mapping | None, *keys: Any) -> dict:
    out = dict(mapping or {})
    for key in keys:
        out.pop(key, None)
    return out


def get_in(mapping: Any, path: Sequence, default: Any = None) -> Any:
    cur = mapping
    for key in path:
        if cur is None:
            return default
        getter = getattr(cur, "get", None)
        if callable(getter):
            if key not in cur:
                return default
            cur = cur[key]
            continue
        try:
            cur = cur[key]
        except (KeyError, IndexError, TypeError):
            return default
    return cur


def assoc_in(mapping: Mapping | None, path: Sequence, value: Any) -> dict:
    path = list(path)
    if not path:
        return value
    key = path[0]
    if len(path) == 1:
        return assoc(mapping, key, value)
    nested = (mapping or {}).get(key) if isinstance(mapping, dict) else None
    return assoc(mapping, key, assoc_in(nested, path[1:], value))


def update(mapping: Mapping | None, key: Any, fn: Callable, *args: Any) -> dict:
    current = None if mapping is None else mapping.get(key) if hasattr(mapping, "get") else None
    return assoc(mapping, key, fn(current, *args))


def update_in(mapping: Mapping | None, path: Sequence, fn: Callable, *args: Any) -> dict:
    path = list(path)
    if not path:
        return fn(mapping, *args)
    key = path[0]
    if len(path) == 1:
        return update(mapping, key, fn, *args)
    nested = (mapping or {}).get(key) if isinstance(mapping, dict) else None
    return assoc(mapping, key, update_in(nested, path[1:], fn, *args))


def dmerge(*maps: Mapping | None) -> dict:
    out: dict = {}
    for mapping in maps:
        if mapping:
            out.update(mapping)
    return out
