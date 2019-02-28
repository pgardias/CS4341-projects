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
	duration_bomb_and_exp = 10 + 2

	# flags
	monster_moves_randomly = False
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

		print('weights:', self.weights)
		next_action = self.bestAction(wrld)
		self.move(next_action[0], next_action[1])

		# end turn
		self.genNewWeights(wrld)
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
			self.weights = [10, -100, 10, -5]

	def writeWeights(self):
		with open('../weights', 'w') as f:
			try:
				f.writelines(['%s\n' % weight for weight in self.weights])
			except TypeError:
				print('ERROR (TypeError): weights is empty (is None)')

	def checkGameOver(self, wrld):
		pass

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
				if wrld.empty_at(i, j) or wrld.characters_at(i, j) or wrld.bomb_at(i, j) or wrld.explosion_at(i, j):
					valid_moves = self.getEmptySpaces((i, j), wrld)
					valid_moves.sort()
					print('checking a cell if its a corner')
					if len(valid_moves) is 4 and (bool(set(valid_moves).intersection(self.top_left)) \
					                              or bool(set(valid_moves).intersection(self.top_right)) \
					                              or bool(set(valid_moves).intersection(self.bot_left)) \
					                              or bool(set(valid_moves).intersection(self.bot_right))):
						print('added a corner:', (i, j))
						self.set_cell_color(i, j, Fore.RED + Back.GREEN)
						self.corner_cells.append((i, j))

		# check for precorners
		for corner in self.corner_cells:
			for move in self.getEmptySpaces(corner, wrld):
				self.precorner_cells.append((corner[0] + move[0], corner[1] + move[1]))

		self.precorner_cells = self.remove_duplicates(self.precorner_cells)

	def remove_duplicates(self, x):
		z = [x[0]]
		for i in range(1, len(x)):
			for y in range(0, i):
				if x[i] == x[y]:
					break
			else:
				z.append(x[i])
		return z

	def genNewWeights(self, wrld):
		pass
		new_weights = []
		# game_over = self.checkGameOver(wrld)

		future = SensedWorld.from_world(wrld)

		current_score = wrld.scores['me']
		next_score = future.next()[0].scores['me']
		reward = next_score - current_score

		next_qval = 0

		delta = (reward + self.gamma * next_qval)  # - qval #(how will this be passed in?)

	# for weight in

	def bestAction(self, wrld):
		q_vals = dict()
		best_action = 0, 0
		best_qval = -1e9999999999999999
		moves = self.getValidMoves((self.x, self.y), wrld)
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
			self.place_bomb()
			if not self.waiting_for_explosion:
				self.waiting_for_explosion = True
				self.turns_until_explosion_ends = self.duration_bomb_and_exp

		if self.distanceToExit((self.x + best_action[0], self.y + best_action[1]), wrld) < self.distanceToExit(
				(self.x, self.y), wrld):
			print("next distance to exit:",
			      self.distanceToExit((self.x + best_action[0], self.y + best_action[1]), wrld))
			print("previous distance to exit:", self.distanceToExit((self.x, self.y), wrld))
			self.place_bomb()
			if not self.waiting_for_explosion:
				self.waiting_for_explosion = True
				self.turns_until_explosion_ends = self.duration_bomb_and_exp

		return best_action[0], best_action[1]

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
			origin = 0, 0
			# print("Astar from origin to exit: ", len(self.astar(wrld, origin, wrld.exitcell)))

			return 1 - (len(astar_distance_to_exit) / self.distance((0, 0), wrld.exitcell))

	def predictAggressiveMonsterMove(self, pos, wrld):
		monster_valid_moves = self.getValidMoves(pos, wrld)
		next_move = 0, 0
		shortest_distance = 1e99999
		for move in monster_valid_moves:
			path = self.astar(wrld, (pos[0] + move[0], pos[1] + move[1]), (self.x, self.y))
			if path is not None:
				distance = len(path)
				if distance < shortest_distance:
					next_move = move
					shortest_distance = distance
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

		# # get A* path length for each monster
		# monster_found = False
		# closestMonster = -1,-1
		# shortest_path_to_monster = 1e99999
		# for location in monster_locations:
		# 	myActualPos = wrld.me(self).x,wrld.me(self).y
		# 	if 0 <= myActualPos[0] + action[0] < wrld.width() and 0 <= myActualPos[1] + action[1] < wrld.height():
		# 		if not wrld.wall_at(myActualPos[0] + action[0], myActualPos[1] + action[1]):
		# 			path = self.astar(wrld, (myActualPos[0] + action[0], myActualPos[1] + action[1]), location)
		# 			if path is not None:
		# 				if len(path) < shortest_path_to_monster:
		# 					shortest_path_to_monster = len(path)
		# 					closestMonster = location[0],location[1]
		# 					monster_found = True
		#
		# ourPos = wrld.me(self).x ,wrld.me(self).y
		# nextPos= ourPos[0] + action[0], ourPos[1] + action[1]
		# # monsterX = ourPos[0] - closestMonster[0]
		# # MonsterY = ourPos[1] - closestMonster[1]
		# # if(monsterX > 0):
		# # 	monsterX = 1
		# # if(monsterX < 0):
		# # 	monsterX = -1
		# # if MonsterY < 0:
		# # 	MonsterY = -1
		# # if MonsterY > 0:
		# # 	MonsterY = 1
		# if(monster_found==True):
		# 	monsterX,MonsterY = self.getMoveFromPath(self.astar(wrld,closestMonster,nextPos),nextPos)
		# 	closestMonster = closestMonster[0] + monsterX, closestMonster[1] + MonsterY
		# 	path = self.astar(wrld, closestMonster, (ourPos[0] + action[0], ourPos[1] + action[1]))
		# if monster_found and path is not None:
		# 	if len(path) < 5 and len(path) > 0:
		# 		return 1 - len(path) / 6
		# 	else:
		# 		return 1
		# else:
		# 	return 1

		monster_found = False
		shortest_distance_to_monster = 1e99999
		for monster_pos in monster_locations:
			# if self.monster_moves_randomly:
			# print('TODO: random monster movements')
			# TODO predict next turn move of monster by averaging distance of all moves of the monster
			# else:
			monster_move = self.predictAggressiveMonsterMove(monster_pos, wrld)
			oldPos = wrld.me(self).x, wrld.me(self).y
			myPos = wrld.me(self).x + action[0], wrld.me(self).y + action[1]
			monPos = monster_pos[0] + monster_move[0], monster_pos[1] + monster_move[1]

			path = self.astar(wrld, myPos, monPos)
			if path is not None:
				monster_found = True
				if len(path) < shortest_distance_to_monster:
					shortest_distance_to_monster = len(path)

		if monster_found:
			if shortest_distance_to_monster <= self.max_distance_to_detect_monster:
				print('MONSTER FOUND WITHIN DISTANCE WE CARE ABOUT')
				print('shortest distance to monster:', shortest_distance_to_monster)
				return 1 - shortest_distance_to_monster / self.max_distance_to_detect_monster
			else:
				print('MONSTER FOUND, BUT DISTANCE IS LARGER THAN WE CARE ABOUT')
				return 0
		else:
			print('MONSTER NOT FOUND')
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
		sim = wrld.from_world(wrld)
		character = sim.me(self)
		startpos = self.x, self.y
		character.x = self.x + move[0]
		character.y = self.y + move[1]
		sooner = sim.next()
		for e in sooner[1]:
			if e.tpe == 2:
				return True
		if sooner[0].explosion_at(startpos[0] + move[0], startpos[1] + move[1]) is not None:
			return True
		future = sooner[0].next()
		for e in future[1]:
			if e.tpe == 2:
				return True
		if future[0].explosion_at(startpos[0] + move[0], startpos[1] + move[1]) is not None:
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

	def getEmptySpaces(self, pos, wrld):
		valid_moves = []
		for i in [-1, 0, 1]:
			for j in [-1, 0, 1]:
				x_pos = pos[0] + i
				y_pos = pos[1] + j
				if wrld.exit_at(x_pos, y_pos):
					return [(i, j)]
				elif 0 <= x_pos < wrld.width() and 0 <= y_pos < wrld.height():
					if (wrld.empty_at(x_pos, y_pos) or wrld.bomb_at(x_pos, y_pos) or wrld.characters_at(x_pos, y_pos) \
					    or wrld.explosion_at(x_pos, y_pos)) and not self.explosionNextTurn((x_pos, y_pos), wrld):
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

				if (0 <= x < wrld.width() and 0 <= y < wrld.height()):
					if (wrld.empty_at(x, y) or wrld.exit_at(x, y) or wrld.monsters_at(x, y) or wrld.explosion_at(x,
					                                                                                             y) or wrld.bomb_at(
						x, y)) or wrld.characters_at(x, y) and not wrld.wall_at(x, y):
						move = x, y
						allmoves.append(move)
		return allmoves
