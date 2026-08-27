# A brain in a neural web: glowing core, real 3D network turning around it.
#
#   blender -b -P tools/blender/brain-orb.py -- --src <brain.png> --still 1
#   blender -b -P tools/blender/brain-orb.py -- --src <brain.png> --frames 180
#
# The source is one 2D view of a brain, so the brain itself cannot be spun --
# turning a picture only proves it is a picture. What CAN turn is the network
# around it, and that is the half worth building for real: a few hundred nodes
# on a spherical shell, wired to their neighbours, orbiting the core. Nodes in
# front sweep across the brain and nodes behind pass out of sight, which is
# genuine 3D occlusion and reads as depth no flat glow can fake.
#
# The brain sits at the centre as a volume rather than a card, so it has
# thickness to light and can swing a few degrees against the turning web.

import sys, os, math, argparse, random
import bpy
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
TAU = math.pi * 2

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument('--src', required=True)
ap.add_argument('--name', default='world-brain')
ap.add_argument('--size', type=int, default=512)
ap.add_argument('--frames', type=int, default=0)
ap.add_argument('--samples', type=int, default=192)
ap.add_argument('--nodes', type=int, default=260)
ap.add_argument('--density', type=float, default=44.0)
ap.add_argument('--glow', type=float, default=7.5)
ap.add_argument('--warp', type=float, default=0.022)   # keep the brain crisp
ap.add_argument('--thick', type=float, default=0.22)
ap.add_argument('--swing', type=float, default=0.13)   # radians of core swing
ap.add_argument('--bob', type=float, default=0.035)    # the float
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
    c.volume_bounces = 2
    c.transparent_max_bounces = 24
    c.volume_step_rate = 0.4
    c.volume_max_steps = 1024

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


def black_world():
    w = bpy.data.worlds.new('w')
    bpy.context.scene.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes['Background']
    bg.inputs['Color'].default_value = (0, 0, 0, 1)
    bg.inputs['Strength'].default_value = 0.0
    return w


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


def bezier_keys(ob, path, samples):
    """samples = [(frame, value_tuple)] -- smooth, and closed at LOOP+1."""
    for frame, value in samples:
        setattr(ob, path, value)
        ob.keyframe_insert(path, frame=frame)
    for fc in ob.animation_data.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = 'BEZIER'
        fc.extrapolation = 'LINEAR'


# --------------------------------------------------------------- the backdrop

def backdrop(radius=1.0):
    """Pitch black disc. Emission of #000 still registers as a surface hit, so
    the orb stays opaque in the alpha instead of punching a hole in the page."""
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
    emit.inputs['Color'].default_value = (0, 0, 0, 1)
    mix = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(geo.outputs['Backfacing'], mix.inputs['Fac'])
    nt.links.new(clear.outputs['BSDF'], mix.inputs[1])
    nt.links.new(emit.outputs['Emission'], mix.inputs[2])
    nt.links.new(mix.outputs['Shader'], out.inputs['Surface'])
    ob.data.materials.append(m)
    ob.visible_shadow = False
    return ob


# ------------------------------------------------------------------ the brain

def brain_core(scene, span=0.70):
    """The image as a volume: density from its luminance, glow from its colour.

    A volume rather than a card so the core has real thickness -- the network
    nodes that swing behind it are genuinely occluded by something, and the
    swing below parallaxes its front against its back."""
    bpy.ops.mesh.primitive_cube_add(size=2)
    box = bpy.context.active_object
    box.name = 'brain'
    box.scale = (span, A.thick, span)
    bpy.ops.object.transform_apply(scale=True)

    m = bpy.data.materials.new('brain')
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    vol = nt.nodes.new('ShaderNodeVolumePrincipled')
    coord = nt.nodes.new('ShaderNodeTexCoord')

    # gentle depth warp -- enough to give thickness, not enough to smear the folds
    nse = nt.nodes.new('ShaderNodeTexNoise')
    nse.noise_dimensions = '3D'
    nse.inputs['Scale'].default_value = 4.0
    nse.inputs['Detail'].default_value = 5.0
    ctr = nt.nodes.new('ShaderNodeVectorMath'); ctr.operation = 'SUBTRACT'
    ctr.inputs[1].default_value = (0.5, 0.5, 0.5)
    amt = nt.nodes.new('ShaderNodeVectorMath'); amt.operation = 'SCALE'
    amt.inputs['Scale'].default_value = A.warp
    warped = nt.nodes.new('ShaderNodeVectorMath'); warped.operation = 'ADD'
    nt.links.new(coord.outputs['Generated'], nse.inputs['Vector'])
    nt.links.new(nse.outputs['Color'], ctr.inputs[0])
    nt.links.new(ctr.outputs['Vector'], amt.inputs[0])
    nt.links.new(coord.outputs['Generated'], warped.inputs[0])
    nt.links.new(amt.outputs['Vector'], warped.inputs[1])

    swz = nt.nodes.new('ShaderNodeSeparateXYZ')
    uv = nt.nodes.new('ShaderNodeCombineXYZ')
    nt.links.new(warped.outputs['Vector'], swz.inputs['Vector'])
    nt.links.new(swz.outputs['X'], uv.inputs['X'])
    nt.links.new(swz.outputs['Z'], uv.inputs['Y'])

    img = nt.nodes.new('ShaderNodeTexImage')
    img.image = bpy.data.images.load(A.src)
    img.extension = 'EXTEND'
    img.interpolation = 'Cubic'
    nt.links.new(uv.outputs['Vector'], img.inputs['Vector'])
    lum = nt.nodes.new('ShaderNodeRGBToBW')
    nt.links.new(img.outputs['Color'], lum.inputs['Color'])

    # depth falloff
    dsub = nt.nodes.new('ShaderNodeMath'); dsub.operation = 'SUBTRACT'
    dsub.inputs[1].default_value = 0.5
    dabs = nt.nodes.new('ShaderNodeMath'); dabs.operation = 'ABSOLUTE'
    dfall = nt.nodes.new('ShaderNodeMapRange')
    dfall.inputs['From Min'].default_value = 0.0
    dfall.inputs['From Max'].default_value = 0.5
    dfall.inputs['To Min'].default_value = 1.0
    dfall.inputs['To Max'].default_value = 0.0
    nt.links.new(swz.outputs['Y'], dsub.inputs[0])
    nt.links.new(dsub.outputs['Value'], dabs.inputs[0])
    nt.links.new(dabs.outputs['Value'], dfall.inputs['Value'])

    # tight circular mask: the source crop still carries painted network around
    # the brain, and doubling that against the real 3D web looks like a mistake.
    rx = nt.nodes.new('ShaderNodeMath'); rx.operation = 'SUBTRACT'
    rx.inputs[1].default_value = 0.5
    rz = nt.nodes.new('ShaderNodeMath'); rz.operation = 'SUBTRACT'
    rz.inputs[1].default_value = 0.5
    nt.links.new(swz.outputs['X'], rx.inputs[0])
    nt.links.new(swz.outputs['Z'], rz.inputs[0])
    sx = nt.nodes.new('ShaderNodeMath'); sx.operation = 'MULTIPLY'
    sz = nt.nodes.new('ShaderNodeMath'); sz.operation = 'MULTIPLY'
    nt.links.new(rx.outputs['Value'], sx.inputs[0]); nt.links.new(rx.outputs['Value'], sx.inputs[1])
    nt.links.new(rz.outputs['Value'], sz.inputs[0]); nt.links.new(rz.outputs['Value'], sz.inputs[1])
    ssum = nt.nodes.new('ShaderNodeMath'); ssum.operation = 'ADD'
    nt.links.new(sx.outputs['Value'], ssum.inputs[0])
    nt.links.new(sz.outputs['Value'], ssum.inputs[1])
    rad = nt.nodes.new('ShaderNodeMath'); rad.operation = 'SQRT'
    nt.links.new(ssum.outputs['Value'], rad.inputs[0])
    rfall = nt.nodes.new('ShaderNodeMapRange')
    rfall.inputs['From Min'].default_value = 0.30
    rfall.inputs['From Max'].default_value = 0.47
    rfall.inputs['To Min'].default_value = 1.0
    rfall.inputs['To Max'].default_value = 0.0
    rfall.clamp = True
    nt.links.new(rad.outputs['Value'], rfall.inputs['Value'])

    # One shape factor, applied to BOTH density and emission colour.
    #
    # Principled Volume does not scale emission by density -- an emissive volume
    # glows everywhere inside its box whatever the density says. Masking density
    # alone therefore renders the brain as a glowing square, which is exactly
    # what the first pass did. The smoke orb got away with it only because that
    # source was black outside the smoke; this crop has haze in every pixel.
    shape = nt.nodes.new('ShaderNodeMath'); shape.operation = 'MULTIPLY'
    nt.links.new(dfall.outputs['Result'], shape.inputs[0])
    nt.links.new(rfall.outputs['Result'], shape.inputs[1])

    dens = nt.nodes.new('ShaderNodeMath'); dens.operation = 'MULTIPLY'
    scale = nt.nodes.new('ShaderNodeMath'); scale.operation = 'MULTIPLY'
    scale.inputs[1].default_value = A.density
    nt.links.new(lum.outputs['Val'], dens.inputs[0])
    nt.links.new(shape.outputs['Value'], dens.inputs[1])
    nt.links.new(dens.outputs['Value'], scale.inputs[0])
    nt.links.new(scale.outputs['Value'], vol.inputs['Density'])

    lit = nt.nodes.new('ShaderNodeMix')
    lit.data_type = 'RGBA'
    lit.blend_type = 'MULTIPLY'
    lit.inputs['Factor'].default_value = 1.0
    nt.links.new(img.outputs['Color'], lit.inputs[6])       # A (colour)
    nt.links.new(shape.outputs['Value'], lit.inputs[7])     # B (grey mask)

    setv(vol, 'Emission Strength', A.glow)
    setv(vol, 'Color', (0.10, 0.09, 0.20, 1))
    setv(vol, 'Anisotropy', 0.2)
    nt.links.new(lit.outputs[2], vol.inputs['Emission Color'])
    nt.links.new(vol.outputs['Volume'], out.inputs['Volume'])
    box.data.materials.append(m)
    return box


# ---------------------------------------------------------------- the network

def network(scene, hub):
    """Nodes on a shell, wired to near neighbours. Built as two objects rather
    than a few hundred: one vertex cloud instancing a glowing bead, and one
    edge mesh converted to a bevelled curve for the filaments. Spawning 400
    separate objects would render the same picture and take far longer to
    build."""
    rng = random.Random(A.seed)
    pts = []
    for _ in range(A.nodes):
        # even-ish on the sphere, then pushed out to a shell
        z = rng.uniform(-1, 1)
        th = rng.uniform(0, TAU)
        r = math.sqrt(max(0.0, 1 - z * z))
        rad = rng.uniform(0.68, 1.00)
        pts.append(Vector((r * math.cos(th) * rad, r * math.sin(th) * rad, z * rad)))

    # --- beads
    nmesh = bpy.data.meshes.new('nodes')
    nmesh.from_pydata([tuple(p) for p in pts], [], [])
    nmesh.update()
    nodes_ob = bpy.data.objects.new('nodes', nmesh)
    scene.collection.objects.link(nodes_ob)

    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.0070)
    bead = bpy.context.active_object
    bead.name = 'bead'
    bpy.ops.object.shade_smooth()
    bead.data.materials.append(emissive('bead', (0.72, 0.88, 1.00), 7.5))
    bead.parent = nodes_ob
    nodes_ob.instance_type = 'VERTS'          # one bead per vertex, no copies

    # --- filaments: connect each node to near neighbours, capped so the web
    # stays readable rather than becoming a solid ball of wire.
    edges, deg = [], [0] * len(pts)
    for i in range(len(pts)):
        near = sorted(((pts[i] - pts[j]).length, j) for j in range(len(pts)) if j != i)
        for d, j in near[:4]:
            if d > 0.20 or deg[i] >= 3 or deg[j] >= 3:
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
    edges_ob.data.bevel_depth = 0.0015
    edges_ob.data.bevel_resolution = 1
    edges_ob.data.materials.append(emissive('filament', (0.26, 0.40, 1.00), 1.4))
    edges_ob.select_set(False)

    nodes_ob.parent = hub
    edges_ob.parent = hub
    return nodes_ob, edges_ob, len(edges)


# -------------------------------------------------------------------- render

def main():
    if not os.path.isfile(A.src):
        raise SystemExit('no such image: ' + A.src)
    scene, dev = configure()
    black_world()
    backdrop()

    hub = bpy.data.objects.new('hub', None)
    scene.collection.objects.link(hub)
    core = brain_core(scene)
    _, _, nedges = network(scene, hub)

    if LOOP > 1:
        STEPS = 24
        # the web turns a whole revolution -- real 3D, so it closes exactly
        bezier_keys(hub, 'rotation_euler',
                    [(1 + LOOP * i / STEPS, (0.0, 0.0, TAU * i / STEPS))
                     for i in range(STEPS + 1)])
        for fc in hub.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'      # constant rate, no ease per key

        # the float, and a slow swing of the core against the turning web.
        # Full sine cycles: they return in position AND velocity, so no snap.
        bezier_keys(core, 'rotation_euler',
                    [(1 + LOOP * i / STEPS,
                      (0.0, 0.0, A.swing * math.sin(TAU * i / STEPS)))
                     for i in range(STEPS + 1)])
        bezier_keys(hub, 'location',
                    [(1 + LOOP * i / STEPS,
                      (0.0, 0.0, A.bob * math.sin(TAU * i / STEPS)))
                     for i in range(STEPS + 1)])
        core_bob = [(1 + LOOP * i / STEPS,
                     (0.0, 0.0, A.bob * math.sin(TAU * i / STEPS)))
                    for i in range(STEPS + 1)]
        for frame, loc in core_bob:
            core.location = loc
            core.keyframe_insert('location', frame=frame)
        for fc in core.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = 'BEZIER'

    camera(scene, radius=1.0)

    if A.still:
        scene.frame_set(A.still)
        out = os.path.join(ROOT, 'assets', '3d', A.name + '-still.png')
        scene.render.filepath = out
        print('[brain-orb] frame %d, %d nodes / %d links, on %s'
              % (A.still, A.nodes, nedges, dev))
        bpy.ops.render.render(write_still=True)
    elif LOOP > 1:
        out = os.path.join(ROOT, 'assets', '3d', 'frames', A.name) + os.sep
        scene.render.filepath = out
        print('[brain-orb] %s %dpx x%d, %d nodes / %d links, on %s'
              % (A.name, A.size, LOOP, A.nodes, nedges, dev))
        bpy.ops.render.render(animation=True)
    else:
        out = os.path.join(ROOT, 'assets', '3d', A.name + '-still.png')
        scene.render.filepath = out
        print('[brain-orb] still, %d nodes / %d links, on %s' % (A.nodes, nedges, dev))
        bpy.ops.render.render(write_still=True)


main()
