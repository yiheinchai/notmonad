from notmonad import *
from tests.sample_data import json_data


class TestMem:
    def test_loop_with_mem(self):
        answer = [
            {"address": ["00001", "00002", "00003"], "phone": ["1", "2"]},
            {
                "address": ["00004", "00005", "00006"],
                "phone": ["3", "4", "5", "6"],
            },
        ]

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

    def test_post_get_retain_and_delete(self):
        pipeline = (
            chain(10, App)(__post="x", __retain=True)(lambda n: n + 1)(
                __post="y", __retain=True
            )(__get="x", __retain=True)
        )
        assert pipeline() == 10
        assert pipeline.mem == {"x": 10, "y": 11}

        cleared = pipeline(__delete="y")(__get="x")
        assert cleared() == 10
        assert cleared.mem == {}

    def test_post_and_get_same_step(self):
        assert chain(1, App)(__post="a")(__mount=2)(__post="b", __get="a")() == 1

    def test_strict_missing_key(self):
        import pytest

        with pytest.raises(MemKeyError):
            chain(1, App)(__get="missing", __strict=True)()

    def test_call_requires_callable(self):
        import pytest

        with pytest.raises(TypeError, match="callable"):
            chain(1, App)(__mount=2, __call=True)()

    def test_mount_none(self):
        assert chain(5, App)(__mount=None)() is None
