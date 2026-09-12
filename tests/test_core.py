from notmonad import *


def add(arg1, arg2):
    return arg1 + arg2


def append(arr, ele):
    return [*arr, ele]


class TestJustMonad:
    def test_construction_direct(self):
        assert monad(5, Just)() == 5

    def test_construction_with_compose(self):
        assert monad(5, compose(just))() == 5

    def test_able_to_chain_methods(self):
        assert monad(5, Just)(add, 1)(lambda x: x + 2)(add, 3)() == 11

    def test_will_error(self):
        import pytest

        with pytest.raises(ZeroDivisionError):
            monad(5, Just)(add, 1)(lambda x: x / 0)(lambda x: x + 2)(add, 3)()

    def test_able_to_call_with_none_value(self):
        assert monad(None, Just)(lambda: 5)() == 5

    def test_chain_helper(self):
        assert chain(5)(add, 1)(add, 3)() == 9

    def test_pipe_alias(self):
        assert pipe(5)(add, 1)() == 6

    def test_result_and_expect(self):
        pipeline = chain(5)(add, 1)
        assert pipeline.result() == 6
        assert pipeline.expect() == 6


class TestMaybeMonad:
    def test_construction_direct(self):
        assert monad(5, Maybe)() == 5

    def test_construction_with_compose(self):
        assert monad(5, compose(maybe))() == 5

    def test_able_to_not_error(self):
        assert isinstance(
            monad(5, compose(maybe))(add, 1)(lambda x: x / 0)(lambda x: x + 2)(
                add, 3
            )(),
            ZeroDivisionError,
        )

    def test_able_to_call_with_none_value(self):
        assert monad(None, Maybe)(lambda: 5)() == 5

    def test_expect_raises_captured_error(self):
        import pytest

        with pytest.raises(ZeroDivisionError):
            monad(5, Maybe)(lambda x: x / 0).expect()

    def test_short_circuit_keeps_mem(self):
        pipeline = monad(5, App)(__post="x", __retain=True)(lambda x: x / 0)(add, 3)
        assert isinstance(pipeline(), ZeroDivisionError)
        assert pipeline.mem == {"x": 5}


class TestLogMonad:
    def test_able_to_log_execution_trace(self):
        assert monad(5, compose(log, just))(add, 1)(add, 3).keywords["_log"] == [
            "add",
            "add",
        ]

    def test_log_property(self):
        assert monad(5, compose(log, just))(add, 1)(add, 3).log == ["add", "add"]


class TestDebugMonad:
    def test_return_none_on_error(self):
        assert isinstance(
            monad(5, compose(debug, maybe))(add, 1)(lambda x: x / 0)(add, 3)(),
            ZeroDivisionError,
        )

    def test_able_to_get_debug_trace(self):
        assert monad(5, compose(debug, maybe))(add, 1)(lambda x: x / 0)(
            add, 3
        ).keywords["_debug_trace"] == [
            {
                "func": "add",
                "args": (5, 1),
                "kwargs": {},
                "value": 6,
                "errors": "''",
                "repr": "add(5, 1) -> 6 ['']",
            },
            {
                "func": "<lambda>",
                "args": (6,),
                "kwargs": {},
                "value": None,
                "errors": "ZeroDivisionError('division by zero')",
                "repr": "<lambda>(6,) -> None [ZeroDivisionError('division by zero')]",
            },
        ]

    def test_debug_runs_function_once(self):
        calls = []

        def inc(x):
            calls.append(x)
            return x + 1

        assert monad(1, compose(debug, just))(inc)(inc)() == 3
        assert calls == [1, 2]


class TestMonadConstruction:
    def test_seq_has_mem_and_raises(self):
        import pytest

        pipeline = chain(5, Seq)(__post="x", __retain=True)(add, 1)
        assert pipeline() == 6
        assert pipeline.mem == {"x": 5}
        with pytest.raises(ZeroDivisionError):
            chain(5, Seq)(lambda x: x / 0)()

    def test_construct_monads_directly(self):
        assert monad(5, Just)(add, 1)() == 6

    def test_construct_monads_with_compose(self):
        assert monad(5, compose(just))(add, 1)() == 6

    def test_construct_monads_with_mmonads(self):
        assert monad(5, mmonad(just)())(add, 1)() == 6

    def test_construct_monads_with_monads(self):
        assert monad(5, compose(*monad([log], Just)(append, just)()))(add, 1)() == 6

    def test_mmonad_kwargs_are_forwarded(self):
        assert monad(5, mmonad(log)(just)())(add, 1)(add, 2).log == ["add", "add"]

    def test_two_callers_rejected_at_compose_time(self):
        import pytest

        with pytest.raises(CallerConflictError):
            compose(just, maybe)
