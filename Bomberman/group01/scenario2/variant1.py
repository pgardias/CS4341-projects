# This is necessary to find the main code
import sys
sys.path.insert(0, '../../bomberman')
sys.path.insert(1, '..')

# Import necessary stuff
from game import Game

# TODO This is your code!
sys.path.insert(1, '../group01')
from q_learning import Q_Learning


# Create the game
g = Game.fromfile('map.txt')

g.add_character(Q_Learning("me", "C", 0, 0, 2, 1))

# Run!
g.go()
