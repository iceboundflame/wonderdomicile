"""Util for making parameterized effects

Borrowed from dliu's merkaba project
"""

import time


class PeriodicTrigger(object):
    def __init__(self, interval):
        self.interval = interval
        self.last = time.perf_counter()

    def step(self):
        if time.perf_counter() - self.last > self.interval:
            self.last = time.perf_counter()
            return True
        return False

    def reset(self):
        self.last = time.perf_counter()


class EdgeTrigger(object):
    """Trigger each time the input signal, assumed to be monotonically increasing, resets.
    """
    def __init__(self):
        self.last = None

    def step(self, in_val):
        last = in_val if self.last is None else self.last
        self.last = in_val
        return in_val < last


class ValueChangeTrigger(object):
    """Trigger each time the input signal changes.
    """
    def __init__(self):
        self.last = None

    def step(self, in_val):
        last = in_val if self.last is None else self.last
        self.last = in_val
        return in_val != last
