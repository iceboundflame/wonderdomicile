"""
Fast palette implementation bypassing BiblioPixel crap
"""
import glob
import os

import numpy as np


def load_palettes(basedir):
    palettes = {}
    for f in glob.iglob(os.path.join(basedir, '*.npy')):
        p = np.load(f)
        assert p.shape == (256, 3), "Palette shape " + str(p.shape)
        p.flags.writeable = False
        name = os.path.splitext(os.path.basename(f))[0]
        palettes[name] = p
    assert len(palettes), "No palettes loaded"
    return palettes


palettes = load_palettes(os.path.join(os.path.dirname(__file__), "..", 'palettes/'))
print("Loaded palettes", ', '.join(palettes.keys()))


def apply_palette_1(vals_1, palette):
    """Map floats in [0,1] to the given palette (a numpy array of shape (256,3))
    :param vals_1
    :returns array with shape (..., 3) matching vals_1
    """
    # assert vals_1.ndim == 1
    return palette[(np.clip(vals_1, 0, 1) * 255).astype(np.uint8)]
