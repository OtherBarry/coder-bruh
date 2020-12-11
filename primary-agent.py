"""File for primary agent"""
import random
from enum import Enum


class Action(Enum):
    UP = "u"
    DOWN = "d"
    LEFT = "l"
    RIGHT = "r"
    BOMB = "b"


class Agent:
    """Class for primary agent"""

    def __init__(self):
        self.tick_number = -1
        self.updated = True
        self.action_queue = []

    def next_move(self, game_state, player_state):
        """This method is called each time the player needs to choose an action"""
        updated = game_state.tick_number != self.tick_number
        self.tick_number = game_state.tick_number
        if not updated:
            return self.action_queue.pop()
        return None

    def calculate_distance(self):
        pass
