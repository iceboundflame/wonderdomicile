import math

import numpy as np
from bibliopixel.animation.matrix import Matrix
from bibliopixel.colors import COLORS, palette


# based on shift5 from https://stackoverflow.com/a/42642326/133518
from animations import np_palettes


def shift_and_copy_2d(arr, num):
    result = np.empty_like(arr)
    if num > 0:
        result[:,:num] = arr[:,[-1]]
        result[:,num:] = arr[:,:-num]
    elif num < 0:
        result[:,num:] = arr[:,[-1]]
        result[:,:num] = arr[:,-num:]
    else:
        result[:] = arr
    return result


class FlameSimulator:
    def __init__(self, width, height):
        super().__init__()

        self.cooling = 3
        self.sparking = 10/255

        self.width = width
        self.height = height

        self.heat_buf = np.zeros((self.width, self.height,))

    def step(self, heat_mask=None):
        """
        :param heat_mask: shape (width,) - 0-1 multiplier for the probability of sparking that column.
        :return:
        """

        # intensity = math.pow(1 - self.ctx.beat_tracker.beat_raw, self.param('beat_alpha'))
        intensity = 1

        # Step 1.  Cool down every cell a little
        self.heat_buf = self.heat_buf - np.random.random_sample(self.heat_buf.shape) * (
                self.cooling / self.height)
        np.clip(self.heat_buf, 0, 1, self.heat_buf)

        # Step 2.  Heat from each cell drifts 'up' and diffuses a little
        # self.heat_buf = 0.33 * shift_and_copy_2d(self.heat_buf, -1) + \
        #                 0.67 * shift_and_copy_2d(self.heat_buf, -2)

        self.heat_buf =\
            0.25 * shift_and_copy_2d(self.heat_buf, -1) + \
            0.25 * shift_and_copy_2d(self.heat_buf, -2) + \
            0.25 * shift_and_copy_2d(self.heat_buf, -3) + \
            0.25 * shift_and_copy_2d(self.heat_buf, -4)

        # Step 3.  Randomly ignite new 'sparks' of heat
        spark_probs = self.sparking * intensity
        if heat_mask is not None:
            assert heat_mask.shape == (self.width,)
            spark_probs = heat_mask * spark_probs

        self.heat_buf[:,self.height-1] += \
            np.random.uniform(160/255, 1, self.width) * (
                    np.random.uniform(0, 1, self.width) < spark_probs)

        np.clip(self.heat_buf, 0, 1, self.heat_buf)


class Fire(Matrix):
    def __init__(self, *args,
                 **kwds):
        # The base class MUST be initialized by calling super like this
        super().__init__(*args, **kwds)

        width, height = self.layout.dimensions
        self.flames = FlameSimulator(width, height)

        self.palette = np_palettes.palettes['bhw1_03']

    def step(self, amt=1):
        self.flames.step()

        self.color_list[self.layout.coord_map] = \
            np_palettes.apply_palette_1(self.flames.heat_buf, self.palette).transpose((1, 0, 2))

        # for i in range(self.layout.width):
        #     for j in range(self.layout.height):
        #         c = int(self.flames.heat_buf[i,j] * 255)
        #         c = self.palette(c)
        #         # c = (c,c,c)
        #         self.layout.set(i, j, c)

        self._step += amt
