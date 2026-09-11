"""Read prepared SVG patterns without third-party dependencies inside Blender."""

import hashlib
import json
import math
from pathlib import Path


def contains(point, contours, rule='nonzero'):
    """SVG nonzero/evenodd fill test, including holes and disjoint contours."""
    x, y = point
    winding = 0
    for contour in contours:
        for a, b in zip(contour, contour[1:]+contour[:1]):
            if min(a[1], b[1]) <= y < max(a[1], b[1]):
                cross_x = a[0] + (y-a[1])*(b[0]-a[0])/(b[1]-a[1])
                if cross_x > x:
                    winding += 1 if b[1] > a[1] else -1
    return bool(winding % 2) if rule == 'evenodd' else winding != 0


def read_pattern(source):
    source = Path(source)
    data = json.loads(source.with_suffix('.json').read_text())
    if data.get('version') != 1 or data.get('source_sha256') != hashlib.sha256(source.read_bytes()).hexdigest():
        raise ValueError(f'{source}: stale or incompatible pattern; run vectorize.py prepare again.')
    return data['parts']


def sew(root, source, depth, materials, *, frame=None, prefix='Face | ', bone='head',
        offset=.010, layer_gap=.003, thickness=.001, step=.10, tolerance=.0015):
    """Project SVG layers in paint order, with compound fills and round thread strokes."""
    from plush_variants import PhotoFrame, panel
    from restore_halo import attach, thread
    frame = frame or PhotoFrame()
    parts = read_pattern(source)
    colors = {color for part in parts for color in (part['fill'], part['stroke']) if color}
    missing = colors - materials.keys()
    if missing:
        raise ValueError(f'Missing cloth/thread materials: {sorted(missing)}')
    objects = []
    for index, part in enumerate(parts):
        relief = offset + part.get('layer', index)*layer_gap
        name = prefix+part['id']
        paths = part['paths']
        if part['fill']:
            contours = [p['points'] for p in paths if len(p['points']) >= 3]
            if contours:
                objects.append(panel(root, name, contours[0], depth, materials[part['fill']],
                    holes=contours[1:], fill_rule=part['fill_rule'], smooth=0, frame=frame,
                    bone=bone, offset=relief, thickness=thickness, step=step, tolerance=tolerance))
        if part['stroke'] and part['stroke_width'] > 0:
            coords = []
            for path in paths:
                points = path['points'] + (path['points'][:1] if path['closed'] else [])
                dense = []
                for a,b in zip(points, points[1:]):
                    samples = max(1, math.ceil(math.dist(a,b)*frame.scale/min(step,.025)))
                    dense.extend([a[j]+(b[j]-a[j])*i/samples for j in (0,1)] for i in range(samples))
                dense.append(points[-1])
                coords.append([(x, depth(x,z)-relief-.0008, z) for x,z in map(frame, dense)])
            obj = thread(name+' stitch', coords, materials[part['stroke']], root.users_collection[0],
                         radius=part['stroke_width']*frame.scale/2)
            attach(obj, root, bone)
            objects.append(obj)
    return objects
