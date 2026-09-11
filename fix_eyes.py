"""Replace the Hikari/Aoba eye embroidery with reviewed SVG sewing layers."""

import argparse
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).parent))
from plush_variants import PhotoFrame, color_material, remove, save, surface
from sewing_patterns import read_pattern, sew


def rebuild_eyes(root, student):
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    # The Hikari file is also a material library for every student generator.
    for material in bpy.data.materials:
        if material.name[:2].isdigit() and ' | ' in material.name:
            material.use_fake_user = True
    source = Path(__file__).parent/'patterns'/f'{student.lower()}_eyes.svg'
    colors = {part['fill'] for part in read_pattern(source) if part['fill']}
    materials = {hex_color: bpy.data.materials.get(f'{student} | eye thread {hex_color}') or color_material(f'{student} | eye thread {hex_color}',
        tuple(int(hex_color[i:i+2], 16)/255 for i in (1,3,5)), '09 | ivory embroidery') for hex_color in sorted(colors)}
    remove(root, ('Face | eye', 'Face | golden', 'Face | light iris', 'Face | pupil',
                  'Face | white', 'Face | L ', 'Face | R ', 'Face | burgundy', 'Face | wine',
                  'Face | coral', 'Face | rose', 'Face | soft upper', 'Face | ivory glint', 'Face | lower lash'))
    face = surface(bpy.data.objects['Face | broad peach stuffed cushion'])
    frame = PhotoFrame(376, 1000, .0034) if student == 'Hikari' else PhotoFrame()
    objects = sew(root, source, face, materials, frame=frame, prefix='Face | eye ',
                  offset=.007, layer_gap=.003, tolerance=.0015, step=.065)
    root['eye_pattern'] = str(source.relative_to(Path(__file__).parent))
    return objects


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--student', choices=['Hikari', 'Aoba'], required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    root = bpy.data.objects[f'{args.student.upper()} | 170 mm reference plush']
    rig = bpy.data.objects[f'{args.student.upper()} | pose rig']
    rebuild_eyes(root, args.student)
    save(root, rig, args.student, output=args.output)
