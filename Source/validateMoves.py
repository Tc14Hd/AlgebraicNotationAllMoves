import chess
import os

# Paths
dirName  = os.path.dirname(__file__)
fileName = os.path.join(dirName, "../Data/moves.txt")

# Counters
valid    = 0
invalid  = 0
noFen    = 0

# Read moves and their FENs from file
with open(fileName, "r") as f:

    for line in f.readlines():
        line = line.rstrip()

        # No FEN
        pos = line.find(" ")
        if pos == -1:
            noFen += 1

        # FEN
        else:

            # Split line into move and FEN
            moveStr = line[:pos]
            fen = line[pos + 1:]

            # Try to get board and move object
            try:
                board = chess.Board(fen)
                move = board.parse_san(moveStr)

            # Invalid board or move
            except ValueError:
                invalid += 1
                print(line)
                continue

            # Check whether board is valid and whether move is not overspecified
            if board.is_valid() and board.san(move) == moveStr:
                valid += 1
            
            # Invalid
            else:
                invalid += 1
                print(line)

# Output results
print()
print(f"Valid   : {valid}")
print(f"Invalid : {invalid}")
print(f"No FEN  : {noFen}")
