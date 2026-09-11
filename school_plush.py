"""Shared stuffed forms for uncapped students; SVGs supply the visible cut patterns."""

import math
from pathlib import Path

import bpy

from plush_variants import color_material, ellipsoid, remove, surface, warp
from sewing_patterns import read_pattern, sew
from restore_halo import attach, felt, thread

PATTERNS = Path(__file__).parent/'patterns'


def palette(student, source, fabric='09 | ivory embroidery'):
    colors = sorted({color for part in read_pattern(source)
                     for color in (part['fill'],part['stroke']) if color})
    return {color: color_material(f'{student} | {fabric.split(" | ")[-1]} {color}',
            tuple(int(color[i:i+2],16)/255 for i in (1,3,5)), fabric) for color in colors}


def school_base(root, rig, student, *, hair_color, shirt_color, shoe_color):
    keep = {'Face | broad peach stuffed cushion', 'Hair | fitted rear scalp',
            'Hair | soft temple gusset L', 'Hair | soft temple gusset R',
            'Uniform | broad stuffed torso', 'Uniform | rounded lower body',
            'Uniform | relaxed sleeve L', 'Uniform | relaxed sleeve R'}
    remove(root, ('Face |', 'Hair |', 'Cap |', 'Cap badge |', 'Halo |', 'Accessories |',
                  'Uniform |', 'Sleeve ', 'Sole cross', 'Ear subtle', 'Ears |'), keep=keep)
    hair = color_material(student+' | pink velboa', hair_color)
    shirt = color_material(student+' | white blouse', shirt_color, '05 | blue navy woven uniform')
    sole = color_material(student+' | cloth soles', shoe_color, '05 | blue navy woven uniform')
    skin = bpy.data.materials['01 | warm peach short pile']
    for obj in root.children_recursive:
        if obj.name.startswith('Hair |'):
            obj.data.materials[0] = hair
        if obj.name.startswith('Uniform |'):
            obj.data.materials[0] = shirt
        if obj.name.startswith('Glove |'):
            obj.data.materials[0] = skin
        if obj.name.startswith('Shoes |'):
            obj.data.materials[0] = sole
        if obj.name in {'Face | broad peach stuffed cushion', 'Hair | fitted rear scalp',
                        'Hair | soft temple gusset L','Hair | soft temple gusset R'}:
            warp(obj, lambda v: (v.x,v.y,v.z-.065))
    for side,sign in [('L',-1),('R',1)]:
        ellipsoid(root,'Ears | soft round ear '+side,(sign*.84,.03,1.80),(.10,.09,.14),skin,
                  bone='ear.'+side,segments=16,rings=8)
    ellipsoid(root,'Hair | stuffed crown',(.0,.10,2.32),(.94,.53,.65),hair,segments=40,rings=24)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    rig.data.edit_bones.remove(rig.data.edit_bones['belt_tail'])
    bpy.ops.object.mode_set(mode='OBJECT')
    root.pop('eye_pattern', None)
    old_ref = bpy.data.images.get('REFERENCE | Hikari cap and complete felt halo')
    if old_ref:
        bpy.data.images.remove(old_ref)
    face = surface(bpy.data.objects['Face | broad peach stuffed cushion'], fallback='nearest')
    # A continuous drape spans the separate chest and sleeve shells. Ray-casting
    # their silhouettes would jump between front and nearest-edge depths.
    torso = lambda x,z: -.37+.18*(x/.66)**2+.14*((z-.85)/.62)**2
    def hair_depth(x,z):
        cap = .10 - .53*math.sqrt(max(.02, 1-(x/.94)**2-((z-2.32)/.65)**2))
        front = -.625 + .11*(x/.88)**2 + .16*((z-1.92)/.62)**2
        t = max(0,min(1,(z-2.30)/.40))
        blend = t*t*(3-2*t)
        return min(cap,front)*(1-blend)+cap*blend
    return hair, shirt, sole, face, torso, hair_depth


def sew_pattern(root, student, part, depth, *, frame, fabric='09 | ivory embroidery',
                bone='head', **options):
    source = PATTERNS/f'{student.lower()}_{part}.svg'
    return sew(root, source, depth, palette(student, source, fabric), frame=frame,
               prefix={'face':'Face | ','hair':'Hair | ','uniform':'Uniform | '}[part],
               bone=bone, **options)


def pink_halo(root, student, *, center=(0,2.62), radius=.66):
    """Flat printed carrier, not a floating emissive ring; complete on both sides."""
    pink = color_material(student+' | pink halo print',(.90,.54,.72),'09 | ivory embroidery')
    backing = color_material(student+' | pale halo felt',(.99,.88,.96),'09 | ivory embroidery')
    cx,cz = center
    circle = lambda r,ox=0,oz=0: [(cx+ox+r*math.cos(t),cz+oz+r*math.sin(t))
                                  for t in [i*math.tau/96 for i in range(96)]]
    outline = circle(radius)
    if student == 'Hoshino':
        arc = lambda start: [(cx+radius*math.cos(math.radians(t)),cz+radius*math.sin(math.radians(t)))
                             for t in range(start,start+173,4)]
        outline = arc(4)+[(cx-.86,cz+.035),(cx-.88,cz),(cx-.86,cz-.035)]+arc(184)+[
            (cx+.86,cz-.035),(cx+.88,cz),(cx+.86,cz+.035)]
    plate = felt('Halo | continuous pale pink backing',outline,backing,root.users_collection[0],
                 depth=.66,thickness=.024)
    attach(plate,root)
    for side,depth in [('front',.645),('back',.675)]:
        rings = [circle(radius-.07), circle(radius*.56)] if student == 'Natsu' else [
            circle(radius-.07), circle(radius*.62,oz=-.18),circle(radius*.33,oz=-.32)]
        paths = [[(x,depth,z) for x,z in ring+ring[:1]] for ring in rings]
        if student == 'Hoshino':
            paths += [[(x,depth,cz) for x in (-.85,-.49)],[(x,depth,cz) for x in (.49,.85)]]
        else:
            paths += [[(cx+r*math.cos(angle),depth,cz+r*math.sin(angle)) for r in (.29,.44)]
                      for angle in (0,math.pi/2,math.pi,3*math.pi/2)]
        obj = thread('Halo | pink motif '+side,paths,pink,root.users_collection[0],radius=.012)
        attach(obj,root)
