import bibliopixel.animation.matrix
import numpy as np
import scipy.interpolate

from wonderdomicile import params, triggers
from wonderdomicile.control.audio import GlobalAnalyzer


def trilerp(pts, colors):
    lerper = scipy.interpolate.RegularGridInterpolator(
        points=([0,1],[0,1],[0,1]),
        values=colors,
    )
    return lerper(pts)


COLOR_CUBES = {
    'fire': [[[[0, 0, 0], [1, 1, 1], ], [[1, 1, 0], [1, 1, 0.8], ]],
               [[[1, 0, 0], [1, 0.5, 0.5], ], [[1, 0.5, 0], [1, 0.8, 0.5]]]],
    'rgb': [[[[0., 0., 0.], [0., 0., 1.]], [[0., 1., 0.], [0., 1., 1.]]],
              [[[1., 0., 0.], [1., 0., 1.]], [[1., 1., 0.], [1., 1., 1.]]]],
}


class ScrollingSpectrumVisualizer(params.ParamProvider,
                                  bibliopixel.animation.matrix.Matrix):
    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)

        self.add_param(params.SelectParam('colors', COLOR_CUBES.keys()), 'rgb')
        self.buf = np.zeros((self.height//2, 3))

    def step(self, amt=1):
        self.buf[1:, :] = self.buf[:-1]

        colors = COLOR_CUBES[self.param('colors')]

        self.buf[0, :] = trilerp(np.clip(GlobalAnalyzer.spec3.normalized, 0, 1), colors) * 255
        # self.buf[0, :] = trilerp((0.5, 0.5, 0.5), colors) * 255

        coord_map = np.array(self.layout.coord_map)
        self.color_list[coord_map[self.height//2+1:, :]] = self.buf[:, np.newaxis, :]
        self.color_list[coord_map[self.height//2-1::-1, :]] = self.buf[:, np.newaxis, :]


# class ScrollingSpectrumVisualizerByBand(base_effect.Effect):
#     def __init__(self, ctx):
#         super().__init__(ctx)
#
#         self.buf = np.zeros((data.N_LED_PER_SEGMENT, 4))
#
#     def step(self):
#         super().step()
#         self.buf[1:,:] = self.buf[:-1]
#         self.buf[0,:] = np.clip(self.ctx.audio.spec4.normalized, 0, 1)
#
#     def render(self):
#         vals = self.buf[::-1,:]
#         buf = np.zeros((data.N_ALL, 3))
#         buf[data.opposite_tetra_segments_indexes[0,:],:] = \
#             ops.gray1_to_rgb(np.tile(vals[:,0], 6), [255,0,0])
#         buf[data.opposite_tetra_segments_indexes[1,:],:] = \
#             ops.gray1_to_rgb(np.tile(vals[:,1], 6), [255,255,0])
#         buf[data.opposite_tetra_segments_indexes[3,:],:] = \
#             ops.gray1_to_rgb(np.tile(vals[:,2], 6), [0,255,255])
#         buf[data.opposite_tetra_segments_indexes[2,:],:] = \
#             ops.gray1_to_rgb(np.tile(vals[:,3], 6), [255,255,255])
#
#         return buf
#
#
# class SpectrumVisualizerByBand(base_effect.Effect):
#     def __init__(self, ctx):
#         super().__init__(ctx)
#
#         self.buf = np.zeros((data.N_LED_PER_SEGMENT, 3))
#
#     def step(self):
#         super().step()
#         self.buf[1:,:] = self.buf[:-1]
#         self.buf[:,:] = np.clip(self.ctx.audio.spec3.normalized, 0, 1)
#
#     def render(self):
#         buf = np.zeros((data.N_ALL, 3))
#         # print(np.tile(self.buf[:,0], 12).shape)
#         # print((np.tile(np.tile(self.buf[:,0], 12)[:,np.newaxis], (1,3)) * [255,0,0]).shape)
#         buf[data.all_segments_indexes[:12*data.N_LED_PER_SEGMENT],:] = \
#             ops.gray1_to_rgb(np.tile(self.buf[:,0], 12), [255,0,0])
#         buf[data.all_segments_indexes[12*data.N_LED_PER_SEGMENT:24*data.N_LED_PER_SEGMENT],:] = \
#             ops.gray1_to_rgb(np.tile(self.buf[:,1], 12), [0,255,0])
#         buf[data.all_segments_indexes[24*data.N_LED_PER_SEGMENT:],:] = \
#             ops.gray1_to_rgb(np.tile(self.buf[:,2], 12), [255,255,255])
#
#         # return ops.gray1_to_rgb(buf)
#         return buf
#
#
# class ScrollingSpectrumVisualizerBy12Band(base_effect.Effect):
#     def __init__(self, ctx):
#         super().__init__(ctx)
#
#         self.buf = np.zeros((12, data.N_LED_PER_SEGMENT))
#
#     def step(self):
#         super().step()
#         self.buf[:,1:] = self.buf[:,:-1]
#         self.buf[:,0] = np.clip(self.ctx.audio.spec12.normalized, 0, 1)
#
#     def render(self):
#         vals = self.buf[:,::-1]
#         buf = np.zeros((data.N_ALL, 3))
#         buf[data.opposite_tetra_segments_indexes[0,:],:] = \
#             ops.gray1_to_rgb(np.tile(vals[0:3,:].ravel(), 2), [255,0,0])
#         buf[data.opposite_tetra_segments_indexes[1,:],:] = \
#             ops.gray1_to_rgb(np.tile(vals[3:6,:].ravel(), 2), [255,255,0])
#         buf[data.opposite_tetra_segments_indexes[2,:],:] = \
#             ops.gray1_to_rgb(np.tile(vals[6:9,:].ravel(), 2), [0,255,255])
#         buf[data.opposite_tetra_segments_indexes[3,:],:] = \
#             ops.gray1_to_rgb(np.tile(vals[9:12,:].ravel(), 2), [255,255,255])
#
#         return buf


# class LevelMask(base_effect.ColorMappableGrayEffect):
#     def __init__(self, ctx):
#         super().__init__(ctx)
#
#     def render_gray(self):
#         return np.ones(data.N_ALL) * self.ctx.audio.spl.normalized