import pytest

from notmonad import *


def add(a, b):
    return a + b


class TestControlFlow:
    def test_while_loop_until(self):
        assert chain(0)(while_loop, lambda n: n + 1, until=lambda n: n >= 5)() == 5

    def test_while_loop_cond_callable(self):
        assert chain(0)(while_loop, lambda n: n + 2, cond=lambda n: n < 6)() == 6

    def test_while_loop_false_cond_is_noop(self):
        assert chain(3)(while_loop, lambda n: n + 1, cond=False)() == 3

    def test_while_loop_max_steps(self):
        with pytest.raises(LoopLimitError):
            chain(0)(while_loop, lambda n: n + 1, max_steps=10)()

    def test_while_tuple_api(self):
        assert (
            chain(0)(while_, lambda n: (n + 1, n + 1 >= 4))() == 4
        )

    def test_until_helper(self):
        assert chain(1)(until, lambda n: n * 2, lambda n: n >= 8)() == 8

    def test_times(self):
        assert chain(2)(times, 4, lambda n: n + 1)() == 6

    def test_if_else_when_unless_switch(self):
        assert chain(3)(if_else, lambda n: n > 2, lambda n: n * 10, lambda n: n)() == 30
        assert chain(1)(if_else, lambda n: n > 2, lambda n: n * 10)() == 1
        assert chain(4)(when, lambda n: n > 2, lambda n: n + 1)() == 5
        assert chain(1)(when, lambda n: n > 2, lambda n: n + 1)() == 1
        assert chain(1)(unless, lambda n: n > 2, lambda n: n + 8)() == 9
        assert (
            chain("b")(
                switch,
                (
                    (lambda s: s == "a", lambda s: 1),
                    (lambda s: s == "b", lambda s: 2),
                ),
                lambda s: 0,
            )()
            == 2
        )
        assert chain({})(if_else, lambda row: row.get("id"), 200, 404)() == 404
        assert chain({"id": 1})(if_else, lambda row: row.get("id"), 200, 404)() == 200

    def test_foreach_and_flatten(self):
        assert chain([1, 2, 3])(foreach, lambda n: n * 2, lambda n: n > 1)() == [4, 6]
        assert chain([[1, 2], [3]])(flatten)() == [1, 2, 3]

    def test_tap_effect_const_identity(self):
        seen = []
        assert chain(5)(tap, seen.append)(identity)() == 5
        assert seen == [5]
        called = []
        assert chain(5)(effect, called.append, "hi")(const, 9)() == 9
        assert called == ["hi"]


class TestErrors:
    def test_recover_or_else_unwrap(self):
        failed = monad(5, Maybe)(lambda x: x / 0)
        assert chain(failed())(recover, lambda exc: type(exc).__name__)() == (
            "ZeroDivisionError"
        )
        assert chain(failed())(or_else, 0)() == 0
        assert chain(failed())(or_else, lambda exc: 7)() == 7
        assert chain(1, Maybe)(add, 1)(is_error)() is False
        with pytest.raises(ZeroDivisionError):
            chain(failed())(unwrap)()


class TestStateHelpers:
    def test_get_getitem_set_in_attr_invoke(self):
        assert chain({"a": 1, "b": 2})(get, "a")() == 1
        assert chain({"a": 1})(get, "missing", 9)() == 9
        assert chain([10, 20])(getitem, 1)() == 20
        assert chain({"a": 1})(set_in, "b", 2)() == {"a": 1, "b": 2}
        assert chain([1, 2])(set_in, 0, 9)() == [9, 2]

        class Box:
            def __init__(self):
                self.n = 3

            def bump(self, by):
                self.n += by
                return self.n

        box = Box()
        assert chain(box)(attr, "n")() == 3
        assert chain(box)(invoke, "bump", 2)() == 5
