# Real phones, orbiting inside a real bubble.
#
#   blender -b -P tools/blender/phone-orb.py -- --still 1
#   blender -b -P tools/blender/phone-orb.py -- --frames 180
#
# This replaces the earlier billboard approach. That one mapped the source clip
# onto a flat emissive disc at the centre of the sphere, and it read as a photo
# behind glass for exactly the reasons you would expect: an emissive plane
# ignores every light in the scene, casts nothing, receives nothing, and has no
# depth. Nothing was interacting.
#
# Here the phones are geometry. They sit at different distances from the lens,
# they shadow each other, they pick up the bubble's colour, they reflect the
# studio strips and each other, and the far ones go soft because the camera has
# a real aperture. None of that can be faked from a flat frame -- it is the
# whole difference between "in the orb" and "behind the orb".
#
# The loop is exact: everything turns a whole number of times across the frame
# range, so frame N+1 IS frame 1. No crossfade needed.

import sys, os, math, argparse, random
import bpy
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
TAU = math.pi * 2

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument('--name', default='world-phones')
ap.add_argument('--size', type=int, default=512)
ap.add_argument('--frames', type=int, default=180)
ap.add_argument('--samples', type=int, default=128)
ap.add_argument('--count', type=int, default=9)
ap.add_argument('--pscale', type=float, default=1.0)  # phone size
ap.add_argument('--fstop', type=float, default=8.0)   # lower = more depth blur
ap.add_argument('--still', type=int, default=0)
ap.add_argument('--seed', type=int, default=7)
ap.add_argument('--shell', type=int, default=0)   # 1 puts the glass bubble back
ap.add_argument('--cpu', action='store_true')
A = ap.parse_args(argv)

LOOP = A.frames


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
    c.adaptive_threshold = 0.012
    c.max_bounces = 20
    c.transmission_bounces = 12
    c.transparent_max_bounces = 24
    c.glossy_bounces = 8
    c.blur_glossy = 0.6

    r = scene.render
    r.resolution_x = r.resolution_y = A.size
    r.resolution_percentage = 100
    r.film_transparent = True
    r.image_settings.file_format = 'PNG'
    r.image_settings.color_mode = 'RGBA'
    r.image_settings.compression = 20

    # Shutter, for the animation only. Perfectly crisp frames are the giveaway
    # that something was computed rather than filmed -- a real camera smears
    # anything moving across the time the shutter is open. On a still it would
    # only blur the subject for no reason, so it stays off there.
    r.use_motion_blur = (not A.still) and LOOP > 1
    r.motion_blur_shutter = 0.5

    scene.frame_start = 1
    scene.frame_end = LOOP
    scene.view_settings.view_transform = 'Standard'
    return scene, dev


def aim(ob):
    ob.rotation_euler = (Vector((0, 0, 0)) - ob.location).to_track_quat('-Z', 'Y').to_euler()


def camera(scene, lens=85, radius=1.0, fill=0.88):
    cam_d = bpy.data.cameras.new('cam')
    cam_d.lens = lens
    half = math.atan(18.0 / lens)
    dist = radius / math.sin(fill * half)
    cam = bpy.data.objects.new('cam', cam_d)
    scene.collection.objects.link(cam)
    cam.location = (0, -dist, 0)
    scene.camera = cam
    aim(cam)
    # A real aperture, focused on the middle of the swarm. The phones nearest
    # and furthest from the lens go slightly soft, which is the cue that says
    # these things occupy space instead of sitting on one plane.
    cam_d.dof.use_dof = True
    cam_d.dof.focus_distance = dist
    cam_d.dof.aperture_fstop = A.fstop
    return cam


def area(scene, name, loc, size, energy, color=(1, 1, 1), shape='RECTANGLE'):
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
    o.visible_camera = False       # else the light renders as a card over the orb
    return o


def lights(scene):
    area(scene, 'key',   (-3.2, -2.6,  3.4), 8.0, 300, (1.0, 0.97, 0.93))
    area(scene, 'rim',   ( 2.4,  3.6,  2.0), 7.0, 430, (0.95, 0.98, 1.0))
    area(scene, 'under', (-1.4, -1.8, -3.2), 5.0, 150, (1.0, 0.92, 0.98))
    area(scene, 'edge',  ( 3.4, -0.6, -0.4), 5.0, 170, (0.90, 0.95, 1.0), 'DISK')
    # One small hard source. The big soft boxes above give clean gradients but
    # nothing to glint off: polished metal needs a source small enough to make a
    # hot line down a bevel, which is most of what says "polished chrome".
    area(scene, 'spec',  (-1.9, -2.9,  2.2), 0.9, 260, (1.0, 0.99, 0.96), 'DISK')
    # Two big colour cards. Now that the backdrop is out of the reflections the
    # chrome would go pure monochrome, and real chrome almost never does -- it
    # picks up whatever is in the room. These put a lavender and a mint zone
    # into the mirrors, tying the phones to the orb they float against.
    area(scene, 'tintA', (-3.0,  0.4, -1.8), 6.0, 220, (0.78, 0.62, 1.00), 'DISK')
    area(scene, 'tintB', ( 2.6,  0.2,  2.6), 6.0, 200, (0.58, 1.00, 0.86), 'DISK')


def world_gradient(top, bottom, strength):
    w = bpy.data.worlds.new('w')
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputWorld')
    bg = nt.nodes.new('ShaderNodeBackground')
    bg.inputs['Strength'].default_value = strength
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (bottom[0], bottom[1], bottom[2], 1)
    ramp.color_ramp.elements[1].color = (top[0], top[1], top[2], 1)
    ramp.color_ramp.elements[0].position = 0.40
    ramp.color_ramp.elements[1].position = 0.60
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    tex = nt.nodes.new('ShaderNodeTexCoord')
    nt.links.new(tex.outputs['Generated'], sep.inputs['Vector'])
    nt.links.new(sep.outputs['Z'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], bg.inputs['Color'])
    nt.links.new(bg.outputs['Background'], out.inputs['Surface'])


def studio_env(strength=1.0):
    """A graded environment rather than a two-stop wash.

    This is the single biggest lever on how real the metal looks. Chrome has no
    colour of its own -- it is nothing but a picture of its surroundings, so a
    flat grey world renders flat grey phones no matter how good the geometry is.
    Giving the sky a dark floor, a bright band and a cool ceiling puts actual
    structure into every reflection."""
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
    e[0].position, e[0].color = 0.00, (0.07, 0.08, 0.12, 1)     # dark floor
    e[1].position, e[1].color = 1.00, (0.78, 0.85, 1.00, 1)     # cool ceiling
    for pos, col in ((0.34, (0.42, 0.42, 0.50, 1)),
                     (0.58, (1.00, 0.99, 0.97, 1)),             # the bright band
                     (0.72, (0.92, 0.94, 1.00, 1))):
        ramp.color_ramp.elements.new(pos).color = col

    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    tex = nt.nodes.new('ShaderNodeTexCoord')
    nt.links.new(tex.outputs['Generated'], sep.inputs['Vector'])
    nt.links.new(sep.outputs['Z'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], bg.inputs['Color'])
    nt.links.new(bg.outputs['Background'], out.inputs['Surface'])
    return w


def setv(node, key, value):
    if key in node.inputs:
        node.inputs[key].default_value = value
        return True
    return False


def keys(ob, path, frames_values, index=None):
    """Linear keys with the last frame at LOOP+1, so the loop closes exactly."""
    for frame, value in frames_values:
        setattr(ob, path, value)
        ob.keyframe_insert(path, frame=frame)
    if ob.animation_data and ob.animation_data.action:
        for fc in ob.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'
            # Keep the motion going outside the keyed range. Without this the
            # curve holds flat before frame 1, so frame 1's shutter opens on a
            # stationary pre-roll and renders under-blurred -- one crisp frame
            # in an otherwise blurred sequence, which reads as a hitch every
            # time the loop comes round.
            fc.extrapolation = 'LINEAR'


def spin(ob, turns=(0, 0, 1)):
    """Whole turns across the range -- frame LOOP+1 lands back on frame 1."""
    if LOOP < 2:
        return
    keys(ob, 'rotation_euler', [
        (1, (0.0, 0.0, 0.0)),
        (LOOP + 1, (TAU * turns[0], TAU * turns[1], TAU * turns[2])),
    ])


# ------------------------------------------------------------------- material

def chrome():
    m = bpy.data.materials.new('chrome')
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    setv(b, 'Base Color', (0.73, 0.74, 0.76, 1))
    setv(b, 'Metallic', 1.0)
    setv(b, 'Roughness', 0.035)         # mirror. chrome IS its reflection
    
    return m


def glassback():
    m = bpy.data.materials.new('backglass')
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    setv(b, 'Base Color', (0.11, 0.12, 0.15, 1))
    setv(b, 'Metallic', 0.6)
    setv(b, 'Roughness', 0.12)
    setv(b, 'Coat Weight', 1.0)
    setv(b, 'Coat Roughness', 0.02)
    return m


def screen():
    """Dark glass with a faint gradient behind it, like a display at low
    brightness. Emissive only slightly -- a screen that out-glows the bubble
    stops reading as glass."""
    m = bpy.data.materials.new('screen')
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    coord = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (0.06, 0.22, 0.24, 1)
    ramp.color_ramp.elements[1].color = (0.20, 0.13, 0.30, 1)
    nt.links.new(coord.outputs['Object'], sep.inputs['Vector'])
    nt.links.new(sep.outputs['Z'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], b.inputs['Emission Color'])
    setv(b, 'Emission Strength', 0.07)
    setv(b, 'Base Color', (0.012, 0.012, 0.016, 1))
    setv(b, 'Roughness', 0.015)
    setv(b, 'Metallic', 0.0)
    setv(b, 'Coat Weight', 1.0)
    setv(b, 'Coat Roughness', 0.01)
    return m


# ---------------------------------------------------------------------- phone

PH_W, PH_T, PH_L = 0.30 * A.pscale, 0.036 * A.pscale, 0.62 * A.pscale


def smooth(ob, angle=0.6):
    bpy.ops.object.shade_smooth()
    try:                                   # 4.1+ moved auto-smooth to an operator
        bpy.ops.object.shade_auto_smooth(angle=angle)
    except AttributeError:
        pass


def phone(mats, tag):
    """A rounded titanium slab, a display, and a camera plateau. At the size
    these render, the silhouette is doing most of the work -- the bevel catching
    a highlight along its length is what makes it read as a phone."""
    bpy.ops.mesh.primitive_cube_add(size=2)
    body = bpy.context.active_object
    body.name = 'phone_' + tag
    body.scale = (PH_W / 2, PH_T / 2, PH_L / 2)
    bpy.ops.object.transform_apply(scale=True)
    bev = body.modifiers.new('round', 'BEVEL')
    bev.width = 0.021
    bev.segments = 6
    bev.limit_method = 'ANGLE'
    bev.angle_limit = math.radians(30)
    smooth(body)
    body.data.materials.append(mats['ti'])

    # display, a hair proud of the front face so it never z-fights the body
    bpy.ops.mesh.primitive_plane_add(size=1)
    scr = bpy.context.active_object
    scr.name = 'screen_' + tag
    # primitive_plane_add(size=1) already spans +/-0.5, so these are full widths,
    # not half-extents like the cube above.
    scr.scale = (PH_W * 0.87, PH_L * 0.91, 1)
    bpy.ops.object.transform_apply(scale=True)
    scr.rotation_euler = (math.pi / 2, 0, 0)
    scr.location = (0, -(PH_T / 2 + 0.0015), 0)
    scr.data.materials.append(mats['scr'])
    scr.parent = body

    # camera plateau on the back, plus three lenses. Cheap, and it is most of
    # what tells a phone from a blank slab when the back is facing you.
    bpy.ops.mesh.primitive_cube_add(size=2)
    plate = bpy.context.active_object
    plate.name = 'plate_' + tag
    plate.scale = (PH_W * 0.30, 0.008, PH_W * 0.30)
    bpy.ops.object.transform_apply(scale=True)
    plate.location = (-PH_W * 0.20, PH_T / 2 + 0.006, PH_L * 0.30)
    pb = plate.modifiers.new('round', 'BEVEL')
    pb.width = 0.012
    pb.segments = 4
    pb.limit_method = 'ANGLE'
    smooth(plate)
    plate.data.materials.append(mats['back'])
    plate.parent = body

    for i, (dx, dz) in enumerate(((-0.035, 0.035), (0.035, 0.035), (-0.035, -0.035))):
        bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.030, depth=0.016)
        lens = bpy.context.active_object
        lens.name = 'lens%d_%s' % (i, tag)
        lens.rotation_euler = (math.pi / 2, 0, 0)
        lens.location = (-PH_W * 0.20 + dx, PH_T / 2 + 0.012, PH_L * 0.30 + dz)
        smooth(lens)
        lens.data.materials.append(mats['scr'])
        lens.parent = body

    return body


# ------------------------------------------------------------------- interior

def backdrop(radius=0.96):
    """The pastel fill you see through the bubble.

    Transparent on the near side, emissive on the far side, switched by the
    Backfacing output -- so the camera looks straight through the front of this
    sphere, sees its lit far wall behind the phones, and the phones are lit BY
    it. A plain emissive sphere would simply block the view."""
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=5, radius=radius)
    ob = bpy.context.active_object
    ob.name = 'backdrop'
    bpy.ops.object.shade_smooth()

    m = bpy.data.materials.new('backdrop')
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')

    geo = nt.nodes.new('ShaderNodeNewGeometry')
    clear = nt.nodes.new('ShaderNodeBsdfTransparent')
    emit = nt.nodes.new('ShaderNodeEmission')
    emit.inputs['Strength'].default_value = 0.85

    coord = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.interpolation = 'B_SPLINE'
    e = ramp.color_ramp.elements
    e[0].position, e[0].color = 0.18, (0.60, 0.36, 0.98, 1)     # lavender floor
    e[1].position, e[1].color = 0.86, (0.28, 0.96, 0.80, 1)     # mint ceiling
    ramp.color_ramp.elements.new(0.52).color = (0.74, 0.74, 1.00, 1)

    mix = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(coord.outputs['Object'], sep.inputs['Vector'])
    nt.links.new(sep.outputs['Z'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], emit.inputs['Color'])
    nt.links.new(geo.outputs['Backfacing'], mix.inputs['Fac'])
    nt.links.new(clear.outputs['BSDF'], mix.inputs[1])          # front: see through
    nt.links.new(emit.outputs['Emission'], mix.inputs[2])       # back: glowing wall
    nt.links.new(mix.outputs['Shader'], out.inputs['Surface'])
    ob.data.materials.append(m)
    ob.visible_shadow = False
    # Hidden from reflection rays. This is what makes the phones read as chrome
    # rather than as grey plastic: enclosed by an evenly-lit pastel wall, a
    # mirror has nothing to mirror but one flat colour, and chrome with no
    # contrast in it stops looking like metal. Dropping the backdrop out of
    # glossy rays lets them reflect the graded studio instead -- deep darks and
    # hot highlights -- while it still lights them and still backs the orb.
    ob.visible_glossy = False
    return ob


def shell(radius=1.0):
    """Transparent mixed into an iridescent metallic lobe by Fresnel. Metallic,
    not a black dielectric: a black base colour leaves a black diffuse lobe that
    the Fresnel mix fades in around the rim, which renders as a black ring."""
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=6, radius=radius)
    ob = bpy.context.active_object
    ob.name = 'shell'
    bpy.ops.object.shade_smooth()

    m = bpy.data.materials.new('bubble')
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')

    film = nt.nodes.new('ShaderNodeBsdfPrincipled')
    setv(film, 'Base Color', (1, 1, 1, 1))
    setv(film, 'Metallic', 1.0)
    setv(film, 'Roughness', 0.06)
    setv(film, 'IOR', 1.33)
    setv(film, 'Transmission Weight', 0.0)
    setv(film, 'Thin Film IOR', 1.50)

    coord = nt.nodes.new('ShaderNodeTexCoord')
    noise = nt.nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = 3.0
    noise.inputs['Detail'].default_value = 4.0
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    drain = nt.nodes.new('ShaderNodeMapRange')
    drain.inputs['From Min'].default_value = -1.0
    drain.inputs['From Max'].default_value = 1.0
    drain.inputs['To Min'].default_value = 1.0
    drain.inputs['To Max'].default_value = 0.35      # film thins toward the top
    mixf = nt.nodes.new('ShaderNodeMix')
    mixf.data_type = 'FLOAT'
    mixf.inputs['Factor'].default_value = 0.65
    thick = nt.nodes.new('ShaderNodeMapRange')
    thick.inputs['To Min'].default_value = 280.0     # nanometres
    thick.inputs['To Max'].default_value = 680.0

    nt.links.new(coord.outputs['Object'], noise.inputs['Vector'])
    nt.links.new(coord.outputs['Object'], sep.inputs['Vector'])
    nt.links.new(sep.outputs['Z'], drain.inputs['Value'])
    nt.links.new(drain.outputs['Result'], mixf.inputs['A'])
    nt.links.new(noise.outputs['Fac'], mixf.inputs['B'])
    nt.links.new(mixf.outputs['Result'], thick.inputs['Value'])
    nt.links.new(thick.outputs['Result'], film.inputs['Thin Film Thickness'])

    clear = nt.nodes.new('ShaderNodeBsdfTransparent')
    fres = nt.nodes.new('ShaderNodeFresnel')
    fres.inputs['IOR'].default_value = 1.38
    mix = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(fres.outputs['Fac'], mix.inputs['Fac'])
    nt.links.new(clear.outputs['BSDF'], mix.inputs[1])
    nt.links.new(film.outputs['BSDF'], mix.inputs[2])
    nt.links.new(mix.outputs['Shader'], out.inputs['Surface'])
    ob.data.materials.append(m)
    ob.visible_shadow = False
    return ob


# -------------------------------------------------------------------- the set

def swarm(scene, mats):
    """Phones on a slow carousel, each tumbling on its own whole-number cycle so
    the whole arrangement returns to its start exactly on the loop."""
    rng = random.Random(A.seed)

    hub = bpy.data.objects.new('hub', None)
    scene.collection.objects.link(hub)
    spin(hub, turns=(0, 0, 1))            # one revolution per loop

    for i in range(A.count):
        ph = phone(mats, str(i))
        a = TAU * i / A.count + rng.uniform(-0.16, 0.16)
        rad = rng.uniform(0.12, 0.34) if A.count < 6 else rng.uniform(0.38, 0.62)
        ph.location = (math.cos(a) * rad, math.sin(a) * rad,
                       rng.uniform(-0.22, 0.22) if A.count < 6 else rng.uniform(-0.52, 0.52))
        ph.parent = hub

        # tumble: whole turns only, or the loop breaks
        t = (rng.choice([-1, 1]), rng.choice([0, 0, 1]), rng.choice([-1, 1]))
        base = (rng.uniform(0, TAU), rng.uniform(0, TAU), rng.uniform(0, TAU))
        keys(ph, 'rotation_euler', [
            (1, base),
            (LOOP + 1, (base[0] + TAU * t[0], base[1] + TAU * t[1], base[2] + TAU * t[2])),
        ])


# -------------------------------------------------------------------- render

def main():
    scene, dev = configure()
    studio_env(strength=1.05)
    lights(scene)

    mats = {'ti': chrome(), 'back': glassback(), 'scr': screen()}
    # No bubble shell. The orb is a soft matte sphere and nothing else -- all the
    # shine in the frame now belongs to the phones. Dirt's flower orb works the
    # same way: a plain gradient ball with a chrome subject in front of it, no
    # glass anywhere. Keeping a glossy shell here would put highlight sweeps on
    # top of the chrome and flatten the very thing that is meant to read as metal.
    backdrop(radius=1.0)
    swarm(scene, mats)
    if A.shell:
        shell()
    camera(scene, radius=1.0)

    if A.still:
        scene.frame_set(A.still)
        out = os.path.join(ROOT, 'assets', '3d', A.name + '-still.png')
        scene.render.filepath = out
        print('[phone-orb] still frame %d, %d phones, on %s' % (A.still, A.count, dev))
        bpy.ops.render.render(write_still=True)
    else:
        out = os.path.join(ROOT, 'assets', '3d', 'frames', A.name) + os.sep
        scene.render.filepath = out
        print('[phone-orb] %s %dpx x%d, %d phones, on %s -> %s'
              % (A.name, A.size, LOOP, A.count, dev, out))
        bpy.ops.render.render(animation=True)


main()
