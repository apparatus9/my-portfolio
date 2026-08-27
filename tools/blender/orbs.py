# Cycles orb rig. Renders one orb, alpha-cut, square, ready for the ring.
#
#   blender -b -P tools/blender/orbs.py -- --orb glass  --look clear
#   blender -b -P tools/blender/orbs.py -- --orb liquid --look refract --frames 180
#
# Why Blender and not the three.js rig: glass and liquid are the two orbs that
# need real refraction. A rasterised fake gives you a rim highlight and a lie in
# the middle. Cycles traces the back of the sphere through the front of it,
# which is the entire look.
#
# Frames land in assets/3d/frames/<name>/####.png so the existing
# frames -> webm step keeps working unchanged.

import sys, os, math, argparse
import bpy
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument('--orb', required=True)
ap.add_argument('--look', default=None)           # variant; default is the first
ap.add_argument('--name', default=None)           # output stem
ap.add_argument('--size', type=int, default=512)
ap.add_argument('--frames', type=int, default=0)  # 0 = single still
ap.add_argument('--samples', type=int, default=256)
ap.add_argument('--cpu', action='store_true')
A = ap.parse_args(argv)

LOOP = A.frames or 1


# ---------------------------------------------------------------- scene setup

def gpu(scene):
    """OptiX if the box has it, else CUDA, else CPU. Blackwell wants OptiX."""
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
    # Even under --factory-startup the default scene ships a 2m cube at the
    # origin, which lands inside the orb. Start genuinely empty.
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
    # Glass is all transmission bounces. The default budget turns the far side
    # of the sphere into black mush.
    c.max_bounces = 32
    c.transmission_bounces = 24
    c.transparent_max_bounces = 32
    c.glossy_bounces = 8
    c.blur_glossy = 0.5           # keeps fireflies off the caustic highlights
    c.caustics_refractive = True
    c.caustics_reflective = True

    r = scene.render
    r.resolution_x = r.resolution_y = A.size
    r.resolution_percentage = 100
    r.film_transparent = True     # the ring sits on paper white, not on a plate
    r.image_settings.file_format = 'PNG'
    r.image_settings.color_mode = 'RGBA'
    r.image_settings.compression = 20

    scene.frame_start = 1
    scene.frame_end = LOOP

    # AgX desaturates hard -- on saturated orbs against paper white it turns
    # every colour to pastel chalk. Standard keeps the pigment; the lighting
    # below is dialled so nothing clips.
    scene.view_settings.view_transform = 'Standard'
    return scene, dev


def camera(scene, lens=85, radius=1.0, fill=0.86):
    """Pull back to exactly the distance that makes a sphere of `radius` cover
    `fill` of the frame, rather than guessing a distance and eyeballing it.
    Square render, so the 36mm sensor spans the frame in both axes."""
    cam_d = bpy.data.cameras.new('cam')
    cam_d.lens = lens
    half = math.atan(18.0 / lens)                 # frame half-angle
    dist = radius / math.sin(fill * half)         # sphere subtends fill*half
    cam = bpy.data.objects.new('cam', cam_d)
    scene.collection.objects.link(cam)
    cam.location = (0, -dist, 0)
    scene.camera = cam
    aim(cam)
    return cam


def aim(ob):
    """Point -Z at the origin."""
    ob.rotation_euler = (Vector((0, 0, 0)) - ob.location).to_track_quat('-Z', 'Y').to_euler()


def area(scene, name, loc, size, energy, color=(1, 1, 1), shape='DISK'):
    d = bpy.data.lights.new(name, 'AREA')
    d.shape = shape
    d.size = size
    if shape == 'RECTANGLE':
        d.size_y = size * 0.18
    d.energy = energy
    d.color = color
    o = bpy.data.objects.new(name, d)
    scene.collection.objects.link(o)
    o.location = loc
    aim(o)
    # Cycles area lights are camera-visible by default. These are metres wide
    # and sit between the lens and the orb, so left on they render as an opaque
    # card over the whole frame. They still light, reflect and refract.
    o.visible_camera = False
    return o


def studio(scene, warm=(1.0, 0.96, 0.92), cool=(0.86, 0.92, 1.0), power=1.0):
    """Two big soft sources plus a rim, so it reads as a photographed object.
    The strips are long and thin on purpose: a glass sphere reflects a light's
    actual shape, and a bar of highlight looks like studio glass where a round
    blob looks like clip art."""
    area(scene, 'key',  (-3.4, -3.0,  3.6), 6.0, 700 * power, warm, 'RECTANGLE')
    area(scene, 'fill', ( 4.2, -2.2, -0.8), 9.0, 180 * power, cool)
    area(scene, 'rim',  ( 1.6,  4.4,  2.2), 4.0, 900 * power, (1, 1, 1), 'RECTANGLE')


def world_gradient(top, bottom, strength=1.0):
    """Glass refracts whatever is out there. film_transparent hides this from
    the camera but keeps it in refraction and reflection rays -- an empty world
    would render a black marble, and a flat mid-grey one renders milky mush.
    The top/bottom split is what puts a horizon in the refraction."""
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
    ramp.color_ramp.elements[0].position = 0.42   # a hard-ish horizon, not a wash
    ramp.color_ramp.elements[1].position = 0.58
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    tex = nt.nodes.new('ShaderNodeTexCoord')
    nt.links.new(tex.outputs['Generated'], sep.inputs['Vector'])
    nt.links.new(sep.outputs['Z'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], bg.inputs['Color'])
    nt.links.new(bg.outputs['Background'], out.inputs['Surface'])
    return w


# ---------------------------------------------------------------- node helper

def setv(node, key, value):
    """Principled input names moved around across 4.x. Miss quietly rather than
    dying three minutes into a render."""
    if key in node.inputs:
        node.inputs[key].default_value = value
        return True
    return False


def ico(name, radius=1.0, subdiv=6):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdiv, radius=radius)
    ob = bpy.context.active_object
    ob.name = name
    bpy.ops.object.shade_smooth()
    return ob


def spin(ob, turns=1.0, axis='Z'):
    """One clean revolution across the loop -- constant speed, seamless."""
    if LOOP < 2:
        return
    i = 'XYZ'.index(axis)
    for frame, angle in ((1, 0.0), (LOOP + 1, 2 * math.pi * turns)):
        e = [0.0, 0.0, 0.0]
        e[i] = angle
        ob.rotation_euler = e
        ob.keyframe_insert('rotation_euler', frame=frame)
    for fc in ob.animation_data.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'


def swirl_ramp(nt, stops):
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.interpolation = 'B_SPLINE'
    e = ramp.color_ramp.elements
    e[0].position, e[0].color = stops[0][0], stops[0][1]
    e[1].position, e[1].color = stops[-1][0], stops[-1][1]
    for pos, col in stops[1:-1]:
        ramp.color_ramp.elements.new(pos).color = col
    return ramp


def marble(nt, stops, scale=1.6, distortion=18.0, wave='BANDS'):
    """Noise-warped wave bands -- the standard way to get a marbled swirl that
    reads as depth rather than as a printed pattern."""
    coord = nt.nodes.new('ShaderNodeTexCoord')
    noise = nt.nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = scale
    noise.inputs['Detail'].default_value = 6.0
    noise.inputs['Roughness'].default_value = 0.55
    w = nt.nodes.new('ShaderNodeTexWave')
    w.wave_type = wave
    if wave == 'RINGS':
        w.rings_direction = 'SPHERICAL'
    else:
        w.bands_direction = 'Z'
    w.inputs['Scale'].default_value = scale
    w.inputs['Distortion'].default_value = distortion
    w.inputs['Detail'].default_value = 4.0
    ramp = swirl_ramp(nt, stops)
    nt.links.new(coord.outputs['Object'], noise.inputs['Vector'])
    nt.links.new(noise.outputs['Fac'], w.inputs['Vector'])
    nt.links.new(w.outputs['Fac'], ramp.inputs['Fac'])
    return ramp


def absorb(mat, color, density):
    """Volume absorption inside a closed mesh: colour that deepens with the
    thickness of glass the ray crosses. This is what a tinted marble does that
    a coloured surface cannot -- thin edges stay pale, the middle goes rich."""
    nt = mat.node_tree
    vol = nt.nodes.new('ShaderNodeVolumeAbsorption')
    vol.inputs['Color'].default_value = (color[0], color[1], color[2], 1)
    vol.inputs['Density'].default_value = density
    out = [n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'][0]
    nt.links.new(vol.outputs['Volume'], out.inputs['Volume'])


def glass_shell(name='shell', radius=1.0, roughness=0.0, ior=1.5):
    shell = ico(name, radius, 6)
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes['Principled BSDF']
    setv(bsdf, 'Base Color', (1, 1, 1, 1))
    setv(bsdf, 'Roughness', roughness)
    setv(bsdf, 'Metallic', 0.0)
    setv(bsdf, 'IOR', ior)
    setv(bsdf, 'Transmission Weight', 1.0)
    setv(bsdf, 'Transmission', 1.0)            # pre-4.0 name
    shell.data.materials.append(m)
    return shell, m


# ---------------------------------------------------------------- orb: glass

GLASS_CORE = [
    (0.15, (0.02, 0.06, 0.60, 1)),
    (0.40, (0.05, 0.65, 0.95, 1)),
    (0.62, (0.98, 0.20, 0.45, 1)),
]


def orb_glass(scene, look):
    """A thick glass marble. Something has to sit inside it: with nothing to
    refract, a clear sphere is only a rim light on white paper."""
    world_gradient(top=(1.0, 1.0, 1.0), bottom=(0.10, 0.13, 0.22), strength=1.6)
    studio(scene)

    if look == 'tinted':
        # No core at all -- the colour is the glass itself, deepening toward
        # the middle where the ray path is longest.
        shell, m = glass_shell(roughness=0.0)
        absorb(m, (0.10, 0.45, 0.95), 1.9)
        return

    if look == 'frosted':
        shell, m = glass_shell(roughness=0.22, ior=1.46)
        absorb(m, (0.55, 0.30, 0.95), 0.9)
    else:                                       # 'clear'
        shell, m = glass_shell(roughness=0.0)
        absorb(m, (0.35, 0.55, 0.95), 0.45)

    # Small and dense: the more glass between the core and the eye, the more
    # the sphere reads as a solid object rather than a shell.
    core = ico('core', 0.38, 5)
    cm = bpy.data.materials.new('core')
    cm.use_nodes = True
    bsdf = cm.node_tree.nodes['Principled BSDF']
    ramp = marble(cm.node_tree, GLASS_CORE, scale=2.4, distortion=14.0, wave='RINGS')
    cm.node_tree.links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
    setv(bsdf, 'Roughness', 0.18)
    setv(bsdf, 'Metallic', 0.55)
    core.data.materials.append(cm)
    spin(core, 1.0, 'Z')


# --------------------------------------------------------------- orb: liquid

LIQUID_MARBLE = [
    (0.10, (0.02, 0.04, 0.35, 1)),
    (0.34, (0.05, 0.40, 0.95, 1)),
    (0.60, (0.98, 0.15, 0.40, 1)),
    (0.90, (1.00, 0.80, 0.35, 1)),
]


def liquid_body(scale=1.5, strength=0.22, depth=2):
    """A displaced sphere that keeps a liquid's fat, rounded lobes. Subdivide
    first, then displace: displacing a coarse cage and smoothing afterwards is
    what gave the first pass its asteroid crinkle."""
    ob = ico('liquid', 1.0, 6)

    sub = ob.modifiers.new('dense', 'SUBSURF')
    sub.levels = sub.render_levels = 2

    tex = bpy.data.textures.new('wobble', 'CLOUDS')
    tex.noise_scale = scale          # big scale = few fat lobes, not gravel
    tex.noise_depth = depth
    d = ob.modifiers.new('displace', 'DISPLACE')
    d.texture = tex
    d.strength = strength
    d.mid_level = 0.5
    d.texture_coords = 'OBJECT'

    # Spin an empty the modifier reads its coordinates from: the mesh stays put,
    # the wobble travels through it, and one full turn is a seamless loop.
    drv = bpy.data.objects.new('wobble_field', None)
    bpy.context.scene.collection.objects.link(drv)
    d.texture_coords_object = drv
    spin(drv, 1.0, 'Z')

    sm = ob.modifiers.new('relax', 'SMOOTH')
    sm.factor = 0.5
    sm.iterations = 4
    return ob


def orb_liquid(scene, look):
    """A blob of heavy liquid mid-wobble. The silhouette moves, which is the
    whole point -- the canvas version could only ever be a perfect circle."""
    world_gradient(top=(1.0, 1.0, 1.0), bottom=(0.12, 0.14, 0.24), strength=1.5)

    if look == 'chrome':
        studio(scene, power=1.15)
        ob = liquid_body(scale=1.3, strength=0.26)
        m = bpy.data.materials.new('liquid')
        m.use_nodes = True
        nt = m.node_tree
        bsdf = nt.nodes['Principled BSDF']
        ramp = marble(nt, [
            (0.15, (0.35, 0.38, 0.55, 1)),
            (0.50, (0.95, 0.75, 0.55, 1)),
            (0.85, (0.60, 0.85, 1.00, 1)),
        ], scale=1.4, distortion=14.0)
        nt.links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
        setv(bsdf, 'Metallic', 1.0)
        setv(bsdf, 'Roughness', 0.08)
        ob.data.materials.append(m)
        return

    if look == 'refract':
        # Actual liquid: light goes through it and picks up colour by depth.
        studio(scene, power=1.1)
        ob = liquid_body(scale=1.5, strength=0.22)
        m = bpy.data.materials.new('liquid')
        m.use_nodes = True
        bsdf = m.node_tree.nodes['Principled BSDF']
        setv(bsdf, 'Base Color', (1, 1, 1, 1))
        setv(bsdf, 'Roughness', 0.04)
        setv(bsdf, 'IOR', 1.38)
        setv(bsdf, 'Transmission Weight', 1.0)
        setv(bsdf, 'Transmission', 1.0)
        ob.data.materials.append(m)
        absorb(m, (0.15, 0.35, 0.95), 1.5)
        return

    # 'marble' -- opaque, wet, swirled. Closest to the orb this replaces.
    studio(scene, warm=(1.0, 0.94, 0.86))
    ob = liquid_body(scale=1.5, strength=0.22)
    m = bpy.data.materials.new('liquid')
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes['Principled BSDF']
    ramp = marble(nt, LIQUID_MARBLE, scale=1.6, distortion=18.0)
    nt.links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
    setv(bsdf, 'Roughness', 0.10)
    setv(bsdf, 'Metallic', 0.20)
    setv(bsdf, 'Coat Weight', 1.0)             # the wet look
    setv(bsdf, 'Clearcoat', 1.0)               # pre-4.0 name
    setv(bsdf, 'Coat Roughness', 0.03)
    setv(bsdf, 'IOR', 1.42)
    ob.data.materials.append(m)


# build fn, looks (first is default), and the radius the camera has to frame --
# liquid displaces outward past the unit sphere, so it needs more room or the
# wobble clips the edge.
ORBS = {
    'glass':  (orb_glass,  ['clear', 'tinted', 'frosted'], 1.02),
    'liquid': (orb_liquid, ['marble', 'refract', 'chrome'], 1.22),
}


# -------------------------------------------------------------------- render

def main():
    if A.orb not in ORBS:
        raise SystemExit('unknown orb ' + repr(A.orb) + '; have ' + ', '.join(ORBS))
    build, looks, radius = ORBS[A.orb]
    look = A.look or looks[0]
    if look not in looks:
        raise SystemExit('unknown look ' + repr(look) + '; have ' + ', '.join(looks))
    name = A.name or 'world-' + A.orb + ('' if look == looks[0] else '-' + look)

    scene, dev = configure()
    build(scene, look)
    camera(scene, radius=radius)      # after the orb: framing follows its size

    if LOOP > 1:
        out = os.path.join(ROOT, 'assets', '3d', 'frames', name) + os.sep
        scene.render.filepath = out
        print('[orbs] %s/%s %dpx x%d on %s -> %s' % (A.orb, look, A.size, LOOP, dev, out))
        bpy.ops.render.render(animation=True)
    else:
        out = os.path.join(ROOT, 'assets', '3d', name + '.png')
        scene.render.filepath = out
        print('[orbs] %s/%s %dpx still on %s -> %s' % (A.orb, look, A.size, dev, out))
        bpy.ops.render.render(write_still=True)


main()
