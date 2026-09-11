"""Validate the saved Nozomi/Aoba geometry, visible face, packed references and FK rig."""

import math

import bpy
from mathutils import Vector

scene = bpy.context.scene
root = next(o for o in scene.objects if o.type == 'EMPTY' and o.get('student'))
student = root['student']
rig = scene.objects[f'{student.upper()} | pose rig']
parts = [o for o in root.children_recursive if o.type in {'MESH', 'CURVE'}]
stage = [o for o in scene.objects if o not in parts and o not in {root, rig}]
stage_matrices = {o.name: o.matrix_world.copy() for o in stage}
assert all(o.parent == rig for o in parts), 'Unattached component'
assert all(o in root.children_recursive for o in root.users_collection[0].objects if o != root)
assert 3000 <= sum(len(o.data.vertices) for o in parts if o.type == 'MESH') <= 9000
assert all(i.packed_file for i in bpy.data.images if i.name.startswith('REFERENCE |'))
assert any(student+' Chocopuni' in i.name for i in bpy.data.images)
assert any(student+' official' in i.name for i in bpy.data.images)
assert all(not o.hide_render for o in parts)
for obj in parts:
    if obj.parent_type == 'BONE':
        assert obj.parent_bone in rig.pose.bones, obj.name
    else:
        assert obj.type == 'MESH' and any(m.type == 'ARMATURE' for m in obj.modifiers)
        assert all(abs(sum(g.weight for g in v.groups)-1) < 1e-6 for v in obj.data.vertices)


def vertices(objects=parts):
    bpy.context.view_layer.update()
    graph = bpy.context.evaluated_depsgraph_get()
    result = {}
    for obj in objects:
        evaluated = obj.evaluated_get(graph)
        mesh = evaluated.to_mesh()
        result[obj.name] = [evaluated.matrix_world @ v.co for v in mesh.vertices]
        evaluated.to_mesh_clear()
    return result


def distance(a, b):
    assert a.keys() == b.keys()
    assert all(len(a[k]) == len(b[k]) for k in a)
    return max((p-q).length for k in a for p,q in zip(a[k],b[k]))


def reset():
    for bone in rig.pose.bones:
        bone.matrix_basis.identity()
    bpy.context.view_layer.update()


baseline = vertices()
assert all(math.isfinite(c) for points in baseline.values() for p in points for c in p)
assert all(-1.6 < p.x < 1.6 and -.95 < p.y < 1.1 and -.1 < p.z < 3.6
           for points in baseline.values() for p in points), 'Unexpected component scale or placement'

# Front-facing embroidery must be in front of the cushion and unobscured by rear hair.
face_samples = {'Nozomi': [(275, 490), (465, 490), (377, 544)],
                'Aoba': [(286, 516), (468, 516), (375, 576)]}[student]
for x, y in face_samples:
    hit, _, _, _, obj, _ = scene.ray_cast(bpy.context.evaluated_depsgraph_get(),
        Vector(((x-375)*.0038, -5, (947-y)*.0038)), Vector((0, 1, 0)))
    assert hit and obj.name.startswith('Face |'), f'Face obscured at {(x,y)}: {obj.name if hit else None}'

if student == 'Aoba':
    for sign in (-1, 1):
        origin = Vector((sign*3, -4, 2.1))
        direction = (Vector((sign*.75, -.2, 2.1))-origin).normalized()
        hit, _, _, _, obj, _ = scene.ray_cast(bpy.context.evaluated_depsgraph_get(), origin, direction)
        assert hit and obj.name.startswith('Hair |'), 'Exposed scalp above the ear'

halo = [o for o in parts if o.name.startswith('Halo |')]
assert halo and all(o.parent_bone == 'head' for o in halo)
assert any(o.type == 'MESH' and max(v.co.z for v in o.data.vertices)
           - min(v.co.z for v in o.data.vertices) > .8 for o in halo), 'Incomplete halo'

# Every control must affect real geometry, without moving the opposite limb.
for bone in rig.pose.bones:
    reset()
    bone.rotation_euler.x = .20
    posed = vertices()
    assert distance(baseline, posed) > .005, f'Unused control: {bone.name}'
    if bone.name.startswith(('upper_arm.', 'forearm.', 'hand.', 'thigh.', 'shin.', 'foot.')):
        opposite = 'R' if bone.name.endswith('.L') else 'L'
        for prefix in ('Glove | cloth mitten ', 'Shoes | stuffed oval sole '):
            name = prefix+opposite
            assert distance({name: baseline[name]}, {name: posed[name]}) < 1e-5
reset()
rig.pose.bones['head'].rotation_euler.z = .25
posed = vertices()
for obj in halo:
    assert distance({obj.name: baseline[obj.name]}, {obj.name: posed[obj.name]}) > .1
reset()
rig.pose.bones['root'].location = (.2, -.1, .3)
delta = (rig.matrix_world @ rig.data.bones['root'].matrix_local).to_3x3() @ Vector((.2, -.1, .3))
assert distance({n: [p+delta for p in points] for n,points in baseline.items()}, vertices()) < 1e-5
reset()
for name in ('spine', 'head', 'upper_arm.L', 'forearm.R', 'hair_front.L', 'hair_back.R'):
    rig.pose.bones[name].rotation_euler = (.1, -.1, .15)
assert distance(baseline, vertices()) > .1
reset()
assert distance(baseline, vertices()) < 1e-5, 'Pose reset changed appearance'
assert all(o.matrix_world == stage_matrices[o.name] for o in stage), 'Posing moved the studio'
print(f'PASS: {student}, {len(parts)} components, {len(rig.data.bones)} controls; '
      'geometry budget, visible face, packed references, attachments, weights, '
      'independent limbs, halo following head, root translation, combined pose and reset')
