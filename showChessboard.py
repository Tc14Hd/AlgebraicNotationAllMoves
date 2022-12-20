import chess
import chess.svg
from cairosvg import svg2png

fileName = "./Data/moves.txt"
moveToFen = {}

with open(fileName, "r") as f:

    for line in f.readlines():

        line = line.rstrip()
        pos = line.find(" ")

        moveStr = line[:pos]
        fen = line[pos + 1:]
        moveToFen[moveStr] = fen


moveStr = input("Move: ").strip()
fen = moveToFen[moveStr]
board = chess.Board(fen)
move = board.parse_san(moveStr)

arrow = chess.svg.Arrow(move.from_square, move.to_square)
svg = chess.svg.board(board, arrows=[arrow])

width = 1000
height = 1000
svg2png(bytestring=svg, write_to="./chessboard.png", output_width=width, output_height=height)
