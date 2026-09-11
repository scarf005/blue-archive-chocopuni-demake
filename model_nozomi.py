"""Build Nozomi Chocopuni from the official product photograph and character art."""

import argparse
import math
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).parent))
from plush_variants import (load_template, remove, surface, panel, seam, oval,
                            mesh_object, warp, save)
from restore_halo import felt, thread, attach

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--reference', help='Product photo; otherwise reuse the saved model reference')
parser.add_argument('--character-reference', help='Character art; otherwise reuse the saved model reference')
parser.add_argument('--output', type=Path, help='Candidate .blend path; defaults to the repository model')
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
root, rig = load_template('Nozomi', args.reference, args.character_reference, reference_model=args.output)
mat = bpy.data.materials
green, greenback = mat['02 | lime green velboa'], mat['03 | shaded green velboa']
navy, blue = mat['05 | blue navy woven uniform'], mat['08 | flat blue embroidered trim']
ivory, gold = mat['09 | ivory embroidery'], mat['10 | golden embroidery']
brown, red, black = mat['14 | chocolate eye outlines'], mat['16 | burgundy face thread'], mat['18 | woven shoulder strap']
# Preserve the approved depth fields and their existing edge extrapolation.
face = surface(bpy.data.objects['Face | broad peach stuffed cushion'], fallback='nearest')
torso = surface(bpy.data.objects['Uniform | broad stuffed torso'], fallback='nearest')
remove(root, ('Face | eye', 'Face | golden', 'Face | light iris', 'Face | pupil',
              'Face | white', 'Face | L ', 'Face | R ', 'Face | red upper',
              'Face | fine green', 'Face | tiny', 'Face | blush', 'Face | little',
              'Hair | outer', 'Hair | left fringe', 'Hair | center', 'Hair | right fringe',
              'Hair | curled', 'Hair | stitched', 'Hair | rear loose', 'Hair | stuffed rear',
              'Accessories | diagonal', 'Accessories | shoulder', 'Accessories | keeper',
              'Accessories | loose belt end',
              'Uniform | hem blue', 'Sleeve insignia'))

# A short, flatter conductor's crown. Keep the matching embroidered railway crest.
old_crown = bpy.data.objects['Cap | structured sewn crown']
old_surface = surface(old_crown, fallback='nearest')
remove(root, ('Cap | structured sewn crown', 'Cap | blue woven band',
              'Cap | ivory woven band', 'Cap | crown perimeter',
              'Cap | deep soft curved visor', 'Cap | visor'))
profiles = [(2.48, .84, .61), (2.55, .88, .64), (3.12, .88, .64),
            (3.22, .83, .60), (3.26, .66, .47), (3.27, .20, .14)]
vertices = [(rx*math.cos(t), ry*math.sin(t), z + .23*max(0, -math.sin(t))*(i < 2))
            for i, (z, rx, ry) in enumerate(profiles) for t in [j*math.tau/48 for j in range(48)]]
faces = [(i*48+j, i*48+(j+1)%48, (i+1)*48+(j+1)%48, (i+1)*48+j)
         for i in range(len(profiles)-1) for j in range(48)]
faces += [tuple(reversed(range(48))), tuple(range((len(profiles)-1)*48, len(vertices)))]
crown = mesh_object(root, 'Cap | structured sewn crown', vertices, faces,
                    mat['06 | cap navy twill'], subdiv=True)
cap = surface(crown, fallback='nearest')
for obj in list(root.children_recursive):
    if obj.name.startswith('Cap badge |'):
        warp(obj, lambda v: (v.x, v.y + cap(v.x, v.z) - old_surface(v.x, v.z), v.z))
    if obj.name.startswith('Halo |'):
        warp(obj, lambda v: (-v.x, v.y, v.z - .06))

panel(root, 'Cap | blue woven band',
      [(160,246),(220,231),(294,217),(374,211),(452,217),(537,231),(590,251),
       (590,260),(537,241),(452,228),(374,223),(294,229),(220,242),(160,257)],
      cap, blue, step=.04, smooth=2, offset=.012)
panel(root, 'Cap | ivory woven band',
      [(160,257),(220,242),(294,229),(374,223),(452,228),(537,241),(590,260),
       (590,266),(537,248),(452,235),(374,230),(294,236),(220,249),(160,264)],
      cap, ivory, step=.04, smooth=2, offset=.016)
seam(root, 'Cap | crown top seam', [(190,113),(260,98),(372,93),(487,104),(552,129)],
     cap, mat['19 | dark blue sewing thread'], radius=.001, offset=.002)

def visor_depth(x, z):
    top = 2.724 - .13*(abs(x)/.82)**1.4
    t = max(0,min(1,(top-z)/.39))
    return cap(x,top)-.018-.10*math.sin(t*math.pi/2)

panel(root, 'Cap | deep soft curved visor',
      [(158,268),(214,251),(288,238),(375,232),(461,240),(540,253),(591,270),
       (588,294),(575,320),(552,332),(493,336),(375,339),(286,336),
       (217,329),(184,318),(169,298)], visor_depth, mat['07 | dark stuffed shoes'],
      thickness=.035, subdiv=True, step=.065)
seam(root, 'Cap | visor bound edge',
     [(174,291),(190,314),(221,325),(292,333),(375,335),(489,332),(551,327),(576,309)],
     visor_depth, mat['06 | cap navy twill'], radius=.004)
seam(root, 'Cap | visor topstitch',
     [(177,286),(193,309),(223,320),(292,328),(375,330),(489,327),(550,322),(573,306)],
     visor_depth, mat['19 | dark blue sewing thread'], radius=.001)
for side, points in [
    ('L', [(147,215),(126,234),(117,278),(123,318),(113,373),(109,460),(109,526),
           (97,588),(73,634),(57,680),(67,708),(104,728),(125,709),(112,696),
           (102,679),(123,634),(145,571),(150,498),(146,420),(153,339),(166,299)]),
    ('R', [(603,209),(628,226),(640,270),(634,322),(648,381),(648,478),(642,552),
           (658,607),(689,665),(700,702),(685,731),(665,746),(674,778),(681,803),
           (669,819),(632,823),(622,810),(640,792),(638,772),(623,742),(638,711),
           (659,693),(639,644),(615,605),(609,548),(612,465),(605,382),(594,310)]),
]:
    panel(root, 'Hair | rear loose lock ' + side, points, lambda x, z: .22,
          green, bone='hair_back.' + side, thickness=.045, subdiv=True, step=.09)

hair_depth = lambda x, z: min(-.46, face(x, z)-.04) if z < 2.4 else -.55
for name, points in [
    ('left fringe', [(180,329),(222,326),(247,337),(258,362),(244,405),(236,433),
                     (224,414),(219,440),(200,418),(183,384)]),
    ('middle fringe', [(235,327),(288,328),(310,342),(300,376),(290,416),(280,447),
                       (267,431),(260,398),(252,366)]),
    ('swept center fringe', [(289,329),(353,332),(403,337),(430,350),(411,405),(407,446),
                            (416,484),(396,473),(380,462),(373,476),(349,456),
                            (330,428),(317,389),(303,357)]),
    ('right fringe', [(424,337),(480,334),(525,336),(549,355),(548,395),(554,436),
                      (529,423),(522,437),(501,413),(485,379),(482,423),(460,409),(443,379)]),
]:
    panel(root, 'Hair | ' + name, points, hair_depth, green, thickness=.022,
          offset=.018, subdiv=True, step=.085)

for side, points in [
    ('L', [(143,341),(171,338),(172,399),(177,468),(190,516),(210,566),(225,619),
           (235,668),(215,653),(190,615),(166,573),(148,526),(137,460),(136,388)]),
    ('R', [(549,334),(583,333),(595,377),(584,449),(574,513),(557,561),(536,606),
           (514,635),(490,647),(505,609),(523,561),(538,499),(542,440),(543,380)]),
]:
    panel(root, 'Hair | tapered side panel ' + side, points,
          lambda x, z: -.50 if z < 1.60 else hair_depth(x, z)-.025,
          green, bone='hair_front.' + side, thickness=.025, subdiv=True, step=.085)

# Half-lidded gold eyes, heavy horizontal lashes and the open, fang-like smile.
for side, shift in [('L', 0), ('R', 185)]:
    shifted = lambda points: [(x+shift, y) for x, y in points]
    panel(root, 'Face | half-lidded outline '+side,
          shifted([(225,438),(244,432),(279,440),(314,442),(326,448),(318,479),
                   (302,501),(280,509),(252,504),(236,487)]), face, brown, step=.035)
    panel(root, 'Face | ivory eye ground '+side,
          shifted([(237,447),(266,448),(312,449),(310,479),(295,499),
                   (274,502),(251,494),(240,477)]), face, ivory, offset=.012, step=.035)
    panel(root, 'Face | amber iris '+side,
          shifted([(251,445),(284,448),(311,449),(309,477),(296,496),
                   (276,500),(256,489)]), face, mat['12 | amber iris satin stitch'], offset=.017, step=.035)
    panel(root, 'Face | butter iris '+side,
          shifted([(255,477),(278,480),(308,474),(297,494),(278,498),(261,488)]),
          face, mat['13 | butter iris satin stitch'], offset=.020, step=.035)
    oval(root, 'Face | pupil border '+side, (286+shift,456), (12,20), face,
         brown, offset=.024, step=.035)
    oval(root, 'Face | amber pupil '+side, (286+shift,455), (7,14), face,
         mat['15 | brown pupils'], offset=.027, step=.035)
    panel(root, 'Face | heavy upper lashes '+side,
          shifted([(218,433),(230,435),(234,426),(242,433),(253,431),(263,438),
                   (303,441),(321,443),(327,451),(299,451),(264,446),(239,446),
                   (239,466),(231,481),(225,469)]), face, brown, offset=.030, step=.035, smooth=1)
    oval(root, 'Face | stitched glint '+side, (239+shift,478), (8,5), face,
         ivory, offset=.033, step=.03)
    seam(root, 'Face | lower eyelid '+side, shifted([(244,504),(267,509),(288,509)]), face, red)
    seam(root, 'Face | red eyebrow '+side, shifted([(291,420),(302,420),(313,423)]), face, red)
    for j in range(4):
        x = 259+shift+j*4
        seam(root, 'Face | blush '+side, [(x,528),(x-2,541)], face,
             mat['17 | salmon face thread'], radius=.0015)
    for x, y in [(237,501),(242,494),(315,493)]:
        seam(root, 'Face | cheek stitch '+side, shifted([(x,y),(x+3,y+3)]), face, red, radius=.0015)

mouth = [(346,524),(380,526),(392,531),(402,525),(406,529),(400,548),
         (388,560),(374,562),(359,554),(350,540)]
panel(root, 'Face | open smile outline', mouth, face, red, offset=.009, step=.035, smooth=2)
panel(root, 'Face | open smile pink fill', [(376+(x-376)*.84,542+(y-542)*.82) for x,y in mouth],
      face, mat['17 | salmon face thread'], offset=.014, step=.035, smooth=2)

panel(root, 'Accessories | reversed shoulder belt',
      [(249,580),(268,595),(306,618),(390,650),(477,682),(529,698),(529,718),
       (477,702),(391,672),(303,639),(257,614),(240,601)], torso, black,
      bone='spine', offset=.020, thickness=.012, step=.075)
for points in [[(291,614),(309,621),(302,640)],[(323,629),(337,635),(331,650)]]:
    seam(root, 'Accessories | strap keeper', points, torso, mat['19 | dark blue sewing thread'],
         bone='spine', radius=.005, offset=.037)
seam(root, 'Uniform | trouser center seam', [(376,771),(377,812),(380,844)], torso,
     black, bone='spine', radius=.0025)
seam(root, 'Uniform | trouser pocket L', [(282,760),(278,790),(286,815)], torso,
     black, bone='spine', radius=.003)
seam(root, 'Uniform | hanging gold cord', [(450,611),(445,632),(447,650),(455,659),(462,651)],
     torso, gold, bone='spine', radius=.0025, offset=.025)
panel(root, 'Uniform | cord whistle', [(451,658),(459,658),(461,680),(453,681)], torso,
      blue, bone='spine', offset=.03, smooth=0)
arm = surface(bpy.data.objects['Uniform | relaxed sleeve R'], fallback='nearest')
panel(root, 'Sleeve insignia R | broad armband',
      [(556,628),(585,650),(568,689),(540,673)], arm, blue,
      bone='upper_arm.R', offset=.014, smooth=0, thickness=.003, step=.02)
for dx in (0, 6):
    seam(root, 'Sleeve insignia R | ivory stripe', [(555+dx,644),(548+dx,659),(546+dx,674)],
         arm, ivory, bone='upper_arm.R', offset=.019, radius=.0018)
seam(root, 'Sleeve insignia R | railway mark',
     [(559,643),(568,628),(580,632),(581,639),(570,637),(567,646),(577,648)],
     arm, ivory, bone='upper_arm.R', offset=.019, radius=.0025)

# The character art shows a fine dark tail with an arrow tip behind the shorts.
control = [(.42,.36,.67),(.98,.54,.50),(.52,.58,.17),(-.50,.54,.38)]
tail_points = [tuple((1-t)**3*a + 3*(1-t)**2*t*b + 3*(1-t)*t*t*c + t**3*d
                    for a,b,c,d in zip(*control)) for t in [i/36 for i in range(37)]]
tail = thread('Accessories | pointed tail cord', [tail_points], black,
              root.users_collection[0], radius=.017)
attach(tail, root, 'belt_tail')
tip = felt('Accessories | arrow tail tip',
           [(-.49,.40),(-.40,.46),(-.53,.42),(-.65,.48),(-.69,.24),(-.56,.31)],
           black, root.users_collection[0], depth=.54, thickness=.018)
attach(tip, root, 'belt_tail')
rig['belt_tail'] = 'Controls the pointed tail behind the shorts.'

# Gather the ponytails behind the cap; their controls pivot where the hair is tied.
worlds = {obj: obj.matrix_world.copy() for obj in root.children_recursive
          if obj.type in {'MESH', 'CURVE'}}
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode='EDIT')
for side, sign in [('L', -1), ('R', 1)]:
    rig.data.edit_bones['hair_back.'+side].head = (sign*.85, .22, 2.65)
    rig.data.edit_bones['hair_back.'+side].tail = (sign*1.0, .22, .83)
bpy.ops.object.mode_set(mode='OBJECT')
bpy.context.view_layer.update()
for obj, world in worlds.items():
    obj.matrix_world = world
root['limitation'] = ('Front construction follows the product photo; gathered rear hair and '
                     'mirrored halo follow the side character art. Hidden seam placement is interpreted.')
root['halo_reference'] = root['character_reference']
save(root, rig, 'Nozomi', output=args.output)
