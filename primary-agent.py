"""File for primary agent"""
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

    MAX_AMMO_WEIGHTING = 5
    MIN_AMMO_WEIGHTING = 1

    PATHFINDING_HEURISTIC = 2

    WAITING_BLOCKS = [(5, 5), (5, 4), (6, 5), (6, 4)]

    MAX_DESYNC = 2
    STATIONARY_HISTORY = [''] * MAX_DESYNC

    OPENING = "o"
    MIDDLE = "m"
    END = "e"

    IMPENETRABLE_OBJECTS = set(["b", "ib", "ob", "sb"])

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
            self.player_location = player_state.location

        if self.desync_count > self.MAX_DESYNC:
            self.player_location = player_state.location
            entity_at_current_loc = game_state.entity_at(player_state.location)
        else:
            entity_at_current_loc = game_state.entity_at(self.player_location)

        recent_history = self.move_history[-min(self.MAX_DESYNC, len(self.move_history)) :]
        self.synced = entity_at_current_loc == player_state.id or (
            entity_at_current_loc == "b"
            and (self.BOMB
            in recent_history or recent_history == self.STATIONARY_HISTORY)
        )

        self.tick_number = game_state.tick_number
        self.track_bombs(game_state.bombs)

        if self.synced:
            self.desync_count = 0
            if self.in_bomb_radius(self.player_location, time_remaining=self.MAX_DESYNC + 3):
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
            print("missed {} out of {} turns ({:.2f}%)".format(self.missed_turns, self.tick_number, (self.missed_turns / self.tick_number) * 100))


    def make_move(self, move):
        self.move_history.append(move)
        return move

    def is_moveable_to(self, location):
        entity = self.game_state.entity_at(location)
        return entity not in self.IMPENETRABLE_OBJECTS and entity != self.enemy_id

    def on_first(self):
        self.first = False
        self.enemy_id = int(self.player_state.id == 0)
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
            print("Moving to new stage:", next_stage)
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
        affected = [loc]
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
                if location in self.get_surrounding_tiles(loc):  # This is inefficiten
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
                elif self.game_stage == self.END and entity == self.enemy_id:
                    points += 0.5
                elif self.in_bomb_radius(location):
                    continue
                elif entity == "sb":
                    points += 2


        return points

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
            print("Failed to move to tile (tiles provided are not neighbours")
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
        paths_tried = 0
        for value in values:
            targets = worth_attempting[value]
            paths = []
            if self.target in targets:
                return self.path
            for i, target in enumerate(targets):
               targets[i] = (self.get_manhattan_distance(target, current_location), target)
            targets.sort(key=lambda x: x[0])
            for target in targets:
                coords = target[1]
                if current_location == coords:
                    return []
                distance = target[0]
                path = self.generate_path(
                    current_location, coords, max_count=10 + distance ** 2
                )
                paths_tried += 1
                if path is not None:
                    print("Paths tried:", paths_tried)
                    return path
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
            bombing_value = self.bombing_value(self.player_location, inculde_pickups=False)
            if self.synced and self.player_state.ammo > 0 and bombing_value > 0:
                return self.make_move(self.BOMB)
            else:
                return self.make_move(self.DO_NOTHING)
        else:
            target = self.path.pop()
            if self.in_bomb_radius(target, time_remaining=3):
                print("Avoiding Bomb, Waiting one turn")
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

            for tile in self.get_surrounding_tiles(current_node.position):
                if self.is_moveable_to(tile):
                    node = Node(None, tile)
                    if node not in closed_list:
                        node.parent = current_node
                        node.g = current_node.g + 1
                        node.h = self.get_manhattan_distance(node.position, current_node.position) * self.PATHFINDING_HEURISTIC
                        node.f = node.g + node.h
                        for open_node in open_list:
                            if node == open_node and node.f > open_node.f:
                                continue
                        open_list.append(node)
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

    def __hash__(self):
        return hash(self.position)
