import sys

sys.path.insert(0, '../bomberman')
from entity import CharacterEntity
from colorama import Fore, Back
from sensed_world import SensedWorld
from events import Event

gamma = 0.9
weights = []
max_depth: int = 2

class TestCharacter2(CharacterEntity):
	w = []
	learningRate = .8
	bombPlaced = False
	bombtimer = 11
	turn_after_explosion = False
	first_turn_flag = True
	last_score = -5000  # starting score
	turn_after_bomb = 0  # keeps track of turns after placing bomb to reduce number of bomb placements
	prev_qval = 0

	def getAllWalls(self,wrld):
		for i in range(0,wrld.width()):
			for j in range(0,wrld.height()):
				if wrld.wall_at(i,j):
					print("Wall at: ", i, j)

	def readWeights(self):
		self.w = [float(line.rstrip('\n')) for line in open('../weights', 'r')]
		if not self.w:
			self.w = [0, 0, 0, 0]

	def writeWeights(self):
		with open('../weights', 'w') as f:
			f.writelines(['%s\n' % weight for weight in self.w])

	def findMonster(self,wrld):
		monsterpos = -1,-1
		for i in range(0,wrld.width()):
			for j in range(0,wrld.height()):
				if wrld.monsters_at(i, j):
					monsterpos = i, j
		return monsterpos

	def isLastTurn(self, nextpos, wrld):
		mPos = self.findMonster(wrld)
		mondx = (-1 * mPos[0] + (nextpos[0] + self.x))
		mondy = (-1 * mPos[1] + (nextpos[1] + self.y))
		if(mondx < 0):
			mondx = -1
		if(mondx > 0):
			mondx = 1
		if (mondy < 0):
			mondy = -1
		if (mondy > 0):
			mondy = 1
		if (mPos[0] + mondx * 3 == nextpos[0] + self.x and mPos[1] + mondy * 3 == nextpos[1] + self.y) or (mPos[0] + mondx * 2 == nextpos[0] + self.x and mPos[1] + mondy * 2 == nextpos[1] + self.y) or (mPos[0] + mondx * 1 == nextpos[0] + self.x and mPos[1] + mondy * 1 == nextpos[1] + self.y):
			return 1
		return 0

	def getValidSpotsFrom(self, position, wrld):
		allmoves = []
		for i in [-1, 0, 1]:
			for j in [-1, 0, 1]:
				x = position[0] + i
				y = position[1] + j

				if 0 <= x < wrld.width() and 0 <= y < wrld.height():
					if wrld.empty_at(x, y) or wrld.exit_at(x, y) or wrld.explosion_at(x, y) or wrld.bomb_at(x, y) and not wrld.wall_at(x,y):
						move = i, j
						allmoves.append(move)

		return allmoves

	def distance(self, x, y):
		return abs(x[1] - y[1]) + abs(x[0] - y[0])

	def distanceToExit(self, nextpos, wrld):
		exit = wrld.exitcell
		originpos = 0, 0
		normalized = self.distance(nextpos, exit) / self.distance(originpos, exit)
		return normalized

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
		mPos = self.findMonster(wrld)
		mondx = (-1 * mPos[0] + (nextpos[0] + self.x))
		mondy = (-1 * mPos[1] + (nextpos[1] + self.y))
		if (mondx < 0):
			mondx = -1
		if (mondx > 0):
			mondx = 1
		if (mondy < 0):
			mondy = -1
		if (mondy > 0):
			mondy = 1
		monsterpos = monsterpos[0] + mondx, monsterpos[1]+mondy
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

	# using next qval even though he may be dead
	def genNewWeights(self, action, qval, wrld, final_turn):
		new_weights = []
		feature = 0
		sensed_wrld = SensedWorld.from_world(wrld)
		score = (sensed_wrld.next()[0]).scores['me']
		current_score = wrld.scores['me']
		# if sensed_world has the new position then all you have to do is run bestAction and get the max qVal for this new world
		# then plug that into the equation as Q'(s',a') and then subtract off the Qvalue that the action we just took gave us

		next_qval = 0
		if not final_turn:
			next_qval = self.bestAction(sensed_wrld)[1]
		reward = score - current_score
		print("Reward: ", reward)
		delta = (reward + gamma * next_qval) - qval

		for weight in self.w:
			new_weight = 0
			if feature is 0:
				new_weight = weight + self.learningRate * delta * self.distanceToExit(action, wrld)
				print("feature of distanceToExit: ", self.distanceToExit(action, wrld))
				# if (new_weight < 0):
				# 	new_weight = 1000
			elif feature is 1:
				new_weight = weight + self.learningRate * delta * self.distanceToMonster(action, wrld)
				print("feature of distanceToMonster: ", self.distanceToMonster(action, wrld))
			elif feature is 2:
				new_weight = weight + self.learningRate * delta * self.inExplosion(wrld, action)
				print("feature of inExplosion: ", self.inExplosion(wrld, action))
			elif feature is 3:
				new_weight = weight + self.learningRate * delta * self.isLastTurn(action,wrld)
				print("feature of isLastTurn: ", self.isLastTurn(action,wrld))
			else:
				print('THIS SHOULD NEVER OCCUR')
			feature += 1
			new_weights.append(new_weight)
		self.last_score = current_score
		self.w = new_weights

	def bestAction(self, wrld):
		q_vals = dict()
		bestaction = 0, 0
		best = -1e99999999999
		currentpos = self.x, self.y
		actions = self.getValidSpotsFrom(currentpos, wrld)
		place_bomb = False
		for a in actions:
			q_vals[a] = self.w[0] * self.distanceToExit(a, wrld) + self.w[1] * self.distanceToMonster(a, wrld) + self.w[
				2] * self.inExplosion(wrld, a) + self.w[3] * self.isLastTurn(a,wrld)
		for val in q_vals.keys():
			if q_vals[val] > best:
				bestaction = val
				best = q_vals[val]
		new_move = currentpos[0] + bestaction[0], currentpos[1] + bestaction[1]
		if self.distance(new_move, wrld.exitcell) >= self.distance(currentpos, wrld.exitcell) and not self.bombPlaced:
			if self.turn_after_explosion:
				if self.turn_after_bomb >= 2:
					self.turn_after_explosion = False
					self.turn_after_bomb = 0
				else:
					self.turn_after_bomb += 1
			else:
				place_bomb = True  # bomb action
		return bestaction, best, place_bomb

	def do(self, wrld):
		self.getAllWalls(wrld)
		if self.first_turn_flag:
			self.readWeights()
		else:
			self.genNewWeights((self.x, self.y), self.prev_qval, wrld, False)
		print('weights:', self.w)
		print(self.x, ',  ', self.y)
		if (self.bombPlaced):
			self.bombtimer -= 1
		nextAction, qval, place_bomb = self.bestAction(wrld)
		print("NEXT ACTION:", nextAction)
		print("NEXT ACTION QVAL:", qval)
		if (self.bombtimer == 0):
			self.bombPlaced = False
			self.bombtimer = 11
			self.turn_after_explosion = True
		else:
			if place_bomb:
				self.place_bomb()
				self.bombPlaced = True
			self.move(nextAction[0], nextAction[1])

		if self.first_turn_flag:
			self.first_turn_flag = False
		else:
			self.prev_qval = qval


		# Update weights
		# if nextAction is 'b':
		# 	nextAction = (0, 0)
		self.writeWeights()

