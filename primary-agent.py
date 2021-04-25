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

    PATHFINDER_HEURISTIC = 7
    PATHFINDER_ITERATION_MULTIPLIER = 4.6

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
        self.attack_enemy = False
        self.bomb_map = {}

    # def next_move(self, game_state, player_state):
    #     cProfile.runctx('self.next_move_alt(g, p)', {'g': game_state, 'p': player_state, 'self': self}, {}, 'out.pstat')
    #     quit()

    def next_move(self, game_state: GameState, player_state: PlayerState):
        """This method is called each time the player needs to choose an action"""
        self.game_state = game_state
        self.player_state = player_state

        if self.first:
            self.on_first()

        if self.tick_number != game_state.tick_number:
            print("Took too long to make move")
            self.synced = False
        else:
            self.synced = True

        self.track_bombs(game_state.bombs)
        self.create_bomb_map()

        if self.synced and self.player_location != player_state.location:
            last_move = self.move_history[-1]
            print("Last move failed", last_move)
            print("Expected vs actual", self.player_location, player_state.location)
            self.player_location = player_state.location
            self.path = []
            self.target = None

        if self.desync_count > self.MAX_DESYNC:
            print("Resyncing")
            self.tick_number = game_state.tick_number + 1
            self.player_location = player_state.location

        if self.synced:
            self.desync_count = 0
            to_avoid = self.avoid_bombs_and_traps()
            if to_avoid is not None:
                return self.make_move(to_avoid)
            self.update_game_stage()
            worth_attempting = self.get_locations_worth_attempting()
            self.path = self.get_path_to_best(worth_attempting)
            if self.path:
                self.target = self.path[0]
            next = self.get_action_from_path()
            return self.make_move(next)
        else:
            self.desync_count += 1
            self.missed_turns += 1
            print(
                "missed {} out of {} turns ({:.2f}%)".format(
                    self.missed_turns,
                    self.tick_number,
                    (self.missed_turns / self.tick_number) * 100,
                )
            )
            self.tick_number += 1

    def make_move(self, move):
        if not self.check_move_valid(self.player_location, move):
            print("Invalid Move attempted:", move)
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

    def is_moveable_to(self, location, skip_enemy=False):
        if self.game_state.is_in_bounds(location):
            entity = self.game_state.entity_at(location)
            return entity not in self.IMPENETRABLE_OBJECTS and (
                skip_enemy or entity != self.enemy_id
            )
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
            score = self.player_state.reward
            damage_taken = 3 - self.player_state.hp
            if score < (
                56 + (damage_taken * 25)
            ):  # Max points obtainable by other player
                self.attack_enemy = True
            else:
                self.attack_enemy = False
        elif current_block_count == 0:
            next_stage = self.MIDDLE
        elif current_block_count != self.block_counter[0]:
            self.block_counter = (current_block_count, self.tick_number)
            next_stage = self.OPENING
        elif len(self.bombs) < 1 and self.block_counter[1] <= self.tick_number - 20:
            next_stage = self.MIDDLE
        if next_stage != self.game_stage:
            print("Moving to new stage:", next_stage)
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
            if tick < detonation_tick:
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
                self.bombs[location] = self.bombs[tile] + 1

    def create_bomb_map(self):
        bomb_map = {}
        for bomb in self.bombs:
            if bomb not in bomb_map or bomb_map[bomb] > self.bombs[bomb] + 35:
                bomb_map[bomb] = self.bombs[bomb] + 35
            for tile in self.bomb_affect(bomb):
                if tile not in bomb_map or bomb_map[tile] > self.bombs[bomb] + 35:
                    bomb_map[tile] = self.bombs[bomb] + 35
        self.bomb_map = bomb_map

    def is_safe(self, location, tick, late_game=False):
        if location not in self.bomb_map:
            return True
        det_tick = self.bomb_map[location]
        if late_game:
            if det_tick < tick + 5:
                return False
        elif det_tick == tick or det_tick == tick + 1:
            return False
        return True

    def is_trap(self, location, skip_cells=()):
        for tile in self.get_surrounding_tiles(location):
            if tile not in skip_cells and self.is_moveable_to(tile):
                return False
        return True

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

        if (
            points == 0
            and self.game_stage == self.END
            and not self.attack_enemy
            and self.player_state.ammo > 0
        ):
            cells = self.get_surrounding_tiles(loc)
            safe = True
            for cell in cells:
                if self.game_state.entity_at(cell) is not None:
                    safe = False
            if safe:
                points += 10
                return points

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
                elif entity == self.enemy_id and self.attack_enemy:
                    points += 0.5
                elif location in self.bomb_map:
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
        if location[1] != self.y_bound:  # UP
            surrounding_tiles.append((location[0], location[1] + 1))
        if location[0] != self.x_bound:  # RIGHT
            surrounding_tiles.append((location[0] + 1, location[1]))
        if location[1] != 0:  # DOWN
            surrounding_tiles.append((location[0], location[1] - 1))
        if location[0] != 0:  # LEFT
            surrounding_tiles.append((location[0] - 1, location[1]))
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
                print("Failed to move to tile (tiles provided are not neighbours)")
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
            if (
                self.target in targets
                and self.path
                and self.path[-1] in self.get_surrounding_tiles(self.player_location)
                and self.is_moveable_to(self.path[-1], skip_enemy=False)
            ):
                return self.path
            for coords in targets:
                if current_location == coords:
                    return []
                if self.is_trap(coords):
                    continue
                distance = self.get_manhattan_distance(current_location, coords)
                path = self.generate_path(
                    current_location,
                    coords,
                    max_count=distance * self.PATHFINDER_ITERATION_MULTIPLIER,
                )
                if path is not None:
                    paths.append(path)
            if paths != []:
                return min(paths, key=len)
        if self.player_state.ammo > 0:
            return []
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
                return self.DO_NOTHING
        else:
            target = self.path[-1]
            if not self.is_safe(target, self.tick_number + 1):
                print("Avoiding Bomb, Waiting one turn")
                return self.DO_NOTHING
            if self.game_state.entity_at(self.player_location) == self.BOMB:
                trap, exit = self.get_trap_details(target)
                if trap is not None and exit is None:
                    print("Avoiding Trap, Waiting one turn")
                    return self.DO_NOTHING
            if self.player_location not in self.get_surrounding_tiles(target):
                print("PATHING ERROR")
                for tile in self.get_surrounding_tiles(self.player_location):
                    if self.is_moveable_to(
                        tile
                    ) and target in self.get_surrounding_tiles(tile):
                        target = tile
                    else:
                        self.path = []
                        self.target = None
                        target = self.player_location
            if self.path and target == self.path[-1]:
                self.path.pop()
            next = self.move_to_tile(self.player_location, target)
            return next

    def get_trap_details(self, location):
        starting_tiles = [
            tile
            for tile in self.get_surrounding_tiles(location)
            if self.is_moveable_to(tile, skip_enemy=False)
        ]
        move_count = len(starting_tiles)
        if move_count > 2:
            return None, None
        if move_count == 0:
            return location, None
        exit = None
        trap = None
        open_tiles = starting_tiles
        closed_tiles = {self.player_location}
        while len(open_tiles) > 0:
            current_tile = open_tiles.pop()
            closed_tiles.add(current_tile)
            neighbours = [
                tile
                for tile in self.get_surrounding_tiles(current_tile)
                if tile not in closed_tiles
                and self.is_moveable_to(tile, skip_enemy=False)
            ]
            n_count = len(neighbours)
            if n_count == 0:  # Trap
                if trap is None:
                    trap = current_tile
                else:
                    return trap, None
            elif n_count > 1:  # exit
                if exit is None:
                    exit = current_tile
                else:
                    return trap, None
            else:
                open_tiles.extend(neighbours)
        return trap, exit

    def avoid_bombs_and_traps(self):
        if self.player_location not in self.bomb_map:
            _, exit = self.get_trap_details(self.player_location)
            if exit is None:
                return None
            opponent = self.game_state.opponents(self.player_state.id)[0]
            path_to_opponent = self.generate_path(
                self.player_location, opponent, skip_enemy=True
            )
            if path_to_opponent is None:
                return None
            path_to_escape = self.generate_path(
                self.player_location, exit, skip_enemy=False
            )
            if len(path_to_opponent) <= len(path_to_escape):
                return self.move_to_tile(self.player_location, path_to_escape.pop())
        else:
            if (
                not self.is_safe(self.player_location, self.tick_number + 3)
                or not self.is_safe(self.player_location, self.tick_number + 2)
                or not self.is_safe(self.player_location, self.tick_number + 1)
            ):
                neighbours = self.get_surrounding_tiles(self.player_location)
                for tile in neighbours:
                    if self.is_moveable_to(tile) and self.is_safe(
                        tile, self.tick_number + 2
                    ):
                        return self.move_to_tile(self.player_location, tile)
                for tile in neighbours:
                    secondary_tiles = self.get_surrounding_tiles(tile)
                    for t2 in secondary_tiles:
                        if self.is_moveable_to(t2) and self.is_safe(
                            t2, self.tick_number + 3
                        ):
                            return self.move_to_tile(self.player_location, tile)
                print("Unable to escape bomb")
            return None

    def generate_path(self, location, target, max_count=200, skip_enemy=True):
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
                return path

            tiles = self.get_surrounding_tiles(current_node.position)
            random.shuffle(tiles)
            for tile in tiles:
                if self.is_moveable_to(tile, skip_enemy=skip_enemy):
                    node = Node(None, tile)
                    if node not in closed_list:
                        node.parent = current_node
                        node.g = current_node.g + 1
                        node.h = (
                            self.get_manhattan_distance(
                                node.position, end_node.position
                            )
                            * self.PATHFINDER_HEURISTIC
                        )
                        node.f = node.g + node.h
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
