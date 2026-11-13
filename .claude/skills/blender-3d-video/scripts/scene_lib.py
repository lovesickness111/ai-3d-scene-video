"""Scene-building kit for headless Blender scripts: primitives with materials,
parented groups, a sample room/desk/programmer/mascot/speech bubble (edit or
replace -- they show the style), camera framing (shot_face), stepped poses
(key_pose), eased camera holds (hold), subtree visibility (toggle), driver sway
and a three-point light rig.

Not runnable directly -- imported by sibling scripts via:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from scene_lib import *
"""
import math
import random

import bpy
from mathutils import Vector


def linear(rgb):
    return tuple(v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in rgb)


def mat(name, rgb, rough=.6, emit=0.0, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes['Principled BSDF']
    color = (*linear(rgb), 1)
    bsdf.inputs['Base Color'].default_value = color
    bsdf.inputs['Roughness'].default_value = rough
    bsdf.inputs['Metallic'].default_value = metal
    if emit:
        bsdf.inputs['Emission Color'].default_value = color
        bsdf.inputs['Emission Strength'].default_value = emit
    return m


def finish(o, m, parent=None, bevel=0.0, smooth=False):
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(m)
    if bevel:
        mod = o.modifiers.new('bevel', 'BEVEL')
        mod.width = bevel
        mod.segments = 3
        smooth = True
    if smooth:
        bpy.ops.object.shade_smooth()
    if parent:
        o.parent = parent
    return o


def box(size, loc, m, parent=None, bevel=0.0, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.scale = size
    return finish(o, m, parent, bevel)


def ball(r, loc, m, parent=None, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=32, ring_count=16)
    o = bpy.context.active_object
    o.scale = scale
    return finish(o, m, parent, smooth=True)


def cyl(r, depth, loc, m, parent=None, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, location=loc, rotation=rot, vertices=32)
    o = bpy.context.active_object
    return finish(o, m, parent, smooth=True)


def limb(a, b, r, m, parent=None):
    a, b = Vector(a), Vector(b)
    d = b-a
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=d.length, location=(a+b)/2, vertices=24)
    o = bpy.context.active_object
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = d.to_track_quat('Z', 'Y')
    finish(o, m, parent, smooth=True)
    ball(r, a, m, parent)
    ball(r, b, m, parent)


def group(name, loc=(0, 0, 0), yaw_deg=0.0, parent=None, scale=1.0):
    e = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(e)
    e.location = loc
    e.rotation_euler = (0, 0, math.radians(yaw_deg))
    e.scale = (scale,)*3
    e.parent = parent
    return e


def room(M):
    bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 0, 0))
    finish(bpy.context.active_object, M['floor'])
    box((10, .1, 4), (0, 1.3, 2), M['wall'])
    box((.1, 10, 4), (-1.6, 0, 2), M['wall'])
    box((10, .1, 4), (0, -5, 2), M['wall'])  # far end: the dev close-up looks down the side wall past the floor's edge
    box((10, .02, .12), (0, 1.24, .06), M['trim'])


def painting(M, loc, yaw, size, art):
    """Framed canvas flat against a wall; local -y faces the room (yaw 0 = back
    wall, 90 = side wall, 180 = far wall). art: (kind, material, u, v, su, sv)
    shapes stacked in order, u/v = centre in -1..1 of the canvas, su/sv = extent
    as a fraction of its width/height; a 'disc' takes su as radius/short side."""
    w, h = size
    g = group('painting', loc, yaw)
    box((w, .03, h), (0, -.015, 0), M['pic_frame'], g, bevel=.004)
    cw, ch = w-.07, h-.07
    box((cw, .004, ch), (0, -.031, 0), M['canvas'], g)
    for i, (kind, m, u, v, su, sv) in enumerate(art):
        pos = (u*cw/2, -.034-i*.002, v*ch/2)
        if kind == 'disc':
            bpy.ops.mesh.primitive_circle_add(radius=su*min(cw, ch), vertices=48, fill_type='NGON',
                                              location=pos, rotation=(math.radians(90), 0, 0))
            finish(bpy.context.active_object, M[m], g)
        else:
            box((su*cw, .002, sv*ch), pos, M[m], g)
    return g


def desk(M):
    box((1.6, .7, .05), (0, 0, .725), M['wood'], bevel=.01)
    for x in (-.75, .75):
        for y in (-.3, .3):
            box((.05, .05, .7), (x, y, .35), M['metal'])
    lap = group('laptop', (-.2, -.05, .75), 8)
    box((.34, .24, .018), (0, 0, .009), M['alu'], lap, bevel=.004)
    box((.3, .1, .002), (0, -.03, .019), M['dark'], lap)
    hinge = group('lid', (0, .12, .018), 0, lap)
    hinge.rotation_euler.x = math.radians(-14)
    box((.34, .012, .23), (0, 0, .115), M['alu'], hinge, bevel=.004)
    box((.31, .002, .2), (0, -.0065, .115), M['screen'], hinge)
    rng = random.Random(7)
    code_colors = [M['code_a'], M['code_b'], M['code_c']]
    for i in range(10):
        w = rng.uniform(.05, .2)
        indent = rng.choice((0, .02, .04))
        box((w, .002, .008), (-.13+indent+w/2, -.009, .2-i*.017), rng.choice(code_colors), hinge)
    mug = group('mug', (.2, .18, .75))
    cyl(.04, .1, (0, 0, .05), M['mug'], mug)
    cyl(.034, .002, (0, 0, .098), M['coffee'], mug)
    bpy.ops.mesh.primitive_torus_add(major_radius=.026, minor_radius=.007, location=(.045, 0, .05),
                                     rotation=(math.radians(90), 0, 0))
    finish(bpy.context.active_object, M['mug'], mug, smooth=True)
    pot = group('plant', (-.65, .18, .75))
    cyl(.06, .11, (0, 0, .055), M['pot'], pot)
    for dx, dy, dz, r in ((0, 0, .17, .07), (.04, .02, .21, .05), (-.04, -.01, .22, .055), (.0, .03, .26, .045)):
        ball(r, (dx, dy, dz), M['leaf'], pot)


def programmer(M, loc, yaw, head_yaw):
    p = group('programmer', loc, yaw, scale=1.0)
    p.rotation_mode = 'XYZ'
    box((.48, .46, .07), (0, .02, .44), M['chair'], p, bevel=.02)
    box((.46, .06, .52), (0, .26, .8), M['chair'], p, bevel=.025, rot=(math.radians(-8), 0, 0))
    cyl(.03, .32, (0, .02, .25), M['metal'], p)
    cyl(.28, .03, (0, .02, .06), M['metal'], p)
    box((.36, .3, .16), (0, .04, .55), M['jeans'], p, bevel=.05)
    for s in (-1, 1):
        limb((s*.1, .02, .56), (s*.11, -.38, .56), .075, M['jeans'], p)
        limb((s*.11, -.4, .54), (s*.115, -.43, .12), .062, M['jeans'], p)
        box((.11, .22, .07), (s*.115, -.48, .045), M['shoe'], p, bevel=.025)
    box((.42, .26, .5), (0, .05, .87), M['hoodie'], p, bevel=.09, rot=(math.radians(-6), 0, 0))
    bpy.ops.mesh.primitive_torus_add(major_radius=.1, minor_radius=.04, location=(0, .05, 1.1))
    finish(bpy.context.active_object, M['hoodie'], p, smooth=True)
    cyl(.05, .12, (0, .03, 1.15), M['skin'], p)

    h = group('head', (0, .03, 1.15), head_yaw, p)
    ball(.13, (0, -.01, .15), M['skin'], h, scale=(1, 1, 1.08))
    ball(.136, (0, .02, .2), M['hair'], h, scale=(1.02, 1, .82))
    ball(.06, (.03, -.09, .245), M['hair'], h, scale=(1.4, .8, .5))
    eyes, brows = [], []
    for s in (-1, 1):
        ball(.03, (s*.13, -.01, .15), M['skin'], h, scale=(.6, 1, 1))
        eyes.append(ball(.016, (s*.046, -.128, .165), M['dark'], h))
        brows.append(box((.036, .012, .007), (s*.047, -.124, .2), M['hair'], h, bevel=.002,
                         rot=(0, math.radians(s*8), 0)))
    ball(.02, (0, -.145, .13), M['skin'], h)
    mouth = ball(.022, (0, -.122, .09), M['mouth'], h, scale=(1.2, .5, .6))

    limb((.22, .04, 1.03), (.25, -.04, .8), .055, M['hoodie'], p)
    limb((.25, -.04, .8), (.15, -.3, .66), .05, M['hoodie'], p)
    ball(.045, (.14, -.35, .65), M['skin'], p)
    limb((-.22, .04, 1.03), (-.28, -.08, .82), .055, M['hoodie'], p)
    limb((-.28, -.08, .82), (-.22, -.32, .98), .05, M['hoodie'], p)
    ball(.045, (-.21, -.36, 1.01), M['skin'], p, scale=(.8, .6, 1.1))
    return p, h, {'mouth': [mouth], 'eyes': eyes, 'brows': brows}


def mascot(M, loc, yaw, scale):
    c = group('mascot', loc, yaw, scale=scale)
    for x in (-.095, -.035, .035, .095):
        box((.035, .045, .05), (x, 0, .025), M['clawd'], c, bevel=.004)
    box((.26, .13, .15), (0, 0, .125), M['clawd'], c, bevel=.01)
    eyes = []
    for s in (-1, 1):
        box((.05, .07, .045), (s*.152, 0, .13), M['clawd'], c, bevel=.006)
        eyes.append(box((.022, .01, .042), (s*.055, -.066, .15), M['dark'], c, bevel=.003))
    mouth = box((.034, .01, .012), (0, -.066, .108), M['dark'], c, bevel=.003)
    return c, {'mouth': [mouth], 'eyes': eyes}


def bubble(M, loc, scale=1.0, parent=None):
    """Returns (root, body): toggle visibility on root, project body for the 2D text box."""
    b = group('bubble', loc, parent=parent, scale=scale)
    body = ball(.12, (0, 0, 0), M['bubble'], b, scale=(1.5, .25, 1))
    bpy.ops.mesh.primitive_cone_add(radius1=.04, depth=.09, location=(-.06, 0, -.12),
                                    rotation=(0, math.radians(200), 0))
    finish(bpy.context.active_object, M['bubble'], b, smooth=True)
    return b, body


def toggle(obj, frame, hidden):
    """hide_render does not cascade to children in Blender -- toggle the
    whole subtree (e.g. a bubble empty + its ball/cone meshes) explicitly."""
    for o in (obj, *obj.children_recursive):
        o.hide_render = hidden
        o.keyframe_insert('hide_render', frame=frame)
        if o.animation_data:
            for fcurve in o.animation_data.action.fcurves:
                if fcurve.data_path == 'hide_render':
                    kp = fcurve.keyframe_points[-1]
                    if kp.co.x == frame:
                        kp.interpolation = 'CONSTANT'


def look_at(obj, target):
    """`obj` must be unparented (camera/lights) -- uses `.location`, which is
    accurate immediately after being set, unlike `.matrix_world` (stale until
    a view-layer update)."""
    direction = Vector(target)-Vector(obj.location)
    obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()


def anchor_world(obj, local_offset=(0, 0, 0)):
    """World position of a point given in `obj`'s local space (handles parenting/rotation)."""
    return obj.matrix_world @ Vector(local_offset)


def shot_face(cam, target_obj, offset=(0, 0, 0), lens=85, dist=.55, side=(1, -1, .35), low=0.0, aside=0.0):
    """Tight framing on a head/face anchor. `side` is the unit-ish direction
    from the target to the camera, in world space (x,y,z weights). `low`
    (0..~0.3) aims slightly above the target so the subject sits lower in
    frame, leaving headroom; `aside` aims to its right (negative: its left)
    so it sits toward the left (right) edge."""
    cam.data.lens = lens
    target = anchor_world(target_obj, offset)
    d = Vector(side).normalized()
    cam.location = target + d*dist
    facing = (target-cam.location).to_track_quat('-Z', 'Y')
    aim = target + facing @ Vector((dist*aside, dist*low, 0))
    # compatible with the previous shot's angles, so a move keyed between the two takes the short way round
    cam.rotation_euler = (aim-cam.location).to_track_quat('-Z', 'Y').to_euler('XYZ', cam.rotation_euler)


def sway(obj, data_path, amplitude, period_frames, phase=0.0, index=-1, offset=0.0):
    """Smooth continuous sine motion via a driver (no keyframe judder, exact every frame)."""
    fcurve = obj.driver_add(data_path, index) if index >= 0 else obj.driver_add(data_path)
    drv = fcurve.driver
    drv.type = 'SCRIPTED'
    var = drv.variables.new()
    var.name = 'frame'
    var.type = 'SINGLE_PROP'
    var.targets[0].id_type = 'SCENE'
    var.targets[0].id = bpy.context.scene
    var.targets[0].data_path = 'frame_current'
    drv.expression = f'{offset}+{amplitude}*sin(frame/{period_frames}*6.28318+{phase})'


def key_pose(obj, frame, scale=(1, 1, 1), lift=0.0, hidden=False):
    """Step `obj` into a pose at `frame` -- scaled, raised by `lift` from where it
    was built, or hidden -- and stay in it until the next key. Key in frame order."""
    if 'rest_z' not in obj:
        obj['rest_z'] = obj.location.z
    obj.scale, obj.location.z, obj.hide_render = scale, obj['rest_z']+lift, hidden
    for path in ('scale', 'location', 'hide_render'):
        obj.keyframe_insert(path, frame=frame)
    for fcurve in obj.animation_data.action.fcurves:
        fcurve.keyframe_points[-1].interpolation = 'CONSTANT'


def hold(obj, frame, interpolation='BEZIER'):
    obj.keyframe_insert('location', frame=frame)
    obj.keyframe_insert('rotation_euler', frame=frame)
    if obj.data and hasattr(obj.data, 'lens'):
        obj.data.keyframe_insert('lens', frame=frame)
    anims = [obj.animation_data, obj.data.animation_data if obj.data else None]
    for anim in anims:
        if anim is None:
            continue
        for fcurve in anim.action.fcurves:
            kp = fcurve.keyframe_points[-1]
            if kp.co.x == frame:
                kp.interpolation = interpolation
                kp.easing = 'EASE_IN_OUT'


def lights(scene):
    def area(name, loc, energy, size, color, target):
        data = bpy.data.lights.new(name, 'AREA')
        data.energy, data.size, data.color = energy, size, color
        o = bpy.data.objects.new(name, data)
        scene.collection.objects.link(o)
        o.location = loc
        o.visible_camera = False  # wide corner shots can catch lights directly otherwise
        direction = Vector(target)-Vector(loc)
        o.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    area('key', (2.2, -1.6, 2.8), 650, 2.0, (1, .95, .88), (.2, -.5, .9))
    # kept clear of the side wall: a panel that pokes through it draws a hard light edge across the wall
    area('fill', (-.3, -2.6, 1.8), 180, 2.0, (.75, .85, 1), (.2, -.5, .9))
    area('rim', (-.4, 1.0, 2.2), 260, 1.0, (1, .8, .6), (.2, -.6, 1.1))
    lamp = bpy.data.lights.new('desk_glow', 'POINT')
    lamp.energy, lamp.color, lamp.shadow_soft_size = 25, (1, .7, .45), .2
    o = bpy.data.objects.new('desk_glow', lamp)
    scene.collection.objects.link(o)
    o.location = (.45, .1, 1.05)
    world = bpy.data.worlds.new('world')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (*linear((.12, .13, .16)), 1)
    scene.world = world


MATERIALS = {
    'floor': ((.52, .45, .38), .7), 'wall': ((.2, .37, .4), .9),
    'trim': ((.9, .88, .84), .5), 'wood': ((.62, .45, .3), .45),
    'metal': ((.2, .2, .22), .35, 0, .8), 'alu': ((.72, .73, .75), .3, 0, .9),
    'dark': ((.03, .03, .035), .4), 'screen': ((.08, .12, .2), .2, 1.5),
    'code_a': ((.45, .75, 1), .6, 4), 'code_b': ((.95, .6, .45), .6, 4),
    'code_c': ((.6, .9, .55), .6, 4), 'mug': ((.93, .92, .9), .25),
    'coffee': ((.18, .09, .04), .1), 'pot': ((.72, .42, .3), .7),
    'leaf': ((.25, .5, .25), .6), 'chair': ((.16, .17, .2), .6),
    'jeans': ((.17, .25, .42), .8), 'shoe': ((.92, .92, .9), .5),
    'hoodie': ((.72, .77, .87), .5), 'string': ((.9, .9, .88), .6),
    'skin': ((.89, .7, .56), .55), 'hair': ((.12, .08, .06), .7),
    'frame': ((.06, .06, .07), .3), 'mouth': ((.45, .18, .16), .5),
    'clawd': ((.84, .38, .2), .55), 'bubble': ((.97, .96, .93), .4),
    'pic_frame': ((.8, .63, .42), .5), 'canvas': ((.93, .89, .8), .8),
    'art_terra': ((.8, .36, .22), .8), 'art_mustard': ((.88, .66, .22), .8),
    'art_sage': ((.52, .63, .5), .8), 'art_navy': ((.13, .2, .36), .8),
}


def build_materials():
    out = {}
    for name, spec in MATERIALS.items():
        rgb, rough = spec[0], spec[1]
        emit = spec[2] if len(spec) > 2 else 0.0
        metal = spec[3] if len(spec) > 3 else 0.0
        out[name] = mat(name, rgb, rough, emit, metal)
    return out
