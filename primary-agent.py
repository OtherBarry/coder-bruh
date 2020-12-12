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

    def next_move(self, game_state, player_state):
        """This method is called each time the player needs to choose an action"""
        updated = game_state.tick_number != self.tick_number
        self.tick_number = game_state.tick_number
        if not updated:
            return self.action_queue.pop()
        return None

    def track_bombs(self, bombs):
        detonation_tick = self.tick_number - 35
        for location, tick in self.bombs.items():
            if tick == detonation_tick:
                self.track_detonation(location)
                del self.bombs[location]
        for bomb in bombs:
            if bomb not in self.bombs:
                self.bombs[bomb] = self.tick_number

    def track_detonation(self, location):
        pass

    def calculate_distance(self):
        pass

    def go_to(self):
        pass

    def bomb_affect(self, loc):
        affected = []

        for i, m in [(0, 1), (0, -1), (1, 1), (1, -1)]:
            for c in range(2):
                coords = loc
                coords[i] = coords[i] + (c * m)
                affected.append((coords))
                if self.is_item_here(coords):
                    break

        return affected

    def is_item_here(self, coords):
        return len(self.game_state.entity_at(coords)) == 2

    def bombing_value(self, x, y):
        points = 0
        block_name = ""
        for x_val in range(x - 2, x + 2):
            block = self.game_state.entity_at((x_val, y))
            if block_name == "sb":
                points = points + 2
            elif block_name == "ob":
                return 10  ## ASDF NEED TO TRACK BLOCK HP
            points = points + self.block_values(block)
