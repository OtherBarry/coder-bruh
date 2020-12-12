"""File for primary agent"""


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
        updated = game_state.tick_number != self.tick_number
        self.tick_number = game_state.tick_number
        if not updated:
            return self.action_queue.pop()
        return None

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
        affected = []

        for i, m in [(0, 1), (0, -1), (1, 1), (1, -1)]:
            for c in range(2):
                coords = list(loc)
                coords[i] = coords[i] + (c * m)
                affected.append(tuple(coords))
                if self.is_item_here(coords):
                    break

        return affected

    def is_item_here(self, coords):
        entity = self.game_state.entity_at(coords)
        return entity is not None and len(entity) == 2 or entity == "b"

    def bombing_value(self, x, y):
        points = 0
        affected = self.bomb_affect((x, y))
        for entity in affected:
            if entity == "sb":
                points = points + 2
            elif entity == "ob":  # ON LAST HP
                pass

        # for x_val in range(x - 2, x + 2):
        #     block = self.game_state.entity_at((x_val, y))
        #     if block_name == "sb":
        #         points = points + 2
        #     elif block_name == "ob":
        #         return 10  ## ASDF NEED TO TRACK BLOCK HP
        #     points = points + self.block_values(block)
