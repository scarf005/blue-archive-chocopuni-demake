"""Build the 170 mm Hoshino Chocopuni from product and rear/side character references."""

import argparse
import math
from pathlib import Path
import sys

import bpy

sys.path.insert(0,str(Path(__file__).parent))
from plush_variants import PhotoFrame, load_template, panel, seam, ellipsoid, color_material, surface, save
from school_plush import school_base, sew_pattern, pink_halo
from restore_halo import attach

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--reference')
parser.add_argument('--character-reference')
parser.add_argument('--rear-reference', help='Optional official rear/side reference to pack')
parser.add_argument('--output',type=Path)
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
root,rig = load_template('Hoshino',args.reference,args.character_reference,reference_model=args.output)
frame = PhotoFrame(325,745,.0048)
hair,shirt,sole,face,torso,hair_depth = school_base(root,rig,'Hoshino',
    hair_color=(.94,.65,.81),shirt_color=(.95,.94,.98),shoe_color=(.50,.50,.48))
root['reference'] = 'https://www.goodsmile.com/en/product/60773/Chocopuni+Plushie+Shiroko+Hoshino'
root['rear_reference'] = 'https://www.goodsmile.com/en/product/1139188/Hoshino'
root['halo_reference'] = root['rear_reference']
root['photo_frame'] = [frame.center_x,frame.floor_y,frame.scale]
if args.rear_reference:
    previous = bpy.data.images.get('REFERENCE | Hoshino side character construction')
    if previous:
        bpy.data.images.remove(previous)
    image = bpy.data.images.load(args.rear_reference)
    image.name = 'REFERENCE | Hoshino side character construction'
    image.pack()
    image.use_fake_user = True

# Long, unbound hair spreads behind the seated body; not twin tails.
rear = color_material('Hoshino | rear pink velboa',(.83,.53,.70))
for side,points in [
    ('L',[(191,296),(245,365),(205,455),(169,519),(138,567),(121,604),
          (88,623),(55,618),(48,597),(74,551),(99,508),(126,446),(153,362)]),
    ('R',[(454,297),(477,343),(500,420),(535,491),(568,548),(596,595),
          (585,624),(546,625),(521,606),(506,566),(469,502),(430,421),(411,357)])]:
    panel(root,'Hair | long rear fall '+side,points,lambda x,z:.31+.14*(1-min(1,abs(x))),rear,
          bone='hair_back.'+side,frame=frame,thickness=.045,step=.10,subdiv=True)
# A central drape closes the back and joins both independently poseable side falls.
panel(root,'Hair | center rear drape',[(229,298),(405,298),(434,425),(462,554),(446,613),
      (391,637),(323,639),(255,632),(213,607),(201,551),(220,411)],
      lambda x,z:.43+.09*math.cos(x*2),rear,frame=frame,thickness=.045,step=.10,subdiv=True)
objects = sew_pattern(root,'Hoshino','hair',hair_depth,frame=frame,
                      fabric='02 | lime green velboa',thickness=.020,tolerance=.004,
                      step=.10,offset=.025,layer_gap=.007)
for obj in objects:
    if obj.name.endswith('side-panel-L'):
        attach(obj,root,'hair_front.L')
    if obj.name.endswith('side-panel-R'):
        attach(obj,root,'hair_front.R')
pink_halo(root,'Hoshino',center=(0,2.62),radius=.64)
# Hollow felt ahoge, with the opening retained by a compound SVG-style panel.
outer = [(309,151),(301,119),(304,87),(321,63),(344,57),(369,68),(388,91),
         (396,127),(391,153),(374,149),(376,117),(367,98),(352,90),(337,96),(329,117),(327,151)]
panel(root,'Hair | looped ahoge',outer,lambda x,z:-.12,hair,frame=frame,
      thickness=.022,step=.08,smooth=3)
sew_pattern(root,'Hoshino','face',face,frame=frame,offset=.008,layer_gap=.003,step=.065)
sew_pattern(root,'Hoshino','uniform',torso,frame=frame,bone='spine',offset=.018,step=.10,tolerance=.003)

# Checked navy skirt, including the visible underbody and rear.
navy = color_material('Hoshino | checked navy skirt',(.22,.27,.39),'05 | blue navy woven uniform')
check = color_material('Hoshino | blue grey checks',(.42,.47,.57),'19 | dark blue sewing thread')
skirt = ellipsoid(root,'Uniform | checked skirt',(.02,.07,.48),(.58,.36,.24),navy,bone='pelvis')
skirt_front = surface(skirt,fallback='nearest')
for x in (238,266,294,348,378,403):
    seam(root,'Uniform | vertical skirt check',[(x,621),(x+3,650),(x+5,683)],
         skirt_front,check,frame=frame,bone='pelvis',radius=.0018,offset=.007)
for y in (637,660,680):
    seam(root,'Uniform | horizontal skirt check',[(220,y),(271,y+7),(325,y+10),(379,y+6),(426,y)],
         skirt_front,check,frame=frame,bone='pelvis',radius=.002,offset=.008)
for side,sign in [('L',-1),('R',1)]:
    # White cuffs cover the inherited sleeve endpoints, with a single soft stitch.
    sleeve = surface(bpy.data.objects['Uniform | relaxed sleeve '+side],fallback='nearest')
    points = [(325+sign*(x-325),y) for x,y in [(514,557),(533,581),(520,600),(500,574)]]
    panel(root,'Uniform | blouse cuff '+side,points,sleeve,shirt,frame=frame,
          bone='forearm.'+side,offset=.016,thickness=.008,step=.075)
root['limitation'] = ('Product photo defines the 170 mm sewn design and heterochromatic embroidery; '
    'official art and WING three-quarter views define long loose hair and complete halo. '
    'Hidden plush seam placement and the schoolbag harness back are interpreted. Weapons are not part of the plush.')
save(root,rig,'Hoshino',output=args.output)
