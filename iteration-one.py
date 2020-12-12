"""File for primary agent"""
import random


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
        self.player_state = player_state
        if self.first:
            self.on_first()

        self.track_bombs(game_state.bombs)
        updated = game_state.tick_number != self.tick_number
        self.tick_number = game_state.tick_number
        # if not updated:
        #     return ""
        # if self.in_bomb_radius(player_state.location, time_remaining=2):
        #     target = self.avoid_bombs(player_state.location)
        #     if target is not None:
        #         return self.move_to_tile(player_state.location, target)
        return self.find_best_bombing_location(player_state.location)

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

    def calculate_distance(self):
        pass

    def go_to(self):
        pass

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

    def is_moveable_to(self, location):
        entity = self.game_state.entity_at(location)
        return entity in ["b", "ib", "ob", "sb", "0", "1"]

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

    def find_best_bombing_location(self, location):
        tiles = {}
        for tile in self.get_surrounding_tiles(location):
            if not self.is_moveable_to(tile):
                tiles[tile] = self.bombing_value(tile)
        tiles[location] = self.bombing_value(location)
        best_score = max(tiles.values())
        best_tiles = [key for key, value in tiles.items() if value == best_score]
        if location in best_tiles and best_score > 0:
            return self.BOMB
        best_tiles = [
            tile
            for tile in best_tiles
            if not self.in_bomb_radius(tile, time_remaining=2)
        ]
        if best_tiles == []:
            return random.choice([self.UP, self.DOWN, self.LEFT, self.RIGHT])
        return self.move_to_tile(location, random.choice(best_tiles))

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
                if self.in_bomb_radius(location):
                    print(loc)
                    print("in radiius in bomb_value")
                    print(affected)
                    continue
                if entity == "sb":
                    points += 2
                    continue
                if entity == "ob" and self.ores[location] == 1:
                    points += 10

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

    def move_to_tile(self, location, tile):
        """Movement input is calculated based on target tile distance delta"""
        diff = tuple(x - y for x, y in zip(location, tile))
        if diff == (0, 1):
            action = self.DOWN
        elif diff == (1, 0):
            action = self.LEFT
        elif diff == (0, -1):
            action = self.UP
        elif diff == (-1, 0):
            action = self.RIGHT
        else:
            action = self.DO_NOTHING
        return action

    def get_empty_tiles(self, tiles):
        """Get empty tiles from list of tiles"""
        empty_tiles = []
        for tile in tiles:
            if not self.game_state.is_occupied(tile):
                empty_tiles.append(tile)
        return empty_tiles
