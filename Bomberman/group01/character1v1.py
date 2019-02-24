import sys
sys.path.insert(0, '../bomberman')
from entity import CharacterEntity
from astar import AStar

class Character1v1(CharacterEntity):
	def do(self, wrld):
		start = self.x, self.y
		end = wrld.exitcell
		move = AStar.getMoveFromPath(AStar.astar(wrld, start, end), end)
		print("move: ", move)
		self.move(move[0], move[1])
