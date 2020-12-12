import random


class Agent:
    def __init__(self):
        self.actions = ["u", "d", "l", "r", "b"]

    def next_move(self, game_state, player_state):
        return random.choice(self.actions)
