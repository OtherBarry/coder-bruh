"""File for primary agent"""
import random


class Agent:
    """Class for primary agent"""

    UP = "u"
    DOWN = "d"
    LEFT = "l"
    RIGHT = "r"
    BOMB = "b"

    def __init__(self):
        self.tick_number = -1
        self.updated = True
        self.action_queue = []
        self.bombs = {}
        self.ores = {}
        self.first = True

    def next_move(self, game_state, player_state):
        """This method is called each time the player needs to choose an action"""
        self.game_state = game_state
        if self.first:
            self.on_first()

        self.track_bombs(game_state.bombs)
        print(self.bombing_value(player_state.location))
        updated = game_state.tick_number != self.tick_number
        self.tick_number = game_state.tick_number
        if not updated:
            return ""
        valid_tiles = get_surrounding_tiles(player_state.location)
        empty_tiles = get_empty_tiles(valid_tiles)
        return move_to_tile(
            random.choice(empty_tiles)
        )  # this should now check for valid empty tiles and move to one at random
        # return random.choice([self.UP, self.DOWN, self.LEFT, self.RIGHT])

    def on_first(self):
        self.first = False
        self.ores = {ore: 3 for ore in self.game_state.ore_blocks}

    def track_bombs(self, bombs):
        detonation_tick = self.tick_number - 35
        to_delete = []
        for location, tick in self.bombs.items():
            if tick == detonation_tick:
                self.track_detonation(location)
                to_delete.append(location)
        for loc in to_delete:
            del self.bombs[loc]
        for bomb in bombs:
            if bomb not in self.bombs:
                self.bombs[bomb] = self.tick_number

    def track_detonation(self, location):
        affected = self.bomb_affect(location)
        for tile in affected:
            if tile in self.ores:
                self.ores[tile] -= 1
                if self.ores[tile] == 0:
                    del self.ores[tile]
                #  update other players
                #  update wooden blocks

    def calculate_distance(self):
        pass

    def go_to(self):
        pass

    def bomb_affect(self, loc):
        affected = [loc]

        for i, m in [(0, 1), (0, -1), (1, 1), (1, -1)]:
            for c in range(2):
                coords = list(loc)
                coords[i] = coords[i] + (c * m)  # yee boi
                affected.append(tuple(coords))
                if self.is_item_here(coords):
                    break

        return affected

    def is_item_here(self, coords):
        return self.game_state.entity_at(coords) in ["b", "ib", "ob", "sb"]

    def in_bomb_radius(self, location):
        for bomb in self.bombs:
            if location in self.bomb_affect(bomb):
                return True
        return False

    def avoid_bombs(self, location):
        for i, c in [(0, 1), (0, -1), (1, 1), (1, -1)]:
            loc = list(location)
            loc[i] += c
            loc = tuple(loc)
            if not (self.game_state.is_occupied(loc) or self.in_bomb_radius(loc)):
                return loc

    def bombing_value(self, loc):
        points = 0
        affected = self.bomb_affect(loc)
        for location in affected:
            entity = self.game_state.entity_at(location)
            if entity == "sb":
                points = points + 2
            elif entity == "ob" and self.ores[location] == 1:  # ON LAST HP
                points = points + 10
        return points

    def get_surrounding_tiles(self, location):
        """Gets a list of surrounding tiles from up, down, left right"""
        surrounding_tiles = [
            (location[0], location[1] + 1),
            (location[0], location[1] - 1),
            (location[0] - 1, location[1]),
            (location[0] + 1, location[1]),
        ]
        valid_tiles = []
        for tile in surrounding_tiles:
            if self.game_state.is_in_bounds(tile):
                valid_tiles.append(tile)
        return valid_tiles

    def move_to_tile(self, location, tile):
        """Movement input is calculated based on target tile distance delta"""
        actions = ["", "u", "d", "l", "r", "p"]
        # see where the tile is relative to our current location
        diff = tuple(x - y for x, y in zip(self.location, tile))
        # return the action that moves in the direction of the tile
        if diff == (0, 1):
            action = "d"
        elif diff == (1, 0):
            action = "l"
        elif diff == (0, -1):
            action = "u"
        elif diff == (-1, 0):
            action = "r"
        else:
            action = ""
        return action

    def get_empty_tiles(self, tiles):
        """Get empty tiles from list of tiles"""
        empty_tiles = []
        for tile in tiles:
            if not self.game_state.is_occupied(tile):
                empty_tiles.append(tile)
        return empty_tiles
