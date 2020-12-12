'''
This is a bot facing an existential crisis.
All it does is walk around the map.
'''

import time
import random

path = []
path_progress = 0

class Node():
    """A node class for A* Pathfinding"""

    def __init__(self, parent=None, position=None):
        self.parent = parent
        self.position = position

        self.g = 0
        self.h = 0
        self.f = 0

    def __eq__(self, other):
        return self.position == other.position


class agent:

	def __init__(self):
		pass

	def next_move(self, game_state, player_state):
		""" 
		This method is called each time the agent is required to choose an action
		"""

		########################
		###    VARIABLES     ###
		########################

		# list of all possible actions to take
		actions = ['', 'u', 'd', 'l','r','p']

		# store some information about the environment
		# game map is represented in the form (x,y)
		self.cols = game_state.size[0]
		self.rows = game_state.size[1]

		self.game_state = game_state # for us to refer to later

		self.location = player_state.location

		ammo = player_state.ammo

		bombs = game_state.bombs

		########################
		###      AGENT       ###
		########################
		ammo_deposits = self.game_state.ammo
		#print(ammo_deposits)
		#if len(ammo_deposits) != 0:
		global path
		global path_progress
		new_path = self.generate_path(self.location, (1,1))
		if new_path == path:
			if path_progress < len(path):
				print("MATCH")
				action = self.move_to_tile(self.location, path[path_progress])
				path_progress += 1
				return action
			else:
				pass
		else:
			path = new_path
			path_progress = 0
		print(path)

		#surrounding_tiles = self.get_surrounding_tiles(self.location)
		#empty_tiles = self.get_empty_tiles(surrounding_tiles)
		#tileset = self.prioritise_pickups(empty_tiles)
		#random_tile = random.choice(tileset)
		#if random.uniform(0, 100) < ammo**2:
		#	return "b"
		#else:
		#	action = self.move_to_tile(self.location, random_tile)
		#	return action


	########################
	###     HELPERS      ###
	########################

	# given a tile location as an (x,y) tuple, this function
	# will return the surrounding tiles up, down, left and to the right as a list
	# (i.e. [(x1,y1), (x2,y2),...])
	# as long as they do not cross the edge of the map
	def get_surrounding_tiles(self, location):

		# find all the surrounding tiles relative to us
		# location[0] = col index; location[1] = row index
		tile_up = (location[0], location[1]+1)	
		tile_down = (location[0], location[1]-1)     
		tile_left = (location[0]-1, location[1]) 
		tile_right = (location[0]+1, location[1]) 		 

		# combine these into a list
		all_surrounding_tiles = [tile_up, tile_down, tile_left, tile_right]

		# we'll need to remove tiles that cross the border of the map
		# start with an empty list to store our valid surrounding tiles
		valid_surrounding_tiles = []

		# loop through our tiles
		for tile in all_surrounding_tiles:
			# check if the tile is within the boundaries of the game
			if self.game_state.is_in_bounds(tile):
				# if yes, then add them to our list
				valid_surrounding_tiles.append(tile)

		return valid_surrounding_tiles

	# given a list of tiles
	# return the ones which are actually empty
	def get_empty_tiles(self, tiles):

		# empty list to store our empty tiles
		empty_tiles = []

		for tile in tiles:
			if not self.game_state.is_occupied(tile) or self.game_state.entity_at(tile) in ["a", "t"]:
				# the tile isn't occupied, so we'll add it to the list
				empty_tiles.append(tile)

		return empty_tiles

	def prioritise_pickups(self, tiles):

		pickups = []
		for tile in tiles:
			if self.game_state.entity_at(tile) in ["a", "t"]:
				pickups.append(tile)
		if len(pickups) == 0:
			return tiles
		else:
			return pickups

	# given an adjacent tile location, move us there
	def move_to_tile(self, location, tile):

		actions = ['', 'u', 'd', 'l','r','p']

		# see where the tile is relative to our current location
		diff = tuple(x-y for x, y in zip(self.location, tile))

		# return the action that moves in the direction of the tile
		if diff == (0,1):
			action = 'd'
		elif diff == (1,0):
			action = 'l'
		elif diff == (0,-1):
			action = 'u'
		elif diff == (-1,0):
			action = 'r'
		else:
			action = ''

		return action

	def generate_path(self, location, target):
		start_node = Node(None, location)
		start_node.g = start_node.h = start_node.f = 0
		end_node = Node(None, target)
		end_node.g = end_node.h = end_node.f = 0

		# Initialize both open and closed list
		open_list = []
		closed_list = []

		# Add the start node
		open_list.append(start_node)
		# Loop until you find the end
		while len(open_list) > 0:
			# Get the current node
			current_node = open_list[0]
			current_index = 0
			for index, item in enumerate(open_list):
				if item.f < current_node.f:
					current_node = item
					current_index = index

			# Pop current off open list, add to closed list
			open_list.pop(current_index)
			closed_list.append(current_node)

			# Found the goal
			if current_node == end_node:
				path = []
				current = current_node
				while current is not None:
					path.append(current.position)
					current = current.parent
				return path[::-1]  # Return reversed path

			# Generate children
			children = []
			for new_position in [(0, -1), (0, 1), (-1, 0), (1, 0)]:  # Adjacent squares

				# Get node position
				node_position = (current_node.position[0] + new_position[0], current_node.position[1] + new_position[1])
				if not self.game_state.is_in_bounds(node_position):
					continue
				if self.is_obstructed(node_position):
					continue

				# Create new node
				new_node = Node(current_node, node_position)

				# Append
				children.append(new_node)

			# Loop through children
			for child in children:

				# Child is on the closed list
				for closed_child in closed_list:
					if child == closed_child:
						continue

				# Create the f, g, and h values
				child.g = current_node.g + 1
				child.h = ((child.position[0] - end_node.position[0]) ** 2) + (
							(child.position[1] - end_node.position[1]) ** 2)
				child.f = child.g + child.h

				# Child is already in the open list
				for open_node in open_list:
					if child == open_node and child.g > open_node.g:
						continue

				# Add the child to the open list
				open_list.append(child)
		print("NO PATH")
		pass

	def is_obstructed(self, location):
		entity = self.game_state.entity_at(location)
		return entity in ["b", "ib", "ob", "sb", "0", "1"]