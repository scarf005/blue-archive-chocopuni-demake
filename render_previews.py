"""Render the saved plush with the shared studio cameras, without saving scene changes."""

import argparse
import sys
from pathlib import Path
from time import perf_counter

import bpy
from mathutils import Vector

CAMERAS = {'front': 'Front comparison', 'three_quarter': 'Three quarter', 'back': 'Back inspection'}
PRESETS = {'draft': (50, 8), 'final': (100, 64)}


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prefix', default='preview')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--preset', choices=PRESETS, default='final')
    parser.add_argument('--percentage', type=int)
    parser.add_argument('--samples', type=int)
    parser.add_argument('--views', nargs='+', choices=CAMERAS, default=list(CAMERAS))
    parser.add_argument('--focus', nargs='+', metavar='PREFIX',
                        help='Frame matching component names; keep surrounding geometry visible')
    args = parser.parse_args(argv)
    percentage, samples = PRESETS[args.preset]
    args.percentage = args.percentage if args.percentage is not None else percentage
    args.samples = args.samples if args.samples is not None else samples
    if not 1 <= args.percentage <= 100 or args.samples < 1:
        parser.error('percentage must be 1–100 and samples must be positive')
    if args.output is None:
        args.output = Path(__file__).parent
        if args.preset == 'draft':
            args.output /= '.work/previews'
    return args


def frame_camera(camera, objects, scene):
    """Fit rendered geometry; curve bounding boxes can greatly overestimate bevels."""
    if camera.data.type != 'ORTHO':
        raise ValueError('Component focus requires an orthographic inspection camera.')
    bpy.context.view_layer.update()
    graph = bpy.context.evaluated_depsgraph_get()
    inverse = camera.matrix_world.inverted()
    points = []
    for obj in objects:
        evaluated = obj.evaluated_get(graph)
        mesh = evaluated.to_mesh()
        try:
            if mesh:
                transform = inverse @ evaluated.matrix_world
                points.extend(transform @ v.co for v in mesh.vertices)
        finally:
            evaluated.to_mesh_clear()
    if not points:
        raise ValueError('No geometry to frame.')
    bounds = [(min(p[i] for p in points), max(p[i] for p in points)) for i in (0, 1)]
    frame = camera.data.view_frame(scene=scene)
    size = [max(p[i] for p in frame)-min(p[i] for p in frame) for i in (0, 1)]
    scale = max((high-low)/span for (low,high),span in zip(bounds,size))
    if scale <= 0:
        raise ValueError('Focused components have no visible extent.')
    world = camera.matrix_world.copy()
    world.translation += world.to_3x3() @ Vector((sum(bounds[0])/2, sum(bounds[1])/2, 0))
    camera.matrix_world = world
    camera.data.ortho_scale *= scale * 1.12
    bpy.context.view_layer.update()


def render_previews(args):
    scene = bpy.context.scene
    focus = [o for o in scene.objects if args.focus and o.type in {'MESH', 'CURVE'}
             and not o.hide_render and o.name.startswith(tuple(args.focus))]
    if args.focus and not focus:
        raise ValueError(f'No visible components match {args.focus}.')
    cameras = [scene.objects[CAMERAS[view]] for view in args.views]
    camera_state = {camera: (camera.matrix_world.copy(), camera.data.ortho_scale) for camera in cameras}
    render, settings = scene.render, scene.render.image_settings
    saved = [(render, key, getattr(render, key)) for key in
             ('resolution_x', 'resolution_y', 'resolution_percentage', 'filepath')]
    saved += [(settings, key, getattr(settings, key)) for key in ('file_format', 'color_mode', 'quality')]
    saved += [(scene, 'camera', scene.camera), (scene.cycles, 'samples', scene.cycles.samples)]
    try:
        render.resolution_x, render.resolution_y = 1200, 1500
        render.resolution_percentage = args.percentage
        scene.cycles.samples = args.samples
        settings.file_format, settings.color_mode, settings.quality = 'WEBP', 'RGB', 90
        args.output.mkdir(parents=True, exist_ok=True)
        for view, camera in zip(args.views, cameras):
            scene.camera = camera
            if focus:
                frame_camera(camera, focus, scene)
            render.filepath = str(args.output / f'{args.prefix}_{view}.webp')
            started = perf_counter()
            bpy.ops.render.render(write_still=True)
            print(f'RENDER {view}: {1200*args.percentage//100}x{1500*args.percentage//100}, '
                  f'{args.samples} samples, {perf_counter()-started:.3f}s -> {render.filepath}')
    finally:
        for owner, key, value in saved:
            setattr(owner, key, value)
        for camera, (world, scale) in camera_state.items():
            camera.matrix_world = world
            camera.data.ortho_scale = scale
        bpy.context.view_layer.update()


if __name__ == '__main__':
    render_previews(parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []))
