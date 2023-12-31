from notmonad import *
import numpy as np
import pytest


def add(arg1, arg2):
    return arg1 + arg2


def append(arr, ele):
    print([*arr, ele])
    return [*arr, ele]


json_data = [
    {
        "name": "Leanne Graham",
        "addresses": [
            {
                "zipcode": "00001-999",
            },
            {
                "zipcode": "00002-999",
            },
            {
                "zipcode": "00003-999",
            },
        ],
        "phones": ["1-770", "2-770"],
    },
    {
        "name": "Ervin Howell",
        "addresses": [
            {
                "zipcode": "00004-999",
            },
            {
                "zipcode": "00005-999",
            },
            {
                "zipcode": "00006-999",
            },
        ],
        "phones": ["3-770", "4-770", "5-770", "6-770"],
    },
]


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

    def test_able_to_call_with_none_value(self):
        assert monad(None, Just)(lambda: 5)() == 5


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


class TestLogMonad:
    def test_able_to_log_execution_trace(self):
        assert monad(5, compose(log, just))(add, 1)(add, 3).keywords["_log"] == [
            "add",
            "add",
        ]


class TestDebugMonad:
    def test_return_none_on_error(self):
        assert isinstance(
            monad(5, compose(debug, maybe))(add, 1)(lambda x: x / 0)(add, 3)(),
            ZeroDivisionError,
        )

    def test_able_to_get_debug_trace(self):
        print(
            monad(5, compose(debug, maybe))(add, 1)(lambda x: x / 0)(add, 3).keywords[
                "_debug_trace"
            ]
        )

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
            map=monad(lambda x: x + 1, compose(swap_val, just))(p_loop)(p_loop)(p_loop)(
                p_loop
            )(p_loop)(),
        )() == [[[[[[2, 3, 4]]]]]]

    def test_cloop_4_layer_nesting_with_flat_syntax(self):
        assert monad(
            [[[[[[1, 2, 3]]]]]],
            Maybe,
        )(
            loop,
            map=monad(lambda x: x + 1, compose(swap_val, maybe))(p_loop)(p_loop)(
                p_loop
            )(p_loop)(p_loop)(),
        )() == [[[[[[2, 3, 4]]]]]]

    def test_cloop_with_lambda_modifications(self):
        assert monad(
            [[1, 2], [3, 4]],
            Maybe,
        )(
            loop,
            map=monad(lambda x: x + 1, compose(swap_val, just))(p_loop)(
                wrap,
                lambda x: {"cluster": x},
            )(),
        )() == [{"cluster": [2, 3]}, {"cluster": [4, 5]}]

    def test_loop_with_lambda_mod_direct(self):
        test_data = [[[[[[[1, 2], [3, 4]]]]]]]
        test_answer = [[[[[[{"cluster": [2, 3]}, {"cluster": [4, 5]}]]]]]]

        # fmt: off
        assert (monad(test_data,Maybe)
                (monad(lambda x: x + 1, compose(swap_val, maybe))
                 (p_loop)
                 (wrap, lambda x: {"cluster": x})
                 (p_loop)
                 (p_loop)
                 (p_loop)
                 (p_loop)
                 (p_loop)
                 (p_loop)
                 ())() == test_answer)
        # fmt: on

        # VS

        assert [
            [
                [
                    [
                        [[{"cluster": [o + 1 for o in n]} for n in m] for m in l]
                        for l in k
                    ]
                    for k in j
                ]
                for j in i
            ]
            for i in test_data
        ] == test_answer

    def test_loop_with_flatten(self):
        test_data = [[[[[[[1, 2], [3, 4]]]]]]]
        test_answer = [{"cluster": [2, 3]}, {"cluster": [4, 5]}]

        # fmt: off
        assert (monad(test_data,Maybe)
                (monad(lambda x: x + 1, compose(swap_val, maybe))
                 (p_loop)
                 (wrap, lambda x: {"cluster": x})
                 (p_loop)
                 (peel, lambda x: x[0])
                 (peel, lambda x: x[0])
                 (peel, lambda x: x[0])
                 (peel, lambda x: x[0])
                 (peel, lambda x: x[0])
                 ())()) == test_answer
        # fmt: on

    def test_loop_with_real_world_data(self):
        # TASK: Return the first 5 numbers of zip code and the first number of each phone
        answer = [
            [["00001", "00002", "00003"], ["1", "2"]],
            [["00004", "00005", "00006"], ["3", "4", "5", "6"]],
        ]

        assert answer == [
            [
                [address["zipcode"][:5] for address in user["addresses"]],
                [phone[0] for phone in user["phones"]],
            ]
            for user in json_data
        ]

        # VS

        assert (
            answer
            == monad(json_data, Maybe)(
                monad(
                    lambda user: [
                        monad(
                            lambda address: address["zipcode"][:5],
                            compose(swap_val, maybe),
                        )(p_loop)(peel, lambda x: x["addresses"],)()(user),
                        monad(lambda phone: phone[0], compose(swap_val, maybe))(p_loop)(
                            peel, lambda x: x["phones"]
                        )()(user),
                    ],
                    compose(swap_val, maybe),
                )(p_loop)()
            )()
        )

    def test_loop_with_join_on_real_world_data(self):
        # TASK: Return the first 5 numbers of zip code and the first number of each phone
        answer = [
            [["00001", "00002", "00003"], ["1", "2"]],
            [["00004", "00005", "00006"], ["3", "4", "5", "6"]],
        ]

        assert answer == [
            [
                [address["zipcode"][:5] for address in user["addresses"]],
                [phone[0] for phone in user["phones"]],
            ]
            for user in json_data
        ]

        # VS

        assert (
            answer
            == monad(json_data, Maybe)(
                monad(
                    lambda address: address["zipcode"][:5],
                    compose(swap_val, maybe),
                )(p_loop)(peel, lambda x: x["addresses"])(
                    join,
                    monad(lambda phone: phone[0], compose(swap_val, maybe))(p_loop)(
                        peel,
                        lambda x: x["phones"],
                    )(),
                )(
                    p_loop
                )()
            )()
        )

    def test_loop_with_merge_on_real_world_data(self):
        # TASK: Return the first 5 numbers of zip code and the first number of each phone
        answer = [
            {"address": ["00001", "00002", "00003"], "phone": ["1", "2"]},
            {
                "address": ["00004", "00005", "00006"],
                "phone": ["3", "4", "5", "6"],
            },
        ]

        assert answer == [
            {
                "address": [address["zipcode"][:5] for address in user["addresses"]],
                "phone": [phone[0] for phone in user["phones"]],
            }
            for user in json_data
        ]

        # VS

        assert (
            answer
            == monad(json_data, Maybe)(
                monad(
                    lambda address: address["zipcode"][:5],
                    compose(swap_val, maybe),
                )(p_loop)(
                    peel,
                    lambda x: x["addresses"],
                )(
                    wrap,
                    lambda x: {"address": x},
                )(
                    merge,
                    monad(lambda phone: phone[0], compose(swap_val, maybe))(p_loop)(
                        peel,
                        lambda x: x["phones"],
                    )(
                        wrap,
                        lambda x: {"phone": x},
                    )(),
                )(
                    p_loop
                )()
            )()
        )


class TestMem:
    def test_loop_with_mem(self):
        # TASK: Return the first 5 numbers of zip code and the first number of each phone
        answer = [
            {"address": ["00001", "00002", "00003"], "phone": ["1", "2"]},
            {
                "address": ["00004", "00005", "00006"],
                "phone": ["3", "4", "5", "6"],
            },
        ]

        assert answer == [
            {
                "address": [address["zipcode"][:5] for address in user["addresses"]],
                "phone": [phone[0] for phone in user["phones"]],
            }
            for user in json_data
        ]

        # VS
        # fmt: off
        assert (
            answer
            == monad(json_data, compose(mem, debug, swap_val, maybe))
                (__post="data")
                (__mount=lambda address: address["zipcode"][:5])
                (p_loop)
                (peel,  lambda x: x["addresses"])
                (wrap, lambda x: {"address": x})
                (__post="user_func")
                (__mount=lambda phone: phone[0])
                (p_loop)
                (peel,  lambda x: x["phones"])
                (wrap, lambda x: {"phone": x})
                (p_merge)
                (__get="user_func", __call=True)
                (p_loop)
                (__get="data", __call=True)
                ()
        )
        # fmt: on
