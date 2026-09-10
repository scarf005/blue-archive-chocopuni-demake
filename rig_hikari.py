"""Add an FK plush rig to the sewn Hikari model without rebuilding its geometry."""

import bpy

ROOT = 'HIKARI | 170 mm reference plush'
RIG = 'HIKARI | pose rig'


def component_binding(name):
    """Use the existing component labels, including their stitch/pile suffixes."""
    for side in ('L', 'R'):
        for prefix, bone in (
            ('Uniform | relaxed sleeve', 'upper_arm'),
            ('Sleeve insignia', 'upper_arm'),
            ('Sleeve insignia line', 'upper_arm'),
            ('Sleeve cuff blue', 'forearm'),
            ('Sleeve cuff stitch', 'forearm'),
            ('Glove | cloth mitten', 'hand'),
            ('Shoes | stuffed oval sole', 'foot'),
            ('Sole cross seam', 'foot'),
            ('Sole edge topstitch', 'foot'),
            ('Hair | rear loose lock', 'hair_back'),
            ('Hair | curled side panel', 'hair_front'),
            ('Hair | stitched lock edge', 'hair_front'),
            ('Ears | soft pointed fleece', 'ear'),
            ('Ear subtle folded seam', 'ear'),
        ):
            if name.startswith(f'{prefix} {side}'):
                return f'{bone}.{side}'
    if name.startswith('Accessories | loose belt end'):
        return 'belt_tail'
    if name.startswith(('Face |', 'Hair |', 'Cap |', 'Cap badge |', 'Halo |')):
        return 'head'
    if name.startswith(('Uniform |', 'Accessories |')):
        return 'spine'
    raise ValueError(f'Unrecognized model component: {name}')


def add_rig():
    scene = bpy.context.scene
    root = scene.objects.get(ROOT)
    if root is None:
        raise ValueError('Open the sewn Hikari model before adding its rig.')
    if scene.objects.get(RIG):
        raise ValueError('Hikari already has a pose rig; refusing to overwrite it.')
    parts = list(root.children)
    bindings = {o.name: component_binding(o.name) for o in parts}
    if any(o.type not in {'MESH', 'CURVE'} or o.animation_data or o.vertex_groups
           or any(m.type == 'ARMATURE' for m in o.modifiers) for o in parts):
        raise ValueError('Expected unrigged sewn components without animation or weights.')
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    armature = bpy.data.armatures.new(RIG)
    rig = bpy.data.objects.new(RIG, armature)
    root.users_collection[0].objects.link(rig)
    rig.parent = root
    rig.show_in_front = True
    armature.display_type = 'STICK'
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')

    def bone(name, head, tail, parent=None):
        b = armature.edit_bones.new(name)
        b.head, b.tail = head, tail
        if parent:
            b.parent = armature.edit_bones[parent]
            b.use_connect = (b.head - b.parent.tail).length < 1e-6
        return b

    # Model-local coordinates retain the seated silhouette and asymmetric limbs.
    bone('root', (0, 0, 0), (0, 0, .25))
    bone('pelvis', (.035, .08, .45), (.035, .08, .70), 'root')
    bone('spine', (.035, .08, .70), (.035, .08, 1.25), 'pelvis')
    bone('neck', (.035, .08, 1.25), (.005, .02, 1.48), 'spine')
    bone('head', (.005, .02, 1.48), (.005, .02, 2.60), 'neck')
    for side, sign, shoulder, elbow, wrist, hand, hip in (
        ('L', -1, (-.49, .10, 1.25), (-.77, .10, .99),
         (-1.00, .10, .75), (-1.07, .10, .65), (-.40, .04, .67)),
        ('R', 1, (.59, .10, 1.25), (.85, .10, .99),
         (1.03, .10, .75), (1.09, .10, .66), (.57, .04, .69)),
    ):
        bone(f'upper_arm.{side}', shoulder, elbow, 'spine')
        bone(f'forearm.{side}', elbow, wrist, f'upper_arm.{side}')
        bone(f'hand.{side}', wrist, hand, f'forearm.{side}')
        knee = (hip[0], -.18, hip[2] - .15)
        ankle = (hip[0], -.34, .32)
        bone(f'thigh.{side}', hip, knee, 'pelvis')
        bone(f'shin.{side}', knee, ankle, f'thigh.{side}')
        bone(f'foot.{side}', ankle, (hip[0], -.63, .18), f'shin.{side}')
        bone(f'hair_front.{side}', (sign * .79, -.48, 2.17),
             (sign * .69, -.48, 1.02), 'head')
        bone(f'hair_back.{side}', (sign * .82, .16, 1.56),
             (sign * 1.16, .16, .78), 'head')
        bone(f'ear.{side}', (sign * .83, .01, 1.90),
             (sign * 1.12, .01, 1.97), 'head')
    bone('belt_tail', (.46, .14, .66), (1.22, .14, .43), 'spine')
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.update()

    for obj in parts:
        target = bindings[obj.name]
        world = obj.matrix_world.copy()
        if obj.name.startswith('Uniform | relaxed sleeve ') and obj.type == 'MESH':
            side = target[-1]
            upper = armature.bones[target]
            axis = (upper.tail_local - upper.head_local).normalized()
            groups = [obj.vertex_groups.new(name=n) for n in (target, f'forearm.{side}')]
            to_rig = rig.matrix_world.inverted() @ world
            for v in obj.data.vertices:
                distance = (to_rig @ v.co - upper.tail_local).dot(axis)
                t = max(0, min(1, (distance + .12) / .24))
                weight = t * t * (3 - 2 * t)
                for group, value in zip(groups, (1 - weight, weight)):
                    if value > 0:
                        group.add([v.index], value, 'REPLACE')
            modifier = obj.modifiers.new('Hikari sleeve deformation', 'ARMATURE')
            modifier.object = rig
            modifier.use_deform_preserve_volume = True
            obj.modifiers.move(len(obj.modifiers) - 1, 0)
            obj.parent = rig
            obj.matrix_world = world
        else:
            # Bone parenting keeps editable curves, embroidery and modifiers intact.
            obj.parent = rig
            obj.parent_type = 'BONE'
            obj.parent_bone = target
            bpy.context.view_layer.update()
            obj.matrix_world = world
    for pb in rig.pose.bones:
        pb.rotation_mode = 'XYZ'
    rig['usage'] = 'Pose Mode: rotate bones; root moves the whole plush. Clear transforms to reset.'
    rig['sides'] = 'L/R retain the original component labels (front-view image left/right).'
    rig['construction'] = 'FK seated plush: rigid sewn pieces, weighted elbows; no separate fingers.'
    root['limitation'] = root.get('limitation', '').replace('; no animation rig.', '.')
    bpy.context.view_layer.update()
    bpy.ops.object.mode_set(mode='POSE')
    armature.bones.active = armature.bones['spine']
    bpy.ops.pose.select_all(action='DESELECT')
    rig.pose.bones['spine'].select = True
    return rig


if __name__ == '__main__':
    add_rig()
    bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
