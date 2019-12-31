import math
import random

from bibliopixel.animation.matrix import Matrix


class Sparkles(Matrix):
    def __init__(self, *args,
                 fade=0.8,
                 sparkle_prob=0.005,
                 **kwds):

        self.fade = fade
        self.sparkle_prob = sparkle_prob

        # The base class MUST be initialized by calling super like this
        super().__init__(*args, **kwds)

    def step(self, amt=1):
        self.layout.color_list[:] = self.layout.color_list * self.fade

        for i in range(self.layout.width):
            # color = self.palette(self._step + 50 * math.floor(i / 2))
            for j in range(self.layout.height):
                # color = self.palette(random.randint(0, 255))
                color = (255,255,255)

                if random.random() < self.sparkle_prob:
                    self.layout.set(i, j, color)

        self._step += amt
