"""Tic-tac-toe built entirely with notmonad pipelines.

Run interactively::

    python examples/tic_tac_toe.py

The game loop, branching, memory slots, and IO effects are all pipeline
steps so this file is also a reference for building other apps.
"""

from __future__ import annotations

import random
from typing import Callable

from notmonad import App, chain, effect, p_loop, tap, unless, while_loop

EMPTY_BOARD = [" "] * 9
WIN_LINES = (
    (0, 1, 2),
    (3, 4, 5),
    (6, 7, 8),
    (0, 3, 6),
    (1, 4, 7),
    (2, 5, 8),
    (0, 4, 8),
    (2, 4, 6),
)


def print_board(board, write=print):
    write("-------------")
    for row in range(3):
        write(
            f"| {board[row * 3]} | {board[row * 3 + 1]} | {board[row * 3 + 2]} |"
        )
        write("-------------")
    return board


def print_instructions(write=print):
    write("Welcome to Tic-Tac-Toe!")
    write("You are X and the computer is O.")
    write("The board positions are numbered as follows:")
    write("-------------")
    write("| 1 | 2 | 3 |")
    write("-------------")
    write("| 4 | 5 | 6 |")
    write("-------------")
    write("| 7 | 8 | 9 |")
    write("-------------")


def is_winner(board, player):
    return any(all(board[index] == player for index in line) for line in WIN_LINES)


def is_full(board):
    return all(cell != " " for cell in board)


def game_over(board):
    return is_winner(board, "X") or is_winner(board, "O") or is_full(board)


def outcome(board):
    if is_winner(board, "X"):
        return "win"
    if is_winner(board, "O"):
        return "lose"
    if is_full(board):
        return "tie"
    return "ongoing"


def place(board, move, mark):
    out = list(board)
    out[move] = mark
    return out


def get_computer_move(board):
    moves = [index for index, cell in enumerate(board) if cell == " "]
    for move in moves:
        if is_winner(place(board, move, "O"), "O"):
            return move
    for move in moves:
        if is_winner(place(board, move, "X"), "X"):
            return move
    return random.choice(moves)


def get_user_move(board, reader=input, writer=print):
    while True:
        raw = reader("Enter your move (1-9): ")
        try:
            move = int(raw) - 1
        except (TypeError, ValueError):
            writer("Invalid input. Try again.")
            continue
        if move in range(9) and board[move] == " ":
            return move
        writer("Invalid move. Try again.")


def announce(board, write=print):
    status = outcome(board)
    if status == "win":
        write("You win!")
    elif status == "lose":
        write("You lose!")
    elif status == "tie":
        write("It's a tie!")
    return board


def apply_mark(move, mark):
    def mapper(idx_val):
        index, cell = idx_val
        return mark if index == move else cell

    return mapper


def make_half(read_move: Callable, mark: str, write=print):
    """One player's turn as a notmonad pipeline (uses mem + nested maps)."""

    def half(board):
        return (
            chain(board, App)(tap, print_board, write)(
                __post="board", __retain=True
            )(lambda current: list(enumerate(current)))(__post="enumerated")(
                __get="board", __retain=True
            )(read_move)(lambda move: apply_mark(move, mark))(p_loop)(
                __get="enumerated", __call=True
            )()
        )

    return half


def play(*, read_user_move=None, read_computer_move=None, write=print):
    """Run a full game. Inject move getters to script games in tests."""
    user = read_user_move or (
        lambda board: get_user_move(board, writer=write)
    )
    computer = read_computer_move or get_computer_move
    user_turn = make_half(user, "X", write)
    computer_turn = make_half(computer, "O", write)

    def turn(board):
        return chain(board, App)(user_turn)(unless, game_over, computer_turn)()

    return (
        chain(list(EMPTY_BOARD), App)(effect, print_instructions, write)(
            while_loop, turn, until=game_over
        )(tap, print_board, write)(tap, announce, write)(
            effect, write, "Thanks for playing!"
        )()
    )


def main():
    play()


if __name__ == "__main__":
    main()
