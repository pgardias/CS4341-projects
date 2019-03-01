import math
import agent
import time


###########################
# Alpha-Beta Search Agent #
###########################

class AlphaBetaAgent(agent.Agent):
	"""Agent that uses alpha-beta search"""

	# Class constructor.
	#
	# PARAM [string] name:      the name of this player
	# PARAM [int]    max_depth: the maximum search depth
	def __init__(self, name, max_depth):
		super().__init__(name)
		# Max search depth
		self.max_depth = max_depth

	# Pick a column.
	#
	# PARAM [board.Board] brd: the current board state
	# RETURN [int]: the column where the token must be added
	#
	# NOTE: make sure the column is legal, or you'll lose the game.
	def go(self, brd):
		"""Return the best move (choice of column for the token) - will only be
			called on own turn"""
		start = time.time()
		m = self.minimax_decision(brd, self.max_depth, -1e999, 1e999, 0, True)[1]
		return m

	def minimax_decision(self, brd, depth, alpha, beta, c, maximizing):
		"""Returns the score associated with the node and the move that it represents
			as a tuple"""
		successors = self.get_successors(brd)
		if depth == 0 or not successors:  # Leaf node
			return self.evaluation(brd), c

		if maximizing:
			val = -1e999
			move = c
			for b, col in successors:
				r = self.minimax_decision(b, depth - 1, alpha, beta, col, False)
				if r[0] > val:
					val = r[0]
					move = col
				alpha = max(alpha, val)
				if alpha >= beta:
					break
			return val, move
		else:
			val = 1e999
			move = c
			for b, col in successors:
				r = self.minimax_decision(b, depth - 1, alpha, beta, col, True)
				if r[0] < val:
					val = r[0]
					move = col
				beta = min(beta, val)
				if alpha >= beta:
					break
			return val, move

	def evaluation(self, brd):
		"""Iterates over entire board to determine total heuristic score"""
		total_score = 0
		for i in range(brd.w):
			for j in range(brd.h):
				total_score += self.score_cell(brd, i, j)
		return total_score

	def score_cell(self, brd, x, y):
		"""Returns the score for the given cell at (x, y), only checking in the +y
			and +x direction (down, right, and diagonally down and to the right)
			to avoid counting duplicate segment counting"""
		return (self.segment_score(brd, x, y, 0, 1) +  # Vertical down
		        self.segment_score(brd, x, y, 1, 0) +  # Horizontal right
		        self.segment_score(brd, x, y, 1, 1))  # Diagonal down right

	def segment_score(self, brd, x, y, dx, dy):
		t = brd.board[y][x]
		count = 0
		for i in range(brd.n):
			new_x = x + dx * i
			new_y = y + dy * i
			if new_x and new_y >= 0 and new_x < brd.w and new_y < brd.h:
				cell = brd.board[new_y][new_x]
				if t is "0":  # First player token encountered
					t = cell
				if cell is not t:  # Terminate score counting
					return 0
				elif cell is self.player:
					count += 1
		return self.score(brd, count, t is self.player)

	def score(self, brd, count, positive):
		if count == brd.n or (not positive and count == brd.n - 1):
			if positive:
				return 1e999
			else:
				return -1e999
		else:
			score = 10 * (count ** 3 / brd.n)
			if positive:
				return count
			else:
				return -1.2 * score

	# Get the successors of the given board.
	#
	# PARAM [board.Board] brd: the board state
	# RETURN [list of (board.Board, int)]: a list of the successor boards,
	#                                      along with the column where the last
	#                                      token was added in it
	def get_successors(self, brd):
		"""Returns the reachable boards from the given board brd. The return value
		    is a tuple (new board state, column number where last token was added)."""
		# Get possible actions
		freecols = brd.free_cols()
		# Are there legal actions left?
		if not freecols:
			return []
		# Make a list of the new boards along with the corresponding actions
		succ = []
		for col in freecols:
			# Clone the original board
			nb = brd.copy()
			# Add a token to the new board
			# (This internally changes nb.player, check the method definition!)
			nb.add_token(col)
			# Add board to list of successors
			succ.append((nb, col))
		return succ


THE_AGENT = AlphaBetaAgent("GardiasPrzemek", 3)
