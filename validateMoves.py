import chess

fileName = "./Data/moves.txt"
valid = 0
invalid = 0
noFen = 0

with open(fileName, "r") as f:

    for line in f.readlines():
        line = line.rstrip()

        pos = line.find(" ")
        if pos == -1:
            noFen += 1

        else:

            moveStr = line[:pos]
            fen = line[pos + 1:]

            try:
                board = chess.Board(fen)
                move = board.parse_san(moveStr)
            except ValueError:
                invalid += 1
                print(line)
                continue

            if board.is_valid() and board.san(move) == moveStr:
                valid += 1
            else:
                invalid += 1
                print(line)

print()
print(f"Valid   : {valid}")
print(f"Invalid : {invalid}")
print(f"No FEN  : {noFen}")
