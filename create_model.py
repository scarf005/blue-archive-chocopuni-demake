import bpy
import math
from mathutils import Vector
from pathlib import Path

OUT = Path('/home/scarf/opt/blender-5.2.1-linux-x64/hikari_chocopuni')
scene = bpy.data.scenes.new('Hikari • Chocopuni')
bpy.context.window.scene = scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 0.05

def material(name, color, textile=True):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    n = m.node_tree.nodes
    p = n.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Roughness'].default_value = 0.83
    if textile:
        p.inputs['Sheen Weight'].default_value = 0.28
        tex = n.new('ShaderNodeTexNoise')
        tex.inputs['Scale'].default_value = 190
        tex.inputs['Detail'].default_value = 2
        bump = n.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = 0.19
        bump.inputs['Distance'].default_value = 0.012
        m.node_tree.links.new(tex.outputs['Fac'], bump.inputs['Height'])
        m.node_tree.links.new(bump.outputs['Normal'], p.inputs['Normal'])
    return m

skin = material('Peach fleece', (0.91, .64, .55))
hair = material('Pistachio felt', (.48, .67, .20))
hairlight = material('Light green felt', (.60, .76, .29))
navy = material('Midnight navy twill', (.035, .055, .105))
blue = material('Blue piping', (.065, .27, .52))
dark = material('Charcoal embroidery', (.022, .016, .02))
white = material('Ivory thread', (.96, .92, .77))
gold = material('Golden embroidery', (.85, .53, .075))
yellow = material('Iris honey', (.94, .68, .12))
cream = material('Iris pale gold', (.98, .87, .40))
brown = material('Iris dark brown', (.23, .09, .015))
pink = material('Blush thread', (.91, .31, .34))
mouth = material('Mouth embroidery', (.48, .07, .08))
strap = material('Black woven strap', (.019, .029, .045))
silver = material('Silver button thread', (.55, .61, .65))

def uv(name, loc, scale, mat):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=32, location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    o.data.materials.append(mat)
    for p in o.data.polygons: p.use_smooth = True
    return o

def line(name, pts, radius, mat, cyclic=False):
    c = bpy.data.curves.new(name, 'CURVE')
    c.dimensions = '3D'
    c.resolution_u = 16
    c.bevel_depth = radius
    c.bevel_resolution = 3
    s = c.splines.new('BEZIER')
    s.bezier_points.add(len(pts)-1)
    for b, co in zip(s.bezier_points, pts):
        b.co = co
        b.handle_left_type = 'AUTO'
        b.handle_right_type = 'AUTO'
    s.use_cyclic_u = cyclic
    o = bpy.data.objects.new(name, c)
    scene.collection.objects.link(o)
    c.materials.append(mat)
    return o

def patch(name, coords, mat, thickness=.045, bevel=.035):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(coords, [], [list(range(len(coords)))])
    mesh.update()
    o = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(o)
    mesh.materials.append(mat)
    sol = o.modifiers.new('Soft felt thickness', 'SOLIDIFY')
    sol.thickness = thickness
    b = o.modifiers.new('Rounded fabric edge', 'BEVEL')
    b.width = bevel
    b.segments = 3
    o.modifiers.new('Weighted corner normals', 'WEIGHTED_NORMAL')
    return o

# Full volume hair behind the seated body.
uv('Back hair cushion', (0,.25,1.79), (.94,.46,1.03), hair)
for s in [-1,1]:
    o = uv('Long rear hair '+str(s), (s*.77,.21,1.11), (.27,.29,.73), hair)
    o.rotation_euler[1] = s*-.30
uv('Stuffed uniform torso', (0,0,.92), (.61,.39,.59), navy)
uv('Rounded uniform hem', (0,-.03,.55), (.62,.37,.25), navy)
for s in [-1,1]:
    o = uv('Sleeve '+str(s), (s*.72,-.01,.87), (.245,.28,.40), navy)
    o.rotation_euler[1] = s*.65
    uv('White mitten '+str(s), (s*.96,-.04,.62), (.17,.21,.18), white)
    line('Cuff blue seam '+str(s), [(s*.78,-.245,.57),(s*.91,-.275,.69),(s*1.01,-.16,.79)], .024, blue)
    uv('Seated boot '+str(s), (s*.48,-.41,.32), (.34,.48,.36), navy)
    line('Boot toe seam '+str(s), [(s*.48-.29,-.66,.21),(s*.48,-.873,.19),(s*.48+.29,-.66,.21)], .012, strap)
    line('Boot perimeter seam '+str(s), [(s*.48-.29,-.62,.35),(s*.48-.21,-.70,.59),(s*.48,-.72,.65),(s*.48+.23,-.69,.56),(s*.48+.30,-.62,.32)], .009, silver)

uv('Large stuffed face', (0,-.035,2.01), (.86,.57,.69), skin)
for s in [-1,1]:
    patch('Pointed elf ear '+str(s), [(s*.75,.00,2.12),(s*1.17,-.01,2.27),(s*1.13,-.02,2.09),(s*.88,-.09,1.89)], skin,.15,.07)
    patch('Ear inner stitch '+str(s), [(s*.89,-.095,2.10),(s*1.09,-.10,2.19),(s*.94,-.115,2.00)], pink,.008,.02)

# Raised embroidered face, with relaxed upper eyelids and golden irises.
for s in [-1,1]:
    x = s*.335
    uv('Eye dark border '+str(s), (x,-.559,2.005), (.199,.041,.245), dark)
    uv('Eye ivory '+str(s), (x,-.594,2.004), (.177,.018,.218), white)
    uv('Golden iris '+str(s), (x+s*.006,-.615,2.004), (.139,.014,.198), yellow)
    uv('Light lower iris '+str(s), (x+s*.006,-.627,1.925), (.124,.009,.104), cream)
    uv('Brown pupil border '+str(s), (x,-.638,2.025), (.056,.012,.082), dark)
    uv('Brown pupil '+str(s), (x,-.650,2.025), (.039,.009,.062), brown)
    uv('White eye glint '+str(s), (x-.097,-.651,1.995), (.043,.011,.022), white)
    line('Thick upper eyelid '+str(s), [(x-.183,-.607,2.125),(x-.10,-.632,2.205),(x+.055,-.634,2.208),(x+.173,-.607,2.14)], .020, dark)
    line('Outer eyelash '+str(s), [(x+s*.15,-.603,2.12),(x+s*.205,-.58,2.20),(x+s*.24,-.551,2.19)], .024, dark)
    line('Red lid embroidery '+str(s), [(x-.13,-.568,2.265),(x,-.58,2.29),(x+.10,-.564,2.265)], .009, mouth)
    line('Green eyebrow '+str(s), [(x-.10,-.523,2.38),(x,-.54,2.34),(x+.08,-.52,2.39)], .009, hair)
    for j in range(3):
        xx = s*(.48+j*.039)
        line('Cheek blush '+str(s)+' '+str(j), [(xx,-.495,1.799),(xx+s*.012,-.497,1.846)], .009, pink)
line('Small pout', [(-.042,-.583,1.703),(0,-.592,1.722),(.039,-.583,1.702)], .010, mouth)

# Flat, layered felt fringe reproduces the plush's cut fabric silhouette.
for name, coords in [
    ('Left fringe',[(-.83,-.31,2.68),(-.27,-.54,2.69),(-.34,-.59,2.40),(-.47,-.59,2.19),(-.51,-.56,2.29),(-.63,-.51,2.18),(-.75,-.45,2.30)]),
    ('Center fringe',[(-.30,-.58,2.72),(.19,-.58,2.72),(.19,-.67,2.31),(.09,-.675,2.13),(.01,-.675,2.20),(-.005,-.675,2.10),(-.16,-.65,2.15),(-.25,-.65,2.33)]),
    ('Right fringe',[(.18,-.56,2.70),(.76,-.34,2.67),(.79,-.49,2.28),(.66,-.53,2.16),(.52,-.59,2.26),(.54,-.60,2.18),(.36,-.63,2.30)]),
]: patch(name,coords,hairlight,.07,.035)
for s in [-1,1]:
    patch('Curled sidelock '+str(s), [(s*.72,-.42,2.60),(s*.89,-.30,2.42),(s*.92,-.29,1.58),(s*.76,-.37,1.34),(s*.88,-.41,1.28),(s*.72,-.46,1.23),(s*.59,-.48,1.31),(s*.57,-.49,1.45),(s*.69,-.52,1.66),(s*.66,-.56,2.20)], hairlight,.13,.055)
    line('Hair felt seam '+str(s), [(s*.77,-.49,2.44),(s*.80,-.47,2.02),(s*.78,-.46,1.64)], .006, hair)

# Double breasted jacket, collar, diagonal shoulder belt.
for s in [-1,1]:
    line('Jacket blue edge '+str(s), [(s*.26,-.30,1.37),(s*.30,-.377,1.14),(s*.35,-.383,.77),(s*.29,-.36,.56)], .013, blue)
    for z in [.78,1.09]: uv('Jacket button', (s*.245,-.395,z), (.025,.013,.025), silver)
    line('Collar silver piping '+str(s), [(s*.03,-.37,1.39),(s*.23,-.32,1.35),(s*.36,-.245,1.47)], .012, silver)
line('Collar gold tab', [(-.025,-.395,1.36),(.025,-.395,1.36)], .012, gold)
patch('Diagonal shoulder strap', [(-.56,-.35,.81),(-.54,-.36,.94),(-.16,-.455,1.06),(.21,-.423,1.25),(.46,-.28,1.49),(.53,-.26,1.39),(.29,-.44,1.14),(-.14,-.478,.94)], strap,.024,.012)
line('Belt', [(-.54,-.25,.69),(-.30,-.402,.67),(0,-.434,.65),(.30,-.402,.67),(.54,-.25,.69)], .044, strap)
line('Belt buckle', [(.05,-.486,.69),(-.065,-.486,.69),(-.065,-.486,.61),(.05,-.486,.61)], .013, gold)

# Oversized train conductor cap with broad visor and embroidered badge.
uv('Cap crown', (0,.00,2.94), (.91,.62,.45), navy)
uv('Cap structured band', (0,-.014,2.72), (.90,.625,.18), navy)
uv('Cap soft broad visor', (0,-.52,2.63), (.86,.35,.105), navy)
for z, mat, r in [(2.77,blue,.024),(2.733,white,.019)]:
    line('Cap ribbon '+mat.name, [(.88*math.cos(t),.62*math.sin(t)-.016,z) for t in [i*2*math.pi/48 for i in range(48)]],r,mat,True)
line('Visor edge stitching', [(-.82,-.59,2.625),(-.63,-.77,2.594),(0,-.862,2.581),(.63,-.77,2.594),(.82,-.59,2.625)], .008, silver)
patch('Gold shield badge', [(-.16,-.583,3.12),(-.10,-.594,3.18),(0,-.599,3.23),(.10,-.594,3.18),(.16,-.583,3.12),(.14,-.625,2.94),(0,-.65,2.875),(-.14,-.625,2.94)],gold,.023,.02)
line('Badge inner border', [(-.12,-.638,3.10),(-.075,-.64,3.15),(0,-.637,3.18),(.12,-.638,3.10),(.10,-.659,2.96),(0,-.67,2.924),(-.10,-.659,2.96)], .008, cream,True)
line('Badge railway ring', [(.07*math.cos(t),-.675,3.046+.06*math.sin(t)) for t in [i*2*math.pi/24 for i in range(24)]], .009, cream,True)
line('Badge railway base', [(-.07,-.68,2.99),(0,-.68,2.97),(.07,-.68,2.99)],.009,cream)
line('Badge crest', [(0,-.65,3.12),(0,-.65,3.17)],.012,cream)
for s in [-1,1]:
    patch('Halo felt wing '+str(s), [(s*.80,.15,2.94),(s*1.04,.12,2.94),(s*1.01,.13,3.02),(s*.82,.16,3.07)],white,.03,.045)

model_objects = list(scene.objects)
root = bpy.data.objects.new('Hikari Chocopuni • model',None)
scene.collection.objects.link(root)
for o in model_objects: o.parent = root
root['reference'] = 'https://www.goodsmile.com/en/product/1140953/Chocopuni+Plushie+Aoba+Hikari+Nozomi'
root['reference_image'] = 'https://tsurumai-hobby.jp/images/item/goodsmile/4580828663398.jpg'
root['notes'] = 'Reference-inspired plush model. Back details are interpreted from the front reference. Unrigged.'
ref = bpy.data.images.load('/tmp/hikari-reference.jpg')
ref.name = 'REFERENCE • Hikari Chocopuni front'
ref.pack()

floor = material('Studio muted blue',(.16,.23,.28),False)
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.052))
bpy.context.object.name = 'Studio floor'
bpy.context.object.data.materials.append(floor)
world = bpy.data.worlds.new('Soft studio world')
world.use_nodes = True
world.node_tree.nodes['Background'].inputs[0].default_value = (.36,.43,.50,1)
world.node_tree.nodes['Background'].inputs[1].default_value = .35
scene.world = world
def aim(o,p): o.rotation_euler = (Vector(p)-o.location).to_track_quat('-Z','Y').to_euler()
for name,loc,power,size in [('Key softbox',(-3,-4,6),450,4),('Fill softbox',(3,-2,3.8),200,3),('Hair rim',(1,3,5),550,3)]:
    bpy.ops.object.light_add(type='AREA',location=loc)
    o=bpy.context.object
    o.name=name
    o.data.energy=power
    o.data.shape='DISK'
    o.data.size=size
    aim(o,(0,0,1.6))
bpy.ops.object.camera_add(location=(.35,-8,3.05))
cam=bpy.context.object
cam.name='Portrait camera'
aim(cam,(0,-.04,1.69))
cam.data.type='ORTHO'
cam.data.ortho_scale=4.05
scene.camera=cam
scene.render.engine='CYCLES'
scene.cycles.samples=48
scene.cycles.use_denoising=True
scene.render.resolution_x=1000
scene.render.resolution_y=1100
scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX'
scene.render.image_settings.file_format='PNG'
scene.render.filepath=str(OUT/'hikari_chocopuni.png')
bpy.ops.object.select_all(action='DESELECT')
root.select_set(True)
bpy.context.view_layer.objects.active=root
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'hikari_chocopuni.blend'))
result={'saved':bpy.data.filepath,'model_objects':len(model_objects),'scene':scene.name}
