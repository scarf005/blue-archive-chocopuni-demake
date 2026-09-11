"""Restore Hikari's continuous felt halo, using the photographed rear of the cap."""

import argparse
import math
import sys

import bpy
from mathutils import Vector, geometry

REFERENCE = 'https://arca.live/b/bluearchive/181993371'


def attach(obj, root, bone='head'):
    """Keep authored world coordinates when attaching a sewn piece to its control."""
    world = obj.matrix_world.copy()
    rig = next((o for o in root.children if o.type == 'ARMATURE'), None)
    obj.parent = rig or root
    if rig:
        obj.parent_type = 'BONE'
        obj.parent_bone = bone
    bpy.context.view_layer.update()
    obj.matrix_world = world


def felt(name, outline, material, collection, *, depth, thickness=.012):
    """A thin X/Z felt cutout; triangulate concave outlines without a centre fan."""
    points = [Vector((x, z)) for x, z in outline]
    vertices, _, faces, *_ = geometry.delaunay_2d_cdt(
        points, [], [list(range(len(points)))], 1, .000001, False)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([(p.x, depth, p.y) for p in vertices], [], faces)
    mesh.update()
    mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    if thickness:
        modifier = obj.modifiers.new('Felt thickness', 'SOLIDIFY')
        modifier.thickness = thickness
        modifier.offset = 0
    return obj


def thread(name, paths, material, collection, *, radius=.008):
    curve = bpy.data.curves.new(name, 'CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 1
    curve.bevel_resolution = 1
    curve.bevel_depth = radius
    for path in paths:
        spline = curve.splines.new('POLY')
        spline.points.add(len(path) - 1)
        for point, co in zip(spline.points, path):
            point.co = (*co, 1)
    curve.materials.append(material)
    obj = bpy.data.objects.new(name, curve)
    collection.objects.link(obj)
    return obj


def add_halo(root, reference_path=None):
    collection = root.users_collection[0]
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    # These were isolated tips of the same cutout, not separate accessories.
    for obj in list(root.children_recursive):
        if obj.name.startswith('Halo |'):
            bpy.data.objects.remove(obj, do_unlink=True)

    ivory = bpy.data.materials['09 | ivory embroidery']
    green = bpy.data.materials['04 | green sewing thread']
    # The circle sits behind the crown; only its tips show in the front photo.
    center_z, radius = 2.88, .53
    arc = lambda r, start, end, count: [
        (r * math.cos(t), center_z + r * math.sin(t))
        for t in [math.radians(start + (end - start) * i / count)
                  for i in range(count + 1)]]
    outline = arc(radius, 18, 162, 40) + [
        (-.99, 2.92), (-1.03, 2.87), (-1.01, 2.82), (-.51, 2.80),
    ] + arc(radius, 198, 342, 40) + [
        (1.01, 2.82), (1.03, 2.87), (.99, 2.92),
    ]
    plate = felt('Halo | continuous ivory felt backing', outline, ivory,
                 collection, depth=.64, thickness=.026)
    plate['reference'] = REFERENCE + ' (image 2)'
    plate['construction'] = 'One felt cutout behind the cap; green concentric railway motif.'
    parts = [plate]

    # Print on both sides of the felt, with a visible white margin. The asymmetry
    # (filled left wing, outlined right wing) follows the supplied photograph.
    for side, depth in [('front', .621), ('back', .659)]:
        paths = []
        for r in (.455, .365, .165):
            points = arc(r, 0, 360, 72)
            paths.append([(x, depth, z) for x, z in points])
        paths += [[(x, depth, z) for x, z in path] for path in [
            [(0.15, 2.90), (.46, 3.00), (.92, 2.875), (.52, 2.84), (.29, 2.89)],
        ]]
        parts.append(thread('Halo | green railway rings ' + side, paths, green,
                            collection, radius=.014))
        parts.append(felt('Halo | filled railway wing ' + side,
                          [(-.92, 2.865), (-.45, 3.00), (-.49, 2.845)],
                          green, collection, depth=depth, thickness=.002))
    for obj in parts:
        attach(obj, root)
    root['halo_reference'] = REFERENCE + ' (image 2)'
    root['limitation'] = ('Halo follows the rear cap photograph; unseen rear hair '
                         'and clothing seams retain the existing interpretation.')
    if reference_path:
        ref = bpy.data.images.load(str(reference_path), check_existing=True)
        ref.name = 'REFERENCE | Hikari cap and complete felt halo'
        ref.pack()
        ref.use_fake_user = True
    return parts


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', help='Local copy of the second reference photograph')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    root = bpy.context.scene.objects['HIKARI | 170 mm reference plush']
    add_halo(root, args.reference)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath, compress=True)
