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


class TestDebugMonad:
    def test_return_none_on_error(self):
        assert (
            monad(5, compose(debug, maybe))(add, 1)(lambda x: x / 0)(add, 3)() is None
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
                "errors": "",
                "repr": "add(5, 1) -> 6 []",
            },
            {
                "func": "<lambda>",
                "args": (6,),
                "kwargs": {},
                "value": None,
                "errors": "division by zero",
                "repr": "<lambda>(6,) -> None [division by zero]",
            },
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


class TestLoopFunc:
    def test_loop_with_filter_transform(self):
        assert monad([1, 2, 3], Just)(
            loop, lambda x: [x, x + 1], lambda x: x > 2
        )() == [[3, 4]]

    def test_loop_no_change(self):
        assert monad([1, 2, 3], Just)(loop)() == [1, 2, 3]

    def test_loop_2_layer_nesting_lambda(self):
        assert monad([[1, 2, 3], [1, 2, 3], [1, 2, 3]], Just)(
            loop, lambda x: [i + 1 for i in x]
        )() == [[2, 3, 4], [2, 3, 4], [2, 3, 4]]

    def test_loop_2_layer_nesting_partial(self):
        assert monad([[1, 2, 3], [1, 2, 3], [1, 2, 3]], Just)(
            loop, partial(loop, map=lambda x: x + 1)
        )() == [[2, 3, 4], [2, 3, 4], [2, 3, 4]]

    def test_loop_2_layer_nesting_return_then_call(self):
        assert monad([[1, 2, 3], [1, 2, 3], [1, 2, 3]], compose(order_args, just))(
            partial, loop, order=[1, 0]
        )()(partial(loop, map=lambda x: x + 1)) == [
            [2, 3, 4],
            [2, 3, 4],
            [2, 3, 4],
        ]

    def test_loop_2_layer_nesting_call_in_monad(self):
        assert monad([[1, 2, 3], [1, 2, 3], [1, 2, 3]], compose(order_args, just))(
            partial, loop, order=[1, 0]
        )(call, partial(loop, map=lambda x: x + 1))() == [
            [2, 3, 4],
            [2, 3, 4],
            [2, 3, 4],
        ]

    def test_loop_3_layer_nesting_call_with_nested_lambda(self):
        assert monad(
            [[[1, 2, 3]]],
            compose(order_args, just),
        )(partial, loop, order=[1, 0])(
            call,
            partial(loop, map=partial(loop, map=lambda x: x + 1)),
        )() == [
            [[2, 3, 4]]
        ]

    def test_loop_4_layer_nesting_call_with_nested_lambda(self):
        assert monad(
            [[[[1, 2, 3]]]],
            compose(order_args, just),
        )(partial, loop, order=[1, 0])(
            call,
            partial(
                loop,
                map=partial(loop, map=partial(loop, map=lambda x: x + 1)),
            ),
        )() == [
            [[[2, 3, 4]]]
        ]

    def test_loop_4_layer_nesting_call_with_flat_syntax(self):
        assert monad(
            [[[[[[1, 2, 3]]]]]],
            Maybe,
        )(
            loop,
            map=monad(lambda x: x + 1, compose(assign_args, just))(
                partial, loop, order={0: 1, "map": 0}
            )(partial, loop, order={0: 1, "map": 0})(
                partial, loop, order={0: 1, "map": 0}
            )(
                partial, loop, order={0: 1, "map": 0}
            )(
                partial, loop, order={0: 1, "map": 0}
            )(),
        )() == [[[[[[2, 3, 4]]]]]]

    def test_loop_4_layer_nesting_with_swaps_and_flat_syntax(self):
        assert monad(
            [[[[[[1, 2, 3]]]]]],
            Maybe,
        )(
            loop,
            map=monad(lambda x: x + 1, compose(swap_val, just))(
                partial, loop, v_key="map"
            )(partial, loop, v_key="map")(partial, loop, v_key="map")(
                partial, loop, v_key="map"
            )(
                partial, loop, v_key="map"
            )(),
        )() == [[[[[[2, 3, 4]]]]]]

    def test_loop_4_layer_nesting_with_auto_swaps_and_flat_syntax(self):
        assert monad(
            [[[[[[1, 2, 3]]]]]],
            Maybe,
        )(
            loop,
            map=monad(lambda x: x + 1, compose(swap_val_auto("map"), just))(
                partial, loop
            )(partial, loop)(partial, loop)(partial, loop)(partial, loop)(),
        )() == [[[[[[2, 3, 4]]]]]]

    def test_dloop_4_layer_nesting_with_auto_swaps_and_flat_syntax(self):
        assert monad(
            [[[[[[1, 2, 3]]]]]],
            Maybe,
        )(
            loop,
            map=monad(lambda x: x + 1, compose(swap_val_auto("map"), just))(dloop)(
                dloop
            )(dloop)(dloop)(dloop)(),
        )() == [[[[[[2, 3, 4]]]]]]
