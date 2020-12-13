"""File for primary agent"""
import random
from timeit import default_timer as timer


class Agent:
    """Class for primary agent"""

    UP = "u"
    DOWN = "d"
    LEFT = "l"
    RIGHT = "r"
    BOMB = "b"
    DO_NOTHING = ""

    MAX_AMMO_WEIGHTING = 5
    MIN_AMMO_WEIGHTING = 1

    UNEWIGHTED_DISTANCE = 2
    DISTANCE_DEBUFF = 1 / 20

    WAITING_BLOCKS = [(5, 5), (5, 4), (6, 5), (6, 4)]

    def __init__(self):
        self.tick_number = -1
        self.updated = True
        self.action_queue = []
        self.bombs = {}
        self.ores = {}
        self.first = True
        self.target = None
        self.path = None
        self.late_game = False
        self.player_location = (-1, -1)
        self.last_move = self.DO_NOTHING

    def next_move(self, game_state, player_state):
        """This method is called each time the player needs to choose an action"""

        self.game_state = game_state
        self.player_state = player_state

        self.late_game = len(self.game_state.soft_blocks) == 0

        if self.first:
            self.on_first()
            self.player_location = player_state.location
            self.id = player_state.id

        self.track_bombs(game_state.bombs)

        worth_attempting = self.get_locations_worth_attempting()
        path = self.get_path_to_best(worth_attempting)
        entity_at_current_loc = game_state.entity_at(self.player_location)
        if entity_at_current_loc == self.id or (
            self.last_move == self.BOMB and entity_at_current_loc == "b"
        ):
            self.tick_number = game_state.tick_number
            self.last_move = self.get_action_from_path(path)
            return self.last_move
        else:
            print("Desync: ", entity_at_current_loc)

    def is_moveable_to(self, location):
        entity = self.game_state.entity_at(location)
        return entity not in ["b", "ib", "ob", "sb", int(self.player_state.id == 0)]

    def on_first(self):
        self.first = False
        self.ores = {ore: 3 for ore in self.game_state.ore_blocks}

    def track_bombs(self, bombs):
        for bomb in bombs:
            if bomb not in self.bombs:
                self.bombs[bomb] = self.tick_number
                self.on_bomb_plant(bomb)
        detonation_tick = self.tick_number - 35
        to_delete = []
        for location, tick in self.bombs.items():
            if tick == detonation_tick:
                self.on_bomb_detonate(location)
                to_delete.append(location)
        for loc in to_delete:
            del self.bombs[loc]

    def on_bomb_plant(self, location):
        affected = self.bomb_affect(location)
        for tile in affected:
            if tile in self.ores:
                self.ores[tile] -= 1
                if self.ores[tile] == 0:
                    del self.ores[tile]

    def on_bomb_detonate(self, location):
        pass
        #  update other players
        #  update wooden blocks

    def get_manhattan_distance(self, a, b):
        return abs(a[0] - b[0]) + abs(a[1] + b[1])

    def bomb_affect(self, loc):
        x = 0
        y = 1
        pos = 1
        neg = -1

        affected = [loc]
        for axis in [x, y]:
            for direction in [neg, pos]:
                for distance in [1, 2]:
                    coords = list(loc)
                    coords[axis] += distance * direction
                    coords = tuple(coords)
                    if self.game_state.is_in_bounds(coords):
                        affected.append(coords)
                        if self.game_state.entity_at(coords) in ["b", "ib", "ob", "sb"]:
                            break
        return affected

    def in_bomb_radius(self, location, time_remaining=None):
        for bomb in self.bombs.keys():
            if location in self.bomb_affect(bomb):
                if time_remaining is None or (self.tick_number - self.bombs[bomb]) > (
                    35 - time_remaining
                ):
                    return True
        return False

    def avoid_bombs(self, location):
        for loc in self.get_surrounding_tiles(location):
            if not (self.game_state.is_occupied(loc) or self.in_bomb_radius(loc)):
                return loc

    def bombing_value(self, loc):
        points = 0

        entity = self.game_state.entity_at(loc)
        if entity == "t":
            points += 1
        elif entity == "a":
            points += max(
                self.MAX_AMMO_WEIGHTING - self.player_state.ammo,
                self.MIN_AMMO_WEIGHTING,
            )

        if self.player_state.ammo > 0:
            affected = self.bomb_affect(loc)
            affected.pop(0)
            for location in affected:
                entity = self.game_state.entity_at(location)
                if entity == "ob" and (
                    (self.late_game and self.player_state.ammo >= self.ores[location])
                    or ((not self.late_game) and self.ores[location] == 1)
                ):
                    points += 10
                    continue
                if self.in_bomb_radius(location):
                    continue
                if entity == "sb":
                    points += 2

        return points

    def get_surrounding_tiles(self, location):
        """Gets a list of surrounding tiles from up, down, left right"""
        surrounding_tiles = [
            (location[0], location[1] + 1),
            (location[0], location[1] - 1),
            (location[0] - 1, location[1]),
            (location[0] + 1, location[1]),
        ]
        return [
            tile for tile in surrounding_tiles if self.game_state.is_in_bounds(tile)
        ]

    def move_to_tile(self, current_location, destination):
        """Movement input is calculated based on target tile distance delta"""
        diff = tuple(x - y for x, y in zip(current_location, destination))
        if diff == (0, 1):
            action = self.DOWN
        elif diff == (1, 0):
            action = self.LEFT
        elif diff == (0, -1):
            action = self.UP
        elif diff == (-1, 0):
            action = self.RIGHT
        else:
            print("Failed to move to tile (tiles provided are not neighbours")
            action = self.DO_NOTHING

        if action != self.DO_NOTHING:
            self.player_location = destination

        # print("From {} to {} by {}".format(current_location, destination, action))
        return action

    def get_locations_worth_attempting(self):
        x_bound, y_bound = self.game_state.size
        valid_coords = []
        for x in range(x_bound):
            for y in range(y_bound):
                valid_coords.append((x, y))

        worth_attempting = {}
        for coords in valid_coords:
            if self.is_moveable_to(coords):
                value = self.bombing_value(coords)
                if value > 0:
                    if value in worth_attempting:
                        worth_attempting[value].append(coords)
                    else:
                        worth_attempting[value] = [coords]

        return worth_attempting

    def get_path_to_best(self, worth_attempting):
        current_location = self.player_state.location
        values = sorted(worth_attempting.keys(), reverse=True)
        print(worth_attempting)
        for value in values:
            paths = []
            for coords in worth_attempting[value]:
                if current_location == coords:
                    return []
                path = self.generate_path(current_location, coords)
                if path is not None:
                    paths.append((coords, path))
            if paths:
                best = min(paths, key=lambda x: len(x[1]))
                print(best[1])
                return best[1]
        return self.get_path_to_centre()

    def get_path_to_centre(self):
        current_location = self.player_state.location
        if current_location in self.WAITING_BLOCKS:
            return []
        for tile in self.WAITING_BLOCKS:
            path = self.generate_path(current_location, tile)
            if path is not None:

                return path
        return []

    def get_action_from_path(self, path):
        current_location = self.player_state.location
        if path == []:
            bombing_value = self.bombing_value(current_location)
            if self.player_state.ammo > 0 and bombing_value > 0:
                print("Planting Bomb for {} points".format(bombing_value))
                return self.BOMB
            else:
                print("Doing Nothing")
                return self.DO_NOTHING
        else:
            return self.move_to_tile(current_location, path[0])

    def generate_path(self, location, target, max_count=200):
        start_node = Node(None, location)
        start_node.g = start_node.h = start_node.f = 0
        end_node = Node(None, target)
        end_node.g = end_node.h = end_node.f = 0
        open_list = []
        closed_list = []
        open_list.append(start_node)
        iter_count = 0
        while iter_count < max_count and len(open_list) > 0:
            iter_count += 1
            current_node = open_list[0]
            current_index = 0
            for index, item in enumerate(open_list):
                if item.f < current_node.f:
                    current_node = item
                    current_index = index
            open_list.pop(current_index)
            closed_list.append(current_node)

            if current_node == end_node:
                path = []
                current = current_node
                while current is not None:
                    path.append(current.position)
                    current = current.parent
                path = path[::-1]
                return path[1:]  # Return reversed path

            children = []
            for node_position in self.get_surrounding_tiles(current_node.position):
                if not self.is_moveable_to(node_position):
                    continue
                new_node = Node(current_node, node_position)
                children.append(new_node)

            for child in children:
                for closed_child in closed_list:
                    if child == closed_child:
                        continue
                child.g = current_node.g + 1
                child.h = ((child.position[0] - end_node.position[0]) ** 2) + (
                    (child.position[1] - end_node.position[1]) ** 2
                )
                child.f = child.g + child.h
                for open_node in open_list:
                    if child == open_node and child.g > open_node.g:
                        continue
                open_list.append(child)
        # print("Unable to move from {} to {} after {} iterations".format(location, target, max_count))
        return None


class Node:
    """A node class for A* Pathfinding"""

    def __init__(self, parent=None, position=None):
        self.parent = parent
        self.position = position
        self.g = 0
        self.h = 0
        self.f = 0

    def __eq__(self, other):
        return self.position == other.position
