import pytest

np = pytest.importorskip("numpy")

from notmonad import *


def add(arg1, arg2):
    return arg1 + arg2


class TestOrderArgsMonad:
    def test_able_to_order_args_for_numpy_funcs(self):
        result = monad(
            np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]]), compose(order_args, just)
        )(np.apply_along_axis, sum, 0, order=[1, 2, 0])()

        np.testing.assert_array_equal(result, np.array([12, 15, 18]))
