"""Build Aoba Chocopuni from the official product photograph and character art."""

import argparse
import math
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).parent))
from plush_variants import (load_template, remove, color_material, surface, panel, seam,
                            oval, ellipsoid, mesh_object, warp, save)
from restore_halo import felt, thread, attach

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--reference', help='Product photo; otherwise reuse the saved model reference')
parser.add_argument('--character-reference', help='Character art; otherwise reuse the saved model reference')
parser.add_argument('--output', type=Path, help='Candidate .blend path; defaults to the repository model')
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
root, rig = load_template('Aoba', args.reference, args.character_reference, reference_model=args.output)
mat = bpy.data.materials
hair = color_material('Aoba | cream fleece hair', (.95,.91,.76))
hair_back = color_material('Aoba | shaded cream fleece', (.87,.82,.65))
uniform = color_material('Aoba | blue work jacket', (.27,.33,.44), '05 | blue navy woven uniform')
cap_mat = color_material('Aoba | soft blue cap', (.31,.35,.45), '06 | cap navy twill')
collar = color_material('Aoba | charcoal collar', (.15,.17,.21), '05 | blue navy woven uniform')
glove = color_material('Aoba | grey mittens', (.68,.67,.63), '01 | warm peach short pile')
ivory = mat['09 | ivory embroidery']
bow = color_material('Aoba | butter yellow bow', (.92,.76,.41), '09 | ivory embroidery')
clip = color_material('Aoba | yellow hair clip', (.98,.83,.035), '09 | ivory embroidery')
outline = color_material('Aoba | burgundy eye outline', (.32,.10,.16), '14 | chocolate eye outlines')
iris = color_material('Aoba | wine iris', (.63,.25,.32), '12 | amber iris satin stitch')
iris_light = color_material('Aoba | coral iris', (.93,.47,.33), '13 | butter iris satin stitch')
pupil = color_material('Aoba | dark rose pupils', (.43,.16,.22), '15 | brown pupils')
halo_gold = color_material('Aoba | orange gold halo print', (.94,.67,.32), '04 | green sewing thread')
stitch = mat['19 | dark blue sewing thread']
# Preserve the approved depth fields and their existing edge extrapolation.
old_cap_surface = surface(bpy.data.objects['Cap | structured sewn crown'], fallback='nearest')

remove(root, ('Hair |', 'Face | eye', 'Face | golden', 'Face | light iris', 'Face | pupil',
              'Face | white', 'Face | L ', 'Face | R ', 'Face | red upper', 'Face | fine green',
              'Face | tiny', 'Face | blush', 'Face | little', 'Cap |', 'Halo |', 'Accessories |',
              'Uniform | collar', 'Uniform | blue', 'Uniform | flat', 'Uniform | button',
              'Uniform | hem', 'Uniform | fine', 'Sleeve insignia',
              'Sole cross', 'Ear subtle', 'Ears |'),
       keep={'Hair | fitted rear scalp', 'Hair | soft temple gusset L', 'Hair | soft temple gusset R'})
for obj in root.children_recursive:
    if obj.name.startswith('Uniform |') and obj.type == 'MESH':
        obj.data.materials[0] = uniform
    if obj.name.startswith('Glove |') and obj.type == 'MESH':
        obj.data.materials[0] = glove
    if obj.name.startswith('Sleeve cuff blue'):
        obj.data.materials[0] = cap_mat
    if obj.name == 'Hair | fitted rear scalp':
        obj.data.materials[0] = hair_back
    if obj.name.startswith('Hair | soft temple gusset'):
        obj.data.materials[0] = hair
    if obj.name in {'Face | broad peach stuffed cushion', 'Hair | fitted rear scalp',
                    'Hair | soft temple gusset L', 'Hair | soft temple gusset R'}:
        warp(obj, lambda v: (v.x, v.y, v.z-.045))
face = surface(bpy.data.objects['Face | broad peach stuffed cushion'], fallback='nearest')
torso = surface(bpy.data.objects['Uniform | broad stuffed torso'], fallback='nearest')

# Soft asymmetric crown: a broader middle, gathered side panels and a leftward top.
profiles = [(2.35,.86,.59,0), (2.47,.97,.63,0), (2.87,1.04,.66,-.01),
            (3.07,.83,.55,-.10), (3.18,.47,.32,-.20), (3.20,.10,.09,-.25)]
vertices = []
for i, (z, rx, ry, shift) in enumerate(profiles):
    for j in range(48):
        t = j*math.tau/48
        gather = 1 + .025*math.cos(6*t+.5)*math.sin(math.pi*i/(len(profiles)-1))
        vertices.append((shift + rx*math.cos(t)*gather, ry*math.sin(t)*gather,
                         z + .14*max(0,-math.sin(t))*(i < 2) - .055*math.cos(t)*(i in (1,2,3))))
faces = [(i*48+j,i*48+(j+1)%48,(i+1)*48+(j+1)%48,(i+1)*48+j)
         for i in range(len(profiles)-1) for j in range(48)]
faces += [tuple(reversed(range(48))),tuple(range((len(profiles)-1)*48,len(vertices)))]
crown = mesh_object(root, 'Cap | soft gathered crown', vertices, faces, cap_mat, subdiv=True)
cap = surface(crown, fallback='nearest')
def visor(x, z):
    top = 2.59 - .12*(x/.80)**2 - .075*x/.8
    t = max(0,min(1,(top-z)/.32))
    front = min(cap(x,top)-.022, -.65+.18*(x/.85)**2)
    return front-.10*math.sin(t*math.pi/2)
panel(root, 'Cap | broad cloth visor',
      [(177,285),(238,269),(310,265),(393,270),(478,283),(543,309),
       (562,338),(549,360),(503,374),(426,379),(345,378),(265,374),
       (218,364),(193,344),(181,315)], visor, cap_mat,
      thickness=.035, subdiv=True, step=.075)
panel(root, 'Cap | thin gold band',
      [(166,287),(230,269),(302,258),(380,258),(456,270),(517,289),(577,313),
       (578,320),(516,297),(455,278),(380,266),(302,266),(231,277),(168,295)],
      cap, bow, step=.05, smooth=2, offset=.015)
seam(root, 'Cap | visor stitched edge',
     [(188,313),(202,343),(229,359),(305,370),(394,373),(485,370),(535,357),(550,338)],
     visor, stitch, radius=.0013)
for points in [[(252,115),(251,155),(256,194),(268,242)],
               [(498,140),(493,180),(476,218),(457,253)]]:
    seam(root, 'Cap | gathered panel seam', points, cap, stitch, radius=.0035, offset=.003)

# The school crest sits off-centre on the right fold of Aoba's cap.
def badge_position(v):
    dx, dz = (v.x+.054)*.75, (v.z-2.984)*.90
    x = .64 + dx*math.cos(.18) + dz*math.sin(.18)
    z = 2.68 - dx*math.sin(.18) + dz*math.cos(.18)
    return (x, cap(x,z) + v.y-old_cap_surface(v.x,v.z)-.008, z)
for obj in root.children_recursive:
    if obj.name.startswith('Cap badge |'):
        warp(obj, badge_position)

# White felt carrier with the student's gold circular railway halo.
center_x, center_z, radius = .10, 2.82, .52
ring = lambda r,start,end: [(center_x+r*math.cos(t),center_z+r*math.sin(t))
                           for t in [math.radians(start+(end-start)*i/72) for i in range(73)]]
halo = felt('Halo | continuous ivory circular backing', ring(radius,0,355), ivory,
            root.users_collection[0], depth=.68, thickness=.026)
attach(halo, root)
for side, depth in [('front',.661),('back',.699)]:
    paths = [[(x,depth,z) for x,z in ring(r,start,end)]
             for r,start,end in [(.465,12,167),(.465,191,348),(.385,0,360)]]
    for angle in (48,104,221,290):
        t = math.radians(angle)
        paths.append([(center_x+r*math.cos(t),depth,center_z+r*math.sin(t))
                      for r in (.385,.465)])
    lines = thread('Halo | gold railway rings '+side, paths, halo_gold,
                   root.users_collection[0], radius=.018)
    attach(lines, root)
    bar = felt('Halo | gold crossbar '+side,
               [(center_x-.39,center_z+.035),(center_x+.39,center_z+.035),
                (center_x+.39,center_z-.035),(center_x-.39,center_z-.035)],
               halo_gold, root.users_collection[0], depth=depth, thickness=.002)
    attach(bar, root)
old_reference = bpy.data.images.get('REFERENCE | Hikari cap and complete felt halo')
if old_reference:
    bpy.data.images.remove(old_reference)

# Cropped bob at the back, rounded ears, and separate soft curls at the shoulders.
for side, sign in [('L',-1),('R',1)]:
    ellipsoid(root, 'Ears | rounded fleece '+side, (sign*.80,.005,1.82),
              (.115,.09,.16), mat['01 | warm peach short pile'], bone='ear.'+side,
              segments=16, rings=8)
    panel(root, 'Hair | rear bob lock '+side,
          [(375+sign*(x-375),y) for x,y in [(549,424),(581,451),(584,503),(576,555),
              (590,594),(583,633),(557,668),(544,648),(549,615),(540,585),(547,540),(545,486)]],
          lambda x,z: .20, hair_back, bone='hair_back.'+side, thickness=.045,
          subdiv=True, step=.085)
hair_depth = lambda x,z: min(-.48,face(x,z)-.045) if z < 2.45 else -.54
for name,points in [
    ('left layered fringe',[(161,366),(193,351),(232,346),(268,354),(273,390),
        (262,425),(273,479),(249,468),(240,480),(219,465),(198,455),(180,461),(163,435)]),
    ('center blunt fringe',[(268,351),(313,357),(365,359),(414,357),(423,401),
        (427,446),(433,480),(413,482),(384,477),(361,466),(342,450),
        (347,477),(325,468),(300,449),(283,420)]),
    ('right layered fringe',[(416,354),(460,346),(492,339),(520,354),(530,389),
        (550,416),(540,442),(526,451),(538,468),(515,466),(495,449),
        (481,469),(460,454),(444,429)]),
]:
    panel(root,'Hair | '+name,points,hair_depth,hair,offset=.018,thickness=.025,
          subdiv=True,step=.085)

for side,points in [
    ('L',[(162,366),(176,366),(172,420),(176,473),(187,508),(206,531),
        (215,553),(209,576),(228,598),(214,620),(237,638),(253,658),(246,686),
        (226,669),(201,656),(179,637),(173,615),(180,589),(162,570),
        (148,548),(145,516),(149,475),(148,431)]),
    ('R',[(543,366),(572,366),(585,416),(584,467),(571,510),(569,541),
        (549,572),(558,598),(545,625),(547,666),(525,700),(523,676),
        (507,648),(514,621),(509,601),(491,610),(477,642),(470,620),
        (483,581),(499,558),(515,526),(525,490),(530,446),(528,405)]),
]:
    depth = lambda x,z: -.54 if z < 1.53 else hair_depth(x,z)-.035
    obj = panel(root,'Hair | soft curled side panel '+side,points,depth,hair,
                bone='hair_front.'+side,thickness=.040,subdiv=True,step=.08)
    if side == 'R':
        panel(root,'Hair | yellow barrette',[(526,390),(582,375),(586,395),(532,413)],
              surface(obj, fallback='nearest'),clip,bone='hair_front.R',offset=.012,smooth=0,thickness=.008)

# Wine-red embroidered eyes and the small wavering mouth.
for side,shift in [('L',0),('R',178)]:
    shifted = lambda points: [(x+shift,y) for x,y in points]
    panel(root,'Face | burgundy eye outline '+side,
          shifted([(233,493),(246,477),(266,468),(291,469),(316,482),(327,503),
                   (318,530),(298,545),(271,545),(249,533),(238,516)]),
          face,outline,step=.035)
    panel(root,'Face | wine iris '+side,
          shifted([(246,493),(261,479),(282,474),(306,482),(318,500),
                   (311,524),(295,537),(273,538),(254,527)]),
          face,iris,offset=.013,step=.035)
    panel(root,'Face | coral iris '+side,
          shifted([(251,514),(270,514),(286,520),(315,511),(306,531),
                   (291,539),(273,536),(258,527)]),
          face,iris_light,offset=.018,step=.035)
    oval(root,'Face | pupil border '+side,(289+shift,499),(12,19),face,outline,offset=.023,step=.03)
    oval(root,'Face | rose pupil '+side,(289+shift,499),(7,14),face,pupil,offset=.027,step=.03)
    panel(root,'Face | soft upper lashes '+side,
          shifted([(230,489),(241,479),(257,468),(278,463),(300,468),(320,481),
                   (331,484),(326,498),(315,490),(298,477),(276,473),(252,482),
                   (244,496),(241,511),(234,505)]),
          face,outline,offset=.030,step=.035,smooth=2)
    oval(root,'Face | ivory glint '+side,(247+shift,500),(8,7),face,ivory,offset=.034,step=.03)
    seam(root,'Face | eyebrow '+side,shifted([(262,461),(282,454),(300,460)]),
         face,outline,radius=.0018)
    for j in range(4):
        seam(root,'Face | lower lash '+side,shifted([(259+j*13,537),(262+j*13,546)]),
             face,outline,radius=.002)
    for j in range(4):
        x = 268+shift+j*4
        seam(root,'Face | blush '+side,[(x,561),(x-2,570)],face,
             mat['17 | salmon face thread'],radius=.002)
seam(root,'Face | wavy mouth',[(356,576),(362,573),(368,577),(375,574),
                              (381,577),(389,574),(394,576)],
     face,outline,radius=.0028,offset=.009)

# Work jacket, dark collar, light shoulder panels, two pockets and a yellow bow.
for side,points in [
    ('L',[(271,622),(303,623),(329,637),(333,657),(310,645),(294,660),(275,648)]),
    ('R',[(418,638),(448,625),(481,620),(481,647),(458,660),(445,646),(418,657)]),
]:
    panel(root,'Uniform | dark collar '+side,points,torso,collar,bone='spine',offset=.009,step=.06)
for side,points in [
    ('L',[(236,650),(268,655),(310,672),(340,681),(321,691),(273,679),(247,687)]),
    ('R',[(416,678),(452,665),(493,650),(507,679),(480,682),(442,683)]),
]:
    panel(root,'Uniform | pale shoulder yoke '+side,points,torso,ivory,
          bone='spine',offset=.012,step=.065)
for side,shift in [('L',0),('R',147)]:
    points = [(x+shift,y) for x,y in [(299,689),(324,685),(335,729),(314,738),(294,732)]]
    panel(root,'Uniform | patch pocket '+side,points,torso,uniform,
          bone='spine',offset=.018,step=.055,thickness=.009,smooth=1)
    seam(root,'Uniform | pocket outline '+side,points+[points[0]],torso,collar,
         bone='spine',offset=.029,radius=.0025)
    for y in (698,724):
        seam(root,'Uniform | pocket flap '+side,[(299+shift,y),(322+shift,y-3)],
             torso,collar,bone='spine',offset=.030,radius=.003)
    panel(root,'Uniform | pocket label '+side,
          [(303+shift,704),(315+shift,702),(315+shift,707),(304+shift,709)],
          torso,ivory,bone='spine',offset=.031,smooth=0)
seam(root,'Uniform | center zipper',[(377,684),(375,726),(375,777),(377,801)],
     torso,collar,bone='spine',radius=.0022,offset=.013)
seam(root,'Uniform | jacket hem',[(288,773),(328,790),(378,798),(431,786),(471,771)],
     torso,stitch,bone='spine',radius=.002)
for name,points in [
    ('left loop',[(336,631),(358,633),(376,645),(374,663),(353,671),(334,670)]),
    ('right loop',[(384,645),(408,633),(431,632),(434,672),(412,671),(385,662)]),
    ('left ribbon',[(350,663),(374,665),(367,682),(355,706),(330,687)]),
    ('right ribbon',[(386,662),(410,666),(417,681),(440,692),(411,708),(393,681)]),
    ('knot',[(375,642),(387,643),(387,665),(375,665)]),
]:
    panel(root,'Uniform | yellow bow '+name,points,torso,bow,bone='spine',
          offset=.045,thickness=.016,step=.045,smooth=1)
seam(root,'Uniform | bow fold L',[(353,646),(373,651)],torso,
     mat['10 | golden embroidery'],bone='spine',radius=.0015,offset=.056)
seam(root,'Uniform | bow fold R',[(386,652),(408,647)],torso,
     mat['10 | golden embroidery'],bone='spine',radius=.0015,offset=.056)
ellipsoid(root,'Uniform | ivory skirt under jacket',(.025,.08,.40),(.47,.26,.17),
          ivory,bone='pelvis')
for side,sign in [('L',-1),('R',1)]:
    arm = surface(bpy.data.objects['Uniform | relaxed sleeve '+side], fallback='nearest')
    points = ([(109,711),(126,729),(141,743),(117,767),(99,750)] if side == 'L' else
              [(599,706),(618,720),(652,744),(635,763),(610,741)])
    panel(root,'Sleeve | pale inset '+side,points,arm,ivory,bone='upper_arm.'+side,
          offset=.012,step=.05)
    glove_surface = surface(bpy.data.objects['Glove | cloth mitten '+side], fallback='nearest')
    base_points = ([(49,807),(60,813),(73,810)] if side == 'L' else
                   [(678,805),(692,815),(706,811)])
    points = [(375+(x-376)*.0034/.0038,947-(1000-y)*.0034/.0038) for x,y in base_points]
    seam(root,'Glove | mitten seam '+side,points,glove_surface,stitch,
         bone='hand.'+side,radius=.0016,offset=.004)

# Aoba has no tail; all remaining controls retain their original rest transforms.
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode='EDIT')
rig.data.edit_bones.remove(rig.data.edit_bones['belt_tail'])
bpy.ops.object.mode_set(mode='OBJECT')
root['halo_reference'] = root['character_reference']
root['limitation'] = ('Product photo defines the sewn design; the official side character art '
                     'defines the cropped rear bob and circular halo. Hidden seam placement is interpreted.')
save(root,rig,'Aoba',output=args.output)
