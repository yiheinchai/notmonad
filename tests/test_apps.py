from tic_tac_toe import (
    get_computer_move,
    is_winner,
    outcome,
    place,
    play,
)
from todo import run


class TestTicTacToe:
    def test_winner_and_outcome(self):
        board = place(place(place([" "] * 9, 0, "X"), 3, "X"), 6, "X")
        assert is_winner(board, "X")
        assert outcome(board) == "win"

    def test_computer_takes_winning_move(self):
        board = ["O", "O", " ", "X", "X", " ", " ", " ", " "]
        assert get_computer_move(board) == 2

    def test_computer_blocks(self):
        board = ["X", "X", " ", "O", " ", " ", " ", " ", " "]
        assert get_computer_move(board) == 2

    def test_scripted_user_win(self):
        user_moves = iter([0, 3, 6])
        computer_moves = iter([1, 2])
        outputs = []

        def write(*args, **kwargs):
            outputs.append(" ".join(str(arg) for arg in args))

        board = play(
            read_user_move=lambda _board: next(user_moves),
            read_computer_move=lambda _board: next(computer_moves),
            write=write,
        )
        assert outcome(board) == "win"
        assert any("You win!" in line for line in outputs)
        assert any("Thanks for playing!" in line for line in outputs)

    def test_scripted_tie(self):
        # X 1, O 2, X 3, O 5, X 4, O 7, X 6, O 9, X 8  — classic tie if 1-indexed
        # 0-index: 0,1, 2,4, 3,6, 5,8, 7
        user_moves = iter([0, 2, 3, 5, 7])
        computer_moves = iter([1, 4, 6, 8])
        outputs = []

        def write(*args, **kwargs):
            outputs.append(" ".join(str(arg) for arg in args))

        board = play(
            read_user_move=lambda _board: next(user_moves),
            read_computer_move=lambda _board: next(computer_moves),
            write=write,
        )
        assert outcome(board) == "tie"
        assert any("It's a tie!" in line for line in outputs)


class TestTodoApp:
    def test_add_list_done_quit(self):
        lines = iter(["add milk", "add eggs", "list", "done 1", "list", "quit"])
        outputs = []

        def writer(*args, **kwargs):
            outputs.append(" ".join(str(arg) for arg in args))

        items = run(reader=lambda _prompt="": next(lines), writer=writer)
        assert items == ["eggs"]
        joined = "\n".join(outputs)
        assert "added 'milk'" in joined
        assert "done 'milk'" in joined
        assert "1. eggs" in joined
        assert "bye" in joined
