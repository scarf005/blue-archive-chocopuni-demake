"""Run with Blender on either the unrigged source or the saved rigged model."""

import math
import runpy
from pathlib import Path

import bpy
from mathutils import Vector

module = runpy.run_path(str(Path(__file__).with_name('rig_hikari.py')))
scene = bpy.context.scene
root = scene.objects[module['ROOT']]
parts = [o for o in root.children_recursive if o.type in {'MESH', 'CURVE'}]
stage = [o for o in scene.objects if o not in parts and o != root and o.type != 'ARMATURE']


def vertices(objects):
    bpy.context.view_layer.update()
    graph = bpy.context.evaluated_depsgraph_get()
    result = {}
    for obj in objects:
        evaluated = obj.evaluated_get(graph)
        mesh = evaluated.to_mesh()
        if mesh:
            result[obj.name] = [evaluated.matrix_world @ v.co for v in mesh.vertices]
            evaluated.to_mesh_clear()
    return result


def error(a, b):
    assert a.keys() == b.keys()
    assert all(len(a[n]) == len(b[n]) for n in a), 'Topology changed'
    return max((x - y).length for n in a for x, y in zip(a[n], b[n]))


def reset():
    for bone in rig.pose.bones:
        bone.matrix_basis.identity()
    bpy.context.view_layer.update()


baseline = vertices(parts)
stage_matrices = {o.name: o.matrix_world.copy() for o in stage}
rig = scene.objects.get(module['RIG']) or module['add_rig']()
assert error(baseline, vertices(parts)) < 1e-5, 'Rest appearance changed'
assert len(rig.data.bones) == 24
try:
    module['add_rig']()
    raise AssertionError('Duplicate rig was accepted')
except ValueError as exc:
    assert 'already has' in str(exc)
try:
    module['component_binding']('Unknown component')
    raise AssertionError('Unknown component was silently bound')
except ValueError:
    pass

for obj in parts:
    assert obj.parent == rig, obj.name
    if obj.parent_type == 'BONE':
        assert obj.parent_bone in rig.pose.bones, obj.name
    else:
        assert obj.type == 'MESH'
        for v in obj.data.vertices:
            assert abs(sum(g.weight for g in v.groups) - 1) < 1e-6

# Every control must move actual geometry; opposite limbs must remain independent.
for bone in rig.pose.bones:
    reset()
    bone.rotation_euler.x = math.radians(20)
    posed = vertices(parts)
    assert error(baseline, posed) > .01, f'No visible influence: {bone.name}'
    if bone.name.startswith(('upper_arm.', 'forearm.', 'hand.', 'thigh.', 'shin.', 'foot.')):
        opposite = 'R' if bone.name.endswith('.L') else 'L'
        for prefix in ('Glove | cloth mitten ', 'Shoes | stuffed oval sole '):
            name = prefix + opposite
            assert error({name: baseline[name]}, {name: posed[name]}) < 1e-5, bone.name

reset()
rig.pose.bones['root'].location = (.2, -.1, .3)
translated = vertices(parts)
delta = (rig.matrix_world @ rig.data.bones['root'].matrix_local).to_3x3() @ Vector((.2, -.1, .3))
expected = {n: [v + delta for v in vs]
            for n, vs in baseline.items()}
assert error(expected, translated) < 1e-5, 'Root did not move every component together'

reset()
for name, rotation in {
    'spine': (0, -.08, -.06), 'head': (0, .12, .12),
    'upper_arm.L': (.12, 0, -.25), 'forearm.L': (.10, 0, -.35),
    'hand.L': (0, .12, 0), 'upper_arm.R': (.08, 0, .18),
    'thigh.L': (-.18, .08, 0), 'shin.R': (-.15, 0, 0),
    'hair_front.R': (.08, 0, 0), 'belt_tail': (.15, 0, 0),
}.items():
    rig.pose.bones[name].rotation_euler = rotation
posed = vertices(parts)
assert all(math.isfinite(c) for vs in posed.values() for v in vs for c in v)
assert error(baseline, posed) > .1
for obj in stage:
    assert obj.matrix_world == stage_matrices[obj.name], f'Studio moved: {obj.name}'

# Optional render evidence; restore scene settings and neutral pose afterwards.
import os
render_path = os.environ.get('HIKARI_POSE_RENDER')
if render_path:
    old = scene.render.filepath, scene.render.resolution_percentage, scene.cycles.samples
    scene.render.filepath = render_path
    scene.render.resolution_percentage = 40
    scene.cycles.samples = 16
    bpy.ops.render.render(write_still=True)
    scene.render.filepath, scene.render.resolution_percentage, scene.cycles.samples = old
reset()
assert error(baseline, vertices(parts)) < 1e-5, 'Reset failed'
print(f'PASS: {len(parts)} components, 24 controls, rest preservation, weights, '
      'bilateral independence, root movement, combined pose, reset, and duplicate guard')
