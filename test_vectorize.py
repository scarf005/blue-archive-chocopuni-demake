"""Run with the same isolated dependencies as vectorize.py (no Blender needed)."""

import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image, ImageDraw

from vectorize import prepare, trace
from sewing_patterns import contains, read_pattern


class VectorPatterns(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'pattern.svg'

    def svg(self, body, **attrs):
        options = {'width': 100, 'height': 100, 'viewBox': '0 0 100 100'} | attrs
        self.path.write_text('<svg xmlns="http://www.w3.org/2000/svg" '+
                             ' '.join(f'{k}="{v}"' for k,v in options.items())+'>'+body+'</svg>')
        return prepare(self.path)

    def test_transforms_and_viewbox(self):
        data = self.svg('<g transform="translate(10 5)" data-layer="3"><path id="test" fill="#fff" '
                        'd="M10 20h10v10h-10z"/></g>', viewBox='10 20 50 50')
        part = data['parts'][0]
        self.assertEqual(part['id'], 'test')
        self.assertEqual(part['fill'], '#ffffff')
        self.assertEqual(part['layer'], 3)
        self.assertEqual(part['paths'][0]['points'], [[20,10],[40,10],[40,30],[20,30]])

    def test_arcs_curves_and_open_strokes(self):
        data = self.svg('<path id="arc" fill="none" stroke="red" stroke-width="2" '
                        'd="M20 50a30 30 0 0 1 60 0"/><path id="curve" '
                        'd="M10 60q20 -40 40 0t40 0v30H10z"/>')
        arc = data['parts'][0]['paths'][0]
        self.assertFalse(arc['closed'])
        self.assertGreater(len(arc['points']), 8)
        for x,y in arc['points']:
            self.assertAlmostEqual((x-50)**2+(y-50)**2, 900, places=2)
        self.assertTrue(data['parts'][1]['paths'][0]['closed'])

    def test_holes_fill_rules(self):
        outer = [[0,0],[10,0],[10,10],[0,10]]
        inner = [[2,2],[8,2],[8,8],[2,8]]
        self.assertFalse(contains((5,5), [outer, inner], 'evenodd'))
        self.assertTrue(contains((5,5), [outer, inner], 'nonzero'))
        self.assertFalse(contains((5,5), [outer, inner[::-1]], 'nonzero'))
        self.assertTrue(contains((1,1), [outer, inner], 'evenodd'))
        data = self.svg('<path fill-rule="evenodd" d="M0 0h10v10h-10z M2 2h6v6h-6z"/>')
        self.assertEqual(len(data['parts'][0]['paths']), 2)

    def test_visibility_errors_budget_and_stale_cache(self):
        data = self.svg('<g display="none"><circle r="4"/></g><circle id="ok" cx="50" cy="50" r="30"/>')
        self.assertEqual(len(data['parts']), 1)
        with self.assertRaisesRegex(ValueError, 'budget'):
            prepare(self.path, max_points=3)
        self.path.with_suffix('.json').write_text(json.dumps(data))
        self.assertEqual(read_pattern(self.path), data['parts'])
        self.path.write_text(self.path.read_text()+'\n')
        with self.assertRaisesRegex(ValueError, 'stale'):
            read_pattern(self.path)
        for body in ('<text>no</text>', '<path d="M0 0h5v5z" filter="url(#x)"/>',
                     '<path d="M0 0h5v5z" opacity=".5"/>',
                     '<path d="M0 0h5v5z" stroke-dasharray="3 3"/>'):
            with self.assertRaises(ValueError):
                self.svg(body)

    def test_real_tracer_crop_mask_and_reproducibility(self):
        source = self.path.with_suffix('.png')
        mask = self.path.with_name('mask.png')
        image = Image.new('RGB', (100,100), 'white')
        ImageDraw.Draw(image).ellipse((35,40,65,70), fill='#ac263b')
        image.save(source)
        selection = Image.new('L', image.size)
        ImageDraw.Draw(selection).ellipse((35,40,65,70), fill='white')
        selection.save(mask)
        self.assertGreater(trace(source, self.path, crop=(25,30,80,80), mask=mask), 0)
        data = prepare(self.path)
        self.assertEqual(data['canvas'], [100,100])
        points = [p for part in data['parts'] for path in part['paths'] for p in path['points']]
        self.assertTrue(all(33 <= x <= 68 and 38 <= y <= 73 for x,y in points))
        self.assertEqual(data, prepare(self.path))
        with self.assertRaises(ValueError):
            trace(source, self.path, crop=(99,0,101,100))
        Image.new('L', (100,100)).save(mask)
        with self.assertRaisesRegex(ValueError, 'transparent'):
            trace(source, self.path, mask=mask)
        Image.new('L', (10,10)).save(mask)
        with self.assertRaisesRegex(ValueError, 'canvas'):
            trace(source, self.path, mask=mask)
        for tol in (0, float('nan')):
            with self.assertRaises(ValueError):
                prepare(self.path, tolerance=tol)


if __name__ == '__main__':
    unittest.main()
