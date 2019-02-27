import sys

sys.path.insert(0, '../bomberman')
from entity import CharacterEntity
from colorama import Fore, Back
from sensed_world import SensedWorld
from events import Event


class TestCharacter(CharacterEntity):
	weights = []
	gamma = 0.9
	learning_rate = 0.2
	max_distance_to_detect_monster = 4
	monster_moves_randomly = False

	def do(self, wrld):
		# setup
		self.readWeights()

		print('weights:', self.weights)
		next_action = self.bestAction(wrld)
		self.move(next_action[0], next_action[1])

		# end turn
		# self.weights = self.genNewWeights(wrld)
		self.writeWeights()

	def nearWall(self, wrld):
		pos = self.x, self.y  # wrld.me(self).x, wrld.me(self).y
		exit_pos = wrld.exitcell
		dx = exit_pos[0] - pos[0]
		dy = exit_pos[1] - pos[1]
		if dx < 0:
			dx = -1
		if dx > 0:
			dx = 1
		if dy < 0:
			dy = -1
		if dy > 0:
			dy = 1
		if 0 <= pos[0] + dx < wrld.width() and 0 <= pos[1] + dy < wrld.height():
			if wrld.wall_at(pos[0] + dx, pos[1] + dy):
				return True
		return False

	def readWeights(self):
		try:
			self.weights = [float(line.rstrip('\n')) for line in open('../weights', 'r')]
		except ValueError:
			print(
				'ERROR (ValueError): unexpected newline character encountered, attempted to convert empty string to float')
		if not self.weights:
			self.weights = [10, -10, 10]

	def writeWeights(self):
		with open('../weights', 'w') as f:
			try:
				f.writelines(['%s\n' % weight for weight in self.weights])
			except TypeError:
				print('ERROR (TypeError): weights is empty (is None)')

	def genNewWeights(self, wrld):
		pass

	def bestAction(self, wrld):
		q_vals = dict()
		best_action = 0, 0
		best_qval = -1e9999999999999999

		for action in self.getValidMoves((self.x, self.y), wrld):
			"""Features for qval:
			- Distance to exit cell (1 when closest, 0 furthest --> positive weight)
			- Is the cell an explosion in the next turn (1 if yes, 0 otherwise --> negative weight)
			- Distance to monster, only if it is less than 4 (higher value if closer away --> negative weight)
			"""

			next_position = (self.x + action[0], self.y + action[1])
			q_vals[action] = self.weights[0] * self.distanceToExit(next_position, wrld) + \
			                 self.weights[1] * self.explosionNextTurn(action, wrld) + \
			                 self.weights[2] * self.distanceToMonster(action, wrld)
			print('\nAction:', action, 'has qval:', q_vals[action])
			print('distanceToExit:', self.distanceToExit(next_position, wrld))
			print('explosionNextTurn:', self.explosionNextTurn(action, wrld))
			print('Distance to monster:', self.distanceToMonster(action, wrld))

		for key in q_vals.keys():
			if q_vals[key] > best_qval:
				best_action = key
				best_qval = q_vals[key]

		print('Are we near a wall:', self.nearWall(wrld))
		if self.nearWall(wrld):
			self.place_bomb()

		return best_action[0], best_action[1]

	def distance(self, x, y):
		return abs(x[1] - y[1]) + abs(x[0] - y[0])

	def distanceToExit(self, pos, wrld):
		astar_distance_to_exit = self.astar(wrld, pos, wrld.exitcell)
		if not astar_distance_to_exit:
			return 1 - (self.distance(pos, wrld.exitcell) / self.distance((0, 0), wrld.exitcell))
		else:
			return 1 - (astar_distance_to_exit / self.astar(wrld, (0, 0), wrld.exitcell))

	def predictAggressiveMonsterMove(self, pos, wrld):
		monster_valid_moves = self.getValidMoves(pos, wrld)
		next_move = -1, -1
		shortest_distance = 1e99999
		for move in monster_valid_moves:
			distance = self.astar(wrld, (pos[0] + move[0], pos[1] + move[1]), (self.x, self.y))
			if distance is not None:
				if distance < shortest_distance:
					next_move = move
					shortest_distance = distance
		if next_move is (-1, -1):
			return 0, 0
		else:
			return next_move

	"""monster_moves_randomly:  True if monster is moving randomly
								False if monster is moving towards player when within a range"""

	def distanceToMonster(self, action, wrld):
		# get location of closest monster
		monster_locations = []
		for i in range(wrld.width()):
			for j in range(wrld.height()):
				if wrld.monsters_at(i, j):
					monster_locations.append((i, j))

		# get A* path length for each monster
		monster_found = False
		shortest_path_to_monster = 1e99999
		for location in monster_locations:
			myActualPos = wrld.me(self).x,wrld.me(self).y
			path = self.astar(wrld, (myActualPos[0] + action[0], myActualPos[1] + action[1]), location)
			if path is not None:
				if len(path) < shortest_path_to_monster:
					shortest_path_to_monster = len(path)
					monster_found = True

		if monster_found:
			if len(path) < 5:
				return 1 - len(path) / 4
			else:
				return 1
		else:
			return 1

	def explosionNextTurn(self, move, wrld):
		# future = wrld.next()
		# explosion = future[0].explosion_at(pos[0], pos[1])
		# nextFuture = future[0].next()[0]
		# explosion2 = nextFuture.explosion_at(pos[0],pos[1])
		# if explosion is None or explosion2 is None:
		# 	return False
		# else:
		# 	return True
		character = wrld.me(self)
		startpos = self.x, self.y
		character.x = self.x + move[0]
		character.y = self.y + move[1]
		sooner = wrld.next()
		for e in sooner[1]:
			if e.tpe == 2:
				return True
		if sooner[0].explosion_at(startpos[0] + move[0], startpos[1] + move[1]):
			return True
		future = sooner[0].next()
		for e in future[1]:
			if e.tpe == 2:
				return True
		if future[0].explosion_at(startpos[0] + move[0], startpos[1] + move[1]):
			return True
		return False

	def nextWorldState(self, action, wrld):
		pass

	def getValidMoves(self, pos, wrld):
		valid_moves = []
		for i in [-1, 0, 1]:
			for j in [-1, 0, 1]:
				x_pos = pos[0] + i
				y_pos = pos[1] + j
				if wrld.exit_at(x_pos, y_pos):
					return [(i, j)]
				elif 0 <= x_pos < wrld.width() and 0 <= y_pos < wrld.height():
					if (wrld.empty_at(x_pos, y_pos) or wrld.bomb_at(x_pos, y_pos) or wrld.characters_at(x_pos,
					                                                                                    y_pos)) and not self.explosionNextTurn(
						(x_pos, y_pos), wrld):
						valid_moves.append((i, j))
		return valid_moves

	def getPriority(self, elem):
		return elem[1]

	def astar(self, wrld, start, end):
		cameFrom = {}
		costSoFar = {}
		cameFrom[start] = None
		costSoFar[start] = 0

		front = []
		front.append((start, 0))

		while len(front) != 0:
			front.sort(key=self.getPriority)
			current = front.pop(0)
			# self.set_cell_color(current[0][0], current[0][1], Fore.RED + Back.GREEN)

			if (current[0] == end):
				path = []
				current = current[0]
				while current in cameFrom:
					current = cameFrom[current]
					path.append(current)
				path.pop()
				path.reverse()
				return path

			for neighbor in self.getValidSpotsFrom(current[0], wrld):
				cost = costSoFar[current[0]] + 1
				if neighbor not in costSoFar or cost < costSoFar[neighbor]:
					costSoFar[neighbor] = cost
					pVal = cost + self.distance(neighbor, end)
					front.append((neighbor, pVal))
					cameFrom[neighbor] = current[0]

	def getMoveFromPath(self, path, end):
		if len(path) == 1:
			return end[0] - path[0][0], end[1] - path[0][1]
		move = path[1][0] - path[0][0], path[1][1] - path[0][1]
		return move

	def getValidSpotsFrom(self, position, wrld):
		allmoves = []
		for i in [-1, 0, 1]:
			for j in [-1, 0, 1]:
				x = position[0] + i
				y = position[1] + j

				if (0 <= x < wrld.width() and 0 <= y < wrld.height()):
					if (wrld.empty_at(x, y) or wrld.exit_at(x, y) or wrld.monsters_at(x, y)):
						move = x, y
						allmoves.append(move)
		return allmoves
