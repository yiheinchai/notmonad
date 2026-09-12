"""A tiny todo CLI built with notmonad — state, branching, and a main loop."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from notmonad import App, chain, effect, get, set_in, switch, tap, while_loop


def parse(line: str):
    parts = line.strip().split(maxsplit=1)
    if not parts:
        return {"op": "", "arg": ""}
    op = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""
    return {"op": op, "arg": arg}


def prompt(state, reader, _writer):
    try:
        line = reader("todo> ")
    except EOFError:
        return {**state, "done": True, "line": "quit"}
    return {**state, "line": line if line is not None else "quit"}
    try:
        line = reader("todo> ")
    except EOFError:
        return {**state, "done": True, "line": "quit"}
    return {**state, "line": line if line is not None else "quit"}


def apply_command(state):
    command = parse(state.get("line", ""))
    items = list(state.get("items") or [])
    op, arg = command["op"], command["arg"]

    def add(_state):
        if not arg:
            return set_in(state, "message", "usage: add <text>")
        return {**state, "items": [*items, arg], "message": f"added {arg!r}"}

    def listed(_state):
        if not items:
            return set_in(state, "message", "(empty)")
        body = "\n".join(f"{index + 1}. {item}" for index, item in enumerate(items))
        return set_in(state, "message", body)

    def done(_state):
        try:
            index = int(arg) - 1
            removed = items.pop(index)
        except (ValueError, IndexError):
            return set_in(state, "message", "usage: done <n>")
        return {**state, "items": items, "message": f"done {removed!r}"}

    def quit_(_state):
        return {**state, "done": True, "message": "bye"}

    def unknown(_state):
        return set_in(
            state,
            "message",
            "commands: add <text> | list | done <n> | quit",
        )

    return switch(
        state,
        (
            (lambda _s: op in {"add", "a"}, add),
            (lambda _s: op in {"list", "ls", "l"}, listed),
            (lambda _s: op in {"done", "rm", "d"}, done),
            (lambda _s: op in {"quit", "exit", "q"}, quit_),
        ),
        default=unknown,
    )


def show(state, write):
    message = state.get("message")
    if message:
        write(message)
    return state


def run(*, reader=input, writer=print):
    def step(state):
        return (
            chain(state, App)(lambda current: prompt(current, reader, writer))(
                apply_command
            )(tap, show, writer)()
        )

    return (
        chain({"items": [], "done": False, "message": ""}, App)(
            effect,
            writer,
            "todo — commands: add <text> | list | done <n> | quit",
        )(while_loop, step, until=lambda state: state.get("done"))(get, "items")()
    )


def main():
    run()


if __name__ == "__main__":
    main()
