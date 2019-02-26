import sys

sys.path.insert(0, '../bomberman')
from entity import CharacterEntity
from colorama import Fore, Back
from sensed_world import SensedWorld

gamma = 0.9
weights = []
max_depth: int = 2


class TestCharacter(CharacterEntity):
	w = []
	learningRate = .4
	bombPlaced = False
	bombtimer = 11
	turn_after_explosion = False
	current_best = 0

	def readWeights(self):
		self.w = [float(line.rstrip('\n')) for line in open('../weights', 'r')]
		if not self.w:
			self.w = [.5, .2, 10]

	def writeWeights(self):
		with open('../weights', 'w') as f:
			f.writelines(['%s\n' % weight for weight in self.w])

	def getValidSpotsFrom(self, position, wrld):
		allmoves = []
		for i in [-1, 0, 1]:
			for j in [-1, 0, 1]:
				x = position[0] + i
				y = position[1] + j

				if (0 <= x < wrld.width() and 0 <= y < wrld.height()):
					if (wrld.empty_at(x, y) or wrld.exit_at(x, y)):
						move = i, j
						allmoves.append(move)

		return allmoves

	def distance(self, x, y):
		return abs(x[1] - y[1]) + abs(x[0] - y[0])

	def distanceToExit(self, nextpos, wrld):
		exit = wrld.exitcell
		originpos = 0, 0
		normalized = self.distance(nextpos, exit) / self.distance(originpos, exit)
		return 1 - normalized

	def distanceToMonster(self, nextpos, wrld):
		monsterpos = -1, -1
		for i in range(wrld.width()):
			for j in range(wrld.height()):
				if wrld.monsters_at(i, j):
					monsterpos = i, j
		originpos = 0, 0
		maxpos = wrld.width(), wrld.height()
		normalized = self.distance(nextpos, monsterpos) / self.distance(originpos, maxpos)
		return 1 - normalized

	def notInExplosion(self, wrld, move):
		bombLocation = -1, -1
		for i in range(wrld.width()):
			for j in range(wrld.height()):
				if (wrld.bomb_at(i, j)):
					bombLocation = i, j

		if (self.x + move[0] == bombLocation[0] or self.y + move[1] == bombLocation[1]):
			return False
		return True

	# future = wrld.next()[0].next()
	# events = future[1]
	# for e in events:
	#     if e.tpe==2:
	#         return 0
	# return 1

	def isStuck(self, wrld):
		for j in range(wrld.height()):
			if (wrld.wall_at(0, j)):
				for i in range(wrld.width()):
					if not wrld.wall_at(i, j):
						return False
				return True
		return False

	def genNewWeights(self, action, qval, wrld):
		new_weights = []
		feature = 0
		for weight in self.w:
			new_weight = 0
			if feature is 0:
				new_weight = weight + self.learningRate * (
						wrld.scores['me'] + gamma * qval - self.current_best) * self.distanceToExit(action, wrld)
			elif feature is 1:
				new_weight = weight + self.learningRate * (
						wrld.scores['me'] + gamma * qval - self.current_best) * self.distanceToMonster(action, wrld)
			elif feature is 2:
				new_weight = weight + self.learningRate * (
						wrld.scores['me'] + gamma * qval - self.current_best) * self.notInExplosion(action, wrld)
			else:
				print('THIS SHOULD NEVER OCCUR')
			new_weights.append(new_weight)
		self.current_best = qval
		self.w = new_weights

	def bestAction(self, wrld):
		qVals = {}
		bestaction = None
		best = -10000
		currentpos = self.x, self.y
		actions = self.getValidSpotsFrom(currentpos, wrld)
		for a in actions:
			qval = self.w[0] * self.distanceToExit(a, wrld) + self.w[1] * self.distanceToMonster(a, wrld) + self.w[
				2] * self.notInExplosion(wrld, a)
			qVals[a] = qval
		for val in qVals:
			if (qVals[val] > best):
				bestaction = val
				best = qVals[val]
		noMove = currentpos
		newMove = currentpos[0] + bestaction[0], currentpos[1] + bestaction[1]
		if (self.distance(newMove, wrld.exitcell) >= self.distance(noMove, wrld.exitcell) and self.bombPlaced == False):
			if self.turn_after_explosion:
				self.turn_after_explosion = False
			else:
				# self.genNewWeights(noMove, best, wrld)
				return 'b'  # bomb action
		# self.genNewWeights(currentpos, best, wrld)
		return bestaction

	def do(self, wrld):
		self.readWeights()
		print('weights:', self.w)
		print(self.x, ',  ', self.y)
		if (self.bombPlaced):
			self.bombtimer -= 1
		nextAction = self.bestAction(wrld)
		print("NEXT ACTION:", nextAction)
		if (self.bombtimer == 0):
			self.bombPlaced = False
			self.bombtimer = 11
			self.turn_after_explosion = True
		elif (nextAction == 'b'):
			self.place_bomb()
			self.bombPlaced = True
		else:
			self.move(nextAction[0], nextAction[1])
		self.writeWeights()
