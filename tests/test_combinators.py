from notmonad import assoc, assoc_in, atom, cond, deref, do, get_in, inc, let, swap, thread


def test_let_do_thread_and_atom():
    assert let(["x", 1, "y", lambda x: x + 2], lambda x, y: x + y) == 4
    assert do(lambda: 1, lambda: 2) == 2
    assert thread(1, inc, (lambda n, extra: n + extra, 3)) == 5
    box = atom(0)
    swap(box, inc)
    assert deref(box) == 1
    assert get_in(assoc_in({"a": {}}, ["a", "b"], 9), ["a", "b"]) == 9
    assert assoc({"a": 1}, "b", 2)["b"] == 2
    assert cond((False, 1), (True, 2)) == 2
    assert cond((False, 1), else_=3) == 3
