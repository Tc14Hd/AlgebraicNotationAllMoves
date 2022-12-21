import os, chess, chess.svg
from cairosvg import svg2png

# Paths
dirName   = os.path.dirname(__file__) 
movesPath = os.path.join(dirName, "../Data/moves.txt")
pngPath   = os.path.join(dirName, "../chessboard.png")

# Dimensions of PNG
width = 1000
height = 1000

# FEN dictionary
moveToFen = {}

# Read moves and their FENs from file
with open(movesPath, "r") as fileMoves:

    for line in fileMoves.readlines():
        line = line.rstrip()

        # Split line into move and FEN
        pos = line.find(" ")
        moveStr = line[:pos]
        fen = line[pos + 1:]

        # Update FEN dictionary
        moveToFen[moveStr] = fen

# Get move from input
moveStr = input("Move: ").strip()

# Get FEN from dictionary
fen = moveToFen[moveStr]
board = chess.Board(fen)

# Calculate arrow for move
move = board.parse_san(moveStr)
arrow = chess.svg.Arrow(move.from_square, move.to_square)

# Generate SVG and save to file as PNG
svg = chess.svg.board(board, arrows=[arrow])
svg2png(bytestring=svg, write_to=pngPath, output_width=width, output_height=height)
