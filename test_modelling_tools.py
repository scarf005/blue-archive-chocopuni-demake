"""Exercise projection, adaptive panels and review framing in a disposable Blender scene."""

import math
import sys
import unittest
from collections import Counter
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).parent))
from plush_variants import PhotoFrame, ellipsoid, mesh_object, panel, photo, surface
from render_previews import frame_camera, parse_args, render_previews
from restore_halo import thread


class ModellingTools(unittest.TestCase):
    def setUp(self):
        self.scene = bpy.data.scenes.new('Modelling tool test')
        bpy.context.window.scene = self.scene
        self.collection = bpy.data.collections.new('Test components')
        self.scene.collection.children.link(self.collection)
        self.root = bpy.data.objects.new('Test root', None)
        self.collection.objects.link(self.root)
        self.material = bpy.data.materials.new('Test felt')

    def tearDown(self):
        for obj in list(self.collection.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.scenes.remove(self.scene)
        bpy.data.collections.remove(self.collection)
        bpy.data.materials.remove(self.material)

    def test_photo_frame(self):
        self.assertEqual(photo((375, 947)), (0, 0))
        self.assertAlmostEqual(photo((475, 847))[0], .38)
        frame = PhotoFrame.fit(center_x=600, floor_y=1500, top_y=140, height=3.4)
        scaled = PhotoFrame.fit(center_x=300, floor_y=750, top_y=70, height=3.4)
        self.assertEqual(frame((600, 1500)), (0, 0))
        self.assertEqual(frame((600, 140)), (0, 3.4))
        self.assertEqual(frame((700, 950)), scaled((350, 475)))
        for options in ({'top_y': 1500}, {'top_y': 1600}, {'height': 0}, {'height': math.nan}):
            with self.assertRaises(ValueError):
                PhotoFrame.fit(**({'center_x': 600, 'floor_y': 1500, 'top_y': 140} | options))

    def test_compound_svg_fill_and_curved_hole(self):
        frame = PhotoFrame(0, 0, 1)
        outer = [(-.4,-.4),(.4,-.4),(.4,.4),(-.4,.4)]
        hole = [(-.15,-.15),(.15,-.15),(.15,.15),(-.15,.15)]
        for rule, contour in [('evenodd', hole), ('nonzero', hole[::-1])]:
            obj = panel(self.root, 'SVG hole '+rule, outer, lambda x,z: x*x+z*z,
                        self.material, holes=[contour], fill_rule=rule, frame=frame,
                        smooth=0, thickness=0, offset=0, step=.2, tolerance=.005)
            area = sum(p.area for p in obj.data.polygons)
            self.assertGreater(area, .55)
            for polygon in obj.data.polygons:
                center = sum((obj.data.vertices[i].co for i in polygon.vertices), Vector())/len(polygon.vertices)
                self.assertFalse(abs(center.x) < .149 and abs(center.z) < .149)
        with self.assertRaises(ValueError):
            panel(self.root, 'invalid', outer, lambda x,z: 0, self.material,
                  holes=[[(0,0)]], smooth=0)

    def test_curved_long_svg_closing_edge(self):
        # A long oblique closing edge previously kept losing its refinement point.
        boundary = [(0.238, -1.9108),(.50,-2.02),(.57,-1.80),(.2448,-1.7782)]
        depth = lambda x,z: .5*(x*x+(z-1.8)**2)
        obj = panel(self.root, 'Oblique closing edge', boundary, depth, self.material,
                    frame=PhotoFrame(0,0,1), smooth=0, thickness=0, offset=0,
                    step=.065, tolerance=.0015)
        self.assertLess(self.max_error(obj, depth), .0016)

    def test_projection_miss_and_evaluated_transform(self):
        obj = mesh_object(self.root, 'Projection plane', [(-1,0,-1),(1,0,-1),(1,0,1),(-1,0,1)],
                          [(0,1,2,3)], self.material)
        obj.location = (.25, .3, 0)
        modifier = obj.modifiers.new('Thickness', 'SOLIDIFY')
        modifier.thickness = .1
        modifier.offset = 0
        depth = surface(obj)
        self.assertAlmostEqual(depth(.25, 0), .25, places=5)
        with self.assertRaisesRegex(ValueError, 'Projection plane.*no front surface'):
            depth(2, 0)
        self.assertTrue(math.isfinite(surface(obj, fallback='nearest')(2, 0)))
        with self.assertRaisesRegex(ValueError, 'coordinates must be finite'):
            depth(math.nan, 0)
        with self.assertRaisesRegex(ValueError, 'fallback'):
            surface(obj, fallback='guess')
        obj.location.y = -8
        self.assertAlmostEqual(surface(obj)(.25, 0), -8.05, places=5)
        empty = mesh_object(self.root, 'Empty surface', [], [], self.material)
        with self.assertRaisesRegex(ValueError, 'empty surface'):
            surface(empty)
        # Projection snapshots remain usable after replacing the original component.
        bpy.data.objects.remove(obj, do_unlink=True)
        self.assertAlmostEqual(depth(.4, .2), .25, places=5)

    def test_scaled_piece_keeps_placement_when_parented(self):
        obj = ellipsoid(self.root, 'Small ear', (.8, .2, 1.9), (.1,.08,.16), self.material,
                        segments=16, rings=8)
        bpy.context.view_layer.update()
        self.assertLess((obj.matrix_world.translation-Vector((.8,.2,1.9))).length, 1e-6)
        for actual, expected in zip(obj.dimensions, (.2,.16,.32)):
            self.assertAlmostEqual(actual, expected, places=5)

    def make_panel(self, name, depth, **options):
        return panel(self.root, name, [(-.4,.4),(.4,.4),(.4,-.4),(-.4,-.4)],
                     depth, self.material, frame=PhotoFrame(0,0,1),
                     smooth=0, thickness=0, offset=0, **options)

    def max_error(self, obj, depth):
        """Dense barycentric probes are independent of the refinement probes."""
        obj.data.calc_loop_triangles()
        error = 0
        for triangle in obj.data.loop_triangles:
            a,b,c = [obj.data.vertices[i].co for i in triangle.vertices]
            for i in range(11):
                for j in range(11-i):
                    p = a*(i/10)+b*(j/10)+c*(1-(i+j)/10)
                    error = max(error, abs(p.y-depth(p.x,p.z)))
        return error

    def test_adaptive_panel(self):
        curved = lambda x,z: -math.sqrt(1-x*x-z*z)
        coarse = self.make_panel('Coarse', curved, step=1)
        adaptive = self.make_panel('Adaptive', curved, step=1, tolerance=.003)
        dense = self.make_panel('Dense', curved, step=.025)
        self.assertGreater(self.max_error(coarse, curved), .1)
        self.assertLess(self.max_error(adaptive, curved), .0035)
        self.assertLess(len(adaptive.data.vertices), len(dense.data.vertices))
        edges = Counter(tuple(sorted((a,b))) for face in adaptive.data.polygons
                        for a,b in zip(list(face.vertices),list(face.vertices[1:])+[face.vertices[0]]))
        for (a,b),uses in edges.items():
            if uses == 1:
                ends = [adaptive.data.vertices[i].co for i in (a,b)]
                self.assertTrue(any(all(abs(abs(p[axis])-.4) < 1e-6 for p in ends)
                                    for axis in (0,2)), 'Unshared interior edge / T-junction')
        flat = self.make_panel('Flat', lambda x,z: .2*x-.3*z, step=1, tolerance=.003)
        self.assertEqual(len(flat.data.vertices), 4)
        print('PANEL_EVIDENCE', {o.name: {'vertices': len(o.data.vertices),
              'max_depth_error': self.max_error(o, curved)} for o in (coarse, adaptive, dense)})

    def test_panel_failure_does_not_link_a_partial_piece(self):
        count = len(self.collection.objects)
        with self.assertRaisesRegex(ValueError, 'exceeds'):
            self.make_panel('Over budget', lambda x,z: -math.sqrt(1-x*x-z*z),
                            step=1, tolerance=.00001, max_vertices=5)
        self.assertEqual(len(self.collection.objects), count)
        for options in ({'step': 0}, {'step': -1}, {'step': math.nan}, {'tolerance': 0}):
            with self.assertRaises(ValueError):
                self.make_panel('Invalid panel', lambda x,z: 0, **options)
        with self.assertRaisesRegex(ValueError, 'non-finite'):
            self.make_panel('Invalid depth', lambda x,z: math.nan)
        with self.assertRaisesRegex(ValueError, 'converge|exceeds'):
            self.make_panel('Discontinuous depth', lambda x,z: 0 if x < 0 else .1,
                            step=1, tolerance=.0001)
        self.assertEqual(len(self.collection.objects), count)

    def test_concave_cutout_is_preserved(self):
        obj = panel(self.root, 'Concave felt', [(-.4,.4),(.4,.4),(.4,0),(0,0),(0,-.4),(-.4,-.4)],
                    lambda x,z: -math.sqrt(1-x*x-z*z), self.material, frame=PhotoFrame(0,0,1),
                    smooth=0, thickness=0, offset=0, step=1, tolerance=.003)
        area = 0
        obj.data.calc_loop_triangles()
        for triangle in obj.data.loop_triangles:
            a,b,c = [obj.data.vertices[i].co for i in triangle.vertices]
            center = (a+b+c)/3
            self.assertFalse(center.x > 1e-6 and center.z > 1e-6)
            area += abs((b.x-a.x)*(c.z-a.z)-(c.x-a.x)*(b.z-a.z))/2
        self.assertAlmostEqual(area, .48, places=6)

    def test_review_presets(self):
        final = parse_args([])
        self.assertEqual((final.percentage, final.samples), (100, 64))
        self.assertEqual(final.output, Path(__file__).parent)
        draft = parse_args(['--preset', 'draft'])
        self.assertEqual((draft.percentage, draft.samples), (50, 8))
        self.assertIn('.work', draft.output.parts)
        override = parse_args(['--preset','draft','--percentage','60','--samples','24','--views','back'])
        self.assertEqual((override.percentage, override.samples, override.views), (60, 24, ['back']))
        with redirect_stderr(StringIO()), self.assertRaises(SystemExit):
            parse_args(['--samples','0'])

    def test_failed_focus_restores_render_settings(self):
        ellipsoid(self.root, 'Focus part', (0,0,1), (.2,.2,.2), self.material)
        camera = bpy.data.objects.new('Front comparison', bpy.data.cameras.new('Perspective camera'))
        self.collection.objects.link(camera)
        state = lambda: (self.scene.camera, self.scene.render.filepath, self.scene.cycles.samples,
                         self.scene.render.resolution_x, self.scene.render.resolution_y,
                         self.scene.render.resolution_percentage, self.scene.render.image_settings.file_format)
        before = state()
        args = parse_args(['--preset','draft','--views','front','--focus','Focus part',
                           '--output',str(Path(__file__).parent/'.work/render-test')])
        with self.assertRaisesRegex(ValueError, 'orthographic'):
            render_previews(args)
        self.assertEqual(state(), before)
        args.focus = ['Missing component']
        with self.assertRaisesRegex(ValueError, 'No visible components'):
            render_previews(args)
        self.assertEqual(state(), before)

    def test_focus_fits_each_camera_at_portrait_and_landscape_aspects(self):
        obj = ellipsoid(self.root, 'Focus part', (.8,.2,1.9), (.3,.2,.4), self.material)
        for aspect in ((1200,1500),(1500,1200)):
            self.scene.render.resolution_x, self.scene.render.resolution_y = aspect
            for location in ((0,-10,1.7),(5,-9,3.2),(4,8,3.2)):
                camera = bpy.data.objects.new('Inspection camera', bpy.data.cameras.new('Inspection camera'))
                self.collection.objects.link(camera)
                camera.data.type = 'ORTHO'
                camera.location = location
                camera.rotation_euler = (Vector((0,0,1.7))-camera.location).to_track_quat('-Z','Y').to_euler()
                original_rotation = camera.rotation_euler.copy()
                frame_camera(camera, [obj], self.scene)
                self.assertLess((Vector(camera.rotation_euler)-Vector(original_rotation)).length, 1e-6)
                for vertex in obj.data.vertices:
                    point = world_to_camera_view(self.scene, camera, obj.matrix_world @ vertex.co)
                    self.assertTrue(0 < point.x < 1 and 0 < point.y < 1, point)

    def test_focus_fills_the_frame_for_beveled_curves(self):
        curve = thread('Fine seam', [[(-.3,0,2),(.3,0,2)]], self.material,
                       self.collection, radius=.002)
        camera = bpy.data.objects.new('Seam camera', bpy.data.cameras.new('Seam camera'))
        self.collection.objects.link(camera)
        camera.data.type = 'ORTHO'
        camera.location = (0,-10,1.7)
        camera.rotation_euler = (Vector((0,0,1.7))-camera.location).to_track_quat('-Z','Y').to_euler()
        frame_camera(camera, [curve], self.scene)
        evaluated = curve.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = evaluated.to_mesh()
        projected = [world_to_camera_view(self.scene,camera,evaluated.matrix_world @ v.co) for v in mesh.vertices]
        evaluated.to_mesh_clear()
        spans = [max(p[i] for p in projected)-min(p[i] for p in projected) for i in (0,1)]
        self.assertAlmostEqual(max(spans), 1/1.12, places=5)


suite = unittest.defaultTestLoader.loadTestsFromTestCase(ModellingTools)
result = unittest.TextTestRunner(verbosity=2).run(suite)
if not result.wasSuccessful():
    raise SystemExit(1)
