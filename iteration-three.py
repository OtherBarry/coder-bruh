"""File for primary agent"""
from coderone.dungeon.agent import PlayerState, GameState


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

    MAX_DESYNC = 2
    STATIONARY_HISTORY = [""] * MAX_DESYNC

    OPENING = "o"
    MIDDLE = "m"
    END = "e"

    def __init__(self):
        self.tick_number = -1
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

    def next_move(self, game_state: GameState, player_state: PlayerState):
        """This method is called each time the player needs to choose an action"""

        self.game_state = game_state
        self.player_state = player_state

        if self.first:
            self.on_first()
            self.player_location = player_state.location

        if self.desync_count > self.MAX_DESYNC:
            self.player_location = player_state.location
            entity_at_current_loc = game_state.entity_at(player_state.location)
        else:
            entity_at_current_loc = game_state.entity_at(self.player_location)

        recent_history = self.move_history[
            -min(self.MAX_DESYNC, len(self.move_history)) :
        ]
        self.synced = entity_at_current_loc == player_state.id or (
            entity_at_current_loc == "b"
            and (
                self.BOMB in recent_history or recent_history == self.STATIONARY_HISTORY
            )
        )

        self.tick_number = game_state.tick_number
        self.track_bombs(game_state.bombs)

        if self.synced:
            self.desync_count = 0
            if self.in_bomb_radius(
                self.player_location, time_remaining=self.MAX_DESYNC + 3
            ):
                return self.avoid_bombs_and_traps()
            self.update_game_stage()
            worth_attempting = self.get_locations_worth_attempting()
            self.path = self.get_path_to_best(worth_attempting)
            if self.path:
                self.target = self.path[0]
            else:
                self.target = self.player_location
            return self.get_action_from_path()
        else:
            self.desync_count += 1
            self.missed_turns += 1

    def make_move(self, move):
        self.move_history.append(move)
        return move

    def is_moveable_to(self, location):
        entity = self.game_state.entity_at(location)
        return entity not in ["b", "ib", "ob", "sb", int(self.player_state.id == 0)]

    def on_first(self):
        self.first = False
        self.ores = {ore: 3 for ore in self.game_state.ore_blocks}

    def update_game_stage(self):
        next_stage = self.game_stage
        current_block_count = len(self.game_state.soft_blocks)
        if current_block_count == 0:
            if len(self.game_state.ore_blocks) > 0:
                next_stage = self.MIDDLE
            else:
                next_stage = self.END
        elif current_block_count != self.block_counter[0]:
            self.block_counter = (current_block_count, self.tick_number)
            next_stage = self.OPENING
        elif self.block_counter[1] <= self.tick_number - 49:
            next_stage = self.MIDDLE
        if next_stage != self.game_stage:
            self.game_stage = next_stage

    def track_bombs(self, bombs):
        bombs_to_add = []
        for bomb in bombs:
            if bomb not in self.bombs:
                bombs_to_add.append(bomb)

        for bomb in bombs_to_add:
            self.bombs[bomb] = self.tick_number - 1
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
                        if distance > 1 and self.game_state.entity_at(coords) == "ob":
                            break
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

    def bombing_value(self, loc, inculde_pickups=True):
        points = 0

        entity = self.game_state.entity_at(loc)
        if inculde_pickups:
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
                if location in self.get_surrounding_tiles(loc):
                    diff = tuple((x - y) * -1 for x, y in zip(loc, location))
                    if (loc[0] + diff[0], loc[1] + diff[1]) in self.bombs:
                        continue
                entity = self.game_state.entity_at(location)
                if entity == "ob" and (
                    (
                        self.game_stage == self.MIDDLE
                        and self.player_state.ammo >= self.ores[location]
                        and self.ores[location] > 0
                    )
                    or (self.game_stage == self.OPENING and self.ores[location] == 1)
                ):
                    points += 10 / self.ores[location]
                elif self.game_stage == self.END and entity == int(
                    self.player_state.id == 0
                ):
                    points += 0.5
                elif self.in_bomb_radius(location):
                    continue
                elif entity == "sb":
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
            action = self.DO_NOTHING
            if destination in self.path:
                self.target = None

        if action != self.DO_NOTHING:
            self.player_location = destination

        return self.make_move(action)

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
                distance = self.get_manhattan_distance(coords, current_location)
                path = self.generate_path(
                    current_location, coords, max_count=10 + distance ** 2
                )
                if path is not None:
                    paths.append((coords, path))
            if paths:
                best = min(paths, key=lambda x: len(x[1]))
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

    def get_action_from_path(self):
        if self.path == []:
            bombing_value = self.bombing_value(
                self.player_location, inculde_pickups=False
            )
            if self.synced and self.player_state.ammo > 0 and bombing_value > 0:
                return self.make_move(self.BOMB)
            else:
                return self.make_move(self.DO_NOTHING)
        else:
            target = self.path.pop()
            if self.in_bomb_radius(target, time_remaining=3):
                return self.make_move(self.DO_NOTHING)
            return self.move_to_tile(self.player_location, target)

    def avoid_bombs_and_traps(self):
        for tile in self.get_surrounding_tiles(self.player_state.location):
            if self.is_moveable_to(tile):
                for next_tile in self.get_surrounding_tiles(tile):
                    if self.is_moveable_to(next_tile) and not self.in_bomb_radius(
                        next_tile, time_remaining=5
                    ):
                        return self.move_to_tile(self.player_state.location, tile)

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
                path.pop()
                return path

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
