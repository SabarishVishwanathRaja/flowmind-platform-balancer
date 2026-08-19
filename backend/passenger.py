"""A single simulated passenger."""


class Passenger:
    __slots__ = ("zone", "x", "y", "moving_to", "move_ticks")

    def __init__(self, zone, rng):
        self.zone = zone
        self.x = rng.uniform(0.08, 0.92)
        self.y = rng.uniform(0.12, 0.88)
        self.moving_to = None
        self.move_ticks = 0
