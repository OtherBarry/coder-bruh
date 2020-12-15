"""File for primary agent"""
import random

from coderone.dungeon.agent import PlayerState, GameState
import cProfile


class Agent:
    """Class for primary agent"""

    UP = "u"
    DOWN = "d"
    LEFT = "l"
    RIGHT = "r"
    BOMB = "b"
    DO_NOTHING = ""

    OPENING = "o"
    MIDDLE = "m"
    END = "e"

    MAX_AMMO_WEIGHTING = {OPENING: 3, MIDDLE: 5, END: 7}
    MIN_AMMO_WEIGHTING = 1

    PATH_H_MULTIPLIER = 10
    PATH_MIN_H = 1

    WAITING_BLOCKS = [(5, 5), (5, 4), (6, 5), (6, 4)]

    MAX_DESYNC = 2

    IMPENETRABLE_OBJECTS = {"b", "ib", "ob", "sb"}

    def __init__(self):
        self.tick_number = 0
        self.bombs = {}
        self.first = True
        self.target = None
        self.path = []
        self.late_game = False
        self.player_location = (-1, -1)
        self.move_history = []
        self.desync_count = 0
        self.block_counter = [0, 0]
        self.game_stage = self.OPENING
        self.missed_turns = 0
        self.x_bound = 11
        self.y_bound = 9
        self.enemy_id = -1

    # def next_move(self, game_state, player_state):
    #     cProfile.runctx('self.next_move_alt(g, p)', {'g': game_state, 'p': player_state, 'self': self}, {}, 'out.pstat')
    #     quit()

    def next_move(self, game_state: GameState, player_state: PlayerState):
        """This method is called each time the player needs to choose an action"""
        self.game_state = game_state
        self.player_state = player_state

        if self.first:
            self.on_first()

        self.tick_number = game_state.tick_number
        self.player_location = player_state.location

        self.track_bombs(game_state.bombs)

        with open("out_two.txt", "a") as f:
            self.file = f
            locations = self.get_locations_worth_attempting()
            for key in locations:
                for target in locations[key]:
                    path = self.generate_path(
                        self.player_location, target, max_count=400
                    )

    def make_move(self, move):
        if not self.check_move_valid(self.player_location, move):
            self.path = []
            move = self.DO_NOTHING
        self.move_history.append(move)
        if move == self.LEFT:
            self.player_location = (
                self.player_location[0] - 1,
                self.player_location[1],
            )
        if move == self.RIGHT:
            self.player_location = (
                self.player_location[0] + 1,
                self.player_location[1],
            )
        if move == self.UP:
            self.player_location = (
                self.player_location[0],
                self.player_location[1] + 1,
            )
        if move == self.DOWN:
            self.player_location = (
                self.player_location[0],
                self.player_location[1] - 1,
            )
        self.tick_number += 1
        return move

    def is_moveable_to(self, location):
        if self.game_state.is_in_bounds(location):
            entity = self.game_state.entity_at(location)
            return entity not in self.IMPENETRABLE_OBJECTS and entity != self.enemy_id
        return False

    def on_first(self):
        self.first = False
        self.player_location = self.player_state.location
        self.enemy_id = int(self.player_state.id == 0)
        self.ores = {ore: 3 for ore in self.game_state.ore_blocks}

    def update_game_stage(self):
        next_stage = self.game_stage
        current_block_count = len(self.game_state.soft_blocks)
        if len(self.game_state.ore_blocks) < 1:
            next_stage = self.END
        elif current_block_count == 0:
            next_stage = self.MIDDLE
        elif current_block_count != self.block_counter[0]:
            self.block_counter = (current_block_count, self.tick_number)
            next_stage = self.OPENING
        elif len(self.bombs) < 1 and self.block_counter[1] <= self.tick_number - 20:
            next_stage = self.MIDDLE
        if next_stage != self.game_stage:
            self.game_stage = next_stage

    def track_bombs(self, bombs):
        bombs_to_add = []
        for bomb in bombs:
            if bomb not in self.bombs:
                bombs_to_add.append(bomb)

        for bomb in bombs_to_add:
            self.bombs[bomb] = self.tick_number
            self.on_bomb_plant(bomb)

        detonation_tick = self.tick_number - 35
        to_delete = []
        for location, tick in self.bombs.items():
            if tick <= detonation_tick:
                # self.on_bomb_detonate(location)
                to_delete.append(location)
        for loc in to_delete:
            del self.bombs[loc]

    def on_bomb_plant(self, location):
        affected = self.bomb_affect(location)
        for tile in affected:
            if tile in self.ores:
                self.ores[tile] -= 1
                if tile in self.get_surrounding_tiles(location):
                    diff = tuple((x - y) * -1 for x, y in zip(location, tile))
                    if (location[0] + diff[0], location[1] + diff[1]) in self.bombs:
                        self.ores[tile] += 1
            elif tile in self.bombs:
                self.bombs[tile] = self.bombs[location]

    def get_manhattan_distance(self, a, b):  # TODO: Make global
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def bomb_affect(self, loc):
        affected = []
        for axis in (0, 1):
            for direction in (-1, 1):
                for distance in (1, 2):
                    if axis == 0:
                        new_value = loc[0] + (distance * direction)
                        if 0 <= new_value <= self.x_bound:
                            coords = (new_value, loc[1])
                        else:
                            continue
                    else:
                        new_value = loc[1] + (distance * direction)
                        if 0 <= new_value <= self.x_bound:
                            coords = (loc[0], new_value)
                        else:
                            continue
                    entity = self.game_state.entity_at(coords)
                    if distance > 1 and entity == "ob":
                        break
                    affected.append(coords)
                    if entity in self.IMPENETRABLE_OBJECTS:
                        break
        return affected

    def in_bomb_radius(self, location, time_remaining=None):
        if location in self.bombs:
            if (
                time_remaining is None
                or self.tick_number - self.bombs[location] > 35 - time_remaining
            ):
                return True
        for bomb in self.bombs.keys():
            if location in self.bomb_affect(bomb):
                if (
                    time_remaining is None
                    or self.tick_number - self.bombs[bomb] > 35 - time_remaining
                ):
                    return True
        return False

    def bombing_value(self, loc, inculde_pickups=True):
        points = 0

        entity = self.game_state.entity_at(loc)
        if inculde_pickups:
            if entity == "t":
                points += 1
            elif entity == "a":
                points += max(
                    self.MAX_AMMO_WEIGHTING[self.game_stage] - self.player_state.ammo,
                    self.MIN_AMMO_WEIGHTING,
                )

        if self.player_state.ammo > 0:
            affected = self.bomb_affect(loc)
            for location in affected:
                if location in self.get_surrounding_tiles(loc):  # This is inefficient
                    diff = tuple((x - y) * -1 for x, y in zip(loc, location))
                    if (loc[0] + diff[0], loc[1] + diff[1]) in self.bombs:
                        continue
                entity = self.game_state.entity_at(location)
                if entity == "ob" and (
                    (
                        self.game_stage == self.MIDDLE
                        and self.player_state.ammo >= self.ores[location] > 0
                    )
                    or (self.game_stage == self.OPENING and self.ores[location] == 1)
                ):
                    points += 10 / self.ores[location]
                elif (
                    entity == self.enemy_id
                    and self.game_stage == self.END
                    and self.player_state.power < 50 + ((3 - self.player_state.hp) * 25)
                ):
                    points += 0.5
                elif self.in_bomb_radius(location):
                    continue
                elif entity == "sb":
                    points += 2
        return points

    def check_move_valid(self, position, move):
        if move == self.DO_NOTHING:
            return True
        if move == self.LEFT:
            return self.is_moveable_to((position[0] - 1, position[1]))
        if move == self.RIGHT:
            return self.is_moveable_to((position[0] + 1, position[1]))
        if move == self.UP:
            return self.is_moveable_to((position[0], position[1] + 1))
        if move == self.DOWN:
            return self.is_moveable_to((position[0], position[1] - 1))
        if move == self.BOMB:
            if self.game_state.entity_at(position) == self.player_state.id:
                return True
            else:
                return False
        raise ValueError

    def get_surrounding_tiles(self, location):
        """Gets a list of surrounding tiles from up, down, left right"""
        surrounding_tiles = []
        if location[0] != 0:
            surrounding_tiles.append((location[0] - 1, location[1]))
        if location[0] != self.x_bound:
            surrounding_tiles.append((location[0] + 1, location[1]))
        if location[1] != 0:
            surrounding_tiles.append((location[0], location[1] - 1))
        if location[1] != self.y_bound:
            surrounding_tiles.append((location[0], location[1] + 1))
        return surrounding_tiles

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
            if current_location != destination:
                self.path = []
            action = self.DO_NOTHING
            if destination in self.path:
                self.path = []

        return action

    def get_locations_worth_attempting(self):
        x_bound, y_bound = self.game_state.size
        worth_attempting = {}
        for x in range(x_bound):
            for y in range(y_bound):
                coords = (x, y)
                if self.is_moveable_to(coords):
                    value = self.bombing_value(coords)
                    if value > 0.0:
                        if value in worth_attempting:
                            worth_attempting[value].append(coords)
                        else:
                            worth_attempting[value] = [coords]
        return worth_attempting

    def get_path_to_best(self, worth_attempting):
        current_location = self.player_location
        values = sorted(worth_attempting.keys(), reverse=True)
        for value in values:
            targets = worth_attempting[value]
            paths = []
            if self.target in targets:
                return self.path
            for coords in targets:
                if current_location == coords:
                    return []
                path = self.generate_path(current_location, coords, max_count=200)
                if path is not None:
                    paths.append(path)
            if paths != []:
                return min(paths, key=len)
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

    def get_action_from_path(self):
        if self.path == []:
            self.target = None
            bombing_value = self.bombing_value(
                self.player_location, inculde_pickups=False
            )
            if (
                self.synced
                and self.player_state.ammo > 0
                and bombing_value > 0
                and self.player_location not in self.bombs
            ):
                return self.BOMB
            else:
                if self.in_bomb_radius(self.player_location):
                    return self.avoid_bombs_and_traps()
                return self.DO_NOTHING
        else:
            target = self.path[-1]
            if self.in_bomb_radius(
                target, time_remaining=self.MAX_DESYNC + 1
            ) and not self.in_bomb_radius(
                self.player_location, time_remaining=self.MAX_DESYNC
            ):
                return self.DO_NOTHING
            if self.player_location not in self.get_surrounding_tiles(target):
                for tile in self.get_surrounding_tiles(self.player_location):
                    if self.is_moveable_to(
                        tile
                    ) and target in self.get_surrounding_tiles(tile):
                        target = tile
            if target == self.path[-1]:
                self.path.pop()
            next = self.move_to_tile(self.player_location, target)
            return next

    def avoid_bombs_and_traps(self):
        for tile in self.get_surrounding_tiles(self.player_state.location):
            if self.is_moveable_to(tile):
                for next_tile in self.get_surrounding_tiles(tile):
                    if self.is_moveable_to(next_tile) and not self.in_bomb_radius(
                        next_tile, time_remaining=(self.MAX_DESYNC * 2) + 1
                    ):
                        next = self.move_to_tile(self.player_state.location, tile)
                        if next == self.DO_NOTHING:
                            return next
        return self.DO_NOTHING

    def generate_path(self, location, target, max_count=200):
        start_node = Node(None, location)
        start_node.g = start_node.h = start_node.f = 0
        end_node = Node(None, target)
        end_node.g = end_node.h = end_node.f = 0
        open_list = []
        closed_list = set()
        open_list.append(start_node)
        iter_count = 0
        while iter_count < max_count and len(open_list) > 0:
            iter_count += 1
            current_node = min(open_list, key=lambda x: x.f)
            open_list.remove(current_node)
            closed_list.add(current_node)

            if current_node == end_node:
                path = []
                current = current_node
                while current is not None:
                    path.append(current.position)
                    current = current.parent
                path.pop()
                distance = self.get_manhattan_distance(location, target)
                path_len = len(path)
                if path_len >= distance:
                    out = "{}|{}|{}".format(distance, path_len, iter_count)
                    self.file.write(out + "\n")
                else:
                    print(
                        "path len off by",
                        distance - path_len,
                        location,
                        target,
                        distance,
                        path_len,
                    )
                return path

            tiles = self.get_surrounding_tiles(current_node.position)
            random.shuffle(tiles)
            for tile in tiles:
                if self.is_moveable_to(tile):
                    node = Node(None, tile)
                    if node not in closed_list:
                        node.parent = current_node
                        node.g = current_node.g + 1
                        node.h = ((node.position[0] - end_node.position[0]) ** 2) + (
                            (node.position[1] - end_node.position[1]) ** 2
                        )
                        node.f = node.g + node.h
                        for open_node in open_list:
                            if node == open_node and node.g > open_node.g:
                                continue
                        open_list.append(node)
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

    def __hash__(self):
        return hash(self.position)
