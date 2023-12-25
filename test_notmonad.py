from notmonad import *
import numpy as np
import pytest


def add(arg1, arg2):
    return arg1 + arg2


def append(arr, ele):
    print([*arr, ele])
    return [*arr, ele]


class TestOrderArgsMonad:
    def test_able_to_order_args_for_numpy_funcs(self):
        result = monad(
            np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]]), compose(order_args, just)
        )(np.apply_along_axis, sum, 0, order=[1, 2, 0])()

        np.testing.assert_array_equal(result, np.array([12, 15, 18]))


class TestJustMonad:
    def test_construction_direct(self):
        assert monad(5, Just)() == 5

    def test_construction_with_compose(self):
        assert monad(5, compose(just))() == 5

    def test_able_to_chain_methods(self):
        assert monad(5, Just)(add, 1)(lambda x: x + 2)(add, 3)() == 11

    def test_will_error(self):
        with pytest.raises(ZeroDivisionError):
            monad(5, Just)(add, 1)(lambda x: x / 0)(lambda x: x + 2)(add, 3)()


class TestMaybeMonad:
    def test_construction_direct(self):
        assert monad(5, Maybe)() == 5

    def test_construction_with_compose(self):
        assert monad(5, compose(maybe))() == 5

    def test_able_to_not_error(self):
        assert (
            monad(5, compose(maybe))(add, 1)(lambda x: x / 0)(lambda x: x + 2)(add, 3)()
            is None
        )


class TestLogMonad:
    def test_able_to_log_execution_trace(self):
        assert monad(5, compose(log, just))(add, 1)(add, 3).keywords["_log"] == [
            "add",
            "add",
        ]


class TestMonadConstruction:
    def test_construct_monads_directly(self):
        assert monad(5, Just)(add, 1)() == 6

    def test_construct_monads_with_compose(self):
        assert monad(5, compose(just))(add, 1)() == 6

    def test_construct_monads_with_mmonads(self):
        assert monad(5, mmonad(just)())(add, 1)() == 6

    def test_construct_monads_with_monads(self):
        assert monad(5, compose(*monad([log], Just)(append, just)()))(add, 1)() == 6
