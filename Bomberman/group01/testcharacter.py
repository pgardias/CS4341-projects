import sys

sys.path.insert(0, '../bomberman')
from entity import CharacterEntity
from colorama import Fore, Back
from sensed_world import SensedWorld
from events import Event

gamma = 0.9

class TestCharacter(CharacterEntity):
	weights = []
	learning_rate = 0.2

	def do(self, wrld):
		self.readWeights()
		print(self.weights)
		next_action = self.bestAction(wrld)
		self.move(next_action[0], next_action[1])
		self.writeWeights()

	def nearWall(self,wrld):
		myPos = wrld.me(self).x,wrld.me(self).y
		exitPos = wrld.exitcell
		dx = exitPos[0]-myPos[0]
		dy = exitPos[1]-myPos[1]
		if (dx < 0):
			dx = -1
		if (dx > 0):
			dx = 1
		if (dy < 0):
			dy = -1
		if (dy > 0):
			dy = 1
		if(0 <= myPos[0]+dx < wrld.width() and 0 <= myPos[1]+dy < wrld.height()):
			if(wrld.wall_at(myPos[0]+dx, myPos[1]+dy)):
				return True
		return False

	def readWeights(self):
		self.weights = [float(line.rstrip('\n')) for line in open('../weights', 'r')]
		if not self.weights:
			self.weights = [10, 10]

	def writeWeights(self):
		with open('../weights', 'w') as f:
			f.writelines(['%s\n' % weight for weight in self.weights])

	def bestAction(self, wrld):
		q_vals = dict()
		best_action = 0, 0
		best_qval = -1e9999999999999999

		for action in self.getValidMoves(wrld):
			"""Features for qval:
			- Distance to exit cell (1 when closest, 0 furthest)
			- Is the cell an explosion in the next turn (1 if no, 0 is there is)
			"""

			next_position = (self.x + action[0], self.y + action[1])
			q_vals[action] = self.weights[0] * self.distanceToExit(next_position, wrld) + \
			                 self.weights[1] * self.explosionNextTurn(action, wrld)
			print('Action:', action, 'has qval:', q_vals[action])
			print('distanceToExit:', self.distanceToExit(next_position, wrld))
			print('explosionNextTurn:', self.explosionNextTurn(action, wrld))

		for key in q_vals.keys():
			if q_vals[key] > best_qval:
				best_action = key
				best_qval = q_vals[key]

		if(self.nearWall(wrld)):
			self.place_bomb()

		return (best_action[0], best_action[1])

	def distance(self, x, y):
		return abs(x[1] - y[1]) + abs(x[0] - y[0])

	def distanceToExit(self, pos, wrld):
		origin = 0,0

		#return 1 - (self.astar(wrld,pos,wrld.exitcell)/self.astar(wrld,origin,wrld.exitcell))
		return 1 - (self.distance(pos, wrld.exitcell) / self.distance((0, 0), wrld.exitcell))

	def distanceToMonster(self, wrld):
		# get location of closest monster
		monster_locations = []
		for i in range(wrld.width()):
			for j in range(wrld.height()):
				if wrld.monster_at((i, j)):
					monster_locations.append((i, j))

		# get A* path length for each monster
		monster_found = False
		shortest_path_to_monster = 1e99999
		for location in monster_locations:
			path = self.astar(wrld, (self.x, self.y), location)
			if path is not None:
				if len(path) < shortest_path_to_monster:
					shortest_path_to_monster = len(path)
					monster_found = True

		if monster_found:
			if len(path) < 4:
				return len(path) / 3
			else:
				return 0
		else:
			return 0

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
		startpos = self.x,self.y
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

	def getValidMoves(self, wrld):
		valid_moves = []
		for i in [-1,0,1]:
			for j in [-1,0,1]:
				x_pos = self.x + i
				y_pos = self.y + j
				if wrld.exit_at(x_pos, y_pos):
					return [(i, j)]
				elif 0 <= x_pos < wrld.width() and 0 <= y_pos < wrld.height():
					if (wrld.empty_at(x_pos, y_pos) or wrld.characters_at(x_pos,y_pos)) and not self.explosionNextTurn((x_pos, y_pos), wrld):
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
			self.set_cell_color(current[0][0], current[0][1], Fore.RED + Back.GREEN)

			if current[0] == end:
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

	def getValidSpotsFrom(self, start, wrld):
		valid_moves = []
		for i in [-1,0,1]:
			for j in [-1,0,1]:
				pos = (start[0] + i, start[1] + j)
				if(0 <= pos[0] < wrld.width() and 0 <= pos[1] < wrld.height()):
					if wrld.empty_at(pos[0],pos[1]) or wrld.monsters_at(pos[0],pos[1]) or wrld.exit_at(pos[0],pos[1]) or wrld.characters_at(pos[0],pos[1]):
						valid_moves.append((i, j))
		return valid_moves

