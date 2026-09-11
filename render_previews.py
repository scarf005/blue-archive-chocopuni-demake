"""Render the saved plush with the shared studio cameras, without saving scene changes."""

import argparse
import sys
from pathlib import Path

import bpy

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--prefix', default='preview')
parser.add_argument('--output', type=Path, default=Path(__file__).parent)
parser.add_argument('--percentage', type=int, default=100)
parser.add_argument('--samples', type=int, default=64)
parser.add_argument('--views', nargs='+', choices=['front', 'three_quarter', 'back'],
                    default=['front', 'three_quarter', 'back'])
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
scene = bpy.context.scene
scene.render.resolution_x, scene.render.resolution_y = 1200, 1500
scene.render.resolution_percentage = args.percentage
scene.cycles.samples = args.samples
scene.render.image_settings.file_format = 'WEBP'
scene.render.image_settings.color_mode = 'RGB'
scene.render.image_settings.quality = 90
for view in args.views:
    scene.camera = scene.objects[{'front': 'Front comparison', 'three_quarter': 'Three quarter',
                                  'back': 'Back inspection'}[view]]
    scene.render.filepath = str(args.output / f'{args.prefix}_{view}.webp')
    bpy.ops.render.render(write_still=True)
