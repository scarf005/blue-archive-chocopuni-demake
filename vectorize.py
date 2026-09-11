# /// script
# requires-python = ">=3.10,<3.14"
# dependencies = ["vtracer==0.6.15", "Pillow==12.0.0", "svgelements==1.9.6"]
# ///
"""Trace a cropped photo/mask to SVG, then prepare editable SVG sewing patterns."""

import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

from PIL import Image, ImageChops, ImageFilter
from svgelements import SVG, Shape, Path as SVGPath, Move, Close
import vtracer


def trace(source, output, *, crop=None, mask=None, colors=6, speckle=12):
    """Keep the original image canvas; masks are white foreground, black background."""
    with Image.open(source) as image:
        image = image.convert('RGBA')
    width, height = image.size
    box = tuple(crop) if crop else (0, 0, width, height)
    x, y, right, bottom = box
    if not (0 <= x < right <= width and 0 <= y < bottom <= height):
        raise ValueError('Crop must be a nonempty rectangle inside the source image.')
    if not 1 <= colors <= 8 or speckle < 0:
        raise ValueError('Color precision must be 1–8; speckle area must be nonnegative.')
    region = image.crop(box).filter(ImageFilter.MedianFilter(3))
    if mask:
        with Image.open(mask) as selection:
            if selection.size != image.size:
                raise ValueError('Mask and source must have the same canvas dimensions.')
            selection = selection.convert('L').crop(box).point(lambda v: 255 if v >= 128 else 0)
        region.putalpha(ImageChops.multiply(region.getchannel('A'), selection))
    if region.getchannel('A').getbbox() is None:
        raise ValueError('The selected region is fully transparent.')
    data = io.BytesIO()
    region.save(data, format='PNG')
    svg = ET.fromstring(vtracer.convert_raw_image_to_svg(
        data.getvalue(), img_format='png', colormode='color', hierarchical='stacked',
        mode='spline', filter_speckle=speckle, color_precision=colors,
        layer_difference=32, corner_threshold=60, length_threshold=4,
        max_iterations=10, splice_threshold=45, path_precision=2))
    ns = '{http://www.w3.org/2000/svg}'
    ET.register_namespace('', ns[1:-1])
    group = ET.Element(ns+'g', {'transform': f'translate({x} {y})'})
    for i, child in enumerate(list(svg)):
        child.set('id', f'part-{i:03d}')
        group.append(child)
        svg.remove(child)
    svg.append(group)
    svg.set('width', str(width))
    svg.set('height', str(height))
    svg.set('viewBox', f'0 0 {width} {height}')
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(svg).write(output, encoding='unicode', xml_declaration=True)
    return len(group)


def flatten(segment, tolerance, *, limit=16):
    """Adaptive chord approximation in final document pixels, including SVG arcs."""
    result = []

    def subdivide(a, b, depth):
        start, end = segment.point(a), segment.point(b)
        error = max(abs(complex(segment.point(a+(b-a)*t))-
                        (complex(start)*(1-t)+complex(end)*t)) for t in (.25, .5, .75))
        if error > tolerance:
            if depth == limit:
                raise ValueError('Curve subdivision limit exceeded; simplify the source SVG.')
            subdivide(a, (a+b)/2, depth+1)
            subdivide((a+b)/2, b, depth+1)
        else:
            result.append([round(end.x, 5), round(end.y, 5)])
    subdivide(0, 1, 0)
    return result


def prepare(source, *, tolerance=.6, max_points=12000):
    """Resolve transforms/styles once outside Blender. Reject unsupported visual effects."""
    if not math.isfinite(tolerance) or tolerance <= 0 or max_points < 3:
        raise ValueError('Positive pixel tolerance and a point budget of at least 3 are required.')
    raw = Path(source).read_bytes()
    xml = ET.fromstring(raw)
    allowed = {'svg', 'g', 'path', 'circle', 'ellipse', 'rect', 'polygon', 'polyline',
               'line', 'title', 'desc', 'metadata', 'defs', 'namedview'}
    for element in xml.iter():
        tag = element.tag.split('}')[-1]
        if tag not in allowed and (element.tag.startswith('{http://www.w3.org/2000/svg}')
                                   or '}' not in element.tag):
            raise ValueError(f'Unsupported SVG element {tag}; convert it to plain paths first.')
        style = element.get('style', '')
        if any(key in element.attrib or key in style for key in
               ('clip-path', 'mask', 'filter', 'marker-', 'vector-effect', 'stroke-dasharray')) or 'url(' in str(element.attrib):
            raise ValueError('Clips, masks, gradients and effects must be converted to plain paths.')
    svg = SVG.parse(io.BytesIO(raw), reify=True, on_error='raise')
    parts, ids, count = [], set(), 0
    for element in svg.elements():
        if not isinstance(element, Shape):
            continue
        if element.values.get('visibility') == 'hidden':
            continue
        identifier = element.id or f'part-{len(parts):03d}'
        if identifier in ids:
            raise ValueError(f'Duplicate SVG component id: {identifier}')
        ids.add(identifier)
        fill = None if element.fill.value is None else element.fill.hexrgb
        stroke = None if element.stroke.value is None else element.stroke.hexrgb
        if not fill and not stroke:
            continue
        if float(element.values.get('opacity', 1)) != 1 or any(
                float(element.values.get(key, 1)) != 1 for key in ('fill-opacity', 'stroke-opacity')):
            raise ValueError(f'{identifier}: use opaque cloth/thread colors.')
        paths = []
        for subpath in SVGPath(element).as_subpaths():
            points = []
            closed = False
            for segment in subpath:
                if isinstance(segment, Move):
                    points = [[segment.end.x, segment.end.y]]
                else:
                    points.extend(flatten(segment, tolerance))
                    closed = isinstance(segment, Close)
            if closed and points[-1] == points[0]:
                points.pop()
            if len(points) >= 2:
                if not all(math.isfinite(v) for point in points for v in point):
                    raise ValueError(f'{identifier}: non-finite coordinates.')
                paths.append({'points': points, 'closed': closed})
                count += len(points)
                if count > max_points:
                    raise ValueError('SVG point budget exceeded; simplify or split the traced parts.')
        if paths:
            rule = element.values.get('fill-rule', 'nonzero')
            if rule not in {'evenodd', 'nonzero'}:
                raise ValueError(f'{identifier}: unsupported fill rule.')
            parts.append({'id': identifier, 'fill': fill, 'stroke': stroke,
                          'stroke_width': float(element.stroke_width), 'fill_rule': rule,
                          'layer': int(element.values.get('data-layer', len(parts))),
                          'paths': paths})
    if not parts:
        raise ValueError('SVG has no visible sewing paths.')
    return {'version': 1, 'source_sha256': hashlib.sha256(raw).hexdigest(),
            'canvas': [float(svg.width), float(svg.height)], 'tolerance_px': tolerance, 'parts': parts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    tracing = commands.add_parser('trace', help='Trace a cropped photo or masked part to editable SVG')
    tracing.add_argument('source', type=Path)
    tracing.add_argument('output', type=Path)
    tracing.add_argument('--crop', type=int, nargs=4, metavar=('X', 'Y', 'RIGHT', 'BOTTOM'))
    tracing.add_argument('--mask', type=Path)
    tracing.add_argument('--colors', type=int, default=6, help='Color precision bits, 1–8')
    tracing.add_argument('--speckle', type=int, default=12, help='Discard small regions in pixels')
    preparing = commands.add_parser('prepare', help='Compile reviewed SVG to dependency-free Blender input')
    preparing.add_argument('source', type=Path)
    preparing.add_argument('--tolerance', type=float, default=.6, help='Curve approximation in document pixels')
    preparing.add_argument('--max-points', type=int, default=12000)
    args = parser.parse_args()
    if args.command == 'trace':
        count = trace(args.source, args.output, crop=args.crop, mask=args.mask,
                      colors=args.colors, speckle=args.speckle)
        print(f'{args.output}: {count} traced parts; review and label before sewing.')
    else:
        pattern = prepare(args.source, tolerance=args.tolerance, max_points=args.max_points)
        output = args.source.with_suffix('.json')
        output.write_text(json.dumps(pattern, separators=(',', ':'), allow_nan=False)+'\n')
        print(f'{output}: {len(pattern["parts"])} components, '
              f'{sum(len(p["points"]) for part in pattern["parts"] for p in part["paths"])} points')


if __name__ == '__main__':
    main()
