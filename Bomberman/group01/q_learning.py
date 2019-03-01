import math
import os
import sys

sys.path.insert(0, '../bomberman')
from entity import CharacterEntity
from colorama import Fore, Back
from sensed_world import SensedWorld, Event

CHARACTER_WON_GAME = 0x1
CHARACTER_LOST_GAME = 0x2

class Q_Learning(CharacterEntity):
	weights = list()
	weights_file = '../weights/default_weights'
	gamma = 0.9
	learning_rate = 0.2
	corner_cells = list()
	precorner_cells = list()
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
	waiting_for_explosion = False
	sorted_corner_config = False
	init_corners = False
	monster_detected = False

	def __init__(self, name, avatar, x, y, scenario_num, variant_num):
		CharacterEntity.__init__(self, name, avatar, x, y)
		self.scenario_num = scenario_num
		self.variant_num = variant_num

	def do(self, wrld):
		# setup
		self.read_weights()
		if self.waiting_for_explosion and self.turns_until_explosion_ends is 0:
			self.waiting_for_explosion = False
			if not self.sorted_corner_config:
				self.sort_corner_configs()
				self.sorted_corner_config = True
			self.update_corner_values(wrld)
		elif self.waiting_for_explosion:
			self.turns_until_explosion_ends -= 1
		if not self.init_corners:
			self.update_corner_values(wrld)
			self.init_corners = True

		# action
		next_action, qval = self.best_action(False, wrld)
		self.move(next_action[0], next_action[1])

		# end turn
		game_over, cause = self.check_game_over(next_action, wrld)
		if game_over:
			self.gen_new_weights(next_action, qval, True, cause, wrld)
		else:
			self.gen_new_weights(next_action, qval, False, None, wrld)
		self.write_weights()

	def near_wall(self, wrld):
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

	def read_weights(self):
		self.weights_file = '../weights/weights' + str(self.scenario_num) + '_' + str(self.variant_num)
		if os.path.exists(self.weights_file):
			try:
				self.weights = [float(line.rstrip('\n')) for line in open(self.weights_file, 'r')]
			except ValueError:
				print('ERROR (ValueError): unexpected newline character encountered')
		else:
			if not self.weights:
				self.weights = self.weights = [float(line.rstrip('\n')) for line in open('../weights/default_weights', 'r')]

		if self.weights[0] < 0 or self.weights[0] > 100:
			# weight for distance to exit should never be negative
			self.weights[0] = 5

	def write_weights(self):
		with open(self.weights_file, 'w') as f:
			try:
				f.writelines(['%s\n' % weight for weight in self.weights])
			except TypeError:
				print('ERROR (TypeError): weights is empty (is None)')
			f.close()

	def sort_corner_configs(self):
		self.top_left.sort()
		self.top_right.sort()
		self.bot_left.sort()
		self.bot_right.sort()

	def update_corner_values(self, wrld):
		self.corner_cells = list()
		self.precorner_cells = list()
		# check for corners
		for i in range(wrld.width()):
			for j in range(wrld.height()):
				self.set_cell_color(i, j, Back.RESET)
				if wrld.empty_at(i, j) or wrld.characters_at(i, j) is not None or \
						wrld.bomb_at(i, j) is not None or wrld.explosion_at(i, j) is not None:
					valid_moves = self.get_empty_spaces((i, j), wrld)
					valid_moves.sort()
					if len(valid_moves) is 4 and (bool(set(valid_moves).intersection(self.top_left)) \
					                              or bool(set(valid_moves).intersection(self.top_right)) \
					                              or bool(set(valid_moves).intersection(self.bot_left)) \
					                              or bool(set(valid_moves).intersection(self.bot_right))):
						self.set_cell_color(i, j, Back.RED)
						self.corner_cells.append((i, j))

		# check for precorners
		for corner in self.corner_cells:
			for move in self.get_empty_spaces(corner, wrld):
				if move not in self.corner_cells:
					self.set_cell_color(corner[0] + move[0], corner[1] + move[1], Back.MAGENTA)
					self.precorner_cells.append((corner[0] + move[0], corner[1] + move[1]))

		if len(self.precorner_cells) is not 0:
			self.precorner_cells = self.remove_duplicates(self.precorner_cells)

		for valid_move in self.get_empty_spaces(wrld.exitcell, wrld):
			cell = (wrld.exitcell[0] + valid_move[0], wrld.exitcell[1] + valid_move[1])
			if cell in self.precorner_cells:
				self.precorner_cells.remove(cell)
				self.set_cell_color(cell[0], cell[1], Back.RESET)

	def remove_duplicates(self, x):
		z = [x[0]]
		for i in range(1, len(x)):
			for y in range(0, i):
				if x[i] == x[y]:
					break
			else:
				z.append(x[i])
		return z

	def next_world_state(self, action, wrld):
		sensed_world = SensedWorld.from_world(wrld)

		# move character
		if sensed_world.me(self) is not None:
			sensed_world.me(self).move(action[0], action[1])

		# move closest monster
		closest_monster_pos, monster_found = self.find_closest_monster((self.x + action[0], self.y + action[1]), wrld)
		if monster_found:
			monster_move, monster_pos = self.predict_aggressive_monster_move(closest_monster_pos, wrld)
			monster = sensed_world.monsters_at(monster_pos[0], monster_pos[1])
			if monster is not None:
				monster[0].move(monster_move[0], monster_move[1])

		next_world, events = sensed_world.next()
		return next_world, events

	def check_game_over(self, action, wrld):
		next_world, next_world_events = self.next_world_state(action, wrld)
		if next_world.me(self) is None:
			return True, CHARACTER_LOST_GAME
		else:
			for event in next_world_events:
				if event.tpe is Event.CHARACTER_FOUND_EXIT:
					return True, CHARACTER_WON_GAME
				elif event.tpe is Event.BOMB_HIT_CHARACTER or event.tpe is Event.CHARACTER_KILLED_BY_MONSTER:
					return True, CHARACTER_LOST_GAME
			return False, None

	def gen_new_weights(self, action, qval, game_over, game_over_cause, wrld):
		new_weights = list()
		next_position = (self.x + action[0], self.y + action[1])
		next_world, next_world_events = self.next_world_state(action, wrld)
		reward = next_world.scores['me'] - wrld.scores['me']
		if game_over:
			if game_over_cause is CHARACTER_WON_GAME:
				reward = reward + (2 * wrld.time)
			elif game_over_cause is CHARACTER_LOST_GAME:
				reward = reward - 100  # negative score on death to reinforce not walking into monsters

		qval_next_turn = self.best_action(True, next_world)[1]
		if game_over:
			qval_next_turn = 0
		delta = reward + self.gamma * qval_next_turn - qval

		new_weights.append(self.weights[0] + self.learning_rate * delta * self.distance_to_exit(next_position, wrld))
		new_weights.append(self.weights[1] + self.learning_rate * delta * self.explosion_next_turn(next_position, wrld))
		new_weights.append(self.weights[2] + self.learning_rate * delta * self.distance_to_monster(next_position, wrld))
		new_weights.append(self.weights[3] + self.learning_rate * delta * self.move_into_corner(next_position))
		self.weights = new_weights

	def q(self, next_position, wrld):
		f0 = self.distance_to_exit(next_position, wrld)
		f1 = self.explosion_next_turn(next_position, wrld)
		f2 = self.distance_to_monster(next_position, wrld)
		f3 = self.move_into_corner(next_position)
		return self.weights[0] * f0 + self.weights[1] * f1 + self.weights[2] * f2 + self.weights[3] * f3

	def best_action(self, simulating, wrld):
		q_vals = dict()
		best_action = (0, 0)
		best_qval = -math.inf

		if wrld.me(self) is None:
			return (0, 0), 0

		moves = self.get_valid_moves((wrld.me(self).x, wrld.me(self).y), wrld)
		for action in moves:
			next_position = (self.x + action[0], self.y + action[1])
			q_vals[action] = self.q(next_position, wrld)

		for key in q_vals.keys():
			if best_action == (0, 0) and q_vals[key] >= best_qval:
				best_action = key
				best_qval = q_vals[key]
			elif best_action != (0, 0) and q_vals[key] > best_qval:
				best_action = key
				best_qval = q_vals[key]

		if self.near_wall(wrld) and not simulating:
			if not self.waiting_for_explosion:
				self.place_bomb()
				self.waiting_for_explosion = True
				self.turns_until_explosion_ends = self.duration_bomb_and_exp

		next_position = (self.x + best_action[0], self.y + best_action[1])
		if self.distance_to_exit(next_position, wrld) < self.distance_to_exit((self.x, self.y), wrld) and not simulating:
			if not self.waiting_for_explosion:
				self.place_bomb()
				self.waiting_for_explosion = True
				self.turns_until_explosion_ends = self.duration_bomb_and_exp

		return best_action, best_qval

	def move_into_corner(self, pos):
		if self.monster_detected:
			if pos in self.corner_cells:
				return 1
			elif pos in self.precorner_cells:
				if self.scenario_num is 1:
					return 0.5
				else:
					return 0.25
		return 0

	def distance(self, x, y):
		return abs(x[1] - y[1]) + abs(x[0] - y[0])

	def distance_to_exit(self, pos, wrld):
		origin = (abs(wrld.exitcell[0] - wrld.width()), abs(wrld.exitcell[1] - wrld.height()))
		astar_distance_to_exit = self.astar(wrld, pos, wrld.exitcell)
		if not astar_distance_to_exit:
			return 1 - (self.distance(pos, wrld.exitcell) / self.distance(origin, wrld.exitcell))
		else:
			return 1 - (len(astar_distance_to_exit) / self.distance(origin, wrld.exitcell))

	def predict_aggressive_monster_move(self, pos, wrld):
		next_move = (0, 0)
		shortest_distance = math.inf
		for move in self.get_valid_moves(pos, wrld):
			path = self.astar(wrld, (pos[0] + move[0], pos[1] + move[1]), (self.x, self.y))
			if path is not None:
				distance = len(path)
				if distance < shortest_distance:
					next_move = move
					shortest_distance = distance
		return next_move, pos

	def find_closest_monster(self, pos, wrld):
		monster_locations = list()
		for i in range(wrld.width()):
			for j in range(wrld.height()):
				if wrld.monsters_at(i, j) is not None:
					monster_locations.append((i, j))

		monster_found = False
		shortest_distance_to_monster = math.inf
		closest_monster_pos = 0, 0
		for monster_pos in monster_locations:
			monster_move = self.predict_aggressive_monster_move(monster_pos, wrld)[0]
			monster_position = monster_pos[0] + monster_move[0], monster_pos[1] + monster_move[1]
			path = self.astar(wrld, pos, monster_position)
			if path is not None:
				monster_found = True
				if len(path) < shortest_distance_to_monster:
					shortest_distance_to_monster = len(path)
					closest_monster_pos = monster_position
		return closest_monster_pos, monster_found

	def find_all_monsters(self, pos, wrld):
		monster_locations = list()
		for i in range(wrld.width()):
			for j in range(wrld.height()):
				if wrld.monsters_at(i, j) is not None:
					monster_locations.append((i, j))

		monster_found = False
		relevant_monster_locations = list()
		for monster_pos in monster_locations:
			monster_move = self.predict_aggressive_monster_move(monster_pos, wrld)[0]
			monster_position = monster_pos[0] + monster_move[0], monster_pos[1] + monster_move[1]
			path = self.astar(wrld, pos, monster_position)
			if path is not None:
				monster_found = True
				relevant_monster_locations.append(monster_pos)
		return relevant_monster_locations, monster_found

	def distance_to_monster(self, pos, wrld):
		monster_locations, monster_found = self.find_all_monsters(pos, wrld)
		if not monster_found:
			self.monster_detected = False
			return 0
		else:
			self.monster_detected = True
			number_of_monsters = 0
			total_distance = 0
			for monster_location in monster_locations:
				astar_distance = len(self.astar(wrld, pos, monster_location))
				manhattan__distance = self.distance(monster_location, pos)
				average = (astar_distance + manhattan__distance) / 2
				if average <= self.max_distance_to_detect_monster:
					total_distance += average
					number_of_monsters += 1
			if number_of_monsters is not 0:
				average_distance = total_distance / number_of_monsters
				if average_distance < 0:
					return 0
				else:
					return 1 - average_distance / self.max_distance_to_detect_monster
			else:
				return 0

	def explosion_next_turn(self, pos, wrld):
		sim = wrld.from_world(wrld)
		char = sim.me(self)
		char.x = wrld.exitcell[0]
		char.y = wrld.exitcell[1]
		sooner = sim.next()
		if sooner[0].explosion_at(pos[0], pos[1]) is not None:
			return True
		future = sooner[0].next()
		if future[0].explosion_at(pos[0], pos[1]) is not None:
			return True
		return False

	# get character moves
	def get_valid_moves(self, pos, wrld):
		valid_moves = list()
		for i in [-1, 0, 1]:
			for j in [-1, 0, 1]:
				x_pos = pos[0] + i
				y_pos = pos[1] + j
				if 0 <= x_pos < wrld.width() and 0 <= y_pos < wrld.height():
					cond1 = wrld.empty_at(x_pos, y_pos)
					cond2 = wrld.bomb_at(x_pos, y_pos) is not None
					cond3 = wrld.characters_at(x_pos, y_pos) is not None
					cond4 = self.explosion_next_turn((x_pos, y_pos), wrld)
					if wrld.exit_at(x_pos, y_pos):
						return [(i, j)]
					if (cond1 or cond2 or cond3) and not cond4:
						valid_moves.append((i, j))
		return valid_moves

	# get utility moves (e.g. corner configs)
	def get_empty_spaces(self, pos, wrld):
		valid_moves = list()
		for i in [-1, 0, 1]:
			for j in [-1, 0, 1]:
				x_pos = pos[0] + i
				y_pos = pos[1] + j
				if 0 <= x_pos < wrld.width() and 0 <= y_pos < wrld.height():
					cond1 = wrld.empty_at(x_pos, y_pos)
					cond2 = wrld.bomb_at(x_pos, y_pos) is not None
					cond3 = wrld.characters_at(x_pos, y_pos) is not None
					cond4 = wrld.explosion_at(x_pos, y_pos) is not None
					cond5 = wrld.monsters_at(x_pos, y_pos) is not None
					if cond1 or cond2 or cond3 or cond4 or cond5:
						valid_moves.append((i, j))
		return valid_moves

	# get astar moves
	def get_valid_spots_from(self, position, wrld):
		valid_moves = list()
		for i in [-1, 0, 1]:
			for j in [-1, 0, 1]:
				x = position[0] + i
				y = position[1] + j
				if 0 <= x < wrld.width() and 0 <= y < wrld.height():
					cond1 = wrld.empty_at(x, y)
					cond2 = wrld.exit_at(x, y)
					cond3 = wrld.monsters_at(x, y) is not None
					cond4 = wrld.explosion_at(x, y) is not None
					cond5 = wrld.bomb_at(x, y)
					cond6 = wrld.wall_at(x, y)
					if (cond1 or cond2 or cond3 or cond4 or cond5) and not cond6:
						valid_moves.append((x, y))
		return valid_moves

	def get_priority(self, elem):
		return elem[1]

	def astar(self, wrld, start, end):
		came_from = dict()
		cost_so_far = dict()
		came_from[start] = None
		cost_so_far[start] = 0
		front = list()
		front.append((start, 0))

		while len(front) != 0:
			front.sort(key=self.get_priority)
			current = front.pop(0)

			if current[0] == end:
				final = current[0]
				path = list()
				current = current[0]
				while current in came_from:
					current = came_from[current]
					path.append(current)
				path.pop()
				path.reverse()
				if path is None or len(path) == 0:
					path.append(final)
				return path

			for neighbor in self.get_valid_spots_from(current[0], wrld):
				cost = cost_so_far[current[0]] + 1
				if neighbor not in cost_so_far or cost < cost_so_far[neighbor]:
					cost_so_far[neighbor] = cost
					p_val = cost + self.distance(neighbor, end)
					front.append((neighbor, p_val))
					came_from[neighbor] = current[0]

	def get_move_from_path(self, path, end):
		if len(path) == 1:
			return end[0] - path[0][0], end[1] - path[0][1]
		move = path[1][0] - path[0][0], path[1][1] - path[0][1]
		return move
