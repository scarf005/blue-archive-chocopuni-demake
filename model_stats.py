"""Report base and evaluated geometry for the active Blender scene."""

import json
from collections import Counter

import bpy

scene = bpy.context.scene
graph = bpy.context.evaluated_depsgraph_get()
counts = Counter()
categories = Counter()
for obj in scene.objects:
    if obj.type not in {'MESH', 'CURVE'}:
        continue
    counts[obj.type.lower() + '_objects'] += 1
    if obj.type == 'MESH':
        counts['base_mesh_vertices'] += len(obj.data.vertices)
        categories[obj.name.split(' |')[0].split(' ')[0]] += len(obj.data.vertices)
    evaluated = obj.evaluated_get(graph)
    mesh = evaluated.to_mesh()
    counts['evaluated_' + obj.type.lower() + '_vertices'] += len(mesh.vertices)
    mesh.calc_loop_triangles()
    counts['evaluated_triangles'] += len(mesh.loop_triangles)
    evaluated.to_mesh_clear()
print(json.dumps({'scene': scene.name, **counts, 'base_vertices_by_part': categories}, indent=2))
