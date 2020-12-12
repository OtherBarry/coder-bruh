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
