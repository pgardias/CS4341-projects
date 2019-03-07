# This is necessary to find the main code
import sys
import heapq

sys.path.insert(0, '../bomberman')
# Import necessary stuff
from entity import CharacterEntity
from colorama import Fore, Back


class Expectimax2(CharacterEntity):
	origin = 0, 0
	firstTurn = True

	def distance(self, x, y):
		return abs(x[0] - y[0]) + abs(x[1] - y[1])

	def monsterDead(self, wrld):
		for i in range(wrld.width()):
			for j in range(wrld.height()):
				if (wrld.monsters_at(i, j)):
					return False
		return True

	def cautionBomb(self, wrld):
		sim = wrld.next()[0]
		for i in range(wrld.width()):
			for j in range(wrld.height()):
				if (wrld.explosion_at(i, j) or sim.explosion_at(i, j)):
					return True
				if (wrld.bomb_at(i, j) or sim.bomb_at(i, j)):
					bomb = wrld.bomb_at(i, j)
					futurebomb = sim.bomb_at(i, j)
					if (bomb.timer <= 2 or futurebomb.timer <= 2):
						return True
		return False

	def predictAggressiveMonsterMove(self, pos, wrld):
		monster_valid_moves = self.getValidSpotsFrom(pos, wrld)
		next_move = 0, 0
		shortest_distance = 1e99999
		for move in monster_valid_moves:
			move = move[0] - pos[0], move[1] - pos[1]
			path = self.astar(wrld, (pos[0] + move[0], pos[1] + move[1]), (self.x, self.y))
			if path is not None:
				distance = len(path)
				if distance < shortest_distance:
					next_move = move
					shortest_distance = distance

		return next_move

	def findClosestMonsterPos(self, wrld):
		monsterpos = []
		myPos = wrld.me(self).x, wrld.me(self).y
		for i in range(wrld.width()):
			for j in range(wrld.height()):
				if (wrld.monsters_at(i, j)):
					current = i, j
					monsterpos.append(current)
		if (len(monsterpos) == 0):
			return -100, -100
		closest = monsterpos[0]
		for m in monsterpos:
			if self.distance(myPos, m) < self.distance(closest, myPos):
				closest = m
		return closest

	def explosionNextTurn(self, move, wrld):
		sim = wrld.from_world(wrld)
		character = sim.me(self)
		startpos = self.x, self.y
		if (wrld.explosion_at(startpos[0] + move[0], startpos[1] + move[1])) or wrld.explosion_at(startpos[0], startpos[
			1]) or wrld.bomb_at(startpos[0], startpos[1]):
			return True
		character.move(move[0], move[1])
		sooner = sim.next()
		for e in sooner[1]:
			if e.tpe == 2:
				return True
		if sooner[0].explosion_at(startpos[0] + move[0], startpos[1] + move[1]) is not None or sooner[0].bomb_at(
				startpos[0] + move[0], startpos[1] + move[1]):
			return True
		future = sooner[0].next()
		for e in future[1]:
			if e.tpe == 2:
				return True
		if future[0].explosion_at(startpos[0] + move[0], startpos[1] + move[1]) is not None:
			return True
		return False

	def expectimaxBestMove(self, wrld):
		me = self.x, self.y
		monster = self.findClosestMonsterPos(wrld)
		originaldistance = self.distance(me, monster)
		myMoves = self.getValidSpotsFrom(me, wrld)
		sim = wrld.from_world(wrld)
		bestMoves = {}
		for a in myMoves:
			sum = 0
			monsterMoves = self.getValidSpotsFrom(monster, wrld)
			for m in monsterMoves:
				monstersum = 0
				character = wrld.me(self)
				mcharater = wrld.monsters_at(monster[0], monster[1])[0]
				character.move(a[0], a[1])
				mcharater.move(m[0], m[1])
				nextState = sim.next()[0]
				newMyMoves = self.getValidSpotsFrom(a, nextState)
				for a2 in newMyMoves:
					mySecondsum = 0
					finalMonsterMoves = self.getValidSpotsFrom(m, nextState)
					for m2 in finalMonsterMoves:
						if (self.distance(a2, m2) < originaldistance):
							mySecondsum += 0
						else:
							mySecondsum += 3 * self.distance(a2, m2) + 2 * self.distance(a2,
							                                                             wrld.exitcell) + -10 * self.explosionNextTurn(
								a2, wrld)
					monstersum += mySecondsum
				sum += monstersum
			bestMoves[a] = sum
		bestMove = None
		bestVal = -100000000000
		for val in bestMoves:
			if (bestMoves[val] > bestVal):
				bestVal = bestMoves[val]
				bestMove = val
		return bestMove[0] - me[0], bestMove[1] - me[1]

	def getValidSpotsFrom(self, position, wrld):
		allmoves = []
		for i in [-1, 0, 1]:
			for j in [-1, 0, 1]:
				x = position[0] + i
				y = position[1] + j
				if (0 <= x < wrld.width() and 0 <= y < wrld.height()):
					if (wrld.empty_at(x, y) or wrld.exit_at(x, y) or wrld.monsters_at(x, y) or wrld.characters_at(x,
					                                                                                              y) or wrld.bomb_at(
							x, y)):
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
				move = current[0]
				path = []
				current = current[0]
				while current in cameFrom:
					current = cameFrom[current]
					path.append(current)
				path.pop()
				path.reverse()
				if len(path) == 0:
					return [move]
				return path
			for neighbor in self.getValidSpotsFrom(current[0], wrld):
				cost = costSoFar[current[0]] + 1
				if neighbor not in costSoFar or cost < costSoFar[neighbor]:
					costSoFar[neighbor] = cost
					pVal = cost + self.distance(neighbor, end)
					front.append((neighbor, pVal))
					cameFrom[neighbor] = current[0]

	def getValidSpotsRespectBomb(self, position, wrld):
		allmoves = []
		for i in [-1, 0, 1]:
			for j in [-1, 0, 1]:
				x = position[0] + i
				y = position[1] + j
				if (0 <= x < wrld.width() and 0 <= y < wrld.height()):
					if (wrld.empty_at(x, y) or wrld.exit_at(x, y) or wrld.monsters_at(x, y) or wrld.characters_at(x,
					                                                                                              y) or wrld.bomb_at(
							x, y) or wrld.explosion_at(x, y)):
						move = x, y
						allmoves.append(move)
		return allmoves

	def bombastar(self, wrld, start, end):
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
				move = current[0]
				path = []
				current = current[0]
				while current in cameFrom:
					current = cameFrom[current]
					path.append(current)
				path.pop()
				path.reverse()
				if len(path) == 0:
					return [move]
				return path
			for neighbor in self.getValidSpotsRespectBomb(current[0], wrld):
				cost = costSoFar[current[0]] + 1
				if neighbor not in costSoFar or cost < costSoFar[neighbor]:
					costSoFar[neighbor] = cost
					pVal = cost + self.distance(neighbor, end)
					front.append((neighbor, pVal))
					cameFrom[neighbor] = current[0]

	def getMoveFromPath(self, path, end):
		if path is None:
			return -1, -1
		if len(path) == 1:
			return end[0] - path[0][0], end[1] - path[0][1]
		move = path[1][0] - path[0][0], path[1][1] - path[0][1]
		return move

	def nearExplosion(self, wrld):
		for i in [-1, 0, 1]:
			for j in [-1, 0, 1]:
				if (wrld.explosion_at(self.x - i, self.y - j)):
					return True
		return False

	def do(self, wrld):
		# Your code here
		if (self.firstTurn):
			self.origin = self.x, self.y
			self.firstTurn = False
		me = self.x, self.y
		m = self.findClosestMonsterPos(wrld)
		agressive = self.predictAggressiveMonsterMove(m, wrld)
		sim = wrld.from_world(wrld)
		monster = m[0] + agressive[0], m[1] + agressive[1]
		move = None
		monsterDistance = self.astar(wrld, me, monster)
		if (monsterDistance is not None):
			if (len(self.astar(wrld, me, monster)) <= 2) and monster[1] >= me[
				1]:  # and not (monster[0] <= me[0] and monster[1] <= me[1]):
				move = self.expectimaxBestMove(sim)
				if (move == 0, 0):
					if (self.nearExplosion(wrld)):
						safePath = self.bombastar(wrld, me, self.origin)
						if safePath is not None:
							move = self.getMoveFromPath(self.bombastar(wrld, me, self.origin), self.origin)
						else:
							move = 0, 0
					else:
						move = self.getMoveFromPath(self.astar(wrld, me, self.origin), self.origin)
			else:
				end = wrld.exitcell
				move = self.getMoveFromPath(self.astar(wrld, me, end), end)
		else:
			end = wrld.exitcell
			move = self.getMoveFromPath(self.astar(wrld, me, end), end)

		self.move(move[0], move[1])
		hell = wrld.from_world(wrld).next()[0]
		if (self.explosionNextTurn(move, wrld) or self.cautionBomb(hell)):
			move = self.expectimaxBestMove(sim)
		newme = me[0] + move[0], me[1] + move[1]
		if self.distance(me, wrld.exitcell) < self.distance(newme, wrld.exitcell) and not self.monsterDead(
				wrld) and monsterDistance is not None:
			if (len(monsterDistance) <= 1):
				self.place_bomb()
		self.move(move[0], move[1])
