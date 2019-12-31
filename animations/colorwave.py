import datetime

import numpy as np
from bibliopixel import animation
from bibliopixel.colors import COLORS
from bibliopixel.animation.matrix import Matrix

class Horizontal(Matrix):
    def __init__(self, *args, **kwds):
        #The base class MUST be initialized by calling super like this
        super().__init__(*args, **kwds)

    def step(self, amt=1):
        for i in range(self.layout.width):
            for j in range(self.layout.height):
                self.layout.set(i,j,self.palette(1*i + self._step))

        self._step += amt

class Vertical(Matrix):
    def __init__(self, *args,
                 bloom=False,
                 color_speed=2,
                 color_distance=2,
                 **kwds):
        #The base class MUST be initialized by calling super like this

        # Causes the color to bloom from the center
        self.bloom = bloom

        # higher values make colors change faster
        self.color_speed = color_speed

        # higher values display more colors in a single frame
        self.color_distance = color_distance

        super().__init__(*args, **kwds)

    def step(self, amt=1):
        if self.bloom:
            distance = abs(self.layout.height / 2 - np.arange(self.layout.height))
            vals = self._step * self.color_speed - distance * self.color_distance
        else:
            vals = self.color_speed * np.arange(self.layout.height) + self._step * self.color_distance

        colors = self.palette.batch_apply_palette(vals)
        self.layout.color_list[self.layout.coord_map] = colors[:,np.newaxis,:]

        self._step += amt
