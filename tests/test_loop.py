from notmonad import *
from tests.sample_data import json_data


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
            )(partial, loop, order={0: 1, "map": 0})(
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
        answer = [
            [["00001", "00002", "00003"], ["1", "2"]],
            [["00004", "00005", "00006"], ["3", "4", "5", "6"]],
        ]

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
        answer = [
            {"address": ["00001", "00002", "00003"], "phone": ["1", "2"]},
            {
                "address": ["00004", "00005", "00006"],
                "phone": ["3", "4", "5", "6"],
            },
        ]

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
