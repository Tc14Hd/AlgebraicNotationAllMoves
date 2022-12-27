import chess
import os

# Paths
DIR_NAME      = os.path.dirname(__file__)
MOVE_SAN_PATH = os.path.join(DIR_NAME, "../Data/moves-san.txt")
MOVE_LAN_PATH = os.path.join(DIR_NAME, "../Data/moves-lan.txt")

def validateMoves(filePath: str, isSan: bool, text: str) -> None:

    # Counters
    valid    = 0
    invalid  = 0
    noFen    = 0

    # Read moves and their FENs from file
    with open(filePath, "r") as f:

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

                # Check whether board is valid                 
                if board.is_valid(): 
                    # In case of SAN, check whether move is not overspecified
                    if not (isSan and board.san(move) != moveStr):
                        valid += 1

                # Invalid
                else:
                    invalid += 1
                    print(line)

    # Output results
    print(text)
    print(f"Valid   : {valid}")
    print(f"Invalid : {invalid}")
    print(f"No FEN  : {noFen}")


if __name__ == "__main__":

    validateMoves(MOVE_SAN_PATH, True, "SAN")
    print()
    validateMoves(MOVE_LAN_PATH, False, "LAN")
