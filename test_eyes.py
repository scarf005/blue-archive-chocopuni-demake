"""Verify visible scleras, separate iris layers, shallow relief and head attachment."""

import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).parent))
from plush_variants import PhotoFrame, surface

root = next(o for o in bpy.context.scene.objects if o.type == 'EMPTY' and 'reference plush' in o.name)
student = root.get('student', 'Hikari')
if student == 'Hikari':
    for name in ('12 | amber iris satin stitch', '13 | butter iris satin stitch',
                 '14 | chocolate eye outlines', '15 | brown pupils'):
        assert name in bpy.data.materials and bpy.data.materials[name].use_fake_user, name
if student == 'Aoba':
    assert all(f'Face | eyebrow {side}' in bpy.data.objects for side in ('L','R')), 'Eye edits removed eyebrows'
frame = PhotoFrame(376,1000,.0034) if student == 'Hikari' else PhotoFrame()
boxes = {'Hikari': [(207,399,333,512),(433,390,562,510)],
         'Aoba': [(220,465,332,550),(398,465,512,550)]}[student]
face = surface(bpy.data.objects['Face | broad peach stuffed cushion'])
graph = bpy.context.evaluated_depsgraph_get()
for side, (left,top,right,bottom) in zip(('L','R'), boxes):
    white, eyes = 0, 0
    for x in range(left,right,2):
        for y in range(top,bottom,2):
            px,pz = frame((x,y))
            hit, _, _, _, obj, _ = bpy.context.scene.ray_cast(graph, Vector((px,-5,pz)), Vector((0,1,0)))
            if hit and obj.name.startswith('Face | eye '):
                eyes += 1
                white += obj.name == 'Face | eye sclera-'+side
    assert eyes > 150 and .04 < white/eyes < .40, (side, white, eyes)
    print(f'{student} {side}: visible sclera {white}/{eyes} eye probes ({white/eyes:.1%})')
    for label in ('sclera','iris','pupil','glint'):
        obj = bpy.data.objects[f'Face | eye {label}-{side}']
        assert obj.parent_bone == 'head'
        for vertex in obj.data.vertices:
            p = obj.matrix_world @ vertex.co
            assert .003 < face(p.x,p.z)-p.y < .045, (obj.name, p)
assert sum(len(o.data.vertices) for o in root.children_recursive if o.type == 'MESH') <= 9000
print('PASS: visible scleras, distinct iris/pupil/glint layers, shallow surface relief, head bindings and budget')
