"""Shared low-poly sewing tools for students built on the Hikari v4 pose rig."""

import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import bpy
from mathutils import Vector, geometry
from mathutils.bvhtree import BVHTree

from restore_halo import attach, thread
from sewing_patterns import contains

REPO = Path(__file__).parent
PRODUCT = 'https://www.goodsmile.com/en/product/1140953/Chocopuni+Plushie+Aoba+Hikari+Nozomi'


def load_template(student, reference=None, character_reference=None, *, reference_model=None):
    """Use supplied images, or reuse the same student's packed references offline."""
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
    references = {f'REFERENCE | {student} {name}': path for name,path in
                  [('Chocopuni product photograph', reference), ('official character art', character_reference)]}
    missing = [name for name,path in references.items() if path is None]
    if missing:
        source = Path(reference_model) if reference_model is not None else REPO / f'{student.lower()}_chocopuni.blend'
        if not source.is_file():
            source = REPO / f'{student.lower()}_chocopuni.blend'
        if not source.is_file():
            raise ValueError(f'{student}: supply --reference and --character-reference for the first build.')
        with bpy.data.libraries.load(str(source), link=False) as (available, imported):
            if not all(name in available.images for name in missing):
                raise ValueError(f'{source.name}: missing packed references; supply the reference paths.')
            imported.images = missing
        if any(image.packed_file is None for image in imported.images):
            raise ValueError(f'{source.name}: references are not packed; supply the reference paths.')
    for name, path in references.items():
        if path is not None:
            image = bpy.data.images.load(str(path), check_existing=True)
            image.name = name
            image.pack()
        else:
            image = bpy.data.images[name]
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


def surface(obj, *, fallback='error'):
    """Snapshot the evaluated surface; require an explicit opt-in to extrapolate."""
    if fallback not in {'error', 'nearest'}:
        raise ValueError('Surface fallback must be error or nearest.')
    name = obj.name
    bpy.context.view_layer.update()
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try:
        if not mesh or not mesh.polygons:
            raise ValueError(f'{name}: cannot project onto an empty surface.')
        vertices = [evaluated.matrix_world @ v.co for v in mesh.vertices]
        tree = BVHTree.FromPolygons(vertices, [list(p.vertices) for p in mesh.polygons])
        ray_y = min(-5, min(v.y for v in vertices)-1)
    finally:
        evaluated.to_mesh_clear()

    @lru_cache(maxsize=8192)
    def depth(x, z):
        if not math.isfinite(x) or not math.isfinite(z):
            raise ValueError(f'{name}: projection coordinates must be finite.')
        hit, *_ = tree.ray_cast(Vector((x, ray_y, z)), Vector((0, 1, 0)))
        if hit is None and fallback == 'nearest':
            hit, *_ = tree.find_nearest(Vector((x, -.5, z)))
        if hit is None:
            raise ValueError(f'{name}: no front surface at x={x:.5f}, z={z:.5f}; '
                             'check the photo frame or the component boundary.')
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


@dataclass(frozen=True)
class PhotoFrame:
    """Map measured photo landmarks to model X/Z, independently of image resolution."""

    center_x: float = 375
    floor_y: float = 947
    scale: float = .0038

    def __post_init__(self):
        if not all(math.isfinite(v) for v in (self.center_x, self.floor_y, self.scale)) or self.scale <= 0:
            raise ValueError('Photo frame must have finite landmarks and a positive scale.')

    @classmethod
    def fit(cls, *, center_x, floor_y, top_y, height=3.4):
        if not all(math.isfinite(v) for v in (floor_y, top_y, height)) or floor_y <= top_y or height <= 0:
            raise ValueError('Photo top must be above the floor; model height must be positive.')
        return cls(center_x, floor_y, height / (floor_y - top_y))

    def __call__(self, point):
        return ((point[0]-self.center_x)*self.scale, (self.floor_y-point[1])*self.scale)


def photo(point, *, frame=PhotoFrame()):
    """Keep the existing 750 x 1000 calibration unless another frame is supplied."""
    return frame(point)


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
          thickness=.003, smooth=3, step=.07, subdiv=False, frame=PhotoFrame(),
          tolerance=None, max_vertices=4096, holes=(), fill_rule='nonzero'):
    """Project felt; optionally refine where edge/centroid samples exceed tolerance.

    Tolerance measures base-mesh depth error before Subdivision and Solidify.
    A discontinuous depth field or insufficient vertex budget fails before linking a mesh.
    """
    if not math.isfinite(step) or step <= 0:
        raise ValueError(f'{name}: panel step must be positive and finite.')
    if tolerance is not None and (not math.isfinite(tolerance) or tolerance <= 0 or max_vertices < 3):
        raise ValueError(f'{name}: tolerance and vertex budget must be positive.')
    if fill_rule not in {'nonzero', 'evenodd'}:
        raise ValueError(f'{name}: unsupported fill rule.')
    contours = [[photo(p, frame=frame) for p in
                 (outline_samples(ring, smooth) if smooth else ring)] for ring in [points, *holes]]
    boundary = contours[0]
    if len(boundary) < 3 or not all(math.isfinite(c) for p in boundary for c in p):
        raise ValueError(f'{name}: a panel needs at least three finite points.')
    if any(len(ring) < 3 or not all(math.isfinite(c) for p in ring for c in p) for ring in contours):
        raise ValueError(f'{name}: each contour needs at least three finite points.')
    @lru_cache(maxsize=None)
    def projected(x, z):
        try:
            y = depth(x, z)
        except ValueError as exc:
            raise ValueError(f'{name}: {exc}') from exc
        if not math.isfinite(y):
            raise ValueError(f'{name}: non-finite projected depth at {(x, z)}.')
        return y

    if sum(a[0]*b[1] - a[1]*b[0] for a, b in zip(boundary, boundary[1:] + boundary[:1])) < 0:
        for ring in contours:
            ring.reverse()
    vertices = [Vector(p) for ring in contours for p in ring]
    edges, cursor = [], 0
    for ring in contours:
        edges += [(cursor+i, cursor+(i+1)%len(ring)) for i in range(len(ring))]
        cursor += len(ring)
    all_boundary = [p for ring in contours for p in ring]
    ymin, ymax = min(p[1] for p in all_boundary), max(p[1] for p in all_boundary)
    for row in range(1, math.ceil((ymax - ymin) / step)):
        y = ymin + row * step
        xs = sorted(a[0] + (y-a[1])/(b[1]-a[1])*(b[0]-a[0])
                    for ring in contours for a, b in zip(ring, ring[1:] + ring[:1])
                    if min(a[1], b[1]) <= y < max(a[1], b[1]))
        for left, right in zip(xs[::2], xs[1::2]):
            for col in range(1, math.floor((right - left) / step)):
                vertices.append(Vector((left + col * step, y)))
    if tolerance is not None and len(vertices) > max_vertices:
        raise ValueError(f'{name}: adaptive panel exceeds {max_vertices} vertices.')
    coords, _, faces, *_ = geometry.delaunay_2d_cdt(
        vertices, edges if holes else [], [] if holes else [list(range(len(boundary)))],
        0 if holes else 1, .000001, False)
    if holes:
        faces = [face for face in faces if contains(
            tuple(sum(coords[i][j] for i in face)/len(face) for j in (0,1)), contours, fill_rule)]
    coords, faces = list(coords), [list(face) for face in faces]
    for iteration in range(9):
        if tolerance is not None and len(coords) > max_vertices:
            raise ValueError(f'{name}: adaptive panel exceeds {max_vertices} vertices.')
        if not faces:
            raise ValueError(f'{name}: panel outline has no area.')
        if tolerance is None:
            break
        heights = [projected(p.x, p.y) for p in coords]
        split_edges, split_faces = set(), set()
        sampled_error = 0
        for face_index, face in enumerate(faces):
            probes = [tuple(face)] + [(a,b) for a,b in zip(face, face[1:]+face[:1])]
            for indices in probes:
                x, z = (sum(coords[i][j] for i in indices)/len(indices) for j in (0,1))
                error = abs(projected(x,z)-sum(heights[i] for i in indices)/len(indices))
                sampled_error = max(sampled_error, error)
                if error > tolerance:
                    if len(indices) == 2:
                        split_edges.add(tuple(sorted(indices)))
                    else:
                        split_faces.add(face_index)
        if not split_edges and not split_faces:
            break
        if iteration == 8:
            raise ValueError(f'{name}: adaptive projection did not converge '
                             f'(sampled error {sampled_error:.6f}, {len(coords)} vertices); '
                             'check depth continuity.')
        # Refine triangles directly: rerunning CDT can discard collinear boundary
        # samples. Share edge midpoints across neighbors to avoid T-junctions.
        midpoints = {}
        for a,b in sorted(split_edges):
            midpoints[(a,b)] = len(coords)
            coords.append((coords[a]+coords[b])/2)
        refined = []
        for face_index,face in enumerate(faces):
            ring = []
            for a,b in zip(face,face[1:]+face[:1]):
                ring.append(a)
                midpoint = midpoints.get(tuple(sorted((a,b))))
                if midpoint is not None:
                    ring.append(midpoint)
            if len(ring) == len(face) and face_index not in split_faces:
                refined.append(face)
                continue
            center = len(coords)
            coords.append(sum((coords[i] for i in face),Vector((0,0)))/len(face))
            refined.extend([center,a,b] for a,b in zip(ring,ring[1:]+ring[:1]))
        faces = refined

    obj = mesh_object(root, name, [(p.x, projected(p.x, p.y)-offset, p.y) for p in coords],
                      faces, material, bone=bone, subdiv=subdiv)
    if tolerance is not None:
        obj['sampled_surface_error'] = sampled_error
    if thickness:
        modifier = obj.modifiers.new('Thin sewn cloth', 'SOLIDIFY')
        modifier.thickness = thickness
    return obj


def seam(root, name, points, depth, material, *, bone='head', radius=.0025, offset=.012, frame=PhotoFrame()):
    coords = [photo(p, frame=frame) for p in outline_samples(points, 6, cyclic=False)]
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


def save(root, rig, student, *, output=None):
    output = Path(output) if output is not None else REPO / f'{student.lower()}_chocopuni.blend'
    if output.suffix != '.blend':
        raise ValueError('Model output must end in .blend.')
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
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output.resolve()), compress=True)
