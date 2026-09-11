"""Build the 170 mm Natsu Chocopuni from the product photograph and official side art."""

import argparse
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

sys.path.insert(0,str(Path(__file__).parent))
from plush_variants import PhotoFrame, load_template, panel, seam, ellipsoid, color_material, surface, save
from school_plush import school_base, sew_pattern, pink_halo
from restore_halo import attach

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--reference')
parser.add_argument('--character-reference')
parser.add_argument('--output',type=Path)
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
root,rig = load_template('Natsu',args.reference,args.character_reference,reference_model=args.output)
frame = PhotoFrame(300,750,.0048)
# Reuse the cuff curves already fitted to the shared sleeve shells and controls.
for side in ('L','R'):
    for detail in ('blue','stitch'):
        bpy.data.objects[f'Sleeve cuff {detail} {side}'].name = f'Cuffs | fitted {detail} {side}'
hair,shirt,sole,face,torso,hair_depth = school_base(root,rig,'Natsu',
    hair_color=(.95,.72,.82),shirt_color=(.94,.92,.97),shoe_color=(.26,.31,.47))
for obj in root.children_recursive:
    if obj.name.startswith('Cuffs |'):
        obj.data.materials[0] = shirt
root['reference'] = 'https://www.goodsmile.com/en/product/57216/Plushie+Natsu+Kazusa+Airi+Yoshimi'
root['rear_reference'] = 'https://static.wikitide.net/bluearchivewiki/5/5e/Natsu_00.png'
root['halo_reference'] = root['rear_reference']
root['photo_frame'] = [frame.center_x,frame.floor_y,frame.scale]
rear = color_material('Natsu | rear rose velboa',(.87,.60,.73))

# Cropped rear bob, with a single long side ponytail on the front-view left.
panel(root,'Hair | rounded rear bob',[(172,251),(205,204),(383,206),(440,262),
      (463,345),(458,425),(433,487),(384,507),(317,514),(243,506),(196,472),(170,394)],
      lambda x,z:.35+.14*max(0,1-(x/.90)**2),rear,frame=frame,thickness=.045,step=.09,subdiv=True)
panel(root,'Hair | long side ponytail L',[(166,159),(193,183),(194,220),(165,263),(159,329),
      (141,391),(123,440),(119,478),(144,522),(176,549),(143,554),(104,549),
      (78,530),(71,499),(37,496),(57,477),(79,437),(90,386),(102,333),(98,274),(120,204)],
      lambda x,z:.04+.12*math.cos(z*2),hair,frame=frame,bone='hair_back.L',
      thickness=.040,step=.085,subdiv=True)
panel(root,'Hair | short rear lock R',[(437,321),(463,359),(469,421),(456,469),
      (472,501),(444,496),(424,476),(420,435)],
      lambda x,z:.27,rear,frame=frame,bone='hair_back.R',thickness=.035,step=.09,subdiv=True)
objects = sew_pattern(root,'Natsu','hair',hair_depth,frame=frame,
    fabric='02 | lime green velboa',thickness=.020,tolerance=.004,step=.10,offset=.025,layer_gap=.007)
for obj in objects:
    if obj.name.endswith('side-panel-L'):
        attach(obj,root,'hair_front.L')
    if obj.name.endswith('side-panel-R'):
        attach(obj,root,'hair_front.R')
pink_halo(root,'Natsu',center=(.03,2.68),radius=.65)
panel(root,'Hair | arched ahoge',[(258,175),(259,139),(269,111),(288,100),
      (309,106),(323,128),(331,158),(317,178),(307,168),(308,143),
      (301,129),(288,125),(276,142),(278,174)],lambda x,z:-.14,hair,
      frame=frame,thickness=.023,step=.07)

# Two pale felt tabs and a dark rectangular inset, attached to the ponytail control.
ivory = color_material('Natsu | pale hair ribbons',(.95,.94,.99),'09 | ivory embroidery')
ink = color_material('Natsu | dark ribbon inset',(.27,.21,.29),'09 | ivory embroidery')
for name,points in [('tilted',[(146,158),(178,143),(202,210),(181,225)]),
                    ('upright',[(208,123),(248,129),(237,169),(202,174)])]:
    panel(root,'Hair | ribbon '+name,points,lambda x,z:-.25,ivory,frame=frame,
          bone='hair_back.L',thickness=.016,smooth=0)
panel(root,'Hair | ribbon dark inset',[(172,189),(181,185),(188,208),(178,213)],
      lambda x,z:-.271,ink,frame=frame,bone='hair_back.L',thickness=.001,smooth=0)
sew_pattern(root,'Natsu','face',face,frame=frame,offset=.008,layer_gap=.003,step=.06)
sew_pattern(root,'Natsu','uniform',torso,frame=frame,bone='spine',offset=.018,step=.10,tolerance=.003)

navy = color_material('Natsu | navy pleated skirt',(.22,.24,.36),'05 | blue navy woven uniform')
skirt = ellipsoid(root,'Uniform | navy pleated skirt',(.02,.06,.42),(.58,.36,.19),navy,bone='pelvis')
skirt_front = surface(skirt,fallback='nearest')
for y in (667,675):
    seam(root,'Uniform | skirt ivory hem',[(205,y),(250,y+6),(300,y+8),(353,y+5),(400,y)],
         skirt_front,ivory,frame=frame,bone='pelvis',radius=.003,offset=.010)
for x in (219,248,275,327,352,379):
    seam(root,'Uniform | skirt pleat',[(x,649),(x+3,675)],skirt_front,ink,
         frame=frame,bone='pelvis',radius=.0017,offset=.006)
for side,sign in [('L',-1),('R',1)]:
    # Thin ivory sole edging follows the existing stuffed shoe rather than a front decal.
    shoe = bpy.data.objects['Shoes | stuffed oval sole '+side]
    coords = [shoe.matrix_world@Vector(v) for v in shoe.bound_box]
    cx = (min(v.x for v in coords)+max(v.x for v in coords))/2
    cz = (min(v.z for v in coords)+max(v.z for v in coords))/2
    rx = (max(v.x for v in coords)-min(v.x for v in coords))/2*.95
    rz = (max(v.z for v in coords)-min(v.z for v in coords))/2*.95
    shoe_surface = surface(shoe)
    points = []
    for i in range(97):
        angle = i*math.tau/96
        low,high = 0,1.5
        for _ in range(12):
            radius = (low+high)/2
            x,z = cx+rx*math.cos(angle)*radius,cz+rz*math.sin(angle)*radius
            try:
                shoe_surface(x,z)
                low = radius
            except ValueError:
                high = radius
        x,z = cx+rx*math.cos(angle)*low*.95,cz+rz*math.sin(angle)*low*.95
        points.append((frame.center_x+x/frame.scale,frame.floor_y-z/frame.scale))
    seam(root,'Shoes | ivory piping '+side,points,shoe_surface,ivory,
         frame=frame,bone='foot.'+side,radius=.004,offset=.005)
panel(root,'Uniform | rear sailor collar',[(207,482),(391,482),(384,546),(217,546)],
      lambda x,z:-torso(x,z)+.10,navy,frame=frame,bone='spine',offset=-.008,
      thickness=.008,step=.09,smooth=0,tolerance=.003)
for y in (536,542):
    seam(root,'Uniform | rear collar stripe',[(220,y),(300,y+2),(382,y)],
         lambda x,z:-torso(x,z)+.10,ivory,frame=frame,bone='spine',offset=-.020,radius=.003)
root['limitation'] = ('The product photograph defines the compact sewn bob, single left ponytail, '
    'white eye pupils, sailor collar and pale shoe piping. Official three-quarter character art '
    'defines the ponytail attachment and halo. Hidden rear seams and the collar back are interpreted; '
    'the character shield is not part of this plush.')
save(root,rig,'Natsu',output=args.output)
