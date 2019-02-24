import sys
sys.path.insert(0, '../bomberman')
from entity import CharacterEntity
from colorama import Fore, Back

class AStar(CharacterEntity):
	def distance(self, x, y):
		return abs(x[0] - y[0]) + abs(x[1] - y[1])

	def getValidSpotsFrom(self, position, wrld):
		allmoves = []
		for i in [-1, 0, 1]:
			for j in [-1, 0, 1]:
				x = position[0] + i
				y = position[1] + j

				if (0 <= x < wrld.width() and 0 <= y < wrld.height()):
					if (wrld.empty_at(x, y) or wrld.exit_at(x, y)):
						move = x, y
						allmoves.append(move)

		return allmoves

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
