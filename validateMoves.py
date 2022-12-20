from chess import Board
from tqdm import tqdm

fileName = "./Data/moves.txt"
valid = 0
invalid = 0
noFen = 0

with open(fileName, "r") as f:

    for line in tqdm(f.readlines()):
        line = line.rstrip()

        pos = line.find(" ")
 
        if pos == -1:
            noFen += 1

        else:
            move = line[:pos]
            position = line[pos + 1:]
            board = Board(position)
            moves = [board.san(move) for move in board.legal_moves]

            if board.is_valid() and move in moves:
                valid += 1
            else:
                invalid += 1
                print(line)

print(f"Valid   : {valid}")
print(f"Invalid : {invalid}")
print(f"No FEN  : {noFen}")
