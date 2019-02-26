import sys

sys.path.insert(0, '../bomberman')
from entity import CharacterEntity
from colorama import Fore, Back
from sensed_world import SensedWorld
from events import Event

gamma = 0.9
weights = []
max_depth: int = 2


class TestCharacter(CharacterEntity):
	w = []
	learningRate = .4
	bombPlaced = False
	bombtimer = 11
	turn_after_explosion = False
	first_turn_flag = True
	last_score = -5000  # starting score

	def readWeights(self):
		self.w = [float(line.rstrip('\n')) for line in open('../weights', 'r')]
		if not self.w:
			self.w = [10000, -1000, -10000]

	def writeWeights(self):
		with open('../weights', 'w') as f:
			f.writelines(['%s\n' % weight for weight in self.w])

	def isLastTurn(self, wrld):
		sensed_world = SensedWorld.from_world(wrld)
		for e in sensed_world.next()[1]:
			if e.tpe is Event.BOMB_HIT_CHARACTER or Event.CHARACTER_FOUND_EXIT or Event.CHARACTER_KILLED_BY_MONSTER:
				return True
		return False

	def getValidSpotsFrom(self, position, wrld):
		allmoves = []
		for i in [-1, 0, 1]:
			for j in [-1, 0, 1]:
				x = position[0] + i
				y = position[1] + j

				if 0 <= x < wrld.width() and 0 <= y < wrld.height():
					if wrld.empty_at(x, y) or wrld.exit_at(x, y) or wrld.explosion_at(x, y):
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
		if monsterpos is (-1, -1):
			return 0
		originpos = 0, 0
		maxpos = wrld.width(), wrld.height()
		normalized = self.distance(nextpos, monsterpos) / self.distance(originpos, maxpos)
		return 1 - normalized

	def inExplosion(self, wrld, move):
		character = wrld.me(self)
		character.move(move[0], move[1])
		sooner = wrld.next()
		for e in sooner[1]:
			if e.tpe == 2:
				return 1
		if sooner[0].explosion_at(self.x + move[0], self.y + move[1]):
			return 1
		future = sooner[0].next()
		for e in future[1]:
			if e.tpe == 2:
				return 1
		if future[0].explosion_at(self.x + move[0], self.y + move[1]):
			return 1
		return 0

	def isStuck(self, wrld):
		for j in range(wrld.height()):
			if wrld.wall_at(0, j):
				for i in range(wrld.width()):
					if not wrld.wall_at(i, j):
						return False
				return True
		return False

	# need best qval for next turn, reward (difference in score from last turn and current turn), subtract current qval,
	# make qval function, gennewweights to the first line of do, not bestAction, detect start/end of game, write weights to
	# file

	def genNewWeights(self, action, qval, wrld):
		new_weights = []
		feature = 0
		sensed_wrld = SensedWorld.from_world(wrld)
		score = (sensed_wrld.next()[0]).scores['me']
		current_score = wrld.scores['me']

		# if sensed_world has the new position then all you have to do is run bestAction and get the max qVal for this new world
		# then plug that into the equation as Q'(s',a') and then subtract off the Qvalue that the action we just took gave us

		next_qval = self.bestAction(sensed_wrld)[1]

		for weight in self.w:
			new_weight = 0
			if feature is 0:
				new_weight = weight + self.learningRate * ((self.last_score - current_score) + gamma * next_qval - qval) * self.distanceToExit(action, wrld)
				print("Weight of distanceToExit: ", self.distanceToExit(action, wrld))
			elif feature is 1:
				new_weight = weight + self.learningRate * ((self.last_score - current_score) + gamma * next_qval - qval) * self.distanceToMonster(action, wrld)
				print("Weight of distanceToMonster: ", self.distanceToMonster(action, wrld))
			elif feature is 2:
				new_weight = weight + self.learningRate * ((self.last_score - current_score) + gamma * next_qval - qval) * self.inExplosion(wrld, action)
				print("Weight of inExplosion: ", self.inExplosion(wrld, action))
			else:
				print('THIS SHOULD NEVER OCCUR')
			feature += 1
			new_weights.append(new_weight)
		self.last_score = current_score
		self.w = new_weights

	def bestAction(self, wrld):
		q_vals = {}
		bestaction = 0, 0
		best = -1e99999999999
		currentpos = self.x, self.y
		actions = self.getValidSpotsFrom(currentpos, wrld)
		for a in actions:
			q_vals[a] = self.w[0] * self.distanceToExit(a, wrld) + self.w[1] * self.distanceToMonster(a, wrld) + self.w[
				2] * self.inExplosion(wrld, a)
		for val in q_vals:
			if q_vals[val] > best:
				bestaction = val
				best = q_vals[val]
		new_move = currentpos[0] + bestaction[0], currentpos[1] + bestaction[1]
		if self.distance(new_move, wrld.exitcell) >= self.distance(currentpos, wrld.exitcell) and not self.bombPlaced:
			if self.turn_after_explosion:
				self.turn_after_explosion = False
			else:
				return 'b', best  # bomb action
		return bestaction, best

	def do(self, wrld):
		if self.first_turn_flag:
			self.readWeights()
			self.first_turn_flag = False
		print('weights:', self.w)
		print(self.x, ',  ', self.y)

		if self.bombPlaced:
			self.bombtimer -= 1

		nextAction, qval = self.bestAction(wrld)
		print("NEXT ACTION:", nextAction)
		print("NEXT ACTION QVAL:", qval)

		if self.bombtimer == 0:
			self.bombPlaced = False
			self.bombtimer = 11
			self.turn_after_explosion = True
		elif nextAction == 'b':
			self.place_bomb()
			self.move(0, 0)
			self.bombPlaced = True
		else:
			self.move(nextAction[0], nextAction[1])

		# Update weights
		if nextAction is 'b':
			nextAction = (0, 0)
		self.genNewWeights(tuple(map(sum, zip((self.x, self.y), nextAction))), qval, wrld)

		if self.isLastTurn(wrld):
			self.writeWeights()
