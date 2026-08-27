# Glass "?!" floating in a light brown orb.
#
#   blender -b -P tools/blender/marks-orb.py -- --still 1
#   blender -b -P tools/blender/marks-orb.py -- --frames 180
#
# The marks are built, not traced from the picture: a question mark is a swept
# tube and a dot, which is a handful of curve points rather than anything that
# needs a photograph. Building them means the iridescence is real -- thin-film
# interference over a mirror, recomputed for every angle -- so the colour
# travels across the bend as it floats instead of sitting on it like a decal.
#
# Warm ground, cool objects: the orb is light brown and the marks are blue and
# violet, which is most of why they separate from it.

import sys, os, math, argparse
import bpy
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
TAU = math.pi * 2

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument('--name', default='world-marks')
ap.add_argument('--size', type=int, default=512)
ap.add_argument('--frames', type=int, default=0)
ap.add_argument('--samples', type=int, default=200)
ap.add_argument('--scale', type=float, default=0.72)
ap.add_argument('--yaw', type=float, default=0.30)     # radians of float-turn
ap.add_argument('--bob', type=float, default=0.045)
ap.add_argument('--still', type=int, default=0)
ap.add_argument('--cpu', action='store_true')
A = ap.parse_args(argv)

LOOP = A.frames or 1


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
    c.max_bounces = 12
    c.transmission_bounces = 16
    c.glossy_bounces = 5
    c.transparent_max_bounces = 24
    c.blur_glossy = 0.4

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
    dist = radius / math.sin(fill * half)
    cam = bpy.data.objects.new('cam', cam_d)
    scene.collection.objects.link(cam)
    cam.location = (0, -dist, 0)
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
        d.size_y = size * 0.14
    d.energy = energy
    d.color = color
    o = bpy.data.objects.new(name, d)
    scene.collection.objects.link(o)
    o.location = loc
    aim(o)
    o.visible_camera = False
    return o


def lights(scene):
    """Long strips. A mirrored tube reflects a source's actual shape, and a bar
    drawn down the bend is what says polished; a round blob says clip art."""
    area(scene, 'key',  (-2.8, -2.4,  2.6), 6.0, 380, (1.00, 0.97, 0.92))
    area(scene, 'rim',  ( 2.2,  2.8,  1.8), 5.5, 520, (0.90, 0.94, 1.00))
    area(scene, 'fill', ( 2.6, -1.8, -1.2), 6.0, 200, (0.72, 0.80, 1.00))
    area(scene, 'spec', (-1.4, -2.6,  1.0), 0.8, 220, (1.00, 1.00, 1.00), 'DISK')
    # Colour to interfere with. Thin film shifts whatever hue it reflects, so a
    # white-and-grey room yields a silver mark with a faint tint -- the violets
    # and cyans in the reference come from there being violet and cyan around it
    # in the first place.
    area(scene, 'violet', ( 2.0, -1.0,  2.2), 4.0, 260, (0.72, 0.34, 1.00), 'DISK')
    area(scene, 'cyan',   (-2.2, -0.8, -1.6), 4.0, 230, (0.24, 0.86, 1.00), 'DISK')


def warm_world(strength=0.9):
    """A warm room for the chrome to reflect, so the marks sit in the same light
    as the orb behind them rather than looking pasted over it."""
    w = bpy.data.worlds.new('w')
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputWorld')
    bg = nt.nodes.new('ShaderNodeBackground')
    bg.inputs['Strength'].default_value = strength
    # Cool and high-contrast, NOT warm. This is only ever seen in the marks'
    # reflections -- the brown the viewer sees is the backdrop sphere. Making
    # this warm too was what turned the chrome tan; a dark floor and a bright
    # cool band give the interference something with range to tint.
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.interpolation = 'B_SPLINE'
    e = ramp.color_ramp.elements
    e[0].position, e[0].color = 0.00, (0.02, 0.02, 0.05, 1)
    e[1].position, e[1].color = 1.00, (0.72, 0.82, 1.00, 1)
    for pos, col in ((0.38, (0.20, 0.22, 0.34, 1)),
                     (0.60, (1.00, 1.00, 1.00, 1))):
        ramp.color_ramp.elements.new(pos).color = col
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    tex = nt.nodes.new('ShaderNodeTexCoord')
    nt.links.new(tex.outputs['Generated'], sep.inputs['Vector'])
    nt.links.new(sep.outputs['Z'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], bg.inputs['Color'])
    nt.links.new(bg.outputs['Background'], out.inputs['Surface'])
    return w


# ------------------------------------------------------------------- backdrop

def backdrop(radius=1.0):
    """Light brown, radial: warm and bright behind the marks, deepening to a
    toasted edge so the orb reads as a sphere and not a flat brown disc."""
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
    emit.inputs['Strength'].default_value = 1.0

    coord = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    sx = nt.nodes.new('ShaderNodeMath'); sx.operation = 'SUBTRACT'; sx.inputs[1].default_value = 0.5
    sz = nt.nodes.new('ShaderNodeMath'); sz.operation = 'SUBTRACT'; sz.inputs[1].default_value = 0.5
    qx = nt.nodes.new('ShaderNodeMath'); qx.operation = 'MULTIPLY'
    qz = nt.nodes.new('ShaderNodeMath'); qz.operation = 'MULTIPLY'
    add = nt.nodes.new('ShaderNodeMath'); add.operation = 'ADD'
    rt = nt.nodes.new('ShaderNodeMath'); rt.operation = 'SQRT'
    sc = nt.nodes.new('ShaderNodeMath'); sc.operation = 'MULTIPLY'; sc.inputs[1].default_value = 2.0
    nt.links.new(coord.outputs['Generated'], sep.inputs['Vector'])
    nt.links.new(sep.outputs['X'], sx.inputs[0])
    nt.links.new(sep.outputs['Z'], sz.inputs[0])
    nt.links.new(sx.outputs['Value'], qx.inputs[0]); nt.links.new(sx.outputs['Value'], qx.inputs[1])
    nt.links.new(sz.outputs['Value'], qz.inputs[0]); nt.links.new(sz.outputs['Value'], qz.inputs[1])
    nt.links.new(qx.outputs['Value'], add.inputs[0])
    nt.links.new(qz.outputs['Value'], add.inputs[1])
    nt.links.new(add.outputs['Value'], rt.inputs[0])
    nt.links.new(rt.outputs['Value'], sc.inputs[0])

    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.interpolation = 'B_SPLINE'
    e = ramp.color_ramp.elements
    e[0].position, e[0].color = 0.00, (0.86, 0.72, 0.55, 1)    # light tan centre
    e[1].position, e[1].color = 1.00, (0.30, 0.20, 0.13, 1)    # toasted rim
    for pos, col in ((0.46, (0.72, 0.56, 0.40, 1)),
                     (0.78, (0.48, 0.34, 0.23, 1))):
        ramp.color_ramp.elements.new(pos).color = col
    nt.links.new(sc.outputs['Value'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], emit.inputs['Color'])

    mix = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(geo.outputs['Backfacing'], mix.inputs['Fac'])
    nt.links.new(clear.outputs['BSDF'], mix.inputs[1])
    nt.links.new(emit.outputs['Emission'], mix.inputs[2])
    nt.links.new(mix.outputs['Shader'], out.inputs['Surface'])
    ob.data.materials.append(m)
    ob.visible_shadow = False
    # Out of reflection rays. A mirror sealed inside a brown wall reflects brown
    # and vanishes into it -- the first pass rendered the marks the same tan as
    # the orb. The camera still sees the orb warm; the marks now mirror the
    # studio instead, which is what lets the thin film show any colour at all.
    ob.visible_glossy = False
    return ob


# ------------------------------------------------------------------- material

def iridescent():
    """Mirror with a thin film over it. Thickness drifts across the surface, so
    the interference band walks along the tube instead of tinting it evenly."""
    m = bpy.data.materials.new('iridescent')
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    setv(b, 'Base Color', (0.78, 0.80, 0.88, 1))
    setv(b, 'Metallic', 1.0)
    setv(b, 'Roughness', 0.045)
    setv(b, 'Thin Film IOR', 1.62)

    coord = nt.nodes.new('ShaderNodeTexCoord')
    noise = nt.nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = 2.1
    noise.inputs['Detail'].default_value = 5.0
    thick = nt.nodes.new('ShaderNodeMapRange')
    thick.inputs['To Min'].default_value = 300.0     # nanometres
    thick.inputs['To Max'].default_value = 640.0
    nt.links.new(coord.outputs['Object'], noise.inputs['Vector'])
    nt.links.new(noise.outputs['Fac'], thick.inputs['Value'])
    nt.links.new(thick.outputs['Result'], b.inputs['Thin Film Thickness'])
    return m


# ---------------------------------------------------------------------- marks

def tube(scene, name, pts, depth, mat):
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = depth
    cu.bevel_resolution = 6
    cu.resolution_u = 20
    sp = cu.splines.new('BEZIER')
    sp.bezier_points.add(len(pts) - 1)
    for i, p in enumerate(pts):
        bp = sp.bezier_points[i]
        bp.co = p
        bp.handle_left_type = bp.handle_right_type = 'AUTO'
    ob = bpy.data.objects.new(name, cu)
    scene.collection.objects.link(ob)
    ob.data.materials.append(mat)
    return ob


def ball(scene, name, loc, r, mat):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4, radius=r, location=loc)
    ob = bpy.context.active_object
    ob.name = name
    bpy.ops.object.shade_smooth()
    ob.data.materials.append(mat)
    return ob


def marks(scene, mat):
    """A question mark is a hook that runs into a stem, plus a dot. Swept along
    a bezier with a round bevel, which is the same thing the reference is: one
    continuous tube of even thickness."""
    R = 0.115
    parts = []

    hook = [
        (-0.30, 0.0,  0.42),
        (-0.30, 0.0,  0.74),
        (-0.02, 0.0,  0.90),
        ( 0.26, 0.0,  0.74),
        ( 0.26, 0.0,  0.48),
        ( 0.04, 0.0,  0.30),
        ( 0.00, 0.0,  0.08),
        ( 0.00, 0.0, -0.14),
    ]
    parts.append(tube(scene, 'qmark', hook, R, mat))
    parts.append(ball(scene, 'qtip', (-0.30, 0.0, 0.42), R, mat))     # round the ends
    parts.append(ball(scene, 'qend', (0.00, 0.0, -0.14), R, mat))
    parts.append(ball(scene, 'qdot', (0.00, 0.0, -0.50), R * 1.5, mat))

    bang = [
        (0.78, 0.0,  0.72),
        (0.80, 0.0,  0.30),
        (0.81, 0.0, -0.06),
    ]
    parts.append(tube(scene, 'bang', bang, R * 0.86, mat))
    parts.append(ball(scene, 'btop', (0.78, 0.0, 0.72), R * 0.86, mat))
    parts.append(ball(scene, 'bend', (0.81, 0.0, -0.06), R * 0.72, mat))
    parts.append(ball(scene, 'bdot', (0.82, 0.0, -0.40), R * 1.05, mat))

    grp = bpy.data.objects.new('marks', None)
    scene.collection.objects.link(grp)
    for p in parts:
        p.parent = grp
    # centre the pair on the orb, then size it to leave a margin of brown
    grp.location = (-0.26 * A.scale, 0.0, -0.10 * A.scale)
    grp.scale = (A.scale, A.scale, A.scale)
    return grp


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
    warm_world()
    backdrop()
    lights(scene)
    grp = marks(scene, iridescent())

    if LOOP > 1:
        STEPS = 24
        base_z = grp.location[2]
        # Floating, not spinning. Full sine cycles on every channel: they come
        # back in position AND velocity, so the loop has no snap and no drift.
        keys(grp, 'rotation_euler',
             [(1 + LOOP * i / STEPS,
               (0.10 * math.sin(TAU * i / STEPS + 1.1),
                A.yaw * math.sin(TAU * i / STEPS),
                0.07 * math.sin(TAU * i / STEPS + 2.2)))
              for i in range(STEPS + 1)])
        keys(grp, 'location',
             [(1 + LOOP * i / STEPS,
               (grp.location[0],
                0.0,
                base_z + A.bob * math.sin(TAU * i / STEPS)))
              for i in range(STEPS + 1)])

    camera(scene, radius=1.0)

    if A.still:
        scene.frame_set(A.still)
        out = os.path.join(ROOT, 'assets', '3d', A.name + '-still.png')
        scene.render.filepath = out
        print('[marks-orb] frame %d on %s' % (A.still, dev))
        bpy.ops.render.render(write_still=True)
    elif LOOP > 1:
        out = os.path.join(ROOT, 'assets', '3d', 'frames', A.name) + os.sep
        scene.render.filepath = out
        print('[marks-orb] %s %dpx x%d on %s' % (A.name, A.size, LOOP, dev))
        bpy.ops.render.render(animation=True)
    else:
        out = os.path.join(ROOT, 'assets', '3d', A.name + '-still.png')
        scene.render.filepath = out
        print('[marks-orb] still on %s' % dev)
        bpy.ops.render.render(write_still=True)


main()
