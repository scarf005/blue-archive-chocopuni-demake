"""Compare a rebuilt candidate with a saved model, including evaluated geometry and references."""

import argparse
import hashlib
import sys
from collections import Counter

import bpy

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--baseline', required=True)
parser.add_argument('--candidate', required=True)
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])


def snapshot(path):
    bpy.ops.wm.open_mainfile(filepath=path)
    graph = bpy.context.evaluated_depsgraph_get()
    objects = {}
    for obj in bpy.context.scene.objects:
        state = {'type': obj.type, 'parent': obj.parent.name if obj.parent else None,
                 'parent_type': obj.parent_type, 'bone': obj.parent_bone,
                 'matrix': tuple(value for row in obj.matrix_world for value in row)}
        if obj.type in {'MESH', 'CURVE'}:
            evaluated = obj.evaluated_get(graph)
            mesh = evaluated.to_mesh()
            state['vertices'] = [evaluated.matrix_world @ v.co for v in mesh.vertices]
            # Primitive reconstruction can reorder faces without changing connectivity.
            state['faces'] = Counter((tuple(p.vertices), p.material_index, p.use_smooth) for p in mesh.polygons)
            state['materials'] = [m.name if m else None for m in obj.data.materials]
            evaluated.to_mesh_clear()
        elif obj.type == 'ARMATURE':
            state['rest_bones'] = {b.name: (b.parent.name if b.parent else None,
                tuple(value for row in b.matrix_local for value in row)) for b in obj.data.bones}
        objects[obj.name] = state
    images = {i.name: hashlib.sha256(i.packed_file.data).hexdigest()
              for i in bpy.data.images if i.name.startswith('REFERENCE |') and i.packed_file}
    materials = {m.name: tuple(m.diffuse_color) for m in bpy.data.materials}
    return objects, images, materials


before, before_images, before_materials = snapshot(args.baseline)
after, after_images, after_materials = snapshot(args.candidate)
assert before.keys() == after.keys(), 'Component names changed'
assert before_images == after_images, 'Packed reference images changed'
assert before_materials == after_materials, 'Material palette changed'
max_error = 0
for name, left in before.items():
    right = after[name]
    for key in left.keys() - {'vertices', 'matrix'}:
        assert left[key] == right[key], f'{name}: {key} changed'
    assert max(abs(a-b) for a,b in zip(left['matrix'],right['matrix'])) < 1e-6, name
    if 'vertices' in left:
        assert len(left['vertices']) == len(right['vertices']), f'{name}: vertex count changed'
        error = max((a-b).length for a,b in zip(left['vertices'],right['vertices']))
        assert error < 1e-5, f'{name}: evaluated geometry moved by {error}'
        max_error = max(max_error, error)
print(f'PASS: rebuild preserves {len(before)} objects, topology, bindings, rest bones, '
      f'palette and packed references; maximum vertex displacement {max_error:.9g}')
