import sys

sys.path.insert(0, '../bomberman')
from entity import CharacterEntity
from colorama import Fore, Back
from sensed_world import SensedWorld, Event


class TestCharacter(CharacterEntity):
	weights = []
	gamma = 0.9
	learning_rate = 0.2
	corner_cells = []
	precorner_cells = []
	turns_until_explosion_ends = 0

	# corner valid move configurations
	top_left = [(0, 0), (1, 0), (0, 1), (1, 1)]
	top_right = [(0, 0), (-1, 0), (0, 1), (-1, 1)]
	bot_left = [(0, 0), (1, 0), (0, -1), (1, -1)]
	bot_right = [(0, 0), (-1, 0), (0, -1), (-1, -1)]

	# config values
	max_distance_to_detect_monster = 6
	duration_bomb_and_exp = 10 + 2 + 1

	# flags
	waiting_for_explosion = False
	sorted_corner_config = False
	init_corners = False

	def do(self, wrld):
		# setup
		self.readWeights()
		print('waiting for explosion:', self.waiting_for_explosion)
		print('turns until explosion:', self.turns_until_explosion_ends)
		print('sorted_corner_config:', self.sorted_corner_config)
		if self.waiting_for_explosion and self.turns_until_explosion_ends is 0:
			self.waiting_for_explosion = False
			if not self.sorted_corner_config:
				self.sortCornerConfigurations()
				self.sorted_corner_config = True
			self.updateCornerValues(wrld)
		elif self.waiting_for_explosion:
			self.turns_until_explosion_ends -= 1
		if not self.init_corners:
			self.updateCornerValues(wrld)
			self.init_corners = True

		# action
		print('weights:', self.weights)
		next_action, qval = self.bestAction(wrld)
		self.move(next_action[0], next_action[1])

		# end turn
		self.genNewWeights(next_action, qval, False, wrld)
		if self.checkGameOver(next_action, wrld):
			self.genNewWeights(next_action, qval, True, wrld)
		self.writeWeights()

	def nearWall(self, wrld):
		pos = wrld.me(self).x, wrld.me(self).y
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
			self.weights = [10, -100, 10, -5]

	def writeWeights(self):
		with open('../weights', 'w') as f:
			try:
				f.writelines(['%s\n' % weight for weight in self.weights])
			except TypeError:
				print('ERROR (TypeError): weights is empty (is None)')

	def sortCornerConfigurations(self):
		self.top_left.sort()
		self.top_right.sort()
		self.bot_left.sort()
		self.bot_right.sort()

	def updateCornerValues(self, wrld):
		self.corner_cells = []
		self.precorner_cells = []
		# check for corners
		for i in range(wrld.width()):
			for j in range(wrld.height()):
				if wrld.empty_at(i, j) or wrld.characters_at(i, j) is not None or \
						wrld.bomb_at(i, j) is not None or wrld.explosion_at(i, j) is not None:
					valid_moves = self.getEmptySpaces((i, j), wrld)
					valid_moves.sort()
					if len(valid_moves) is 4 and (bool(set(valid_moves).intersection(self.top_left))
					                              or bool(set(valid_moves).intersection(self.top_right))
					                              or bool(set(valid_moves).intersection(self.bot_left))
					                              or bool(set(valid_moves).intersection(self.bot_right))):
						self.set_cell_color(i, j, Fore.RED + Back.RED)
						self.corner_cells.append((i, j))

		# check for precorners
		for corner in self.corner_cells:
			for move in self.getEmptySpaces(corner, wrld):
				if move not in self.corner_cells:
					self.set_cell_color(corner[0] + move[0], corner[1] + move[1], Fore.MAGENTA + Back.MAGENTA)
					self.precorner_cells.append((corner[0] + move[0], corner[1] + move[1]))

		self.precorner_cells = self.remove_duplicates(self.precorner_cells)
		for valid_move in self.getValidMoves(wrld.exitcell, wrld):
			cell = (wrld.exitcell[0] + valid_move[0], wrld.exitcell[1] + valid_move[1])
			if cell in self.precorner_cells:
				self.precorner_cells.remove(cell)

	def remove_duplicates(self, x):
		z = [x[0]]
		for i in range(1, len(x)):
			for y in range(0, i):
				if x[i] == x[y]:
					break
			else:
				z.append(x[i])
		return z

	def nextWorldState(self, action, wrld):
		sensed_world = SensedWorld.from_world(wrld)

		# move character
		# sensed_world.me(self).move(action[0], action[1]) # TODO

		# move closest monster
		closest_monster_pos, monster_found = self.findClosestMonster((self.x + action[0], self.y + action[1]), wrld)
		if monster_found:
			monster_move, monster_pos = self.predictAggressiveMonsterMove(closest_monster_pos, wrld)
			monster = sensed_world.monsters_at(monster_pos[0], monster_pos[1])
			print('MONSTER:', monster)
			if monster is not None:
				monster[0].move(monster_move[0], monster_move[1])
			else:
				print('EXPECTED TO FIND MONSTER AT', monster_pos)

		next_world, events = sensed_world.next()
		return next_world, events

	def checkGameOver(self, action, wrld):
		next_world, next_world_events = self.nextWorldState(action, wrld)
		if next_world.me(self) is None:
			return True
		elif Event.BOMB_HIT_CHARACTER in next_world_events or Event.CHARACTER_FOUND_EXIT in next_world_events or \
			Event.CHARACTER_KILLED_BY_MONSTER in next_world_events:
			return True
		else:
			return False

	def genNewWeights(self, action, qval, game_over, wrld):
		new_weights = []
		next_position = (self.x + action[0], self.y + action[1])
		next_world, next_world_events = self.nextWorldState(action, wrld)
		if game_over:
			next_world, next_world_events = self.nextWorldState(action, wrld)

		reward = next_world.scores['me'] - wrld.scores['me']
		qval_next_turn = self.bestAction(next_world)[1]
		if self.checkGameOver(action, next_world):
			qval_next_turn = 0
		print('reward:', reward, 'qval_next_turn:', qval_next_turn, 'qval:', qval)
		delta = reward + self.gamma * qval_next_turn - qval
		print('delta:', delta)

		new_weights.append(self.weights[0] + self.learning_rate * delta * self.distanceToExit(next_position, wrld))
		new_weights.append(self.weights[1] + self.learning_rate * delta * self.explosionNextTurn(action, wrld))
		new_weights.append(self.weights[2] + self.learning_rate * delta * self.distanceToMonster(action, wrld))
		new_weights.append(self.weights[3] + self.learning_rate * delta * self.moveIntoCorner(next_position))
		print('old weights:', self.weights)
		print('new weights:', new_weights)
		self.weights = new_weights

	def bestAction(self, wrld):
		# TODO: simulate flag for bestaction that does not place bombs
		q_vals = dict()
		best_action = (0, 0)
		best_qval = -1e9999999999999999

		if wrld.me(self) is None:
			return (0, 0), 0

		moves = self.getValidMoves((wrld.me(self).x, wrld.me(self).y), wrld)
		if len(moves) == 1:
			return moves[0]
		for action in moves:
			"""Features for qval:
			- Distance to exit cell (1 when closest, 0 furthest --> positive weight)
			- Is the cell an explosion in the next turn (1 if yes, 0 otherwise --> negative weight)
			- Distance to monster, only if it is less than 4 (higher value if closer away --> negative weight)
			- Move places us in a corner or pre-corner cell (higher value if pre-corner and even higher if corner --> negative weight)
			"""

			next_position = (self.x + action[0], self.y + action[1])
			q_vals[action] = self.weights[0] * self.distanceToExit(next_position, wrld) + \
			                 self.weights[1] * self.explosionNextTurn(action, wrld) + \
			                 self.weights[2] * self.distanceToMonster(action, wrld) + \
			                 self.weights[3] * self.moveIntoCorner(next_position)
			print('\nAction:', action, 'has qval:', q_vals[action])
			print('distanceToExit:', self.distanceToExit(next_position, wrld))
			print('explosionNextTurn:', self.explosionNextTurn(action, wrld))
			print('Distance to monster:', self.distanceToMonster(action, wrld))
			print('Corner (1) or precorner (0.5) of next action', next_position, ':',
			      self.moveIntoCorner(next_position))
			print('corners:', self.corner_cells)
			print('precorners:', self.precorner_cells)

		for key in q_vals.keys():
			if q_vals[key] > best_qval:
				best_action = key
				best_qval = q_vals[key]

		print('Are we near a wall:', self.nearWall(wrld))
		if self.nearWall(wrld):
			if not self.waiting_for_explosion:
				self.place_bomb()
				self.waiting_for_explosion = True
				self.turns_until_explosion_ends = self.duration_bomb_and_exp

		if self.distanceToExit((self.x + best_action[0], self.y + best_action[1]), wrld) < self.distanceToExit(
				(self.x, self.y), wrld):
			print("next distance to exit:",
			      self.distanceToExit((self.x + best_action[0], self.y + best_action[1]), wrld))
			print("previous distance to exit:", self.distanceToExit((self.x, self.y), wrld))
			if not self.waiting_for_explosion:
				self.place_bomb()
				self.waiting_for_explosion = True
				self.turns_until_explosion_ends = self.duration_bomb_and_exp

		print('best action:', best_action, 'best qval:', best_qval)
		return best_action, best_qval

	def moveIntoCorner(self, pos):
		if pos in self.corner_cells:
			return 1
		elif pos in self.precorner_cells:
			return 0.5
		else:
			return 0

	def distance(self, x, y):
		return abs(x[1] - y[1]) + abs(x[0] - y[0])

	def distanceToExit(self, pos, wrld):
		astar_distance_to_exit = self.astar(wrld, pos, wrld.exitcell)
		if not astar_distance_to_exit:
			return 1 - (self.distance(pos, wrld.exitcell) / self.distance((0, 0), wrld.exitcell))
		else:
			# TypeError: unsupported operand type(s) for /: 'list' and 'list'
			print("Astar distance to exit: ", len(astar_distance_to_exit))
			return 1 - (len(astar_distance_to_exit) / self.distance((0, 0), wrld.exitcell))

	def predictAggressiveMonsterMove(self, pos, wrld):
		next_move = (0, 0)
		shortest_distance = 1e99999
		for move in self.getValidMoves(pos, wrld):
			path = self.astar(wrld, (pos[0] + move[0], pos[1] + move[1]), (self.x, self.y))
			if path is not None:
				distance = len(path)
				if distance < shortest_distance:
					next_move = move
					shortest_distance = distance
		return next_move, pos

	def findClosestMonster(self, pos, wrld):
		# get location of closest monster
		monster_locations = []
		for i in range(wrld.width()):
			for j in range(wrld.height()):
				if wrld.monsters_at(i, j) is not None:
					monster_locations.append((i, j))

		monster_found = False
		shortest_distance_to_monster = 1e99999
		closest_monster_pos = 0, 0
		for monster_pos in monster_locations:
			monster_move = self.predictAggressiveMonsterMove(monster_pos, wrld)[0]
			monster_position = monster_pos[0] + monster_move[0], monster_pos[1] + monster_move[1]
			path = self.astar(wrld, pos, monster_position)
			if path is not None:
				monster_found = True
				if len(path) < shortest_distance_to_monster:
					shortest_distance_to_monster = len(path)
					closest_monster_pos = monster_position
		return closest_monster_pos, monster_found

	def distanceToMonster(self, action, wrld):
		pos = wrld.me(self).x + action[0], wrld.me(self).y + action[1]
		closest_monster, monster_found = self.findClosestMonster(pos, wrld)

		if monster_found:
			shortest_distance_to_monster = len(self.astar(wrld, pos, closest_monster))
			if shortest_distance_to_monster <= self.max_distance_to_detect_monster:
				print('MONSTER FOUND WITHIN DISTANCE WE CARE ABOUT')
				print('shortest distance to monster:', shortest_distance_to_monster)
				return shortest_distance_to_monster / self.max_distance_to_detect_monster
			else:
				print('MONSTER FOUND, BUT DISTANCE IS LARGER THAN WE CARE ABOUT')
				return 1
		else:
			print('MONSTER NOT FOUND')
			return 1

	def explosionNextTurn(self, move, wrld):
		sim = wrld.from_world(wrld)
		character = sim.me(self)
		startpos = self.x, self.y
		character.x = self.x + move[0]
		character.y = self.y + move[1]
		sooner = sim.next()
		# for e in sooner[1]:
		# 	if e.tpe == 2:
		# 		return True
		if sooner[0].explosion_at(startpos[0] + move[0], startpos[1] + move[1]) is not None:
			print('explosion detected 1 turn ahead at', (startpos[0] + move[0], startpos[1] + move[1]))
			return True
		future = sooner[0].next()
		# for e in future[1]:
		# 	if e.tpe == 2:
		# 		return True
		if future[0].explosion_at(startpos[0] + move[0], startpos[1] + move[1]) is not None:
			print('explosion detected 2 turn ahead at', (startpos[0] + move[0], startpos[1] + move[1]))
			return True
		return False

	def getValidMoves(self, pos, wrld):
		valid_moves = []
		for i in [-1, 0, 1]:
			for j in [-1, 0, 1]:
				x_pos = pos[0] + i
				y_pos = pos[1] + j
				if 0 <= x_pos < wrld.width() and 0 <= y_pos < wrld.height():
					cond1 = wrld.empty_at(x_pos, y_pos)
					cond2 = wrld.bomb_at(x_pos, y_pos) is not None
					cond3 = wrld.characters_at(x_pos, y_pos) is not None
					cond4 = self.explosionNextTurn((x_pos, y_pos), wrld)
					# if self.distanceToMonster((0, 0), wrld) == 1:
					print('valid move conditions:', cond1, cond2, cond3, cond4, 'for move', (i, j))
					if wrld.exit_at(x_pos, y_pos):
						return [(i, j)]
					if (cond1 or cond2 or cond3) and not cond4:
						print('move considered valid')
						valid_moves.append((i, j))
		return valid_moves

	def getEmptySpaces(self, pos, wrld):
		valid_moves = []
		for i in [-1, 0, 1]:
			for j in [-1, 0, 1]:
				x_pos = pos[0] + i
				y_pos = pos[1] + j
				if 0 <= x_pos < wrld.width() and 0 <= y_pos < wrld.height():
					if (wrld.empty_at(x_pos, y_pos) or wrld.bomb_at(x_pos, y_pos) is not None or wrld.characters_at(
							x_pos, y_pos) is not None \
					    or wrld.explosion_at(x_pos, y_pos) is not None) and not self.explosionNextTurn((x_pos, y_pos),
					                                                                                   wrld):
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
				final = current[0]
				path = []
				current = current[0]
				while current in cameFrom:
					current = cameFrom[current]
					path.append(current)
				path.pop()
				path.reverse()
				if path is None or len(path) == 0:
					path.append(final)
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

				if 0 <= x < wrld.width() and 0 <= y < wrld.height():
					if (wrld.empty_at(x, y) or wrld.exit_at(x, y) or wrld.monsters_at(x, y) is not None \
					    or wrld.explosion_at(x, y) is not None or wrld.bomb_at(x, y)) or \
							wrld.characters_at(x, y) is None and not wrld.wall_at(x, y):
						move = x, y
						allmoves.append(move)
		return allmoves
