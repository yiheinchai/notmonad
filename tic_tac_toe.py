# Import the random module
import random
from notmonad import *

# Define the board as a list of 9 empty strings
board = [" " for i in range(9)]


# Define a function to print the board
def print_board(board):
    print("-------------")
    for i in range(3):
        print("|", board[i * 3], "|", board[i * 3 + 1], "|", board[i * 3 + 2], "|")
        print("-------------")

    return board


# Define a function to check if the board is full
def is_full(board):
    return board.count(" ") == 0


# Define a function to check if a player has won
def is_winner(board, player):
    # Check the rows
    for i in range(3):
        if board[i * 3] == board[i * 3 + 1] == board[i * 3 + 2] == player:
            return True
    # Check the columns
    for i in range(3):
        if board[i] == board[i + 3] == board[i + 6] == player:
            return True
    # Check the diagonals
    if board[0] == board[4] == board[8] == player:
        return True
    if board[2] == board[4] == board[6] == player:
        return True
    # No winner
    return False


# Define a function to get the user's move
def get_user_move(board):
    while True:
        # Get the user's input
        move = input("Enter your move (1-9): ")
        # Validate the input
        try:
            move = int(move) - 1
            if move in range(9) and board[move] == " ":
                return move
            else:
                print("Invalid move. Try again.")
        except ValueError:
            print("Invalid input. Try again.")


# Define a function to get the computer's move
def get_computer_move(board):
    # Get the list of available moves
    moves = [i for i in range(9) if board[i] == " "]
    # Try to find a winning move
    for move in moves:
        # Make a copy of the board
        board_copy = board[:]
        # Make the move on the copy
        board_copy[move] = "O"
        # Check if it is a winning move
        if is_winner(board, "O"):
            return move
    # Try to find a blocking move
    for move in moves:
        # Make a copy of the board
        board_copy = board[:]
        # Make the move on the copy
        board_copy[move] = "X"
        # Check if it is a winning move for the user
        if is_winner(board, "X"):
            return move
    # Choose a random move
    return random.choice(moves)


def print_instructions():
    print("Welcome to Tic-Tac-Toe!")
    print("You are X and the computer is O.")
    print("The board positions are numbered as follows:")
    print("-------------")
    print("| 1 | 2 | 3 |")
    print("-------------")
    print("| 4 | 5 | 6 |")
    print("-------------")
    print("| 7 | 8 | 9 |")
    print("-------------")


def check_result(board):
    # Check if the user has won
    if is_winner(board, "X"):
        print_board(board)
        print("You win!")

    # Check if the board is full
    if is_full(board):
        print_board(board)
        print("It's a tie!")

    # Check if the computer has won
    if is_winner(board, "O"):
        print_board(board)
        print("You lose!")

    # Check if the board is full
    if is_full(board):
        print_board(board)
        print("It's a tie!")

    return board


# Define the main function
def main():
    # Print a welcome message

    # Start the game loop
    while True:
        # Print the board
        print_board(board)
        # Get the user's move
        user_move = get_user_move(board)
        # Make the user's move
        board[user_move] = "X"
        # Check if the user has won
        if is_winner(board, "X"):
            print_board(board)
            print("You win!")
            break
        # Check if the board is full
        if is_full(board):
            print_board(board)
            print("It's a tie!")
            break
        # Get the computer's move
        computer_move = get_computer_move(board)
        # Make the computer's move
        board[computer_move] = "O"
        # Check if the computer has won
        if is_winner(board, "O"):
            print_board(board)
            print("You lose!")
            break
        # Check if the board is full
        if is_full(board):
            print_board(board)
            print("It's a tie!")
            break
    # Print a goodbye message
    print("Thanks for playing!")


# Call the main function
# main()

# fmt: off
play_turn = (monad(None, compose(mem, maybe))
            (print_instructions)
            (__mount=[" " for i in range(9)])
            (while_loop, lambda board: monad(board, compose(mem, maybe))
            #  User moves
             (print_board)
             (__post="board", __retain=True)
             (enumerate)
             (__post="enumerated_board")
             (__get="board", __retain=True)
             (get_user_move)
             (lambda user_move: lambda idx_val: "X" if idx_val[0] == user_move else idx_val[1])
             (p_loop)
             (__get="enumerated_board", __call=True)
             (check_result)

            #  Computer moves
             (__post="board", __retain=True)
             (enumerate)
             (__post="enumerated_board")
             (__get="board", __retain=True)
             (get_computer_move)
             (lambda user_move: lambda idx_val: "O" if idx_val[0] == user_move else idx_val[1])
             (p_loop)
             (__get="enumerated_board", __call=True)
             (check_result)
             ()))
