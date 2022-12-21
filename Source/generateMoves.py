from __future__ import annotations
from typing import cast, List, Tuple, TypeVar, Generic, Optional
from itertools import product, permutations
from copy import deepcopy
from prettytable import PrettyTable
from PIL import Image, ImageDraw, ImageFont
import re, os


###############
### Classes ###
###############

# Class containing file and rank offset
class Offset:

    file: int
    rank: int

    def __init__(self, file: int, rank: int) -> None:
        self.file = file
        self.rank = rank

# Class for a square on chessboard
class Square:

    # File index [0-7]
    file: int
    # Rank index [0-7]
    rank: int
    # ID of direction from which square is reachable (optional)
    directionId: int

    def __init__(self, file: int, rank: int, dirId=-1) -> None:
        self.file = file
        self.rank = rank
        self.directionId = dirId

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

        self.plainMove = False
        self.fileMove = [False] * 8
        self.rankMove = [False] * 8
        self.squareMove = Board(False)
        self.reachable = Board(False)
        self.missingMoves = {"checkmate": [], "check": [], "both": []}
        self.finalSymbol = [0] * 3

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

# Dimensions of image
SIDE_LENGTH = 200
BORDER_SIZE = 150
CIRCLE_RADIUS = 50

# Colors for image
COLOR_END_SQUARE = "red"
COLOR_LIGHT      = "white"
COLOR_DARK       = "black"
COLOR_MARKED     = "#0b37ba"
COLOR_REACHABLE  = "#dde330"

# Font for image
FONT = ImageFont.truetype("./Data/roboto-regular.ttf", 70)

# File and folder paths
DIR_NAME          = os.path.dirname(__file__)
MANUAL_MOVES_PATH = os.path.join(DIR_NAME, "../Data/manual-moves.txt")
MOVES_PATH        = os.path.join(DIR_NAME, "../Data/moves.txt")
STATS_PATH        = os.path.join(DIR_NAME, "../Data/stats.txt")
IMAGES_FOLDER     = os.path.join(DIR_NAME, "../Images")


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
def flipFileRank(string: str, flipFiles: bool, flipRanks: bool) -> str:

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

# Get an empty 2D array as FEN group
# First Dimension  | 0 No Capture | 1 Capture
# Second Dimension | 0 Nothing    | 1 Check   | 2 Checkmate
def getEmptyFenGroup() -> list[list[Optional[str]]]:
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
def boardToFen(board: Board[str], flipFiles=False, flipRanks=False, swapPlayers=False) -> str:

    ranks: list[str] = []
    # Loop through ranks in specified order
    for rank in (range(7, -1, -1) if not flipRanks else range(8)):
        emptySquares = 0
        rankStr = ""

        # Loop through files in specified order
        for file in (range(8) if not flipFiles else range(7, -1, -1)):
            square = Square(file, rank)

            # Empty square
            if board[square] == "":
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
                    rankStr += board[square].swapcase()
                else:
                    rankStr += board[square]

        # Append number of empty squares
        if emptySquares > 0:
            rankStr += str(emptySquares)

        ranks.append(rankStr)

    # Build FEN string
    player = "b" if swapPlayers else "w"
    boardStr = "/".join(ranks)
    fen = f"{boardStr} {player} - - 0 1"

    return fen

# Get chessboard from a FEN
def fenToBoard(fen: str) -> Board[str]:

    board = Board("")
    boardStr = fen.split(" ")[0]
    ranks = boardStr.split("/")

    # Loop through ranks from 7 to 0
    for rank in range(7, -1, -1):
        file = 0
        for c in ranks[7 - rank]:
            # Empty squares
            if c.isdigit():
                file += int(c)
            # Piece
            else:
                board[Square(file, rank)] = c
                file += 1

    return board


######################
### Piece movement ###
######################

# Get list of start squares from end square for direction moves
def getStartSquaresDirection(endSquare: Square, directions: list[Offset]) -> list[Square]:

    startSquares: list[Square] = []

    # For every direction
    for (directionId, direction) in enumerate(directions):
        square = endSquare + direction
        square.directionId = directionId

        # Go in this direction until edge of chessboard
        while square.onBoard():
            startSquares.append(square)
            square += direction

    return startSquares

# Mark all squares that can be reached from starting square by specified jumps as attacked
def markAttackedSquaresJump(startSquare: Square, attackedSquares: Board[Optional[Square]], jumps: list[Offset]
    ) -> None:

    # For every jump
    for jump in jumps:
        endSquare = startSquare + jump

        # Mark end square if it is on chessboard
        if endSquare.onBoard():
            attackedSquares[endSquare] = Square(-1, -1)

# Mark all squares that can be reached from starting square in specified directions as attacked
def markAttackedSquaresDirection(square: Square, board: Board[str], attackedSquares: Board[Optional[Square]],
    directions: list[Offset]) -> None:

    # For every direction
    for direction in directions:
        squarePrev = square
        squareCurr = square + direction

        # Go in this direction until edge or other piece
        while squareCurr.onBoard():
            attackedSquares[squareCurr] = squarePrev

            # Direction is block by other piece
            if board[squareCurr] != "":
                break

            squarePrev = squareCurr
            squareCurr = squareCurr + direction

# Get board of attacked squares from chessboard
# If a square is attacked by a direction move, store previous square in line of attack
def getAttackedSquares(board: Board[str]) -> Board[Optional[Square]]:

    attackedSquares: Board[Optional[Square]] = Board(None)

    for square in SQUARES:
        piece = board[square]

        if piece == "P":   # Pawn
            markAttackedSquaresJump(square, attackedSquares, PAWN_JUMPS)
        elif piece == "K": # King
            markAttackedSquaresJump(square, attackedSquares, KING_JUMPS)
        elif piece == "N": # Knight
            markAttackedSquaresJump(square, attackedSquares, KNIGHT_JUMPS)
        elif piece == "B": # Bishop
            markAttackedSquaresDirection(square, board, attackedSquares, BISHOP_DIRECTIONS)
        elif piece == "R": # Rook
            markAttackedSquaresDirection(square, board, attackedSquares, ROOK_DIRECTIONS)
        elif piece == "Q": # Queen
            markAttackedSquaresDirection(square, board, attackedSquares, QUEEN_DIRECTIONS)

    return attackedSquares


######################
### Generate FENs ####
######################

# Place white king on chessboard
# Return whether placement was possible
def placeWhiteKing(board: Board[str], keepFree: Board[bool], attackedSquaresAfter: Board[Optional[Square]],
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
        board[square] = "K"
        return True

    # White king couldn't be placed
    return False

# Place white pieces around black king such that all squares adjacent to it are attacked
# Return whether placement was possible
def boxInBlackKing(blackKingSquare: Square, endSquare: Square, boardBefore: Board[str], boardAfter: Board[str],
    attackedSquaresAfter: Board[Optional[Square]]) -> bool:

    previousLineOfAttackSquare = cast(Square, attackedSquaresAfter[blackKingSquare])

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
        if previousLineOfAttackSquare in rookSquares:

            # If attacker is next to black king, it has to be protected
            # Otherwise it could be taken by black king and it wouldn't be checkmate
            if boardAfter[previousLineOfAttackSquare].isupper():
                if not attackedSquaresAfter[previousLineOfAttackSquare]:
                    return False

            # Remove blocking rook
            rookSquares.remove(previousLineOfAttackSquare)

            # Place bishop next to black king and rook
            # Place knight on edge such that it defends rook
            knightSquare = Square(blackKingSquare.file, previousLineOfAttackSquare.rank)
            bishopSquare = Square(previousLineOfAttackSquare.file, blackKingSquare.rank)

            if (bishopSquare.file in [0, 7]) or (bishopSquare.rank in [0, 7]):
                (knightSquare, bishopSquare) = (bishopSquare, knightSquare)

            boardBefore[knightSquare] = "N"
            boardBefore[bishopSquare] = "B"

            # Result:
            # . B R        R B .
            # N k .   or   . k N
            # = = =        = = =

        # Rook doesn't block attack on black king
        else:

            # Moving a rook next to black king as an attacker messes up disambiguation
            if boardAfter[endSquare] == "R" and previousLineOfAttackSquare == endSquare:
                return False

            # Result:
            # R . R
            # . k .
            # = = =

    # Black king in middle
    else:

        # Moving a rook next to black king as an attacker messes up disambiguation
        if boardAfter[endSquare] == "R" and previousLineOfAttackSquare == endSquare:
            return False

        # Remove rook when it blocks attack on black king
        if previousLineOfAttackSquare in rookSquares:
            rookSquares.remove(previousLineOfAttackSquare)
        # Otherwise remove arbitrary rook
        else:
            rookSquares.pop()

        # Result:
        # R . R
        # . k .
        # R . .

    # Place rooks
    for rookSquare in rookSquares:
        boardBefore[rookSquare] = "R"

    # Place black king
    boardBefore[blackKingSquare] = "k"
    return True

# Place black and white king on board such that black king is not in check
# Return FEN of such position if one is found else return None
def placeKingsNoCheck(endSquare: Square, boardBefore: Board[str], boardAfter: Board[str], keepFree: Board[bool],
    hasWhiteKing: bool, flipForPawn: bool) -> Optional[str]:

    boardBefore = deepcopy(boardBefore)
    attackedSquaresBefore = getAttackedSquares(boardBefore)
    attackedSquaresAfter = getAttackedSquares(boardAfter)
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
        boardBefore[square] = "k"
        squareBlackKing = square
        break

    # Black king couldn't be placed
    if not squareBlackKing:
        return None

    # Place white king if not placed yet
    if not hasWhiteKing:
        if not placeWhiteKing(boardBefore, keepFree, attackedSquaresAfter, squareBlackKing):
            return None

    # Return FEN
    return boardToFen(boardBefore, flipRanks=flipForPawn, swapPlayers=flipForPawn)

# Place black and white king on board such that black king is in check
# Return FEN of such position if one is found else return None
def placeKingsCheck(endSquare: Square, boardBefore: Board[str], boardAfter: Board[str], keepFree: Board[bool],
    hasWhiteKing: bool, flipForPawn: bool) -> Optional[str]:

    boardBefore = deepcopy(boardBefore)
    attackedSquaresBefore = getAttackedSquares(boardBefore)
    attackedSquaresAfter = getAttackedSquares(boardAfter)
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
        checkmate = True
        for jump in KING_JUMPS:

            squareNew = square + jump
            if not squareNew.onBoard():
                continue

            # Found unattacked square
            if not attackedSquaresAfter[squareNew]:
                checkmate = False
                break

        # Place king if there is no checkmate
        if not checkmate:
            boardBefore[square] = "k"
            squareBlackKing = square
            break

    # Black king couldn't be placed
    if not squareBlackKing:
        return None

    # Place white king if not placed yet
    if not hasWhiteKing:
        if not placeWhiteKing(boardBefore, keepFree, attackedSquaresAfter, squareBlackKing):
            return None

    # Return FEN
    return boardToFen(boardBefore, flipRanks=flipForPawn, swapPlayers=flipForPawn)

# Place black and white king on board such that black king is checkmated
# Return FEN of such position if one is found else return None
def placeKingsCheckmate(endSquare: Square, boardBefore: Board[str], boardAfter: Board[str], keepFree: Board[bool],
    hasWhiteKing: bool, flipForPawn: bool) -> Optional[str]:

    boardBefore = deepcopy(boardBefore)
    attackedSquaresBefore = getAttackedSquares(boardBefore)
    attackedSquaresAfter = getAttackedSquares(boardAfter)
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

        checkmate = True
        adjacentAllPlacable = True
        previousLineOfAttackSquare = cast(Square, attackedSquaresAfter[square])

        # Check for checkmate and whether we can place a piece on all adjacent squares
        # Except previous square in line of attack
        for jump in KING_JUMPS:

            adjacentSquare = square + jump
            if not adjacentSquare.onBoard():
                continue

            # Found unattacked square
            if not attackedSquaresAfter[adjacentSquare]:
                checkmate = False

            # Square is not previous square in the line of attack and not placable
            if adjacentSquare != previousLineOfAttackSquare and keepFree[adjacentSquare]:
                adjacentAllPlacable = False

        # Checkmate found
        if checkmate:
            # Place black king
            boardBefore[square] = "k"
            squareBlackKing = square
            break

        # All adjacent squares are vacant
        if adjacentAllPlacable:
            # Place white piece around black king
            if boxInBlackKing(square, endSquare, boardBefore, boardAfter, attackedSquaresAfter):
                squareBlackKing = square
                break

    # Black king couldn't be placed
    if not squareBlackKing:
        return None

    # Place white king if not placed yet
    if not hasWhiteKing:
        if not placeWhiteKing(boardBefore, keepFree, attackedSquaresAfter, squareBlackKing):
            return None

    # Return FEN
    return boardToFen(boardBefore, flipRanks=flipForPawn, swapPlayers=flipForPawn)

# Update FEN group with FENs of capture or non-capture moves from specified chessboard
def updateFenGroupCapture(fenGroupCapture: list[Optional[str]], piece: str, startSquare: Square, endSquare: Square,
    boardBefore: Board[str], boardAfter: Board[str], keepFree: Board[bool], flipForPawn: bool) -> None:

    # Generate FENs for no check, check, and checkmate
    placeFunctions = [placeKingsNoCheck, placeKingsCheck, placeKingsCheckmate]
    for i in range(3):
        if not fenGroupCapture[i]:
            fenGroupCapture[i] = placeFunctions[i](endSquare, boardBefore, boardAfter, keepFree, piece == "K", flipForPawn)

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
            if fenGroupCapture[1] and fenGroupCapture[2]:
                break

            # Square must be kept free for move
            if keepFree[squareAttacker]:
                continue

            # Place discovered attacker
            boardBefore[squareAttacker] = pieceDiscovered
            boardAfter[squareAttacker] = pieceDiscovered
            keepFree[squareAttacker] = True

            # Generate FEN for check
            if not fenGroupCapture[1]:
                fenGroupCapture[1] = placeKingsCheck(endSquare, boardBefore, boardAfter, keepFree, piece == "K", flipForPawn)

            # Generate FEN for checkmate
            if not fenGroupCapture[2]:
                fenGroupCapture[2] = placeKingsCheckmate(endSquare, boardBefore, boardAfter, keepFree, piece == "K", flipForPawn)

            # Remove discovered attacker
            boardBefore[squareAttacker] = ""
            boardAfter[squareAttacker] = ""
            keepFree[squareAttacker] = False

# Update FEN group with FENs generated from specified position
def updateFenGroup(fenGroup: list[list[Optional[str]]], piece: str, startSquare: Square, endSquare: Square,
    otherSquares: list[Square], promotePiece="", flipForPawn=False) -> None:

    # Return if FEN group is already full
    alreadyFull = True
    for i in range(2):
        for j in range(3):
            if not fenGroup[i][j]:
                alreadyFull = False

    if alreadyFull:
        return

    boardBefore = Board("")
    keepFree = Board(False)

    # Place pieces on chessboard and calculate squares that must be kept free for move
    for square in [startSquare] + otherSquares:

        # Place piece
        boardBefore[square] = piece

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

    # Calculate board after move
    boardAfter = deepcopy(boardBefore)
    boardAfter[startSquare] = ""
    boardAfter[endSquare] = piece if promotePiece == "" else promotePiece

    # Update FEN group with FENs of non-capture moves
    updateFenGroupCapture(fenGroup[0], piece, startSquare, endSquare, boardBefore, boardAfter, keepFree, flipForPawn)

    # Update FEN group with FENs of capture moves
    boardBefore[endSquare] = "n"
    updateFenGroupCapture(fenGroup[1], piece, startSquare, endSquare, boardBefore, boardAfter, keepFree, flipForPawn)

# Insert FEN group into move list
# Return whether moves were inserted
def insertMoves(moves: list[tuple[str, str]], moveStart: str, moveEnd: str, fenGroup: list[list[Optional[str]]],
    stats: Stats) -> bool:

    moveInserted = False

    # For no capture and capture moves
    for i in range(2):
        capture = "" if i == 0 else "x"

        # For every final symbol
        for (j, symbol) in enumerate(FINAL_SYMBOL):
            move = moveStart + capture + moveEnd + symbol

            # If move is missing, use manual move if available
            if (not fenGroup[i][j]) and (move in MANUAL_MOVES):
                fenGroup[i][j] = MANUAL_MOVES[move]

            # Insert move into move list
            if fenGroup[i][j]:
                moves.append((move, cast(str, fenGroup[i][j])))
                stats.finalSymbol[j] += 1
                moveInserted = True

        # Statistics
        if fenGroup[i][0]:

            moveWithFen = (moveStart + capture + moveEnd, cast(str, fenGroup[i][0]))

            # Checkmate is missing
            if fenGroup[i][1] and not fenGroup[i][2]:
                stats.missingMoves["checkmate"].append(moveWithFen)

            # Check is missing
            if not fenGroup[i][1] and fenGroup[i][2]:
                stats.missingMoves["check"].append(moveWithFen)

            # Both are missing
            if not fenGroup[i][1] and not fenGroup[i][2]:
                stats.missingMoves["both"].append(moveWithFen)

    return moveInserted


######################
### Generate moves ###
######################

# Get all moves of one end square for a piece with disambiguation moves
def getMovesDisambiguation(piece: str, endSquare: Square, startSquares: list[Square], stats: Stats
    ) -> list[tuple[str, str]]:

    movesSquare: list[tuple[str, str]] = []
    endSquareStr = str(endSquare)

    # FEN groups for plain, file, rank, and square moves
    fenGroupPlain = getEmptyFenGroup()
    fenGroupFile = [getEmptyFenGroup() for _ in range(8)]
    fenGroupRank = [getEmptyFenGroup() for _ in range(8)]
    fenGroupSquare = Board(getEmptyFenGroup())

    # One piece
    for startSquare in startSquares:
        # Plain move
        updateFenGroup(fenGroupPlain, piece, startSquare, endSquare, [])

    # Two pieces
    for (startSquare, otherSquare) in permutations(startSquares, 2):

        # Pieces block each other's path
        if startSquare.directionId == otherSquare.directionId:
            continue

        # Rank move
        if startSquare.file == otherSquare.file:
            updateFenGroup(fenGroupRank[startSquare.rank], piece, startSquare, endSquare, [otherSquare])
        # File move
        else:
            updateFenGroup(fenGroupFile[startSquare.file], piece, startSquare, endSquare, [otherSquare])

    # Three pieces
    for (startSquare, otherSquare1, otherSquare2) in permutations(startSquares, 3):

        # Check whether both file and rank are needed for disambiguation
        if not (startSquare.file == otherSquare1.file and startSquare.rank == otherSquare2.rank):
            continue

        # Pieces block each other's path
        if len({startSquare.directionId, otherSquare1.directionId, otherSquare2.directionId}) < 3:
            continue

        # Square move
        updateFenGroup(fenGroupSquare[startSquare], piece, startSquare, endSquare, [otherSquare1, otherSquare2])

    # Insert plain move
    if insertMoves(movesSquare, piece, endSquareStr, fenGroupPlain, stats):
        stats.plainMove = True

    # Insert file moves
    for fileStart in range(8):
        moveStart = piece + fileToStr(fileStart)
        fen = fenGroupFile[fileStart]

        if insertMoves(movesSquare, moveStart, endSquareStr, fen, stats):
            stats.fileMove[fileStart] = True

    # Insert rank moves
    for rankStart in range(8):
        moveStart = piece + rankToStr(rankStart)
        fen = fenGroupRank[rankStart]

        if insertMoves(movesSquare, moveStart, endSquareStr, fen, stats):
            stats.rankMove[rankStart] = True

    # Insert square moves
    for startSquare in SQUARES:
        moveStart = piece + str(startSquare)
        fen = fenGroupSquare[startSquare]

        if insertMoves(movesSquare, moveStart, endSquareStr, fen, stats):
            stats.squareMove[startSquare] = True

    # Mark reachable squares
    for startSquare in startSquares:
        stats.reachable[startSquare] = True

    return movesSquare

# Get all moves of a direction piece
def getMovesDirection(piece: str, directions: list[Offset]) -> resultType:

    moves: list[tuple[str, str]] = []
    statsBoard = Board(Stats())

    # For every end square
    for endSquare in SQUARES:

        # Get start squares
        startSquares = getStartSquaresDirection(endSquare, directions)
        # Generate moves and append to move list
        moves += getMovesDisambiguation(piece, endSquare, startSquares, statsBoard[endSquare])

    return (moves, statsBoard)

# Get all pawn moves
def getMovesPawn() -> resultType:

    moves: list[tuple[str, str]] = []
    statsBoard = Board(Stats())

    # For every end square
    for endSquare in SQUARES:

        stats = statsBoard[endSquare]
        endSquareStr = str(endSquare)

        # If end square can't be reached by white pawn
        # Then flip rank of end square and set flag
        flipForPawn = False
        if endSquare.rank <= 1:
            endSquare = Square(endSquare.file, 7 - endSquare.rank)
            flipForPawn = True

        # For every promotion option (piece or no promotion)
        promotionOptions = PROMOTION if endSquare.rank == 7 else [""]
        for promotePiece in promotionOptions:
            promote = "" if promotePiece == "" else "=" + promotePiece

            # Generate non-capture moves
            startSquare = endSquare + Offset(0, -1)
            fenGroup = getEmptyFenGroup()
            updateFenGroup(fenGroup, "P", startSquare, endSquare, [], promotePiece, flipForPawn)

            # FEN group also contains capture moves, so delete them before insertion into move list
            fenGroup[1] = [None] * 3
            insertMoves(moves, "", endSquareStr + promote, fenGroup, stats)

            # Check both adjacent files
            for offset in [Offset(-1, -1), Offset(1, -1)]:
                startSquare = endSquare + offset
                if startSquare.onBoard():

                    # Generate capture moves
                    fenGroup = getEmptyFenGroup()
                    updateFenGroup(fenGroup, "P", startSquare, endSquare, [], promotePiece, flipForPawn)

                    # FEN group also contains non-capture moves, so delete them before insertion into move list
                    fenGroup[0] = [None] * 3
                    insertMoves(moves, fileToStr(startSquare.file), endSquareStr + promote, fenGroup, stats)

    return (moves, statsBoard)

# Get all king moves
def getMovesKing() -> resultType:

    moves: list[tuple[str, str]] = []
    statsBoard = Board(Stats())

    # For every end square
    for endSquare in SQUARES:
        fenGroup = getEmptyFenGroup()

        # For every adjacent square as start square
        for jump in KING_JUMPS:
            startSquare = endSquare + jump
            if startSquare.onBoard():

                # Update FEN group
                updateFenGroup(fenGroup, "K", startSquare, endSquare, [])

        # Insert moves into move list
        insertMoves(moves, "K", str(endSquare), fenGroup, statsBoard[startSquare])

    return (moves, statsBoard)

# Get all rook moves
def getMovesRook() -> resultType:
    return getMovesDirection("R", ROOK_DIRECTIONS)

# Get all bishop moves
def getMovesBishop() -> resultType:
    return getMovesDirection("B", BISHOP_DIRECTIONS)

# Get all queen moves
def getMovesQueen() -> resultType:
    return getMovesDirection("Q", QUEEN_DIRECTIONS)

# Get all knight moves
def getMovesKnight() -> resultType:

    moves: list[tuple[str, str]] = []
    statsBoard = Board(Stats())

    # For every end square
    for endSquare in SQUARES:

        # Find all start squares
        startSquares: list[Square] = []
        for (dirId, jump) in enumerate(KNIGHT_JUMPS):
            startSquare = endSquare + jump
            startSquare.directionId = dirId

            if startSquare.onBoard():
                startSquares.append(startSquare)

        # Generate moves and append to move list
        moves += getMovesDisambiguation("N", endSquare, startSquares, statsBoard[endSquare])

    return (moves, statsBoard)

# Get all castle moves
def getMovesCastle() -> resultType:

    moves: list[tuple[str, str]] = []
    statsBoard = Board(Stats())
    stats = statsBoard[Square(0, 0)]

    # Short and long castle
    for castle in ["O-O", "O-O-O"]:

        # For every final symbol
        for (i, final) in enumerate(FINAL_SYMBOL):
            move = castle + final

            # Insert move if it is contained in manual moves
            if move in MANUAL_MOVES:
                moves.append((move, MANUAL_MOVES[move]))
                stats.finalSymbol[i] += 1

    return (moves, statsBoard)


####################
### Input/Output ###
####################

# Read manual moves from file
def readManualMoves() -> None:

    # Read lines of file
    with open(MANUAL_MOVES_PATH, "r") as fileManualMoves:
        for line in fileManualMoves.readlines():

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
            board = fenToBoard(fen)
            endSquare = strToSquare(endSquareStr)

            # Duplicate move for all 4 possible flips of files and ranks
            for (flipFiles, flipRanks) in product([False, True], repeat=2):

                # Build flipped move string
                moveFlippedStart = piece + flipFileRank(disambiguation, flipFiles, flipRanks)
                moveFlippedEnd = flipFileRank(endSquareStr, flipFiles, flipRanks) + rest
                moveFlipped = moveFlippedStart + capture + moveFlippedEnd

                # Generate flipped FEN
                fenFlipped = boardToFen(board, flipFiles, flipRanks, flipRanks and pawnMove)

                # Add flipped move to manual moves
                MANUAL_MOVES[moveFlipped] = fenFlipped

                # If move is not a capture move, turn it into one
                if capture == "" and not pawnMove:
                    board[endSquare] = "n"

                    # Generate flipped capture move and FEN
                    moveFlipped = moveFlippedStart + "x" + moveFlippedEnd
                    fenFlipped = boardToFen(board, flipFiles, flipRanks, flipRanks and pawnMove)

                    # Add flipped capture move to manual moves
                    MANUAL_MOVES[moveFlipped] = fenFlipped
                    board[endSquare] = ""

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
def outputStatistics(results: dict[str, resultType]) -> None:

    finalSymbolTotal = [0] * 3
    movesTotal = 0

    with open(STATS_PATH, "w") as fileStats:

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

            # Only available for direction pieces
            if piece in ["Rook", "Bishop", "Queen", "Knight"]:
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
                        for (moveGroup, fen) in statsBoard[Square(file, rank)].missingMoves[key]:

                            # Output move group and FEN
                            fileStats.write(f"{moveGroup:6} {fen}\n")
                            noneMissing = False

                if noneMissing:
                    fileStats.write("-\n")
                fileStats.write("\n")

            fileStats.write("\n")

        # Output total move counts
        fileStats.write(f"Total : {movesTotal} ({'/'.join(map(str, finalSymbolTotal))})\n")

# Output moves and their FEN to file
def outputMoves(results: dict[str, resultType]) -> None:

    with open(MOVES_PATH, "w") as fileMoves:

        # For every piece
        for (moves, _) in results.values():
            # For every move
            for move in moves:

                # FEN available
                if move[1]:
                    fileMoves.write(f"{move[0]:7} {move[1]}\n")
                # FEN unavailable
                else:
                    fileMoves.write(f"{move[0]}\n")

# Generate an image of a chessboard
# Mark files, ranks, and squares according to statistics
def generateImage(endSquare: Square, stats: Stats, filePath: str) -> None:

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

# Output images for every direction piece and square
def outputImages(results: dict[str, resultType]) -> None:

    # For every direction piece
    for piece in ["Rook", "Bishop", "Queen", "Knight"]:
        statsBoard = results[piece][1]

        # For every end square
        for endSquare in SQUARES:

            # Generate image as save to file
            fileName = f"{piece.lower()}-{str(endSquare)}.png"
            filePath = f"{IMAGES_FOLDER}/{piece}/{fileName}"
            generateImage(endSquare, statsBoard[endSquare], filePath)


############
### Main ###
############

# Main program
def main() -> None:

    # Read manual moves from file
    readManualMoves()

    # Generate all moves
    results = {
        "Pawn"   : getMovesPawn(),
        "King"   : getMovesKing(),
        "Rook"   : getMovesRook(),
        "Bishop" : getMovesBishop(),
        "Queen"  : getMovesQueen(),
        "Knight" : getMovesKnight(),
        "Castle" : getMovesCastle()
    }

    # Output
    outputStatistics(results)
    outputMoves(results)
    outputImages(results)

if __name__ == "__main__":
    main()
