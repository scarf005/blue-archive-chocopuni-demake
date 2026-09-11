"""Shared low-poly sewing tools for students built on the Hikari v4 pose rig."""

import math
from pathlib import Path

import bpy
from mathutils import Vector, geometry
from mathutils.bvhtree import BVHTree

from restore_halo import attach, thread

REPO = Path(__file__).parent
PRODUCT = 'https://www.goodsmile.com/en/product/1140953/Chocopuni+Plushie+Aoba+Hikari+Nozomi'


def load_template(student, reference, character_reference):
    bpy.ops.wm.open_mainfile(filepath=str(REPO / 'hikari_chocopuni.blend'))
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    root = bpy.data.objects['HIKARI | 170 mm reference plush']
    rig = bpy.data.objects['HIKARI | pose rig']
    root.name = f'{student.upper()} | 170 mm reference plush'
    rig.name = rig.data.name = f'{student.upper()} | pose rig'
    root.users_collection[0].name = f'{student} | sewn components'
    bpy.context.scene.name = f'{student} | sewn plush'
    root['student'] = student
    root['reference'] = PRODUCT
    root['character_reference'] = f'https://bluearchive.wiki/wiki/{student}/gallery'
    for bone in rig.pose.bones:
        bone.matrix_basis.identity()
    for name, path in [('Chocopuni product photograph', reference),
                       ('official character art', character_reference)]:
        image = bpy.data.images.load(str(path), check_existing=True)
        image.name = f'REFERENCE | {student} {name}'
        image.pack()
        image.use_fake_user = True
    original = bpy.data.images.get('REFERENCE | original Chocopuni Hikari photograph')
    if original:
        bpy.data.images.remove(original)
    bpy.context.view_layer.update()
    return root, rig


def remove(root, prefixes, *, keep=()):
    for obj in list(root.children_recursive):
        if obj.name.startswith(prefixes) and obj.name not in keep:
            bpy.data.objects.remove(obj, do_unlink=True)


def color_material(name, color, source='02 | lime green velboa'):
    material = bpy.data.materials[source].copy()
    material.name = name
    rgb = tuple(c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in color)
    material.diffuse_color = (*rgb, 1)
    material.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value = (*rgb, 1)
    for node in material.node_tree.nodes:
        if node.type == 'VALTORGB':
            node.color_ramp.elements[0].color = (*(v * .88 for v in rgb), 1)
            node.color_ramp.elements[-1].color = (*(min(1, v * 1.10 + .001) for v in rgb), 1)
    return material


def surface(obj):
    bpy.context.view_layer.update()
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    tree = BVHTree.FromPolygons([evaluated.matrix_world @ v.co for v in mesh.vertices],
                               [list(p.vertices) for p in mesh.polygons])
    evaluated.to_mesh_clear()

    def depth(x, z):
        hit, *_ = tree.ray_cast(Vector((x, -5, z)), Vector((0, 1, 0)))
        if hit is None:
            hit, *_ = tree.find_nearest(Vector((x, -.5, z)))
        return hit.y
    return depth


def outline_samples(points, steps=3, cyclic=True):
    result = []
    for i in range(len(points) if cyclic else len(points) - 1):
        a, b, c, d = [points[j % len(points)] if cyclic else points[max(0, min(j, len(points) - 1))]
                      for j in (i - 1, i, i + 1, i + 2)]
        for k in range(steps):
            t = k / steps
            result.append(tuple(.5 * (2 * b[j] + (-a[j] + c[j]) * t
                + (2*a[j] - 5*b[j] + 4*c[j] - d[j]) * t*t
                + (-a[j] + 3*b[j] - 3*c[j] + d[j]) * t*t*t) for j in (0, 1)))
    if not cyclic:
        result.append(points[-1])
    return result


def photo(point):
    """750 x 1000 product-photo landmarks, normalized to the 170 mm Hikari scale."""
    return ((point[0] - 375) * .0038, (947 - point[1]) * .0038)


def mesh_object(root, name, vertices, faces, material, *, bone='head', subdiv=False):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    mesh.materials.append(material)
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    obj = bpy.data.objects.new(name, mesh)
    root.users_collection[0].objects.link(obj)
    if subdiv:
        modifier = obj.modifiers.new('Smooth low-poly surface', 'SUBSURF')
        modifier.levels = modifier.render_levels = 1
        modifier.boundary_smooth = 'PRESERVE_CORNERS'
    attach(obj, root, bone)
    return obj


def panel(root, name, points, depth, material, *, bone='head', offset=.008,
          thickness=.003, smooth=3, step=.07, subdiv=False):
    boundary = [photo(p) for p in (outline_samples(points, smooth) if smooth else points)]
    if sum(a[0]*b[1] - a[1]*b[0] for a, b in zip(boundary, boundary[1:] + boundary[:1])) < 0:
        boundary.reverse()
    vertices = [Vector(p) for p in boundary]
    ymin, ymax = min(p[1] for p in boundary), max(p[1] for p in boundary)
    for row in range(1, math.ceil((ymax - ymin) / step)):
        y = ymin + row * step
        xs = sorted(a[0] + (y-a[1])/(b[1]-a[1])*(b[0]-a[0])
                    for a, b in zip(boundary, boundary[1:] + boundary[:1])
                    if min(a[1], b[1]) <= y < max(a[1], b[1]))
        for left, right in zip(xs[::2], xs[1::2]):
            for col in range(1, math.floor((right - left) / step)):
                vertices.append(Vector((left + col * step, y)))
    coords, _, faces, *_ = geometry.delaunay_2d_cdt(
        vertices, [], [list(range(len(boundary)))], 1, .000001, False)
    obj = mesh_object(root, name, [(p.x, depth(p.x, p.y)-offset, p.y) for p in coords],
                      faces, material, bone=bone, subdiv=subdiv)
    if thickness:
        modifier = obj.modifiers.new('Thin sewn cloth', 'SOLIDIFY')
        modifier.thickness = thickness
    return obj


def seam(root, name, points, depth, material, *, bone='head', radius=.0025, offset=.012):
    coords = [photo(p) for p in outline_samples(points, 6, cyclic=False)]
    obj = thread(name, [[(x, depth(x, z)-offset, z) for x, z in coords]], material,
                 root.users_collection[0], radius=radius)
    attach(obj, root, bone)
    return obj


def oval(root, name, center, radii, depth, material, **options):
    points = [(center[0] + radii[0]*math.cos(t), center[1] + radii[1]*math.sin(t))
              for t in [i*math.tau/24 for i in range(24)]]
    return panel(root, name, points, depth, material, smooth=0, **options)


def ellipsoid(root, name, location, scale, material, *, bone='head', segments=32, rings=16):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(material)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    for collection in list(obj.users_collection):
        collection.objects.unlink(obj)
    root.users_collection[0].objects.link(obj)
    attach(obj, root, bone)
    return obj


def warp(obj, transform):
    """Move mesh and curve points in world space without breaking bone parenting."""
    world, inverse = obj.matrix_world.copy(), obj.matrix_world.inverted()
    if obj.type == 'MESH':
        for vertex in obj.data.vertices:
            vertex.co = inverse @ Vector(transform(world @ vertex.co))
        obj.data.update()
    elif obj.type == 'CURVE':
        for spline in obj.data.splines:
            for point in spline.points:
                point.co = (*(inverse @ Vector(transform(world @ point.co.xyz))), point.co.w)
            for point in spline.bezier_points:
                for attr in ('co', 'handle_left', 'handle_right'):
                    setattr(point, attr, inverse @ Vector(transform(world @ getattr(point, attr))))


def save(root, rig, student):
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.pose.select_all(action='DESELECT')
    rig.data.bones.active = rig.data.bones['spine']
    rig.pose.bones['spine'].select = True
    bpy.context.scene.camera = bpy.data.objects['Front comparison']
    bpy.context.scene.render.filepath = f'//{student.lower()}_preview_front.webp'
    bpy.context.preferences.filepaths.save_version = 0
    bpy.data.orphans_purge(do_recursive=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(REPO / f'{student.lower()}_chocopuni.blend'), compress=True)
