from __future__ import annotations
from typing import cast, List, Tuple, TypeVar, Generic, Optional
from dataclasses import dataclass
from itertools import product, permutations
from copy import deepcopy
from prettytable import PrettyTable
from PIL import Image, ImageDraw, ImageFont
from argparse import ArgumentParser
import re, os


###############
### Classes ###
###############

# Class containing file and rank offset
@dataclass
class Offset:
    file: int
    rank: int

# Class for a square on chessboard
@dataclass
class Square:

    # File index [0-7]
    file: int
    # Rank index [0-7]
    rank: int
    # ID of direction from which square is reachable (optional)
    directionId: int = -1

    # Test whether square is on 8x8 chessboard
    def onBoard(self) -> bool:
        return 0 <= self.file <= 7 and 0 <= self.rank <= 7

    # Test whether two squares are adjacent within a specified distance
    def isAdjacent(self, other: Square, dist=1) -> bool:
        return abs(self.file - other.file) <= dist and abs(self.rank - other.rank) <= dist

    # Get square name as string
    def __str__(self) -> str:
        return fileToStr(self.file) + rankToStr(self.rank)

    # Return new square with added offset
    def __add__(self, offset: Offset):
        return Square(self.file + offset.file, self.rank + offset.rank, self.directionId)

    # Return new square with subtracted offset
    def __sub__(self, offset: Offset):
        return Square(self.file - offset.file, self.rank - offset.rank, self.directionId)

    # Two squares are equal when their files and ranks match
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Square):
            return False
        return self.file == other.file and self.rank == other.rank

# Generic variable
T = TypeVar("T")

# Class for storing a value for every square of an 8x8 chessboard
class Board(Generic[T]):

    # 2D array for storing values
    board: list[list[T]]

    # Create board with initial value for every square
    def __init__(self, initial: T) -> None:
        self.board = [[deepcopy(initial) for _ in range(8)] for _ in range(8)]

    # Get value of square
    def __getitem__(self, square: Square) -> T:
        return self.board[square.file][square.rank]

    # Set value of square
    def __setitem__(self, square: Square, value: T) -> None:
        self.board[square.file][square.rank] = value

# Statistics for one square of one piece
class Stats:

    # Move groups by disambiguation type
    plainMove: bool
    fileMove: list[bool]
    rankMove: list[bool]
    squareMove: Board[bool]

    # Reachable squares
    reachable: Board[bool]

    # Move groups by what moves they are missing
    missingMoves: dict[str, list[tuple[str, str]]]

    # Amount of moves by final symbol
    finalSymbol: list[int]

    def __init__(self) -> None:

        self.plainMove    = False
        self.fileMove     = [False] * 8
        self.rankMove     = [False] * 8
        self.squareMove   = Board(False)
        self.reachable    = Board(False)
        self.missingMoves = {"checkmate": [], "check": [], "both": []}
        self.finalSymbol  = [0] * 3

# Type alias
resultType = Tuple[List[Tuple[str, str]], Board[Stats]]


#################
### Constants ###
#################

# List of all square
SQUARES = [Square(file, rank) for file in range(8) for rank in range(8)]
# Possible promotion pieces
PROMOTION = ["R", "B", "Q", "N"]
# Possible final symbols (nothing, check, checkmate)
FINAL_SYMBOL = ["", "+", "#"]

# Jump offsets for pieces
PAWN_JUMPS        = [Offset(1, 1), Offset(-1, 1)]
KING_JUMPS        = [Offset(file, rank) for (file, rank) in product([1, 0, -1], repeat=2) if (file, rank) != (0, 0)]
KNIGHT_JUMPS      = [Offset(value[0] * sign[0], value[1] * sign[1])
    for value in permutations([1, 2]) for sign in product([1, -1], repeat=2)]

# Direction offsets for pieces
ROOK_DIRECTIONS   = [Offset(1, 0), Offset(-1, 0), Offset(0, 1), Offset(0, -1)]
BISHOP_DIRECTIONS = [Offset(file, rank) for (file, rank) in product([1, -1], repeat=2)]
QUEEN_DIRECTIONS  = ROOK_DIRECTIONS + BISHOP_DIRECTIONS

# FEN dictionary for manually generated moves
MANUAL_MOVES: dict[str, str] = {}

# File and folder paths
DIR_NAME          = os.path.dirname(__file__)
MANUAL_MOVES_PATH = os.path.join(DIR_NAME, "../Data/manual-moves.txt")
MOVES_SAN_PATH    = os.path.join(DIR_NAME, "../Data/moves-san.txt")
MOVES_LAN_PATH    = os.path.join(DIR_NAME, "../Data/moves-lan.txt")
STATS_SAN_PATH    = os.path.join(DIR_NAME, "../Data/stats-san.txt")
STATS_LAN_PATH    = os.path.join(DIR_NAME, "../Data/stats-lan.txt")
IMAGES_FOLDER     = os.path.join(DIR_NAME, "../Images")
FONT_PATH         = os.path.join(DIR_NAME, "../Data/roboto-regular.ttf")

# Dimensions of image
SIDE_LENGTH   = 200
BORDER_SIZE   = 150
CIRCLE_RADIUS = 50

# Colors for image
COLOR_END_SQUARE = "red"
COLOR_LIGHT      = "white"
COLOR_DARK       = "black"
COLOR_MARKED     = "#0b37ba"
COLOR_REACHABLE  = "#dde330"

# Font for image
FONT_SIZE = 70
FONT = ImageFont.truetype(FONT_PATH, FONT_SIZE)


#############
### Utils ###
#############

# Sign function
def sign(x: int) -> int:
    if x > 0:   return 1
    elif x < 0: return -1
    else:       return 0

# Convert file index [0-7] to file name [a-h]
def fileToStr(file: int) -> str:
    return chr(ord("a") + file)

# Convert rank index [0-7] to rank name [1-8]
def rankToStr(rank: int) -> str:
    return str(1 + rank)

# Convert file name [a-h] to file index [0-7]
def strToFile(fileStr: str) -> int:
    return ord(fileStr) - ord("a")

# Convert rank name [1-8] to rank index [0-7]
def strToRank(rankStr: str) -> int:
    return int(rankStr) - 1

# Convert square name [a-h][1-8] to square object
def strToSquare(squareStr: str) -> Square:
    return Square(strToFile(squareStr[0]), strToRank(squareStr[1]))

# Flip files from [a-h] to [h-a] and ranks from [1-8] to [8-1] if corresponding flags are set
def flipFileRank(string: str, flipFiles = False, flipRanks = False) -> str:

    stringNew = ""
    for c in string:
        # Flip file
        if c.islower() and flipFiles:
            stringNew += fileToStr(7 - strToFile(c))
        # Flip rank
        elif c.isdigit() and flipRanks:
            stringNew += rankToStr(7 - strToRank(c))
        # Don't flip
        else:
            stringNew += c

    return stringNew

# Get an empty 2D array as move group
# First Dimension  | 0 No Capture | 1 Capture
# Second Dimension | 0 Nothing    | 1 Check   | 2 Checkmate
def getEmptyMoveGroup() -> list[list[Optional[Board[str]]]]:
    return [[None] * 3 for _ in range(2)]

# Parse move string into its parts
def parseMove(move: str) -> tuple[str, str, str, str, str]:

    piece = ""    # Piece symbol
    capture = ""  # Capture symbol

    # If move is not a pawn move
    if move[0].isupper():
        piece = move[0]
        move = move[1:]

    # Get middle part of move
    coords = ""
    while len(move) > 0 and move[0].isalnum():
        # Capture move
        if move[0] == "x":
            capture = "x"
        else:
            coords += move[0]
        move = move[1:]

    disambiguation = coords[:-2] # Disambiguation for move
    endSquare = coords[-2:]      # Name of end square
    rest = move                  # Promotion and final symbol

    return (piece, disambiguation, capture, endSquare, rest)

# Get FEN of a chessboard
# Flip ranks, flip files, or swap color of pieces if corresponding flags are set
def chessboardToFen(chessboard: Board[str], flipFiles=False, flipRanks=False, swapPlayers=False) -> str:

    ranks: list[str] = []
    # Loop through ranks in specified order
    for rank in (range(7, -1, -1) if not flipRanks else range(8)):
        emptySquares = 0
        rankStr = ""

        # Loop through files in specified order
        for file in (range(8) if not flipFiles else range(7, -1, -1)):
            square = Square(file, rank)

            # Empty square
            if chessboard[square] == "":
                emptySquares += 1
            # Piece
            else:

                # Append number of empty squares
                if emptySquares > 0:
                    rankStr += str(emptySquares)
                    emptySquares = 0

                # Append piece
                # Swap color of piece if specified
                if swapPlayers:
                    rankStr += chessboard[square].swapcase()
                else:
                    rankStr += chessboard[square]

        # Append number of empty squares
        if emptySquares > 0:
            rankStr += str(emptySquares)

        ranks.append(rankStr)

    # Build FEN string
    player = "b" if swapPlayers else "w"
    chessboardStr = "/".join(ranks)
    fen = f"{chessboardStr} {player} - - 0 1"

    return fen

# Get chessboard from FEN
def fenToChessboard(fen: str) -> Board[str]:

    chessboard = Board("")
    chessboardStr = fen.split(" ")[0]
    ranks = chessboardStr.split("/")

    # Loop through ranks from 7 to 0
    for rank in range(7, -1, -1):
        file = 0
        for c in ranks[7 - rank]:
            # Empty squares
            if c.isdigit():
                file += int(c)
            # Piece
            else:
                chessboard[Square(file, rank)] = c
                file += 1

    return chessboard

# Check for checkmate
def isCheckmate(squareKing: Square, attackedSquares: Board[Optional[Square]]) -> bool:

    # Check all adjacent squares
    for jump in KING_JUMPS:

        adjacentSquare = squareKing + jump
        if not adjacentSquare.onBoard():
            continue

        # Found unattacked square
        if not attackedSquares[adjacentSquare]:
            return False

    return True

######################
### Piece movement ###
######################

# Get list of start squares from end square for jump pieces
def getStartSquaresJump(endSquare: Square, jumps: list[Offset]) -> list[Square]:

    startSquares: list[Square] = []

    # For every jump
    for (directionId, jump) in enumerate(jumps):
        startSquare = endSquare - jump
        startSquare.directionId = directionId

        # Add square to list if it is on chessboard
        if startSquare.onBoard():
            startSquares.append(startSquare)

    return startSquares

# Get list of start squares from end square for direction pieces
def getStartSquaresDirection(endSquare: Square, directions: list[Offset]) -> list[Square]:

    startSquares: list[Square] = []

    # For every direction
    for (directionId, direction) in enumerate(directions):
        square = endSquare - direction
        square.directionId = directionId

        # Go in opposite direction until edge of chessboard
        while square.onBoard():
            startSquares.append(square)
            square -= direction

    return startSquares

# Mark all squares that can be reached from starting square by specified jumps as attacked
def markAttackedSquaresJump(startSquare: Square, attackedSquares: Board[Optional[Square]], jumps: list[Offset]
    ) -> None:

    # For every jump
    for jump in jumps:
        endSquare = startSquare + jump

        # Mark end square if it is on chessboard
        if endSquare.onBoard():

            if endSquare.isAdjacent(startSquare):
                attackedSquares[endSquare] = startSquare
            else:
                attackedSquares[endSquare] = Square(-1, -1)

# Mark all squares that can be reached from starting square in specified directions as attacked
def markAttackedSquaresDirection(square: Square, chessboard: Board[str], attackedSquares: Board[Optional[Square]],
    directions: list[Offset]) -> None:

    # For every direction
    for direction in directions:
        squarePrevious = square
        squareCurrent = square + direction

        # Go in this direction until edge or other piece
        while squareCurrent.onBoard():
            attackedSquares[squareCurrent] = squarePrevious

            # Direction is block by other piece
            if chessboard[squareCurrent] != "":
                break

            squarePrevious = squareCurrent
            squareCurrent = squareCurrent + direction

# Get board of attacked squares from chessboard
# The value of a square is an adjacent square that has to be kept free in order for the attack to happen
def getAttackedSquares(chessboard: Board[str]) -> Board[Optional[Square]]:

    attackedSquares: Board[Optional[Square]] = Board(None)

    for square in SQUARES:
        piece = chessboard[square]

        if piece == "P":   # Pawn
            markAttackedSquaresJump(square, attackedSquares, PAWN_JUMPS)
        elif piece == "K": # King
            markAttackedSquaresJump(square, attackedSquares, KING_JUMPS)
        elif piece == "N": # Knight
            markAttackedSquaresJump(square, attackedSquares, KNIGHT_JUMPS)
        elif piece == "B": # Bishop
            markAttackedSquaresDirection(square, chessboard, attackedSquares, BISHOP_DIRECTIONS)
        elif piece == "R": # Rook
            markAttackedSquaresDirection(square, chessboard, attackedSquares, ROOK_DIRECTIONS)
        elif piece == "Q": # Queen
            markAttackedSquaresDirection(square, chessboard, attackedSquares, QUEEN_DIRECTIONS)

    return attackedSquares


#############################
### Generate chessboards ####
#############################

# Place white king on chessboard
# Return whether placement was possible
def placeWhiteKing(chessboard: Board[str], keepFree: Board[bool], attackedSquaresAfter: Board[Optional[Square]],
    squareBlackKing: Square) -> bool:

    # Test all square
    for square in SQUARES:

        # Square must be kept free for move
        if keepFree[square]:
            continue

        # White king can't be on a square that is attacked after move
        # Otherwise white king might block attack on black king
        if attackedSquaresAfter[square]:
            continue

        # White king can't be adjacent to black king or its escape squares
        # Otherwise position might be illegal or stalemate
        if square.isAdjacent(squareBlackKing, 2):
            continue

        # Place white king
        chessboard[square] = "K"
        return True

    # White king couldn't be placed
    return False

# Place white pieces around black king such that all squares adjacent to it are attacked
# Return whether placement was possible
def boxInBlackKing(blackKingSquare: Square, endSquare: Square, chessboardBefore: Board[str], chessboardAfter: Board[str],
    attackedSquaresAfter: Board[Optional[Square]]) -> bool:

    keepFreeForAttack = cast(Square, attackedSquaresAfter[blackKingSquare])

    # Plan to place four rooks in corners of 3x3 box around black king
    rookSquares: list[Square] = []
    for offset in BISHOP_DIRECTIONS:
        squareRook = blackKingSquare + offset

        if squareRook.onBoard():
            rookSquares.append(squareRook)

    # Black king in corner
    if (blackKingSquare.file in [0, 7]) and (blackKingSquare.rank in [0, 7]):
        # Ignore this case
        return False

    # Black king on edge
    elif (blackKingSquare.file in [0, 7]) or (blackKingSquare.rank in [0, 7]):

        # Rook blocks attack on black king
        if keepFreeForAttack in rookSquares:

            # If attacker is next to black king, it has to be protected
            # Otherwise it could be taken by black king and it wouldn't be checkmate
            if chessboardAfter[keepFreeForAttack].isupper():
                if not attackedSquaresAfter[keepFreeForAttack]:
                    return False

            # Remove blocking rook
            rookSquares.remove(keepFreeForAttack)

            # Place bishop next to black king and rook
            # Place knight on edge such that it defends rook
            knightSquare = Square(blackKingSquare.file, keepFreeForAttack.rank)
            bishopSquare = Square(keepFreeForAttack.file, blackKingSquare.rank)

            if (bishopSquare.file in [0, 7]) or (bishopSquare.rank in [0, 7]):
                (knightSquare, bishopSquare) = (bishopSquare, knightSquare)

            chessboardBefore[knightSquare] = "N"
            chessboardBefore[bishopSquare] = "B"

            # Result:
            # . B R        R B .
            # N k .   or   . k N
            # = = =        = = =

        # Rook doesn't block attack on black king
        else:

            # Moving a rook next to black king as an attacker messes up disambiguation
            if chessboardAfter[endSquare] == "R" and endSquare.isAdjacent(blackKingSquare):
                return False

            # Result:
            # R . R
            # . k .
            # = = =

    # Black king in middle
    else:

        # Moving a rook next to black king as an attacker messes up disambiguation
        if chessboardAfter[endSquare] == "R" and endSquare.isAdjacent(blackKingSquare):
            return False

        # Remove rook when it blocks attack on black king
        if keepFreeForAttack in rookSquares:
            rookSquares.remove(keepFreeForAttack)
        # Otherwise remove arbitrary rook
        else:
            rookSquares.pop()

        # Result:
        # R . R
        # . k .
        # R . .

    # Place rooks
    for rookSquare in rookSquares:
        chessboardBefore[rookSquare] = "R"

    # Place black king
    chessboardBefore[blackKingSquare] = "k"
    return True

# Place black and white king on chessboard such that black king is not in check
# Return chessboard of such position if one is found else return None
def placeKingsNoCheck(endSquare: Square, chessboardBefore: Board[str], chessboardAfter: Board[str], keepFree: Board[bool],
    hasWhiteKing: bool) -> Optional[Board[str]]:

    chessboardBefore = deepcopy(chessboardBefore)
    attackedSquaresBefore = getAttackedSquares(chessboardBefore)
    attackedSquaresAfter = getAttackedSquares(chessboardAfter)
    squareBlackKing = None

    # Test all squares
    for square in SQUARES:

        # Square must be kept free for move
        if keepFree[square]:
            continue

        # Black king can't be attacked before and after move
        if attackedSquaresBefore[square] or attackedSquaresAfter[square]:
            continue

        # Black king can't be adjacent to white king
        if hasWhiteKing and square.isAdjacent(endSquare):
            continue

        # Place black king
        chessboardBefore[square] = "k"
        squareBlackKing = square
        break

    # Black king couldn't be placed
    if not squareBlackKing:
        return None

    # Place white king if not placed yet
    if not hasWhiteKing:
        if not placeWhiteKing(chessboardBefore, keepFree, attackedSquaresAfter, squareBlackKing):
            return None

    # Return chessboard
    return chessboardBefore

# Place black and white king on chessboard such that black king is in check
# Return chessboard of such position if one is found else return None
def placeKingsCheck(endSquare: Square, chessboardBefore: Board[str], chessboardAfter: Board[str], keepFree: Board[bool],
    hasWhiteKing: bool) -> Optional[Board[str]]:

    chessboardBefore = deepcopy(chessboardBefore)
    attackedSquaresBefore = getAttackedSquares(chessboardBefore)
    attackedSquaresAfter = getAttackedSquares(chessboardAfter)
    squareBlackKing = None

    # Test all squares
    for square in SQUARES:

        # Square must be kept free for move
        if keepFree[square]:
            continue

        # Black king can't be attacked before move
        if attackedSquaresBefore[square]:
            continue

        # Black king must be attacked after move
        if not attackedSquaresAfter[square]:
            continue

        # Black king can't be adjacent to white king
        if hasWhiteKing and square.isAdjacent(endSquare):
            continue

        # Place king if there is no checkmate
        if not isCheckmate(square, attackedSquaresAfter):
            chessboardBefore[square] = "k"
            squareBlackKing = square
            break

    # Black king couldn't be placed
    if not squareBlackKing:
        return None

    # Place white king if not placed yet
    if not hasWhiteKing:
        if not placeWhiteKing(chessboardBefore, keepFree, attackedSquaresAfter, squareBlackKing):
            return None

    # Return chessboard
    return chessboardBefore

# Place black and white king on chessboard such that black king is checkmated
# Return chessboard of such position if one is found else return None
def placeKingsCheckmate(endSquare: Square, chessboardBefore: Board[str], chessboardAfter: Board[str], keepFree: Board[bool],
    hasWhiteKing: bool) -> Optional[Board[str]]:

    chessboardBefore = deepcopy(chessboardBefore)
    attackedSquaresBefore = getAttackedSquares(chessboardBefore)
    attackedSquaresAfter = getAttackedSquares(chessboardAfter)
    squareBlackKing = None

    # Test all squares
    for square in SQUARES:

        # Square must be kept free for move
        if keepFree[square]:
            continue

        # Black king can't be attacked before move
        if attackedSquaresBefore[square]:
            continue

        # Black king must be attacked after move
        if not attackedSquaresAfter[square]:
            continue

        # Black king can't be adjacent to white king
        if hasWhiteKing and square.isAdjacent(endSquare):
            continue

        # Check for checkmate
        if isCheckmate(square, attackedSquaresAfter):

            # Place black king
            chessboardBefore[square] = "k"
            squareBlackKing = square
            break

        # Check whether pieces can be placed on all adjacent squares
        # Except for square that has to be kept free for attack
        adjacentAllPlacable = True
        keepFreeForAttack = cast(Square, attackedSquaresAfter[square])

        for jump in KING_JUMPS:

            adjacentSquare = square + jump
            if not adjacentSquare.onBoard():
                continue

            # Exclude square that has to be kept free for attack
            if adjacentSquare == keepFreeForAttack:
                continue

            # Square is not placable
            if keepFree[adjacentSquare]:
                adjacentAllPlacable = False
                break

        # All adjacent squares are placable
        if adjacentAllPlacable:
            # Place white piece around black king
            if boxInBlackKing(square, endSquare, chessboardBefore, chessboardAfter, attackedSquaresAfter):
                squareBlackKing = square
                break

    # Black king couldn't be placed
    if not squareBlackKing:
        return None

    # Place white king if not placed yet
    if not hasWhiteKing:
        if not placeWhiteKing(chessboardBefore, keepFree, attackedSquaresAfter, squareBlackKing):
            return None

    # Return chessboard
    return chessboardBefore

# Update move group with chessboards of capture or non-capture moves from partial chessboard
def updateMoveGroupCapture(moveGroupCapture: list[Optional[Board[str]]], piece: str, startSquare: Square, endSquare: Square,
    chessboardBefore: Board[str], chessboardAfter: Board[str], keepFree: Board[bool]) -> None:

    # Generate chessboards for no check, check, and checkmate
    placeFunctions = [placeKingsNoCheck, placeKingsCheck, placeKingsCheckmate]
    hasWhiteKing = piece == "K"
    for i in range(3):
        if not moveGroupCapture[i]:
            moveGroupCapture[i] = placeFunctions[i](endSquare, chessboardBefore, chessboardAfter, keepFree, hasWhiteKing)

    # Place piece for discovered attack
    for (pieceDiscovered, offsets) in [("R", ROOK_DIRECTIONS), ("B", BISHOP_DIRECTIONS)]:

        # No discovered attack possible if moving piece is queen or same as discovered attacker
        if piece in ["Q", pieceDiscovered]:
            continue

        for offset in offsets:
            squareAttacker = startSquare + offset

            if not squareAttacker.onBoard():
                continue

            # Check and checkmate already found
            if moveGroupCapture[1] and moveGroupCapture[2]:
                break

            # Square must be kept free for move
            if keepFree[squareAttacker]:
                continue

            # Place discovered attacker
            chessboardBefore[squareAttacker] = pieceDiscovered
            chessboardAfter[squareAttacker] = pieceDiscovered
            keepFree[squareAttacker] = True

            # Generate chessboard for check
            if not moveGroupCapture[1]:
                moveGroupCapture[1] = placeKingsCheck(endSquare, chessboardBefore, chessboardAfter, keepFree, hasWhiteKing)

            # Generate chessboard for checkmate
            if not moveGroupCapture[2]:
                moveGroupCapture[2] = placeKingsCheckmate(endSquare, chessboardBefore, chessboardAfter, keepFree, hasWhiteKing)

            # Remove discovered attacker
            chessboardBefore[squareAttacker] = ""
            chessboardAfter[squareAttacker] = ""
            keepFree[squareAttacker] = False

# Update move group with chessboards generated from piece locations
def updateMoveGroup(moveGroup: list[list[Optional[Board[str]]]], piece: str, startSquare: Square, endSquare: Square,
    otherSquares: list[Square], promotePiece="") -> None:

    # Return if move group is already full
    alreadyFull = True
    for i in range(2):
        for j in range(3):
            if not moveGroup[i][j]:
                alreadyFull = False

    if alreadyFull:
        return

    chessboardBefore = Board("")
    keepFree = Board(False)

    # Place pieces on chessboard and calculate squares that must be kept free for move
    for square in [startSquare] + otherSquares:

        # Place piece
        chessboardBefore[square] = piece

        # Knight
        if piece == "N":
            # Mark start square of knight
            keepFree[square] = True

        # Piece except knight
        else:
            # Mark start square and line of attack
            direction = Offset(sign(endSquare.file - square.file), sign(endSquare.rank - square.rank))
            while square != endSquare:
                keepFree[square] = True
                square += direction

        # Mark end square
        keepFree[endSquare] = True

    # Calculate chessboard after move
    chessboardAfter = deepcopy(chessboardBefore)
    chessboardAfter[startSquare] = ""
    chessboardAfter[endSquare] = piece if promotePiece == "" else promotePiece

    # Update move group with chessboards of non-capture moves
    updateMoveGroupCapture(moveGroup[0], piece, startSquare, endSquare, chessboardBefore, chessboardAfter, keepFree)

    # Update move group with chessboards of capture moves
    chessboardBefore[endSquare] = "n"
    updateMoveGroupCapture(moveGroup[1], piece, startSquare, endSquare, chessboardBefore, chessboardAfter, keepFree)

# Insert move group into move list
# Return whether moves were inserted
def insertMoves(moves: list[tuple[str, str]], moveStart: str, moveEnd: str, moveGroup: list[list[Optional[Board[str]]]],
    stats: Stats, flipForPawn=False) -> bool:

    movesInserted = False
    moveFens: list[list[Optional[tuple[str, str]]]] = [[None] * 3 for _ in range(2)]

    # For no capture and capture moves
    for i in range(2):
        capture = "" if i == 0 else "x"

        # For every final symbol
        for (j, finalSymbol) in enumerate(FINAL_SYMBOL):

            move = moveStart + capture + moveEnd + finalSymbol
            fen = ""

            # Move was found
            if moveGroup[i][j]:
                chessboard = cast(Board[str], moveGroup[i][j])
                fen = chessboardToFen(chessboard, flipRanks=flipForPawn, swapPlayers=flipForPawn)

            # If move was not found, use manual move if available
            elif move in MANUAL_MOVES:
                fen = MANUAL_MOVES[move]

            # If move is possible, insert it into move list
            if fen:
                moves.append((move, fen))
                stats.finalSymbol[j] += 1
                movesInserted = True
                moveFens[i][j] = (move, fen)

        # Statistics
        if moveFens[i][0]:

            moveFen = cast(Tuple[str, str],  moveFens[i][0])

            # Checkmate is missing
            if moveFens[i][1] and not moveFens[i][2]:
                stats.missingMoves["checkmate"].append(moveFen)

            # Check is missing
            if not moveFens[i][1] and moveFens[i][2]:
                stats.missingMoves["check"].append(moveFen)

            # Both are missing
            if not moveFens[i][1] and not moveFens[i][2]:
                stats.missingMoves["both"].append(moveFen)

    return movesInserted


######################################
### Generate pawn and castle moves ###
######################################

# Get all single square pawn moves for one square
def getMovesPawnSingle(endSquare: Square, player: str, stats: Stats, san: bool) -> list[tuple[str, str]]:

    moves: list[tuple[str, str]] = []
    endSquareStr = str(endSquare)

    # Flip ranks if player is black
    flip = player == "b"
    if flip:
        endSquare = Square(endSquare.file, 7 - endSquare.rank)

    # Single square move not possible
    if endSquare.rank < 2:
        return moves

    # For every promotion option (piece or no promotion)
    promotionOptions = PROMOTION if endSquare.rank == 7 else [""]
    for promotePiece in promotionOptions:

        # Generate non-capture moves
        startSquare = endSquare + Offset(0, -1)
        moveGroup = getEmptyMoveGroup()
        updateMoveGroup(moveGroup, "P", startSquare, endSquare, [], promotePiece)

        # Start of move string
        if san:
            moveStart = ""
        else:
            moveStart = flipFileRank(str(startSquare), flipRanks=flip)

        # End of move string
        promote = "" if promotePiece == "" else "=" + promotePiece
        moveEnd = endSquareStr + promote

        # Move group also contains capture moves, so delete them before insertion into move list
        moveGroup[1] = [None] * 3
        insertMoves(moves, moveStart, moveEnd, moveGroup, stats, flip)

    return moves

# Get all capture pawn moves for one square
def getMovesPawnCapture(endSquare: Square, player: str, stats: Stats, san: bool) -> list[tuple[str, str]]:

    moves: list[tuple[str, str]] = []
    endSquareStr = str(endSquare)

    # Flip ranks if player is black
    flip = player == "b"
    if flip:
        endSquare = Square(endSquare.file, 7 - endSquare.rank)

    # Capture move not possible
    if endSquare.rank < 2:
        return moves

    # For every promotion option (piece or no promotion)
    promotionOptions = PROMOTION if endSquare.rank == 7 else [""]
    for promotePiece in promotionOptions:

        # For both adjacent files
        for offset in [Offset(-1, -1), Offset(1, -1)]:
            startSquare = endSquare + offset
            if startSquare.onBoard():

                # Generate capture moves
                moveGroup = getEmptyMoveGroup()
                updateMoveGroup(moveGroup, "P", startSquare, endSquare, [], promotePiece)

                # Start of move string
                if san:
                    moveStart = fileToStr(startSquare.file)
                else:
                    moveStart = flipFileRank(str(startSquare), flipRanks=flip)

                # End of move string
                promote = "" if promotePiece == "" else "=" + promotePiece
                moveEnd = endSquareStr + promote

                # Move group also contains non-capture moves, so delete them before insertion into move list
                moveGroup[0] = [None] * 3
                insertMoves(moves, moveStart, moveEnd, moveGroup, stats, flip)

    return moves

# Get all double square pawn moves for one square
def getMovesPawnDouble(endSquare: Square, player: str, stats: Stats) -> list[tuple[str, str]]:

    moves: list[tuple[str, str]] = []
    endSquareStr = str(endSquare)

    # Flip ranks if player is black
    flip = player == "b"
    if flip:
        endSquare = Square(endSquare.file, 7 - endSquare.rank)

    # Double square move not possible
    if endSquare.rank != 3:
        return moves

    # Generate non-capture moves
    startSquare = endSquare + Offset(0, -2)
    moveGroup = getEmptyMoveGroup()
    updateMoveGroup(moveGroup, "P", startSquare, endSquare, [])

    # End and start of move string
    moveStart = flipFileRank(str(startSquare), flipRanks=flip)
    moveEnd = endSquareStr

    # Move group also contains capture moves, so delete them before insertion into move list
    moveGroup[1] = [None] * 3
    insertMoves(moves, moveStart, moveEnd, moveGroup, stats, flip)

    return moves

# Get all castle moves
def getMovesCastle() -> resultType:

    moves: list[tuple[str, str]] = []
    statsBoard = Board(Stats())
    stats = statsBoard[Square(0, 0)]

    # San and Lan castle
    for castle in ["O-O", "O-O-O"]:

        # For every final symbol
        for (i, finalSymbol) in enumerate(FINAL_SYMBOL):
            move = castle + finalSymbol

            # Insert move if it is contained in manual moves
            if move in MANUAL_MOVES:
                moves.append((move, MANUAL_MOVES[move]))
                stats.finalSymbol[i] += 1

    return (moves, statsBoard)


##########################
### Generate SAN moves ###
##########################

# Get all SAN moves of one end square for a piece with disambiguation moves
def getMovesDisambiguation(piece: str, endSquare: Square, startSquares: list[Square], stats: Stats
    ) -> list[tuple[str, str]]:

    movesSquare: list[tuple[str, str]] = []
    endSquareStr = str(endSquare)

    # Move groups for plain, file, rank, and square moves
    moveGroupPlain = getEmptyMoveGroup()
    moveGroupFile = [getEmptyMoveGroup() for _ in range(8)]
    moveGroupRank = [getEmptyMoveGroup() for _ in range(8)]
    moveGroupSquare = Board(getEmptyMoveGroup())

    # One piece
    for startSquare in startSquares:
        # Plain move
        updateMoveGroup(moveGroupPlain, piece, startSquare, endSquare, [])

    # Two pieces
    for (startSquare, otherSquare) in permutations(startSquares, 2):

        # Pieces block each other's path
        if startSquare.directionId == otherSquare.directionId:
            continue

        # Rank move
        if startSquare.file == otherSquare.file:
            updateMoveGroup(moveGroupRank[startSquare.rank], piece, startSquare, endSquare, [otherSquare])
        # File move
        else:
            updateMoveGroup(moveGroupFile[startSquare.file], piece, startSquare, endSquare, [otherSquare])

    # Three pieces
    for (startSquare, otherSquare1, otherSquare2) in permutations(startSquares, 3):

        # Check whether both file and rank are needed for disambiguation
        if not (startSquare.file == otherSquare1.file and startSquare.rank == otherSquare2.rank):
            continue

        # Pieces block each other's path
        if len({startSquare.directionId, otherSquare1.directionId, otherSquare2.directionId}) < 3:
            continue

        # Square move
        updateMoveGroup(moveGroupSquare[startSquare], piece, startSquare, endSquare, [otherSquare1, otherSquare2])

    # Insert plain move
    if insertMoves(movesSquare, piece, endSquareStr, moveGroupPlain, stats):
        stats.plainMove = True

    # Insert file moves
    for fileStart in range(8):
        moveStart = piece + fileToStr(fileStart)
        moveGroup = moveGroupFile[fileStart]

        if insertMoves(movesSquare, moveStart, endSquareStr, moveGroup, stats):
            stats.fileMove[fileStart] = True

    # Insert rank moves
    for rankStart in range(8):
        moveStart = piece + rankToStr(rankStart)
        moveGroup = moveGroupRank[rankStart]

        if insertMoves(movesSquare, moveStart, endSquareStr, moveGroup, stats):
            stats.rankMove[rankStart] = True

    # Insert square moves
    for startSquare in SQUARES:
        moveStart = piece + str(startSquare)
        moveGroup = moveGroupSquare[startSquare]

        if insertMoves(movesSquare, moveStart, endSquareStr, moveGroup, stats):
            stats.squareMove[startSquare] = True

    # Mark reachable squares
    for startSquare in startSquares:
        stats.reachable[startSquare] = True

    return movesSquare

# Get all SAN moves of a piece
def getMovesPieceSan(piece: str, movement: list[Offset], isJump: bool) -> resultType:

    moves: list[tuple[str, str]] = []
    statsBoard = Board(Stats())

    # For every end square
    for endSquare in SQUARES:

        # Get start squares
        if isJump:
            startSquares = getStartSquaresJump(endSquare, movement)
        elif piece:
            startSquares = getStartSquaresDirection(endSquare, movement)

        # Generate moves and append to move list
        moves += getMovesDisambiguation(piece, endSquare, startSquares, statsBoard[endSquare])

    return (moves, statsBoard)

# Get all pawn SAN moves
def getMovesPawnSan() -> resultType:

    moves: list[tuple[str, str]] = []
    statsBoard = Board(Stats())

    # For every end square
    for endSquare in SQUARES:
        stats = statsBoard[endSquare]

        # White pawn can't reach first two ranks
        player = "w" if endSquare.rank >= 2 else "b"

        # Generate moves
        moves += getMovesPawnSingle(endSquare, player, stats, True)
        moves += getMovesPawnCapture(endSquare, player, stats, True)

    return (moves, statsBoard)

# Get all king SAN moves
def getMovesKingSan() -> resultType:

    moves: list[tuple[str, str]] = []
    statsBoard = Board(Stats())

    # For every end square
    for endSquare in SQUARES:
        moveGroup = getEmptyMoveGroup()

        # For every adjacent square as start square
        for startSquare in getStartSquaresJump(endSquare, KING_JUMPS):

            # Update move group
            updateMoveGroup(moveGroup, "K", startSquare, endSquare, [])

        # Insert moves into move list
        insertMoves(moves, "K", str(endSquare), moveGroup, statsBoard[startSquare])

    return (moves, statsBoard)

# Get all rook SAN moves
def getMovesRookSan() -> resultType:
    return getMovesPieceSan("R", ROOK_DIRECTIONS, False)

# Get all bishop SAN moves
def getMovesBishopSan() -> resultType:
    return getMovesPieceSan("B", BISHOP_DIRECTIONS, False)

# Get all queen SAN moves
def getMovesQueenSan() -> resultType:
    return getMovesPieceSan("Q", QUEEN_DIRECTIONS, False)

# Get all knight SAN moves
def getMovesKnightSan() -> resultType:
    return getMovesPieceSan("N", KNIGHT_JUMPS, True)


##########################
### Generate LAN moves ###
##########################

# Get all LAN moves of a piece
def getMovesPieceLan(piece: str, movement: list[Offset], isJump: bool) -> resultType:

    moves: list[tuple[str, str]] = []
    statsBoard = Board(Stats())

    # For every end square
    for endSquare in SQUARES:

        # Get start squares
        if isJump:
            startSquares = getStartSquaresJump(endSquare, movement)
        elif piece:
            startSquares = getStartSquaresDirection(endSquare, movement)

        # For every start square
        for startSquare in startSquares:

            # Generate moves and append to move list
            moveGroup = getEmptyMoveGroup()
            updateMoveGroup(moveGroup, piece, startSquare, endSquare, [])
            insertMoves(moves, piece + str(startSquare), str(endSquare), moveGroup, statsBoard[endSquare])

    return (moves, statsBoard)

# Get all pawn LAN moves
def getMovesPawnLan() -> resultType:

    moves: list[tuple[str, str]] = []
    statsBoard = Board(Stats())

    # For every end square
    for endSquare in SQUARES:
        stats = statsBoard[endSquare]

        # For both players
        for player in ["w", "b"]:

            # Generate moves
            moves += getMovesPawnSingle(endSquare, player, stats, False)
            moves += getMovesPawnCapture(endSquare, player, stats, False)
            moves += getMovesPawnDouble(endSquare, player, stats)

    return (moves, statsBoard)

# Get all king LAN moves
def getMovesKingLan() -> resultType:
    return getMovesPieceLan("K", KING_JUMPS, True)

# Get all rook LAN moves
def getMovesRookLan() -> resultType:
    return getMovesPieceLan("R", ROOK_DIRECTIONS, False)

# Get all bishop LAN moves
def getMovesBishopLan() -> resultType:
    return getMovesPieceLan("B", BISHOP_DIRECTIONS, False)

# Get all queen LAN moves
def getMovesQueenLan() -> resultType:
    return getMovesPieceLan("Q", QUEEN_DIRECTIONS, False)

# Get all knight LAN moves
def getMovesKnightLan() -> resultType:
    return getMovesPieceLan("N", KNIGHT_JUMPS, True)


####################
### Input/Output ###
####################

# Read manual moves from file
def readManualMoves() -> None:

    # Read lines of file
    with open(MANUAL_MOVES_PATH, "r") as fileManualMoves:
        for line in fileManualMoves.readlines():

            # Comment
            if line.startswith("#"):
                continue

            # Extract move and FEN
            line = line.rstrip()
            lineSplit = re.split(" +", line, 1)

            if len(lineSplit) != 2:
                continue

            move, fen = lineSplit

            # Don't duplicate castle moves
            if move[0] == "O":
                MANUAL_MOVES[move] = fen
                continue

            # Parse move into parts
            (piece, disambiguation, capture, endSquareStr, rest) = parseMove(move)

            pawnMove = piece == ""
            chessboard = fenToChessboard(fen)
            endSquare = strToSquare(endSquareStr)

            # Duplicate move for all 4 possible flips of files and ranks
            for (flipFiles, flipRanks) in product([False, True], repeat=2):

                # Build flipped move string
                moveFlippedStart = piece + flipFileRank(disambiguation, flipFiles, flipRanks)
                moveFlippedEnd = flipFileRank(endSquareStr, flipFiles, flipRanks) + rest
                moveFlipped = moveFlippedStart + capture + moveFlippedEnd

                # Generate flipped FEN
                fenFlipped = chessboardToFen(chessboard, flipFiles, flipRanks, flipRanks and pawnMove)

                # Add flipped move to manual moves
                MANUAL_MOVES[moveFlipped] = fenFlipped

                # If move is not a capture move, turn it into one
                if capture == "" and not pawnMove:
                    chessboard[endSquare] = "n"

                    # Generate flipped capture move and FEN
                    moveFlipped = moveFlippedStart + "x" + moveFlippedEnd
                    fenFlipped = chessboardToFen(chessboard, flipFiles, flipRanks, flipRanks and pawnMove)

                    # Add flipped capture move to manual moves
                    MANUAL_MOVES[moveFlipped] = fenFlipped
                    chessboard[endSquare] = ""

# Get table that contains the amount of move groups for every square and disambiguation type
def getDisambiguationTable(statsBoard: Board[Stats]) -> PrettyTable:

    table = PrettyTable()
    table.field_names = [""] + [fileToStr(file) for file in range(4)]

    # Only consider files [a-d] and ranks [1-4]
    # Rest of chessboard is analogous because of flips
    for rank in range(3, -1, -1):
        row = [rankToStr(rank)]

        for file in range(4):
            stats = statsBoard[Square(file, rank)]

            # Calculate counts by disambiguation type
            counts = [
                sum(stats.fileMove),
                sum(stats.rankMove),
                sum(stats.squareMove[square] for square in SQUARES),
                sum(stats.reachable[square] for square in SQUARES)
            ]

            # Append row
            field = "/".join(map(str, counts))
            row.append(field)

        table.add_row(row)

    return table

# Output statistics to file
def outputStatistics(results: dict[str, resultType], filePath: str, isSan: bool) -> None:

    finalSymbolTotal = [0] * 3
    movesTotal = 0

    with open(filePath, "w") as fileStats:

        # For every piece
        for (piece, (moves, statsBoard)) in results.items():

            # Increase total move counter
            movesTotal += len(moves)

            # Accumulate final symbol counts for all squares
            finalSymbolPiece = [0] * 3
            for square in SQUARES:
                for i in range(3):
                    finalSymbolTotal[i] += statsBoard[square].finalSymbol[i]
                    finalSymbolPiece[i] += statsBoard[square].finalSymbol[i]

            # Output move counts for piece
            fileStats.write(f"{piece} : {len(moves)} ({'/'.join(map(str, finalSymbolPiece))})\n\n")

            # No statistics for castle moves
            if piece == "Castle":
                fileStats.write("\n")
                continue

            # Output disambiguation table
            # Only available for SAN moves of rook, bishop, queen, and knight
            if isSan and piece in ["Rook", "Bishop", "Queen", "Knight"]:
                table = getDisambiguationTable(statsBoard)
                fileStats.write(str(table) + "\n\n")

            # Output move groups by what moves they are missing
            for key in ["checkmate", "check", "both"]:

                fileStats.write(f"Missing {key}:\n")
                noneMissing = True

                # Only consider files [a-d] and ranks [1-4]
                # Rest of chessboard is analogous because of flips
                for file in range(4):
                    for rank in range(4):
                        for (move, fen) in statsBoard[Square(file, rank)].missingMoves[key]:

                            # Output move and FEN
                            fileStats.write(f"{move:6} {fen}\n")
                            noneMissing = False

                if noneMissing:
                    fileStats.write("-\n")
                fileStats.write("\n")

            fileStats.write("\n")

        # Output total move counts
        fileStats.write(f"Total : {movesTotal} ({'/'.join(map(str, finalSymbolTotal))})\n")

# Output moves and their FEN to file
def outputMoves(results: dict[str, resultType], filePath: str, isSan: bool) -> None:

    # Width is determined by largest move string
    width = 7 if isSan else 8

    with open(filePath, "w") as fileMoves:

        # For every piece
        for (moves, _) in results.values():
            # For every move
            for move in moves:

                # FEN available
                if move[1]:
                    fileMoves.write(f"{move[0]:{width}} {move[1]}\n")
                # FEN unavailable
                else:
                    fileMoves.write(f"{move[0]}\n")

# Generate an image of a chessboard
# Mark files, ranks, and squares according to statistics
def generateDisambiguationImage(endSquare: Square, stats: Stats, filePath: str) -> None:

    image = Image.new("RGB", (2 * BORDER_SIZE + 8 * SIDE_LENGTH, 2 * BORDER_SIZE + 8 * SIDE_LENGTH), "white")
    draw = ImageDraw.Draw(image)

    # Draw squares
    for square in SQUARES:

        # End square
        if square == endSquare:
            colorSquare = COLOR_END_SQUARE
        # Other square
        else:
            colorSquare = COLOR_LIGHT if (square.file + square.rank) % 2 else COLOR_DARK

        # Draw rectangle
        x: float = BORDER_SIZE + square.file       * SIDE_LENGTH
        y: float = BORDER_SIZE + (7 - square.rank) * SIDE_LENGTH
        draw.rectangle((x, y, x + SIDE_LENGTH, y + SIDE_LENGTH), fill=colorSquare)

        # Square move
        if stats.squareMove[square]:
            colorCircle = COLOR_MARKED
        # Reachable square
        elif stats.reachable[square]:
            colorCircle = COLOR_REACHABLE
        # Other square
        else:
            colorCircle = None

        # Draw circle
        if colorCircle:
            x += 0.5 * SIDE_LENGTH
            y += 0.5 * SIDE_LENGTH
            xy = (x - CIRCLE_RADIUS, y - CIRCLE_RADIUS, x + CIRCLE_RADIUS, y + CIRCLE_RADIUS)
            draw.ellipse(xy, colorCircle)

    # Draw file names
    for file in range(8):

        # Draw file name
        fileStr = chr(ord("a") + file)
        w, _ = FONT.getsize(fileStr)
        x = BORDER_SIZE + (file + 0.5) * SIDE_LENGTH - 0.5 * w
        y = 30
        draw.text((x, y), fileStr, "black", FONT)

        # Draw circle
        if stats.fileMove[file]:
            x = BORDER_SIZE + (file + 0.5) * SIDE_LENGTH
            y = 0.5 * BORDER_SIZE
            xy = (x - CIRCLE_RADIUS, y - CIRCLE_RADIUS, x + CIRCLE_RADIUS, y + CIRCLE_RADIUS)
            draw.ellipse(xy, outline=COLOR_MARKED, width=10)

    # Draw rank names
    for rank in range(8):

        # Draw rank name
        rankStr = str(rank + 1)
        w, _ = FONT.getsize(rankStr)
        x = 0.5 * BORDER_SIZE - 0.5 * w
        y = BORDER_SIZE + (7 - rank) * SIDE_LENGTH + 55
        draw.text((x, y), rankStr, "black", FONT)

        # Draw circle
        if stats.rankMove[rank]:
            x = 0.5 * BORDER_SIZE
            y = BORDER_SIZE + (7 - rank + 0.5) * SIDE_LENGTH
            xy = (x - CIRCLE_RADIUS, y - CIRCLE_RADIUS, x + CIRCLE_RADIUS, y + CIRCLE_RADIUS)
            draw.ellipse(xy, outline=COLOR_MARKED, width=10)

    # Draw box around chessboard
    a = BORDER_SIZE
    b = BORDER_SIZE + 8 * SIDE_LENGTH
    draw.rectangle((a, a, b, b), outline="black", width=5)

    # Save image
    image.save(filePath)

# Output disambiguation images for every piece with disambiguation moves and every square
def outputDisambiguationImages(results: dict[str, resultType]) -> None:

    # For every piece with disambiguation moves
    for piece in ["Rook", "Bishop", "Queen", "Knight"]:
        statsBoard = results[piece][1]

        # For every end square
        for endSquare in SQUARES:

            # Generate image as save to file
            fileName = f"{piece.lower()}-{str(endSquare)}.png"
            filePath = f"{IMAGES_FOLDER}/{piece}/{fileName}"
            generateDisambiguationImage(endSquare, statsBoard[endSquare], filePath)


############
### Main ###
############

# Main program
def main() -> None:

    # Parse command line arguments
    parser = ArgumentParser()
    parser.add_argument("--no-san", action="store_true", help="don't generate SAN moves")
    parser.add_argument("--no-lan", action="store_true", help="don't generate LAN moves")
    parser.add_argument("--images", action="store_true", help="output disambiguation images")
    arguments = parser.parse_args()

    san = not arguments.no_san
    lan = not arguments.no_lan
    images = arguments.images

    # Read manual moves from file
    readManualMoves()

    # SAN moves
    if san:

        # Generate moves
        resultsSan = {
            "Pawn"   : getMovesPawnSan(),
            "King"   : getMovesKingSan(),
            "Rook"   : getMovesRookSan(),
            "Bishop" : getMovesBishopSan(),
            "Queen"  : getMovesQueenSan(),
            "Knight" : getMovesKnightSan(),
            "Castle" : getMovesCastle()
        }

        # Output
        outputMoves(resultsSan, MOVES_SAN_PATH, True)
        outputStatistics(resultsSan, STATS_SAN_PATH, True)

    # LAN moves
    if lan:

        # Generate moves
        resultsLan = {
            "Pawn"   : getMovesPawnLan(),
            "King"   : getMovesKingLan(),
            "Rook"   : getMovesRookLan(),
            "Bishop" : getMovesBishopLan(),
            "Queen"  : getMovesQueenLan(),
            "Knight" : getMovesKnightLan(),
            "Castle" : getMovesCastle()
        }

        # Output
        outputMoves(resultsLan, MOVES_LAN_PATH, False)
        outputStatistics(resultsLan, STATS_LAN_PATH, False)

    # Output disambiguation images
    if images and san:
        outputDisambiguationImages(resultsSan)

if __name__ == "__main__":
    main()
