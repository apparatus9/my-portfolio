# A wordmark suspended in a glass ball.
#
#   blender -b -P tools/blender/word-orb.py -- --word Ejay --still 1
#   blender -b -P tools/blender/word-orb.py -- --word Ejay --frames 180
#
# Built from nothing but text objects and a glass sphere, so it is yours: the
# idea of a logo repeated inside a marble is common property, the artwork is not.
#
# The refraction is the whole point and it has to be real. Rows of text sit at
# different depths inside a solid glass sphere, so the ones near the back get
# bent and magnified by the thickness of glass in front of them while the middle
# rows stay legible. Painting that distortion on a flat card is exactly what it
# looks like -- painted.

import sys, os, math, argparse, random
import bpy
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
TAU = math.pi * 2

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument('--word', default='Ejay')
ap.add_argument('--name', default='world-word')
ap.add_argument('--size', type=int, default=512)
ap.add_argument('--frames', type=int, default=0)
ap.add_argument('--samples', type=int, default=200)
ap.add_argument('--rows', type=int, default=3)
ap.add_argument('--depth', type=float, default=0.80)    # how deep the stack runs
ap.add_argument('--hue', default='acid')                # acid | violet | ember | ink
ap.add_argument('--ior', type=float, default=1.52)
ap.add_argument('--still', type=int, default=0)
ap.add_argument('--cpu', action='store_true')
A = ap.parse_args(argv)

LOOP = A.frames or 1

# ink is the word, field is the ball behind it
PALETTE = {
    'acid':   ((0.82, 0.96, 0.03), (0.42, 0.60, 0.01)),
    'violet': ((0.72, 0.42, 1.00), (0.16, 0.06, 0.30)),
    'ember':  ((1.00, 0.42, 0.14), (0.28, 0.05, 0.06)),
    'ink':    ((0.90, 0.94, 1.00), (0.02, 0.03, 0.07)),
}


# ---------------------------------------------------------------- scene setup

def gpu(scene):
    if A.cpu:
        scene.cycles.device = 'CPU'
        return 'CPU'
    prefs = bpy.context.preferences.addons['cycles'].preferences
    for kind in ('OPTIX', 'CUDA'):
        try:
            prefs.compute_device_type = kind
        except TypeError:
            continue
        prefs.get_devices()
        hits = [d for d in prefs.devices if d.type == kind]
        if not hits:
            continue
        for d in prefs.devices:
            d.use = (d.type == kind)
        scene.cycles.device = 'GPU'
        return kind + ': ' + ', '.join(d.name for d in hits)
    scene.cycles.device = 'CPU'
    return 'CPU (no GPU found)'


def configure():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    dev = gpu(scene)

    c = scene.cycles
    c.samples = A.samples
    c.use_denoising = True
    c.denoiser = 'OPENIMAGEDENOISE'
    c.use_adaptive_sampling = True
    c.adaptive_threshold = 0.01
    # Glass is transmission bounces and nothing else. The default budget turns
    # the far side of a solid sphere into black mush.
    c.max_bounces = 32
    c.transmission_bounces = 24
    c.transparent_max_bounces = 32
    c.glossy_bounces = 8
    c.blur_glossy = 0.4
    c.caustics_refractive = True

    r = scene.render
    r.resolution_x = r.resolution_y = A.size
    r.resolution_percentage = 100
    r.film_transparent = True
    r.image_settings.file_format = 'PNG'
    r.image_settings.color_mode = 'RGBA'
    r.image_settings.compression = 20
    r.use_motion_blur = False

    scene.frame_start = 1
    scene.frame_end = LOOP
    scene.view_settings.view_transform = 'Standard'
    return scene, dev


def aim(ob):
    ob.rotation_euler = (Vector((0, 0, 0)) - ob.location).to_track_quat('-Z', 'Y').to_euler()


def camera(scene, lens=85, radius=1.0, fill=0.90):
    cam_d = bpy.data.cameras.new('cam')
    cam_d.lens = lens
    half = math.atan(18.0 / lens)
    cam = bpy.data.objects.new('cam', cam_d)
    scene.collection.objects.link(cam)
    cam.location = (0, -radius / math.sin(fill * half), 0)
    scene.camera = cam
    aim(cam)
    return cam


def setv(node, key, value):
    if key in node.inputs:
        node.inputs[key].default_value = value
        return True
    return False


def area(scene, name, loc, size, energy, color, shape='RECTANGLE'):
    d = bpy.data.lights.new(name, 'AREA')
    d.shape = shape
    d.size = size
    if shape == 'RECTANGLE':
        d.size_y = size * 0.16
    d.energy = energy
    d.color = color
    o = bpy.data.objects.new(name, d)
    scene.collection.objects.link(o)
    o.location = loc
    aim(o)
    o.visible_camera = False
    return o


def lights(scene):
    """Strip sources. A glass ball shows a light's actual shape twice -- once in
    the surface highlight and again bent through the far wall."""
    area(scene, 'key',  (-3.2, -2.0,  4.6), 5.0, 400, (1.00, 0.98, 0.94))
    area(scene, 'rim',  ( 2.4,  3.0,  1.8), 5.0, 560, (0.94, 0.97, 1.00))
    area(scene, 'fill', ( 3.4, -1.2, -3.0), 5.0, 170, (0.92, 0.95, 1.00))
    # small and high: a glint near the shoulder of the ball, not a bar
    # laid across the middle of the word
    area(scene, 'spec', (-2.0, -2.6,  3.2), 0.55, 200, (1.00, 1.00, 1.00), 'DISK')


def studio_env(strength=1.0):
    """Something with range for the glass to bend. A flat grey world refracts to
    flat grey and the ball reads as a plastic bead."""
    w = bpy.data.worlds.new('w')
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputWorld')
    bg = nt.nodes.new('ShaderNodeBackground')
    bg.inputs['Strength'].default_value = strength
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.interpolation = 'B_SPLINE'
    e = ramp.color_ramp.elements
    e[0].position, e[0].color = 0.00, (0.03, 0.03, 0.06, 1)
    e[1].position, e[1].color = 1.00, (0.80, 0.86, 1.00, 1)
    for pos, col in ((0.40, (0.22, 0.24, 0.34, 1)),
                     (0.62, (1.00, 1.00, 1.00, 1))):
        ramp.color_ramp.elements.new(pos).color = col
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    tex = nt.nodes.new('ShaderNodeTexCoord')
    nt.links.new(tex.outputs['Generated'], sep.inputs['Vector'])
    nt.links.new(sep.outputs['Z'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], bg.inputs['Color'])
    nt.links.new(bg.outputs['Background'], out.inputs['Surface'])


# ------------------------------------------------------------------- the ball

def field(radius=0.995):
    """The coloured ball the words sit in. Transparent to the camera on the near
    side, emissive on the far side, so it lights the words from behind and reads
    as a solid colour rather than blocking the view."""
    ink, deep = PALETTE.get(A.hue, PALETTE['acid'])
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=5, radius=radius)
    ob = bpy.context.active_object
    ob.name = 'field'
    bpy.ops.object.shade_smooth()

    m = bpy.data.materials.new('field')
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    geo = nt.nodes.new('ShaderNodeNewGeometry')
    clear = nt.nodes.new('ShaderNodeBsdfTransparent')
    emit = nt.nodes.new('ShaderNodeEmission')
    emit.inputs['Strength'].default_value = 1.0

    coord = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.interpolation = 'B_SPLINE'
    e = ramp.color_ramp.elements
    e[0].position, e[0].color = 0.10, (deep[0], deep[1], deep[2], 1)
    e[1].position, e[1].color = 0.92, (ink[0], ink[1], ink[2], 1)
    nt.links.new(coord.outputs['Object'], sep.inputs['Vector'])
    nt.links.new(sep.outputs['Z'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], emit.inputs['Color'])

    mix = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(geo.outputs['Backfacing'], mix.inputs['Fac'])
    nt.links.new(clear.outputs['BSDF'], mix.inputs[1])
    nt.links.new(emit.outputs['Emission'], mix.inputs[2])
    nt.links.new(mix.outputs['Shader'], out.inputs['Surface'])
    ob.data.materials.append(m)
    ob.visible_shadow = False
    ob.visible_glossy = False
    return ob


def glass(radius=1.0):
    """A solid glass marble. Solid, not a shell: the words have to be refracted
    by a thickness of glass, and a thin bubble bends almost nothing."""
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=6, radius=radius)
    ob = bpy.context.active_object
    ob.name = 'glass'
    bpy.ops.object.shade_smooth()
    m = bpy.data.materials.new('glass')
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    setv(b, 'Base Color', (1, 1, 1, 1))
    setv(b, 'Roughness', 0.0)
    setv(b, 'Metallic', 0.0)
    setv(b, 'IOR', A.ior)
    setv(b, 'Transmission Weight', 1.0)
    setv(b, 'Transmission', 1.0)
    ob.data.materials.append(m)
    return ob


# ------------------------------------------------------------------ the words

def wordmark(scene, hub):
    """Rows of the word stacked through the depth of the ball.

    Each row is its own object so it can sit at its own distance from the lens.
    That spread is what the glass acts on -- rows at the back arrive bent and
    swollen, rows at the middle stay readable, and the difference between them
    is the depth cue."""
    ink, _ = PALETTE.get(A.hue, PALETTE['acid'])
    m = bpy.data.materials.new('ink')
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    setv(b, 'Base Color', (ink[0] * 0.22, ink[1] * 0.30, ink[2] * 0.05, 1))
    setv(b, 'Roughness', 0.42)
    setv(b, 'Emission Strength', 0.0)   # contrast comes from the field behind

    rows = []
    for i in range(A.rows):
        t = (i / max(1, A.rows - 1)) - 0.5              # -0.5 .. 0.5
        bpy.ops.object.text_add()
        ob = bpy.context.active_object
        ob.name = 'word%d' % i
        ob.data.body = A.word
        ob.data.align_x = 'CENTER'
        ob.data.align_y = 'CENTER'
        ob.data.extrude = 0.012
        ob.data.size = 0.58
        # stand it up to face the lens, then place it down the depth axis
        ob.rotation_euler = (math.pi / 2, 0, 0)
        # Spread down the face with room to breathe. Rows closer together than
        # the type is tall just overlap into mush -- the spacing has to clear
        # the cap height. A small alternating nudge sideways stops the stack
        # reading as one rigid column.
        stagger = 0.05 if i % 2 else -0.05
        ob.location = (stagger, t * A.depth * 0.95, -t * 1.05)
        ob.data.materials.append(m)
        ob.parent = hub
        rows.append(ob)
    return rows


def keys(ob, path, samples, interp='BEZIER'):
    for frame, value in samples:
        setattr(ob, path, value)
        ob.keyframe_insert(path, frame=frame)
    for fc in ob.animation_data.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = interp
        fc.extrapolation = 'LINEAR'


# -------------------------------------------------------------------- render

def main():
    scene, dev = configure()
    studio_env()
    lights(scene)
    field()

    hub = bpy.data.objects.new('hub', None)
    scene.collection.objects.link(hub)
    wordmark(scene, hub)
    glass()
    camera(scene, radius=1.0)

    if LOOP > 1:
        STEPS = 24
        # A full sine of yaw: the stack turns into the glass and back, so the
        # refraction swells and settles. Returns in position and velocity, so
        # the loop closes without a snap.
        keys(hub, 'rotation_euler',
             [(1 + LOOP * i / STEPS,
               (0.0, 0.0, 0.42 * math.sin(TAU * i / STEPS)))
              for i in range(STEPS + 1)])
        keys(hub, 'location',
             [(1 + LOOP * i / STEPS,
               (0.0, 0.0, 0.05 * math.sin(TAU * i / STEPS + 1.4)))
              for i in range(STEPS + 1)])

    if A.still:
        scene.frame_set(A.still)
        out = os.path.join(ROOT, 'assets', '3d', A.name + '-still.png')
        scene.render.filepath = out
        print('[word-orb] "%s" frame %d, %d rows, %s, on %s'
              % (A.word, A.still, A.rows, A.hue, dev))
        bpy.ops.render.render(write_still=True)
    elif LOOP > 1:
        out = os.path.join(ROOT, 'assets', '3d', 'frames', A.name) + os.sep
        scene.render.filepath = out
        print('[word-orb] "%s" %dpx x%d, %s, on %s' % (A.word, A.size, LOOP, A.hue, dev))
        bpy.ops.render.render(animation=True)
    else:
        out = os.path.join(ROOT, 'assets', '3d', A.name + '-still.png')
        scene.render.filepath = out
        print('[word-orb] "%s" still, %s, on %s' % (A.word, A.hue, dev))
        bpy.ops.render.render(write_still=True)


main()
