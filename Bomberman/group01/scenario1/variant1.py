# This is necessary to find the main code
import sys
sys.path.insert(0, '../../bomberman')
sys.path.insert(1, '..')

# Import necessary stuff
from game import Game

# TODO This is your code!
sys.path.insert(1, '../group01')
from character1v1 import Character1v1


# Create the game
g = Game.fromfile('map.txt')

# TODO Add your character
g.add_character(Character1v1("me", # name
                              "C",  # avatar
                              0, 0  # position
))

# Run!
g.go()
