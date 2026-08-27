# A real 3D brain, spinning inside the orb, on a gradient.
#
#   blender -b -P tools/blender/brain3d.py -- --still 1
#   blender -b -P tools/blender/brain3d.py -- --frames 180
#
# The previous brain orb mapped a photograph into a volume. That can glow and it
# can drift, but it can never turn: rotating a picture only proves it is a
# picture. So this builds the brain instead -- cerebrum, cerebellum, brainstem,
# folded by displacement -- and then it can spin all the way round because there
# is something there to spin.
#
# The glow comes from the geometry rather than from a texture: an Ambient
# Occlusion node finds the crevices, and emission rides in them. That is why the
# light sits down in the sulci and follows them as the brain turns, instead of
# swimming across the surface the way a projected pattern would.

import sys, os, math, argparse, random
import bpy
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
TAU = math.pi * 2

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument('--name', default='world-brain')
ap.add_argument('--size', type=int, default=512)
ap.add_argument('--frames', type=int, default=0)
ap.add_argument('--samples', type=int, default=160)
ap.add_argument('--nodes', type=int, default=200)
ap.add_argument('--folds', type=float, default=0.085)   # gyri depth
ap.add_argument('--scale', type=float, default=0.74)    # brain vs orb
ap.add_argument('--glow', type=float, default=9.0)      # crevice emission
ap.add_argument('--bob', type=float, default=0.035)
ap.add_argument('--still', type=int, default=0)
ap.add_argument('--seed', type=int, default=11)
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
    c.adaptive_threshold = 0.012
    c.max_bounces = 12
    c.transparent_max_bounces = 16
    c.blur_glossy = 0.5

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


def area(scene, name, loc, size, energy, color, shape='DISK'):
    d = bpy.data.lights.new(name, 'AREA')
    d.shape = shape
    d.size = size
    d.energy = energy
    d.color = color
    o = bpy.data.objects.new(name, d)
    scene.collection.objects.link(o)
    o.location = loc
    aim(o)
    o.visible_camera = False
    return o


def lights(scene):
    """Real lighting, not just glow. The folds only read as folds if something
    outside them casts shadow into them -- an object lit purely by its own
    emission has no form at all."""
    area(scene, 'key',  (-2.6, -2.2,  2.4), 3.0, 150, (0.72, 0.82, 1.00))
    area(scene, 'rim',  ( 2.2,  2.6,  1.6), 3.0, 250, (0.42, 0.35, 1.00))
    area(scene, 'fill', ( 2.4, -1.6, -1.4), 4.0, 70, (0.85, 0.45, 1.00))
    area(scene, 'top',  ( 0.0, -0.4,  3.2), 2.5, 90, (0.60, 0.80, 1.00))


def emissive(name, color, strength):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    e = nt.nodes.new('ShaderNodeEmission')
    e.inputs['Color'].default_value = (color[0], color[1], color[2], 1)
    e.inputs['Strength'].default_value = strength
    nt.links.new(e.outputs['Emission'], out.inputs['Surface'])
    return m


def keys(ob, path, samples, interp='BEZIER'):
    for frame, value in samples:
        setattr(ob, path, value)
        ob.keyframe_insert(path, frame=frame)
    for fc in ob.animation_data.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = interp
        fc.extrapolation = 'LINEAR'


# ------------------------------------------------------------ the gradient orb

def backdrop(radius=1.0):
    """A radial gradient rather than flat black -- violet where the brain sits,
    falling to near-black at the rim. Two things come free from that: the orb
    reads as a lit sphere instead of a disc, and the brain has something to
    stand against, which is most of why it pops."""
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

    # radius from the orb's centre, in generated space
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
    e[0].position, e[0].color = 0.00, (0.085, 0.055, 0.230, 1)   # violet core
    e[1].position, e[1].color = 1.00, (0.004, 0.004, 0.016, 1)   # near-black rim
    for pos, col in ((0.42, (0.045, 0.035, 0.150, 1)),
                     (0.74, (0.012, 0.012, 0.055, 1))):
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
    ob.visible_glossy = False
    return ob


# ------------------------------------------------------------------- the brain

def lump(name, radius, scale, loc, subdiv=5):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdiv, radius=radius, location=loc)
    ob = bpy.context.active_object
    ob.name = name
    ob.scale = scale
    bpy.ops.object.transform_apply(scale=True)
    return ob


def brain_mesh():
    """Cerebrum, cerebellum, brainstem -- joined, then folded by displacement.

    Two displacement passes, coarse then fine. One pass gives an evenly bumpy
    ball; gyri are big meandering ridges with smaller wrinkles running over
    them, and it takes two scales to get that. Both read LOCAL coordinates so
    the folds are welded to the mesh -- on GLOBAL they would swim through the
    surface as it spins, which instantly reads as fake."""
    parts = [
        lump('cerebrum', 1.0, (0.78, 1.02, 0.76), (0.0, 0.0, 0.06), 6),
        lump('cerebellum', 1.0, (0.40, 0.30, 0.22), (0.0, 0.62, -0.52), 5),
    ]
    bpy.ops.mesh.primitive_cone_add(vertices=20, radius1=0.13, radius2=0.07,
                                    depth=0.55, location=(0.0, 0.46, -0.80))
    stem = bpy.context.active_object
    stem.name = 'stem'
    stem.rotation_euler = (math.radians(-16), 0, 0)
    parts.append(stem)

    for p in parts:
        p.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    brain = bpy.context.active_object
    brain.name = 'brain'

    coarse = bpy.data.textures.new('gyri', 'DISTORTED_NOISE')
    coarse.noise_scale = 0.55
    coarse.distortion = 2.7
    d1 = brain.modifiers.new('gyri', 'DISPLACE')
    d1.texture = coarse
    d1.strength = A.folds
    d1.mid_level = 0.5
    d1.texture_coords = 'LOCAL'

    fine = bpy.data.textures.new('wrinkle', 'DISTORTED_NOISE')
    fine.noise_scale = 0.17
    fine.distortion = 1.5
    d2 = brain.modifiers.new('wrinkle', 'DISPLACE')
    d2.texture = fine
    d2.strength = A.folds * 0.30
    d2.mid_level = 0.5
    d2.texture_coords = 'LOCAL'

    brain.scale = (A.scale, A.scale, A.scale)
    bpy.ops.object.transform_apply(scale=True)

    sub = brain.modifiers.new('smooth', 'SUBSURF')
    sub.levels = sub.render_levels = 2
    bpy.ops.object.shade_smooth()
    return brain


def brain_material(brain):
    """Deep translucent tissue with light living in the creases.

    Emission is driven by Ambient Occlusion, so it is the geometry itself that
    decides where the glow goes. A texture would have to be projected, and any
    projection slides across the surface the moment the object rotates."""
    m = bpy.data.materials.new('brain')
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes['Principled BSDF']
    out = [n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'][0]

    setv(bsdf, 'Base Color', (0.055, 0.028, 0.185, 1))
    setv(bsdf, 'Roughness', 0.42)
    setv(bsdf, 'Metallic', 0.0)
    setv(bsdf, 'Subsurface Weight', 0.14)
    setv(bsdf, 'Subsurface Radius', (0.42, 0.18, 0.55))
    setv(bsdf, 'Subsurface Scale', 0.09)
    setv(bsdf, 'Coat Weight', 0.35)
    setv(bsdf, 'Coat Roughness', 0.16)

    ao = nt.nodes.new('ShaderNodeAmbientOcclusion')
    ao.samples = 12
    ao.only_local = True
    ao.inputs['Distance'].default_value = 0.07

    inv = nt.nodes.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'
    inv.inputs[0].default_value = 1.0
    pw = nt.nodes.new('ShaderNodeMath'); pw.operation = 'POWER'
    pw.inputs[1].default_value = 2.9          # tighten the glow into the crease
    gain = nt.nodes.new('ShaderNodeMath'); gain.operation = 'MULTIPLY'
    gain.inputs[1].default_value = A.glow

    # a rim of light so the silhouette separates from the gradient behind it
    fres = nt.nodes.new('ShaderNodeFresnel')
    fres.inputs['IOR'].default_value = 1.5
    rim = nt.nodes.new('ShaderNodeMath'); rim.operation = 'MULTIPLY'
    rim.inputs[1].default_value = A.glow * 0.30
    total = nt.nodes.new('ShaderNodeMath'); total.operation = 'ADD'

    nt.links.new(ao.outputs['AO'], inv.inputs[1])
    nt.links.new(inv.outputs['Value'], pw.inputs[0])
    nt.links.new(pw.outputs['Value'], gain.inputs[0])
    nt.links.new(fres.outputs['Fac'], rim.inputs[0])
    nt.links.new(gain.outputs['Value'], total.inputs[0])
    nt.links.new(rim.outputs['Value'], total.inputs[1])
    nt.links.new(total.outputs['Value'], bsdf.inputs['Emission Strength'])
    setv(bsdf, 'Emission Color', (0.22, 0.58, 1.00, 1))

    brain.data.materials.append(m)
    return m


# ---------------------------------------------------------------- the network

def network(scene, hub):
    rng = random.Random(A.seed)
    pts = []
    for _ in range(A.nodes):
        z = rng.uniform(-1, 1)
        th = rng.uniform(0, TAU)
        r = math.sqrt(max(0.0, 1 - z * z))
        rad = rng.uniform(0.80, 1.02)
        pts.append(Vector((r * math.cos(th) * rad, r * math.sin(th) * rad, z * rad)))

    nmesh = bpy.data.meshes.new('nodes')
    nmesh.from_pydata([tuple(p) for p in pts], [], [])
    nmesh.update()
    nodes_ob = bpy.data.objects.new('nodes', nmesh)
    scene.collection.objects.link(nodes_ob)

    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.0062)
    bead = bpy.context.active_object
    bead.name = 'bead'
    bpy.ops.object.shade_smooth()
    bead.data.materials.append(emissive('bead', (0.70, 0.88, 1.00), 9.0))
    bead.parent = nodes_ob
    nodes_ob.instance_type = 'VERTS'

    edges, deg = [], [0] * len(pts)
    for i in range(len(pts)):
        near = sorted(((pts[i] - pts[j]).length, j) for j in range(len(pts)) if j != i)
        for d, j in near[:4]:
            if d > 0.30 or deg[i] >= 2 or deg[j] >= 2:
                continue
            if (min(i, j), max(i, j)) in edges:
                continue
            edges.append((min(i, j), max(i, j)))
            deg[i] += 1
            deg[j] += 1

    emesh = bpy.data.meshes.new('edges')
    emesh.from_pydata([tuple(p) for p in pts], edges, [])
    emesh.update()
    edges_ob = bpy.data.objects.new('edges', emesh)
    scene.collection.objects.link(edges_ob)
    bpy.context.view_layer.objects.active = edges_ob
    edges_ob.select_set(True)
    bpy.ops.object.convert(target='CURVE')
    edges_ob.data.bevel_depth = 0.0013
    edges_ob.data.bevel_resolution = 1
    edges_ob.data.materials.append(emissive('filament', (0.26, 0.42, 1.00), 1.3))
    edges_ob.select_set(False)

    nodes_ob.parent = hub
    edges_ob.parent = hub
    return len(edges)


# -------------------------------------------------------------------- render

def main():
    scene, dev = configure()
    backdrop()
    lights(scene)

    brain = brain_mesh()
    brain_material(brain)

    hub = bpy.data.objects.new('hub', None)
    scene.collection.objects.link(hub)
    nedges = network(scene, hub)

    if LOOP > 1:
        STEPS = 24
        # the brain turns a whole revolution -- it is real geometry, so every
        # angle is a genuine view and the loop closes on itself exactly
        keys(brain, 'rotation_euler',
             [(1 + LOOP * i / STEPS, (0.0, 0.0, TAU * i / STEPS))
              for i in range(STEPS + 1)], interp='LINEAR')
        # The web turns the other way: counter-rotation reads as two separate
        # depths rather than one rigid object.
        #
        # A WHOLE turn, not a half. Half a revolution leaves the web 180 degrees
        # from where it started, so the loop point snapped it back -- the wrap
        # measured 19.3dB against 22ish for an ordinary step. Anything that
        # animates across the loop has to come back to itself, and a fraction of
        # a turn never does.
        keys(hub, 'rotation_euler',
             [(1 + LOOP * i / STEPS, (0.0, 0.0, -TAU * i / STEPS))
              for i in range(STEPS + 1)], interp='LINEAR')
        # the float. A full sine returns in position and velocity, so no snap.
        keys(brain, 'location',
             [(1 + LOOP * i / STEPS,
               (0.0, 0.0, A.bob * math.sin(TAU * i / STEPS)))
              for i in range(STEPS + 1)])

    camera(scene, radius=1.0)

    if A.still:
        scene.frame_set(A.still)
        out = os.path.join(ROOT, 'assets', '3d', A.name + '-still.png')
        scene.render.filepath = out
        print('[brain3d] frame %d, %d links, on %s' % (A.still, nedges, dev))
        bpy.ops.render.render(write_still=True)
    elif LOOP > 1:
        out = os.path.join(ROOT, 'assets', '3d', 'frames', A.name) + os.sep
        scene.render.filepath = out
        print('[brain3d] %s %dpx x%d, %d links, on %s'
              % (A.name, A.size, LOOP, nedges, dev))
        bpy.ops.render.render(animation=True)
    else:
        out = os.path.join(ROOT, 'assets', '3d', A.name + '-still.png')
        scene.render.filepath = out
        print('[brain3d] still, %d links, on %s' % (nedges, dev))
        bpy.ops.render.render(write_still=True)


main()
