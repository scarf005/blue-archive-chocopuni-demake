"""Build a stuffed, sewn Hikari from measured reference landmarks, via Blender MCP."""
import bpy
import math
import random
from pathlib import Path
from mathutils import Vector, geometry
from mathutils.bvhtree import BVHTree

OUT = Path('/home/scarf/opt/blender-5.2.1-linux-x64/hikari_chocopuni')
K = .0034
random.seed(19)
scene = bpy.data.scenes.new('Hikari • sewn plush v2')
bpy.context.window.scene = scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = .05
model = bpy.data.collections.new('Hikari | sewn components')
scene.collection.children.link(model)
stage = bpy.data.collections.new('Studio and inspection cameras')
scene.collection.children.link(stage)

def xyz(p, depth):
    return ((p[0]-376)*K, depth, (1000-p[1])*K)

def srgb(c):
    return c/12.92 if c <= .04045 else ((c+.055)/1.055)**2.4

def fabric(name, color, weave=False, thread=False):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    rgb = tuple(srgb(c) for c in color)
    m.diffuse_color = (*rgb, 1)
    n, links = m.node_tree.nodes, m.node_tree.links
    p = n.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*rgb, 1)
    p.inputs['Roughness'].default_value = .91 if not thread else .68
    p.inputs['Specular IOR Level'].default_value = .12
    p.inputs['Sheen Weight'].default_value = .065 if not thread else .035
    p.inputs['Sheen Roughness'].default_value = .8
    coord = n.new('ShaderNodeTexCoord')
    noise = n.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = 470 if not weave else 700
    noise.inputs['Detail'].default_value = 2
    links.new(coord.outputs['Object'], noise.inputs['Vector'])
    ramp = n.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = .12
    ramp.color_ramp.elements[0].color = (*(v*.88 for v in rgb),1)
    ramp.color_ramp.elements[1].position = .86
    ramp.color_ramp.elements[1].color = (*(min(1,v*1.10+.001) for v in rgb),1)
    links.new(noise.outputs['Fac'],ramp.inputs[0])
    links.new(ramp.outputs[0],p.inputs['Base Color'])
    bump = n.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = .52
    bump.inputs['Distance'].default_value = .0035 if not thread else .0013
    links.new(noise.outputs['Fac'],bump.inputs['Height'])
    links.new(bump.outputs[0],p.inputs['Normal'])
    if weave or thread:
        wave = n.new('ShaderNodeTexWave')
        wave.wave_type = 'BANDS'
        wave.bands_direction = 'DIAGONAL' if weave else 'X'
        wave.inputs['Scale'].default_value = 310 if weave else 550
        wave.inputs['Distortion'].default_value = 1.2 if weave else .35
        links.new(coord.outputs['Object'],wave.inputs['Vector'])
        b2 = n.new('ShaderNodeBump')
        b2.inputs['Strength'].default_value = .26
        b2.inputs['Distance'].default_value = .0012
        links.new(wave.outputs['Color'],b2.inputs['Height'])
        links.new(bump.outputs['Normal'],b2.inputs['Normal'])
        links.new(b2.outputs['Normal'],p.inputs['Normal'])
    return m

skin = fabric('01 | warm peach short pile', (.95,.76,.70))
green = fabric('02 | lime green velboa', (.70,.80,.40))
greenback = fabric('03 | shaded green velboa', (.60,.73,.30))
hairseam = fabric('04 | green sewing thread', (.59,.70,.32),thread=True)
navy = fabric('05 | blue navy woven uniform', (.20,.25,.36),weave=True)
capnavy = fabric('06 | cap navy twill', (.18,.22,.32),weave=True)
sole = fabric('07 | dark stuffed shoes', (.16,.19,.25),weave=True)
blue = fabric('08 | flat blue embroidered trim', (.22,.46,.70),thread=True)
ivory = fabric('09 | ivory embroidery', (.96,.94,.87),thread=True)
gold = fabric('10 | golden embroidery', (.85,.65,.23),thread=True)
lightgold = fabric('11 | pale gold embroidery', (.96,.85,.54),thread=True)
eye_gold = fabric('12 | amber iris satin stitch', (.94,.73,.24),thread=True)
eye_light = fabric('13 | butter iris satin stitch', (.99,.91,.56),thread=True)
brown = fabric('14 | chocolate eye outlines', (.23,.13,.09),thread=True)
pupil = fabric('15 | brown pupils', (.55,.31,.12),thread=True)
red = fabric('16 | burgundy face thread', (.62,.18,.17),thread=True)
blush = fabric('17 | salmon face thread', (.96,.49,.48),thread=True)
black = fabric('18 | woven shoulder strap', (.105,.12,.155),weave=True)
stitch_navy = fabric('19 | dark blue sewing thread', (.26,.30,.38),thread=True)
button = fabric('20 | muted beige button embroidery', (.73,.69,.60),thread=True)

def link_mesh(name, verts, faces, mat, collection=model):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    o = bpy.data.objects.new(name, mesh)
    collection.objects.link(o)
    mesh.materials.append(mat)
    for f in mesh.polygons: f.use_smooth = True
    return o

def smooth_outline(points, steps=6):
    out=[]
    for i,b in enumerate(points):
        a,c,d=points[(i-1)%len(points)],points[(i+1)%len(points)],points[(i+2)%len(points)]
        for j in range(steps):
            t=j/steps
            out.append(tuple(.5*((2*b[k])+(-a[k]+c[k])*t+(2*a[k]-5*b[k]+4*c[k]-d[k])*t*t+(-a[k]+3*b[k]-3*c[k]+d[k])*t*t*t) for k in (0,1)))
    return out

def surface(o, fallback=-.4):
    tree=BVHTree.FromPolygons([v.co.copy() for v in o.data.vertices],[list(f.vertices) for f in o.data.polygons])
    def get(p):
        co,normal,index,dist=tree.ray_cast(Vector(xyz(p,-5)),Vector((0,1,0)))
        if co is not None: return co.y
        near,normal,index,dist=tree.find_nearest(Vector(xyz(p,fallback)))
        return near.y if near is not None else fallback
    return get

def pillow(name, outline, center, edge, front, back, mat, exponent=.8, wrinkle=0):
    ring=smooth_outline(outline)
    count=len(ring)
    verts=[xyz(center,edge-front)]
    rings=40
    for j in range(1,rings):
        t=math.pi*j/rings
        r=math.sin(t)
        depth=edge-(front if t<math.pi/2 else -back)*abs(math.cos(t))**exponent
        for i,q in enumerate(ring):
            p=(center[0]+r*(q[0]-center[0]),center[1]+r*(q[1]-center[1]))
            perturb=wrinkle*math.sin(i/count*math.tau*9+r*11)*r**5*math.sin(t*2)
            verts.append(xyz(p,depth+perturb))
    verts.append(xyz(center,edge+back))
    faces=[(0,1+(i+1)%count,1+i) for i in range(count)]
    for j in range(rings-2):
        a=1+j*count
        b=a+count
        faces.extend((a+i,a+(i+1)%count,b+(i+1)%count,b+i) for i in range(count))
    last=1+(rings-2)*count
    faces.extend((last+i,last+(i+1)%count,len(verts)-1) for i in range(count))
    o=link_mesh(name,verts,faces,mat)
    # Recalculate consistently before raycasting or adding pile.
    import bmesh
    bm=bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(o.data); bm.free()
    return o,surface(o,edge-front)

def strokes(name, paths, mat, radius=.001, collection=model):
    c=bpy.data.curves.new(name,'CURVE')
    c.dimensions='3D'; c.resolution_u=1
    c.bevel_depth=radius; c.bevel_resolution=1; c.resolution_u=1
    for path in paths:
        if len(path)<2: continue
        s=c.splines.new('POLY'); s.points.add(len(path)-1)
        for v,co in zip(s.points,path): v.co=(*co,1)
    o=bpy.data.objects.new(name,c); collection.objects.link(o)
    c.materials.append(mat)
    return o

def seam(name, points, surf, mat, radius=.0015, dashed=False, offset=.003):
    # Open Catmull-Rom, sampled in reference-image coordinates.
    sample=[]
    for i in range(len(points)-1):
        a,b,c,d=points[max(0,i-1)],points[i],points[i+1],points[min(len(points)-1,i+2)]
        for j in range(16):
            t=j/16
            sample.append(tuple(.5*(2*b[k]+(-a[k]+c[k])*t+(2*a[k]-5*b[k]+4*c[k]-d[k])*t*t+(-a[k]+3*b[k]-3*c[k]+d[k])*t**3) for k in (0,1)))
    sample.append(points[-1])
    if dashed:
        paths=[]; run=[]; length=0
        for i,p in enumerate(sample):
            if i: length+=math.dist(p,sample[i-1])
            if int(length/2.1)%2==0: run.append(xyz(p,surf(p)-offset))
            elif run:
                if len(run)>1: paths.append(run)
                run=[]
        if len(run)>1: paths.append(run)
    else: paths=[[xyz(p,surf(p)-offset) for p in sample]]
    return strokes(name,paths,mat,radius)

def applique(name, outline, surf, mat, offset=.0025, thickness=.0015, smooth=True, stitch=False):
    boundary=smooth_outline(outline,4) if smooth else outline
    # Uniform conforming triangulation keeps continuous normals across fabric panels.
    vectors=[Vector(p) for p in boundary]
    xmin,xmax=min(p[0] for p in boundary),max(p[0] for p in boundary)
    ymin,ymax=min(p[1] for p in boundary),max(p[1] for p in boundary)
    step=4 if max(xmax-xmin,ymax-ymin)>70 else 2
    for row in range(1,math.ceil((ymax-ymin)/step)):
        y=ymin+row*step
        xs=[]
        for a,b in zip(boundary,boundary[1:]+boundary[:1]):
            if (a[1]<=y<b[1]) or (b[1]<=y<a[1]): xs.append(a[0]+(y-a[1])/(b[1]-a[1])*(b[0]-a[0]))
        xs.sort()
        for x1,x2 in zip(xs[::2],xs[1::2]):
            for col in range(1,math.floor((x2-x1)/step)):
                vectors.append(Vector((x1+col*step,y)))
    poly=list(range(len(boundary)))
    area=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(boundary,boundary[1:]+boundary[:1]))
    if area<0: poly.reverse()
    coords,edges,faces,*_=geometry.delaunay_2d_cdt(vectors,[],[poly],1,.00001,False)
    verts=[xyz(p,surf(p)-offset) for p in coords]
    o=link_mesh(name,verts,faces,mat)
    if o.data.polygons and sum(f.normal.y for f in o.data.polygons)>0:
        import bmesh
        bm=bmesh.new(); bm.from_mesh(o.data)
        bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
        bm.to_mesh(o.data); bm.free()
    if thickness:
        m=o.modifiers.new('Thin sewn cloth','SOLIDIFY'); m.thickness=thickness
    if stitch:
        paths=[]
        ymin,ymax=min(p[1] for p in boundary),max(p[1] for p in boundary)
        for row in range(math.ceil((ymax-ymin)/1.0)):
            y=ymin+row+random.uniform(-.12,.12)
            xs=[]
            for a,b in zip(boundary,boundary[1:]+boundary[:1]):
                if (a[1]<=y<b[1]) or (b[1]<=y<a[1]): xs.append(a[0]+(y-a[1])/(b[1]-a[1])*(b[0]-a[0]))
            xs.sort()
            for x1,x2 in zip(xs[::2],xs[1::2]):
                if x2-x1<1: continue
                path=[]
                for i in range(max(2,int((x2-x1)/3))):
                    t=i/max(1,int((x2-x1)/3)-1)
                    x=x1+(x2-x1)*min(1,t)
                    p=(x,y)
                    path.append(xyz(p,surf(p)-offset-.0012))
                paths.append(path)
        strokes(name+' | satin stitch rows',paths,mat,.00065)
    return o

def disk(name, center, rx, ry, surf, mat, offset=.004, stitch=False):
    return applique(name,[(center[0]+rx*math.cos(i*math.tau/32),center[1]+ry*math.sin(i*math.tau/32)) for i in range(32)],surf,mat,offset,stitch=stitch)

# Stuffing forms follow the reference silhouette; all major parts are closed volumes.
head_outline=[(120,388),(144,321),(241,290),(373,284),(503,301),(598,345),(635,418),(616,514),(567,571),(475,604),(370,612),(270,592),(192,551),(139,484)]
backhair,backhair_s=pillow('Hair | stuffed rear cap',[(111,331),(181,251),(390,239),(571,283),(634,391),(642,558),(600,681),(483,749),(272,747),(132,643),(100,499)],(370,464),.19,.24,.46,greenback)
for side,points,center in [
    ('L',[(115,535),(181,552),(160,635),(114,702),(70,751),(14,785),(5,762),(26,694),(63,632)],(97,646)),
    ('R',[(619,526),(651,567),(694,635),(735,707),(742,756),(720,782),(690,751),(650,718),(605,628)],(670,660)),
]: pillow('Hair | rear loose lock '+side,points,center,.16,.025,.025,greenback,1.0)

torso,torso_s=pillow('Uniform | broad stuffed torso',[(244,582),(316,600),(438,598),(511,573),(563,638),(558,741),(524,814),(457,883),(344,909),(269,865),(213,785),(205,685)],(386,744),.08,.40,.32,navy,.7,.009)
for v in torso.data.vertices:
    if v.co.y>=-.04: continue
    px=v.co.x/K+376; py=1000-v.co.z/K
    for yy,slope,strength in [(666,.14,.011),(725,-.10,.014),(808,.08,.009)]:
        d=py-(yy+slope*(px-380))
        v.co.y+=strength*math.exp(-(d/9)**2)*math.exp(-((px-380)/140)**4)
torso.data.update(); torso_s=surface(torso,-.32)
for side,points,center,glove in [
    ('L',[(226,614),(254,654),(210,706),(172,758),(139,798),(86,807),(54,766),(74,717),(132,669),(176,641)],(154,716),[(53,766),(91,769),(100,803),(70,826),(38,821),(33,800)]),
    ('R',[(552,614),(603,642),(656,692),(708,754),(707,785),(663,803),(633,777),(595,733),(558,701),(531,658)],(620,715),[(666,770),(706,766),(724,794),(715,817),(688,816),(662,796)]),
]:
    arm,arm_s=pillow('Uniform | relaxed sleeve '+side,points,center,.10,.235,.19,navy,.85,.005)
    pillow('Glove | cloth mitten '+side,glove,(sum(p[0] for p in glove)/len(glove),sum(p[1] for p in glove)/len(glove)),.10,.19,.13,ivory)
    if side=='L':
        a=[(66,743),(104,773),(143,792)]; b=[(72,733),(112,760),(153,780)]
        patchpts=[(135,652),(156,643),(187,675),(168,688)]
    else:
        a=[(644,780),(672,758),(690,742)]; b=[(638,773),(663,750),(683,737)]
        patchpts=[(611,657),(631,668),(613,693),(594,677)]
    seam('Sleeve cuff blue '+side,a,arm_s,blue,.008)
    seam('Sleeve cuff stitch '+side,b,arm_s,stitch_navy,.001,dashed=True)
    applique('Sleeve insignia '+side,patchpts,arm_s,blue,stitch=True)
    seam('Sleeve insignia line '+side,[patchpts[0],patchpts[1],patchpts[2]],arm_s,ivory,.0012,offset=.006)

feet=[]
for side,points,center in [
    ('L',[(239,766),(291,763),(332,794),(351,850),(346,917),(326,969),(285,992),(222,995),(179,974),(157,932),(149,872),(166,814),(199,780)],(249,880)),
    ('R',[(522,752),(566,746),(610,770),(638,817),(650,885),(641,944),(616,981),(568,992),(518,981),(485,947),(469,885),(470,827),(491,780)],(561,875)),
]:
    foot,fs=pillow('Shoes | stuffed oval sole '+side,points,center,-.31,.40,.25,sole,.65,.003)
    feet.append((foot,fs))
    if side=='L': seampts=[(159,898),(190,925),(239,938),(287,939),(335,923)]
    else: seampts=[(478,910),(515,920),(563,920),(604,912),(643,894)]
    seam('Sole cross seam '+side,seampts,fs,black,.003)
    # A subdued stitch, not the bright raised shoe piping of v1.
    seam('Sole edge topstitch '+side,[(p[0]+(center[0]-p[0])*.045,p[1]+(center[1]-p[1])*.045) for p in points+points[:1]],fs,stitch_navy,.001,dashed=True)

head,face_s=pillow('Face | broad peach stuffed cushion',head_outline,(377,450),-.015,.59,.42,skin,.63,.0012)
# The green sewn scalp continues around both temples and across the entire back.
scalpverts=[v.co+v.normal*.014 for v in head.data.vertices]
scalpfaces=[]
for f in head.data.polygons:
    center=sum((head.data.vertices[i].co for i in f.vertices),Vector())/len(f.vertices)
    py=1000-center.z/K
    if (center.y>-.27 or py<340) and (py<565 or center.y>.15): scalpfaces.append(tuple(f.vertices))
scalp=link_mesh('Hair | fitted rear scalp',scalpverts,scalpfaces,greenback)
for side,points,center in [
    ('L',[(120,411),(83,413),(47,423),(42,440),(61,460),(91,482),(120,493),(143,464)],(100,447)),
    ('R',[(620,405),(665,397),(703,396),(719,408),(711,428),(683,455),(648,481),(619,469)],(659,431)),
]:
    ear,ear_s=pillow('Ears | soft pointed fleece '+side,points,center,.01,.15,.10,skin)
    seam('Ear subtle folded seam '+side,[points[1],points[2],points[3]],ear_s,skin,.0009,dashed=True)

# Embroidered face: filled silhouettes conform to the head, at sub-millimetre relief.
eye_shapes=[
    ('L',[(239,433),(251,419),(269,418),(294,432),(315,453),(319,482),(309,502),(281,510),(255,504),(240,486),(235,459)],(282,460)),
    ('R',[(449,424),(464,409),(488,407),(511,416),(524,439),(526,470),(515,495),(492,504),(464,499),(448,481),(442,453)],(486,454)),
]
for side,shape,center in eye_shapes:
    applique('Face | eye chocolate outline '+side,shape,face_s,brown,.002,stitch=True)
    inner=[(center[0]+(p[0]-center[0])*.91,center[1]+(p[1]-center[1])*.92) for p in shape]
    applique('Face | golden iris '+side,inner,face_s,eye_gold,.005,stitch=True)
    if side=='L': lower=[(242,472),(260,472),(281,478),(304,477),(314,471),(309,495),(288,504),(265,501),(250,491)]
    else: lower=[(448,467),(470,467),(489,472),(516,464),(516,483),(505,495),(480,498),(460,492)]
    applique('Face | light iris stitches '+side,lower,face_s,eye_light,.007,stitch=True)
    disk('Face | pupil dark border '+side,center,13,18,face_s,brown,.009,True)
    disk('Face | pupil amber '+side,center,8.7,13,face_s,pupil,.011,True)
    glint=(center[0]-35,center[1]+17)
    disk('Face | white stitched glint '+side,glint,9,5.5,face_s,ivory,.012,True)

for name,outline in [
    ('L upper lash',[(235,438),(243,417),(254,410),(274,416),(298,429),(314,447),(330,442),(323,427),(300,418),(276,407),(253,401),(246,410),(231,407)]),
    ('L outer lash',[(239,451),(226,444),(224,432),(215,443),(205,446),(216,455),(208,462),(223,483),(232,484),(222,465),(241,471)]),
    ('R upper lash',[(436,437),(445,419),(463,405),(489,399),(513,409),(528,424),(532,420),(527,410),(513,402),(489,391),(467,394),(447,404),(435,416)]),
    ('R outer lash',[(526,433),(535,431),(539,414),(551,420),(551,431),(562,438),(552,451),(548,468),(537,480),(531,474),(539,454)]),
]: applique('Face | '+name,outline,face_s,brown,.006,stitch=True)
for side,pts in [('L',[(279,400),(295,403),(316,414)]),('R',[(438,409),(464,397),(487,396)])]:
    seam('Face | red upper eyelid '+side,pts,face_s,red,.0028,offset=.004)
for side,pts in [('L',[(298,361),(311,368),(325,376)]),('R',[(437,373),(451,367),(466,354)])]:
    seam('Face | fine green eyebrow '+side,pts,face_s,hairseam,.0017,offset=.004)
seam('Face | tiny pout',[(376,550),(382,546),(387,546),(393,550),(398,552)],face_s,red,.0022,offset=.004)
for side,x,y in [('L',248,534),('R',520,528)]:
    # Short uneven stitches give soft cheeks rather than thick plastic bars.
    paths=[]
    for j in range(40):
        xx=x+random.gauss(0,10); yy=y+random.gauss(0,5)
        p=(xx,yy); q=(xx+random.uniform(-1,1),yy+random.uniform(3,9))
        paths.append([xyz(p,face_s(p)-.002),xyz(q,face_s(q)-.002)])
    strokes('Face | blush satin stitches '+side,paths,blush,.0008)
    for dx,dy in [(-14,-37),(-4,-30),(6,-25)]:
        p=(x+dx,y+dy)
        seam('Face | little cheek mark '+side,[p,(p[0]+2,p[1]+3)],face_s,red,.0015,offset=.003)

# Layered felt hair: rounded cut edges with shallow curved thickness, no polygon blocks.
def hair_depth(p):
    r2=((p[0]-377)/273)**2+((p[1]-450)/182)**2
    analytic=-.110-.59*max(.12,1-r2)**.315-.025
    mix=max(0,min(1,(p[1]-380)/35))
    mix=mix*mix*(3-2*mix)
    return analytic*(1-mix)+(face_s(p)-.026)*mix

hair_parts=[
    ('outer left fringe',[(120,293),(158,286),(204,297),(219,331),(211,376),(224,436),(206,427),(185,415),(154,395),(133,365),(123,338)]),
    ('left fringe',[(192,291),(253,287),(300,295),(290,329),(281,367),(280,404),(291,446),(268,430),(262,443),(244,424),(221,400),(207,365)]),
    ('center fringe',[(296,294),(361,293),(405,295),(448,306),(438,343),(433,385),(438,440),(416,426),(419,461),(395,454),(378,433),(371,412),(369,450),(354,432),(349,457),(337,441),(326,408),(321,371),(315,332)]),
    ('right fringe',[(446,302),(499,299),(548,310),(574,344),(596,416),(572,428),(550,414),(528,391),(532,417),(505,405),(482,380),(464,350)]),
]
for name,pts in hair_parts:
    applique('Hair | '+name,pts,hair_depth,green,.007,.016)

for side,points,center in [
    ('L',[(114,306),(157,310),(183,385),(195,465),(204,555),(187,587),(127,582),(110,505),(104,401)],(148,445)),
    ('R',[(574,305),(626,310),(645,385),(649,470),(647,552),(625,595),(587,575),(570,468),(560,382)],(607,449)),
]: pillow('Hair | soft temple gusset '+side,points,center,-.05,.42,.16,green,.80)
side_locks=[
    ('L',[(117,347),(168,365),(180,406),(191,469),(200,527),(213,570),(211,604),(215,630),(232,661),(237,681),(229,699),(216,709),(195,715),(174,710),(163,700),(189,698),(187,685),(169,668),(135,645),(110,616),(104,585),(112,541),(112,483),(111,429),(108,381)]),
    ('R',[(576,349),(614,331),(636,360),(647,413),(645,477),(649,527),(660,561),(654,600),(643,628),(622,650),(609,672),(618,681),(646,690),(630,701),(607,710),(587,711),(567,704),(557,688),(559,666),(571,640),(582,619),(572,578),(573,531),(569,479),(562,427)])
]
for side,pts in side_locks:
    def lockdepth(p):
        # Draped cloth sweeps away from the cheek toward the shoulder.
        return -.49-.045*math.cos((p[1]-470)/180*math.pi)+max(0,p[1]-580)*.0006
    obj=applique('Hair | curled side panel '+side,pts,lockdepth,green,.014,.022)
    if side=='L': seampts=[(122,346),(122,403),(136,467),(163,534),(197,578)]
    else: seampts=[(626,379),(627,445),(624,509),(607,565),(587,586)]
    seam('Hair | stitched lock edge '+side,seampts,lockdepth,hairseam,.0011,dashed=True,offset=.018)

# Collar, embroidered jacket placket, real flat woven straps, buckle and stitches.
for side,pts in [('L',[(240,603),(264,620),(292,627),(310,611)]),('R',[(424,611),(447,602),(477,592)])]:
    seam('Uniform | collar piping '+side,pts,torso_s,ivory,.0023,offset=.004)
for side,pts in [('L',[(310,627),(304,671),(305,709),(304,751)]),('R',[(469,615),(475,664),(480,716),(480,760)])]:
    seam('Uniform | blue placket embroidery '+side,pts,torso_s,blue,.005,offset=.003)
seam('Uniform | collar blue border',[(269,624),(332,631),(394,626),(453,619)],torso_s,blue,.004,offset=.003)
seam('Uniform | collar gold bar',[(386,612),(402,612)],torso_s,gold,.003,offset=.004)
for x,y in [(324,659),(465,705),(309,754),(468,754)]:
    disk('Uniform | flat embroidered button',(x,y),7,6,torso_s,button,.004,True)
    seam('Uniform | button slit',[(x-2,y),(x+2,y)],torso_s,stitch_navy,.0007,offset=.007)
seam('Uniform | hem blue seam',[(273,803),(317,860),(354,898),(401,901),(448,880),(472,838)],torso_s,blue,.0035,offset=.004)
for pts in [[(279,672),(258,682),(250,701)],[(439,740),(411,747),(383,750)],[(276,776),(301,781),(331,780)]]:
    seam('Uniform | fine gathered stitch',pts,torso_s,stitch_navy,.001,offset=.003)
strap_points=[(490,596),(505,601),(492,629),(465,655),(419,685),(369,712),(314,738),(258,755),(230,754),(226,740),(251,738),(306,721),(362,695),(414,668),(455,643),(477,617)]
applique('Accessories | diagonal woven shoulder belt',strap_points,torso_s,black,.011,.012)
seam('Accessories | shoulder belt edge stitching',[(498,602),(484,626),(455,653),(413,678),(362,704),(307,731),(253,747),(235,750)],torso_s,stitch_navy,.0008,True,.025)
for pts in [[(463,626),(469,638),(482,643)],[(432,649),(440,663),(450,666)]]:
    seam('Accessories | shoulder strap keeper',pts,torso_s,black,.008,offset=.026)
seam('Accessories | keeper hardware',[(469,628),(474,639),(485,642),(490,632)],torso_s,button,.0017,offset=.029)
applique('Accessories | flat waist belt',[(276,771),(337,779),(401,779),(464,767),(492,753),(492,780),(461,793),(402,803),(337,800),(286,793)],torso_s,black,.015,.010)
applique('Accessories | squared brass buckle',[(381,772),(410,772),(411,779),(386,779),(384,790),(410,790),(410,797),(379,797),(372,791),(373,780)],torso_s,gold,.028,.002,smooth=False,stitch=True)
seam('Accessories | buckle tongue',[(375,785),(399,785)],torso_s,gold,.002,offset=.033)
tail,tail_s=pillow('Accessories | loose belt end',[(503,801),(542,812),(594,839),(657,853),(699,853),(730,867),(742,877),(701,880),(654,871),(593,864),(540,841),(512,829)],(607,848),.14,.020,.018,black)

# Cap is a stuffed sewn crown, with a deep curved visor that occupies the full forehead.
cap_outline=[(115,266),(124,206),(140,144),(162,94),(196,57),(242,30),(306,11),(376,5),(452,12),(513,33),(563,64),(599,106),(624,157),(636,211),(640,268),(568,237),(491,212),(417,197),(348,197),(265,209),(187,237)]
def crown_depth(p):
    x=abs(p[0]-376)
    lo,hi=0.,1.
    for _ in range(22):
        v=(lo+hi)*.5
        rx=263*(v*(2-v))**.40
        front_factor=math.sqrt(max(0,1-(x/max(rx,.001))**2))
        y=5+263*v-73*front_factor*v**4
        if y<p[1] or x>rx: lo=v
        else: hi=v
    v=(lo+hi)*.5
    r=(v*(2-v))**.40
    return -.64*r*math.sqrt(max(.001,1-(x/max(263*r,.001))**2))
capverts=[xyz((376,5),0)]
capfaces=[]
nr,ns=50,160
for j in range(1,nr+1):
    v=j/nr; r=(v*(2-v))**.40
    for i in range(ns):
        t=i*math.tau/ns
        p=(376+263*r*math.cos(t),5+263*v-73*max(0,-math.sin(t))*v**4)
        capverts.append(xyz(p,.64*r*math.sin(t)))
capfaces.extend((0,1+i,1+(i+1)%ns) for i in range(ns))
for j in range(nr-1):
    a=1+j*ns; b=a+ns
    capfaces.extend((a+i,b+i,b+(i+1)%ns,a+(i+1)%ns) for i in range(ns))
capverts.append(xyz((376,268),0))
capfaces.extend((1+(nr-1)*ns+i,len(capverts)-1,1+(nr-1)*ns+(i+1)%ns) for i in range(ns))
cap=link_mesh('Cap | structured sewn crown',capverts,capfaces,capnavy)
cap_s=crown_depth
visor_outline=[(123,269),(191,235),(281,210),(374,202),(461,211),(553,237),(631,272),(626,296),(613,321),(589,328),(551,325),(497,315),(441,309),(385,306),(321,310),(257,318),(195,327),(164,327),(143,311),(131,291)]
def visor_s(p):
    x=abs(p[0]-376)/255
    top=202+70*x**1.7
    bottom=306+21*x
    t=max(0,min(1,(p[1]-top)/max(8,bottom-top)))
    return crown_depth((p[0],top))-.018-.115*math.sin(t*math.pi/2)
visor=applique('Cap | deep soft curved visor',visor_outline,visor_s,sole,.002,.035)
seam('Cap | visor bound edge',[(137,286),(153,311),(184,318),(260,308),(334,300),(402,299),(485,306),(561,320),(596,320),(616,299)],visor_s,capnavy,.007,offset=.003)
seam('Cap | visor fine topstitch',[(140,278),(158,306),(188,313),(261,304),(335,296),(402,295),(485,302),(562,315),(594,315),(616,290)],visor_s,stitch_navy,.001,True,.004)
# Flat ribbons share the crown's exact surface rather than torus-like tubes.
applique('Cap | blue woven band',[(120,247),(193,214),(270,189),(347,175),(413,177),(488,192),(561,216),(633,250),(633,263),(561,230),(488,206),(412,189),(347,188),(272,201),(194,226),(120,260)],cap_s,blue,.004,.002,smooth=False)
applique('Cap | ivory woven band',[(120,258),(194,224),(271,199),(347,186),(413,187),(488,204),(560,228),(633,262),(633,270),(558,237),(486,213),(412,198),(348,197),(273,209),(196,234),(120,267)],cap_s,ivory,.007,.001,smooth=False)
seam('Cap | crown perimeter topstitch',[(145,154),(169,99),(204,63),(254,38),(313,21),(376,14),(450,21),(509,42),(554,72),(588,112)],cap_s,stitch_navy,.001,True,.002)

# Detailed embroidered crest: scalloped shield, laurel, wheel, crown and railway bars.
badge_outline=[(305,103),(312,89),(328,83),(336,70),(350,63),(361,61),(374,67),(384,73),(397,74),(409,89),(414,107),(409,139),(399,160),(382,173),(362,181),(344,175),(326,162),(315,143)]
applique('Cap badge | scalloped gold shield',badge_outline,cap_s,gold,.007,.001,stitch=True)
inner=[(360+(p[0]-360)*.88,122+(p[1]-122)*.90) for p in badge_outline]
applique('Cap badge | cream ground',inner,cap_s,lightgold,.009,.001,stitch=True)
seam('Cap badge | inner shield border',[(322,107),(328,99),(346,94),(370,93),(394,105),(397,131),(386,150),(362,162),(340,153),(326,135),(322,107)],cap_s,gold,.0018,offset=.013)
for r in [18,11]:
    seam('Cap badge | railway wheel',[(360+r*math.cos(i*math.tau/48),124+r*math.sin(i*math.tau/48)) for i in range(49)],cap_s,gold,.002,offset=.014)
disk('Cap badge | wheel hub',(360,124),4,4,cap_s,gold,.015,True)
for side in [-1,1]:
    seam('Cap badge | laurel stem',[(360+side*25,147),(360+side*34,135),(360+side*35,115),(360+side*26,98)],cap_s,gold,.0014,offset=.014)
    for j in range(5):
        x=360+side*(30+4*math.sin(j*.6)); y=104+j*9
        seam('Cap badge | laurel leaf',[(x,y+4),(x+side*7,y),(x+side*3,y-5)],cap_s,gold,.0015,offset=.014)
    for j in range(3):
        seam('Cap badge | lower railway bar',[(360+side*6,149+j*5),(360+side*23,145+j*5)],cap_s,gold,.0013,offset=.014)
applique('Cap badge | crown cross',[(354,85),(363,85),(363,91),(369,91),(369,97),(362,97),(362,103),(355,103),(355,97),(350,97),(350,91),(355,91)],cap_s,gold,.014,.001,smooth=False,stitch=True)
for p in [(323,109),(399,111),(342,165),(377,165)]: disk('Cap badge | seed stitch',p,3,3,cap_s,ivory,.015,True)

# Short real fibres add a cloth silhouette and directional nap at close viewing distance.
def pile(o, count, length, radius):
    import bisect
    mesh=o.data
    mesh.calc_loop_triangles()
    triangles=list(mesh.loop_triangles)
    cumulative=[]; total=0
    for t in triangles:
        total+=t.area; cumulative.append(total)
    paths=[]
    flat=o.name.startswith('Hair |') and 'cap' not in o.name and 'rear' not in o.name
    for _ in range(count):
        tri=triangles[bisect.bisect_left(cumulative,random.random()*total)]
        a,b,c=(mesh.vertices[i] for i in tri.vertices)
        u=math.sqrt(random.random()); v=random.random()
        p=a.co*(1-u)+b.co*(u*(1-v))+c.co*(u*v)
        n=(a.normal*(1-u)+b.normal*(u*(1-v))+c.normal*(u*v)).normalized()
        if flat and n.y>0: n=-n
        tangent=n.cross(Vector((.2,.3,1))).normalized()
        le=length*random.uniform(.55,1.2)
        end=p+n*le+tangent*le*random.uniform(-.35,.35)
        paths.append([p,p+n*le*.55,end])
    return strokes(o.name+' | short fabric pile',paths,o.data.materials[0],radius)
for o in list(model.objects):
    if o.type!='MESH': continue
    if o.name.startswith('Face | broad'): pile(o,35000,.0040,.00038)
    elif o.name.startswith('Hair |'): pile(o,7000,.0030,.00024)
    elif o.name.startswith('Cap | structured'): pile(o,22000,.0028,.00032)
    elif o.name.startswith('Cap | deep'): pile(o,7000,.0022,.00030)
    elif o.name.startswith('Uniform | broad'): pile(o,17000,.0028,.00030)
    elif o.name.startswith('Uniform | relaxed'): pile(o,6000,.0030,.00032)
    elif o.name.startswith('Shoes |'): pile(o,12000,.0028,.00030)
    elif o.name.startswith('Ears |'): pile(o,4000,.0030,.00030)

root=bpy.data.objects.new('HIKARI | 170 mm reference plush',None)
model.objects.link(root)
for o in list(model.objects):
    if o!=root: o.parent=root
root['reference']='https://tsurumai-hobby.jp/images/item/goodsmile/4580828663398.jpg'
root['construction']='Closed stuffed volumes, conforming felt panels, satin-stitch face and crest, woven clothing.'
root['limitation']='Back details are interpreted from the front product photograph; no animation rig.'
import sys
sys.path.insert(0, str(Path(__file__).parent))
from restore_halo import add_halo
add_halo(root)
ref=bpy.data.images.load('/tmp/hikari-reference.jpg',check_existing=True)
ref.name='REFERENCE | original Chocopuni Hikari photograph'; ref.pack(); ref.use_fake_user=True

def aim(o,p): o.rotation_euler=(Vector(p)-o.location).to_track_quat('-Z','Y').to_euler()
world=bpy.data.worlds.new('Neutral product studio')
world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(1,1,1,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.65
scene.world=world
for name,loc,power,size in [('Large front softbox',(-3,-5,5.5),360,5),('Broad fill',(3,-3,4),200,4),('Top softbox',(0,1,6),160,3)]:
    d=bpy.data.lights.new(name,'AREA'); d.energy=power; d.shape='DISK'; d.size=size
    o=bpy.data.objects.new(name,d); stage.objects.link(o); o.location=loc; aim(o,(0,0,1.7))
floor_mat=fabric('Studio | warm white',(.92,.92,.90))
floor=link_mesh('Studio | ground',[(-200,-200,-.025),(200,-200,-.025),(200,200,-.025),(-200,200,-.025)],[(0,1,2,3)],floor_mat,stage)
for name,loc,scale in [('Front comparison',(0,-10,1.70),3.68),('Three quarter',(5,-9,3.2),3.98),('Back inspection',(4,8,3.2),4.0)]:
    d=bpy.data.cameras.new(name); d.type='ORTHO'; d.ortho_scale=scale
    o=bpy.data.objects.new(name,d); stage.objects.link(o); o.location=loc; aim(o,(0,-.04,1.70))
    if name=='Front comparison': scene.camera=o
scene.render.engine='CYCLES'
scene.cycles.samples=64; scene.cycles.use_denoising=True
scene.render.resolution_x=1200; scene.render.resolution_y=1500; scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX'
scene.view_settings.look='AgX - Medium High Contrast'
scene.render.image_settings.file_format='PNG'
scene.render.filepath=str(OUT/'hikari_chocopuni_v2_front.png')
bpy.ops.object.select_all(action='DESELECT')
root.select_set(True); bpy.context.view_layer.objects.active=root
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_perspective='CAMERA'
            area.spaces.active.shading.type='MATERIAL'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'hikari_chocopuni_v2.blend'))
result={'file':bpy.data.filepath,'scene':scene.name,'components':len(model.objects),'render':scene.render.filepath}
