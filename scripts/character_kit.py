"""Shared bpy primitive helpers for stylized low-poly character scenes.

Imported by scene scripts (e.g. demo_programmer_mascot.py, demo_head_knock.py);
never run directly.
"""
import math

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


def room(M, size=10, wall_height=4):
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, 0))
    finish(bpy.context.active_object, M['floor'])
    box((size, .1, wall_height), (0, size*.13, wall_height/2), M['wall'])
    box((.1, size, wall_height), (-size*.16, 0, wall_height/2), M['wall'])
    if 'trim' in M:
        box((size, .02, .12), (0, size*.124, .06), M['trim'])


def look_at(obj, target):
    direction = Vector(target)-obj.location
    obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()


def lights(scene, bg_color=(.12, .13, .16)):
    def area(name, loc, energy, size, color, target):
        data = bpy.data.lights.new(name, 'AREA')
        data.energy, data.size, data.color = energy, size, color
        o = bpy.data.objects.new(name, data)
        scene.collection.objects.link(o)
        o.location = loc
        look_at(o, target)
    area('key', (2.2, -1.6, 2.8), 650, 2.0, (1, .95, .88), (.2, -.5, .9))
    area('fill', (-1.0, -2.6, 1.8), 180, 3.0, (.75, .85, 1), (.2, -.5, .9))
    area('rim', (-.4, 1.0, 2.2), 260, 1.0, (1, .8, .6), (.2, -.6, 1.1))
    world = bpy.data.worlds.new('world')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (*linear(bg_color), 1)
    scene.world = world
