#! /usr/bin/python

import os
import pygame

drivers = [
    "kmsdrm",
    "directfb",
    "fbcon",
    "dga",
    "svgalib",
    "ggi",
    ""
]

for d in drivers:
    os.environ["SDL_VIDEODRIVER"] = d
    pygame.init()
    print('Testing driver:', pygame.display.get_driver())
    print (pygame.display.get_wm_info())
