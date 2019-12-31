import math
from bibliopixel import animation
from bibliopixel.colors import COLORS
from bibliopixel.animation.matrix import Matrix

class Chase(Matrix):
    def __init__(self, *args,
                 alternating=2,
                 spacing=40,
                 length=2,
                 alternating_colors=True,
                 fade=0.5,
                 direction=-1,
                 **kwds):

        # Specified columns to chase in reverse.
        # Every $alternating will be reversed.
        self.alternating = alternating

        # If alternating, also alternate colors
        self.alternating_colors = alternating_colors

        # Length of empty space between each chase
        self.spacing = spacing

        # Length of the chase
        self.length = length

        # Chase goes up or down (up, down)
        self.direction = direction

        # Fades previously lit pixels by a percentage
        self.fade = fade

        super().__init__(*args, **kwds)

    def step(self, amt=1):
        colors = [self.palette(self._step), self.palette(self._step * -1)]
        color = colors[0]

        self.layout.color_list[:] = self.layout.color_list * self.fade

        for i in range(self.layout.width):

            if self.alternating > 0 and (math.floor(i / self.alternating)) % 2 == 0:
                alter_reverse = 1
                color = colors[0]
            else:
                alter_reverse = -1
                if self.alternating_colors:
                    color = colors[1]

            for j in range(self.layout.height):
                pos = j * alter_reverse * self.direction + self._step

                if pos % (self.spacing + self.length) in range(self.length):
                    self.layout.set(i, j, color)

        self._step += amt

class ChaseUp(Matrix):
    def __init__(self, *args,
                 spacing=40,
                 length=2,
                 fade=0.5,
                 direction=-1,
                 **kwds):

        # Length of empty space between each chase
        self.spacing = spacing

        # Length of the chase
        self.length = length

        # Chase goes up or down (up, down)
        self.direction = direction

        # Fades previously lit pixels by a percentage
        self.fade = fade

        super().__init__(*args, **kwds)

    def step(self, amt=1):
        self.layout.color_list[:] = self.layout.color_list * self.fade

        for i in range(self.layout.width):
            color = self.palette(self._step + 50 * math.floor(i/4))
            for j in range(self.layout.height):
                pos = j * self.direction - self._step

                if pos % (self.spacing + self.length) in range(self.length):
                    self.layout.set(i, j, color)

        self._step += amt
