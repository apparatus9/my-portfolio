# A handshake of real volumetric smoke, on a black orb.
#
#   blender -b -P tools/blender/smoke-orb.py -- --src <clean.png> --still 1
#   blender -b -P tools/blender/smoke-orb.py -- --src <clean.png> --frames 180
#
# The source is a flat picture of smoke. Pasting it on a card would give you a
# picture of smoke, which is what it already is. Instead the image drives the
# DENSITY of an actual Cycles volume, so light marches through it: it scatters,
# it self-shadows, thin parts glow and thick parts occlude what is behind them.
# That is the difference between an image of smoke and smoke.
#
# Depth is the other half. A 2D image extruded straight back is a prism, not a
# cloud, so the image lookup is warped by 3D noise that changes with depth --
# every slice through the volume samples the picture slightly differently, and
# the wisps acquire real thickness and structure front-to-back.

import sys, os, math, argparse
import bpy
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
TAU = math.pi * 2

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument('--src', required=True)            # cleaned smoke-on-black image
ap.add_argument('--name', default='world-smoke')
ap.add_argument('--size', type=int, default=512)
ap.add_argument('--frames', type=int, default=0)
ap.add_argument('--samples', type=int, default=256)
ap.add_argument('--density', type=float, default=26.0)
ap.add_argument('--glow', type=float, default=5.0)   # emission strength
ap.add_argument('--warp', type=float, default=0.09)  # 3D turbulence of the lookup
ap.add_argument('--thick', type=float, default=0.34) # slab half-depth
ap.add_argument('--drift', type=float, default=0.14) # radius of the loop orbit
ap.add_argument('--swing', type=float, default=0.20) # radians of slab yaw
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
    c.max_bounces = 16
    c.volume_bounces = 4          # smoke lit through smoke
    c.transparent_max_bounces = 24
    # Finer marching than default. Smoke driven by an image has detail at the
    # pixel scale, and coarse steps blur the wisps into fog.
    c.volume_step_rate = 0.35
    c.volume_preview_step_rate = 0.35
    c.volume_max_steps = 2048

    r = scene.render
    r.resolution_x = r.resolution_y = A.size
    r.resolution_percentage = 100
    r.film_transparent = True
    r.image_settings.file_format = 'PNG'
    r.image_settings.color_mode = 'RGBA'
    r.image_settings.compression = 20
    r.use_motion_blur = False     # the smoke drifts slowly; blur only muddies it

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
    return cam


def setv(node, key, value):
    if key in node.inputs:
        node.inputs[key].default_value = value
        return True
    return False


def black_world():
    """Nothing to light the scene with. The smoke is its own light source, and
    any ambient at all lifts the blacks and kills the neon."""
    w = bpy.data.worlds.new('w')
    bpy.context.scene.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes['Background']
    bg.inputs['Color'].default_value = (0, 0, 0, 1)
    bg.inputs['Strength'].default_value = 0.0
    return w


# ------------------------------------------------------------------ the orb

def backdrop(radius=1.0):
    """The black disc the smoke sits on.

    Transparent on the near side, emitting pure black on the far side (switched
    on Backfacing) so the camera looks through the front and sees an unlit wall
    behind the smoke. Emission of #000 still counts as a surface hit, so the
    disc stays fully opaque in the alpha -- it reads as pitch black on the page
    rather than punching a transparent hole through it."""
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
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.interpolation = 'B_SPLINE'
    e = ramp.color_ramp.elements
    e[0].position, e[0].color = 0.10, (0.0, 0.0, 0.0, 1)
    e[1].position, e[1].color = 0.92, (0.0, 0.0, 0.0, 1)

    mix = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(coord.outputs['Object'], sep.inputs['Vector'])
    nt.links.new(sep.outputs['Z'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], emit.inputs['Color'])
    nt.links.new(geo.outputs['Backfacing'], mix.inputs['Fac'])
    nt.links.new(clear.outputs['BSDF'], mix.inputs[1])
    nt.links.new(emit.outputs['Emission'], mix.inputs[2])
    nt.links.new(mix.outputs['Shader'], out.inputs['Surface'])
    ob.data.materials.append(m)
    ob.visible_shadow = False
    return ob


def smoke(scene, span=0.92):
    """The volume. A slab whose density is the picture, warped through depth."""
    bpy.ops.mesh.primitive_cube_add(size=2)
    box = bpy.context.active_object
    box.name = 'smoke'
    box.scale = (span, A.thick, span)          # Y is depth, toward the lens
    bpy.ops.object.transform_apply(scale=True)

    m = bpy.data.materials.new('smoke')
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    vol = nt.nodes.new('ShaderNodeVolumePrincipled')

    # Generated coords run 0..1 across the box in every axis.
    coord = nt.nodes.new('ShaderNodeTexCoord')

    # --- turbulence: a 3D noise offsetting the lookup, so each depth slice
    # reads the picture from a slightly different place.
    warp_map = nt.nodes.new('ShaderNodeMapping')   # rotates for the loop
    nse = nt.nodes.new('ShaderNodeTexNoise')
    nse.noise_dimensions = '3D'
    nse.inputs['Scale'].default_value = 3.2
    nse.inputs['Detail'].default_value = 7.0
    nse.inputs['Roughness'].default_value = 0.62
    centre = nt.nodes.new('ShaderNodeVectorMath')  # noise is 0..1, want -0.5..0.5
    centre.operation = 'SUBTRACT'
    centre.inputs[1].default_value = (0.5, 0.5, 0.5)
    amt = nt.nodes.new('ShaderNodeVectorMath')
    amt.operation = 'SCALE'
    amt.inputs['Scale'].default_value = A.warp
    warped = nt.nodes.new('ShaderNodeVectorMath')
    warped.operation = 'ADD'

    nt.links.new(coord.outputs['Generated'], warp_map.inputs['Vector'])
    nt.links.new(warp_map.outputs['Vector'], nse.inputs['Vector'])
    nt.links.new(nse.outputs['Color'], centre.inputs[0])
    nt.links.new(centre.outputs['Vector'], amt.inputs[0])
    nt.links.new(coord.outputs['Generated'], warped.inputs[0])
    nt.links.new(amt.outputs['Vector'], warped.inputs[1])

    # --- the picture, sampled on the warped coords (XZ face-on to the lens)
    swiz = nt.nodes.new('ShaderNodeSeparateXYZ')
    img_uv = nt.nodes.new('ShaderNodeCombineXYZ')
    nt.links.new(warped.outputs['Vector'], swiz.inputs['Vector'])
    nt.links.new(swiz.outputs['X'], img_uv.inputs['X'])
    nt.links.new(swiz.outputs['Z'], img_uv.inputs['Y'])

    img = nt.nodes.new('ShaderNodeTexImage')
    img.image = bpy.data.images.load(A.src)
    img.extension = 'EXTEND'
    img.interpolation = 'Cubic'
    nt.links.new(img_uv.outputs['Vector'], img.inputs['Vector'])

    lum = nt.nodes.new('ShaderNodeRGBToBW')
    nt.links.new(img.outputs['Color'], lum.inputs['Color'])

    # --- shape it: fade out through depth, and inside the orb's circle
    depth = nt.nodes.new('ShaderNodeMath')          # |y-0.5| -> 0 at mid-slab
    depth.operation = 'SUBTRACT'
    depth.inputs[1].default_value = 0.5
    dabs = nt.nodes.new('ShaderNodeMath')
    dabs.operation = 'ABSOLUTE'
    dfall = nt.nodes.new('ShaderNodeMapRange')
    dfall.inputs['From Min'].default_value = 0.0
    dfall.inputs['From Max'].default_value = 0.5
    dfall.inputs['To Min'].default_value = 1.0
    dfall.inputs['To Max'].default_value = 0.0
    nt.links.new(swiz.outputs['Y'], depth.inputs[0])
    nt.links.new(depth.outputs['Value'], dabs.inputs[0])
    nt.links.new(dabs.outputs['Value'], dfall.inputs['Value'])

    # radial mask, so nothing spills past the orb's edge
    rx = nt.nodes.new('ShaderNodeMath'); rx.operation = 'SUBTRACT'
    rx.inputs[1].default_value = 0.5
    rz = nt.nodes.new('ShaderNodeMath'); rz.operation = 'SUBTRACT'
    rz.inputs[1].default_value = 0.5
    nt.links.new(swiz.outputs['X'], rx.inputs[0])
    nt.links.new(swiz.outputs['Z'], rz.inputs[0])
    # hypot the long way: sqrt(dx^2 + dz^2). The Math node has no hypotenuse.
    sqx = nt.nodes.new('ShaderNodeMath'); sqx.operation = 'MULTIPLY'
    sqz = nt.nodes.new('ShaderNodeMath'); sqz.operation = 'MULTIPLY'
    nt.links.new(rx.outputs['Value'], sqx.inputs[0])
    nt.links.new(rx.outputs['Value'], sqx.inputs[1])
    nt.links.new(rz.outputs['Value'], sqz.inputs[0])
    nt.links.new(rz.outputs['Value'], sqz.inputs[1])
    ssum = nt.nodes.new('ShaderNodeMath'); ssum.operation = 'ADD'
    nt.links.new(sqx.outputs['Value'], ssum.inputs[0])
    nt.links.new(sqz.outputs['Value'], ssum.inputs[1])
    rad = nt.nodes.new('ShaderNodeMath'); rad.operation = 'SQRT'
    nt.links.new(ssum.outputs['Value'], rad.inputs[0])
    rfall = nt.nodes.new('ShaderNodeMapRange')
    rfall.inputs['From Min'].default_value = 0.42
    rfall.inputs['From Max'].default_value = 0.50
    rfall.inputs['To Min'].default_value = 1.0
    rfall.inputs['To Max'].default_value = 0.0
    rfall.clamp = True
    nt.links.new(rad.outputs['Value'], rfall.inputs['Value'])

    # --- fractal break-up. Real smoke is detailed at every scale: a billow the
    # size of a fist made of filaments a hair wide. Density that follows the
    # picture through smooth falloffs has only ONE scale of structure, which is
    # what makes it read as airbrush rather than as smoke. Two extra octaves --
    # one coarse for billowing, one fine for filaments -- modulate the density
    # so it tears and thins the way a real plume does.
    billow = nt.nodes.new('ShaderNodeTexNoise')
    billow.noise_dimensions = '3D'
    billow.inputs['Scale'].default_value = 4.5
    billow.inputs['Detail'].default_value = 6.0
    billow.inputs['Roughness'].default_value = 0.68
    bmap = nt.nodes.new('ShaderNodeMapRange')
    bmap.inputs['To Min'].default_value = 0.55
    bmap.inputs['To Max'].default_value = 1.35

    fila = nt.nodes.new('ShaderNodeTexNoise')
    fila.noise_dimensions = '3D'
    fila.inputs['Scale'].default_value = 15.0
    fila.inputs['Detail'].default_value = 9.0
    fila.inputs['Roughness'].default_value = 0.74
    fmap = nt.nodes.new('ShaderNodeMapRange')
    fmap.inputs['To Min'].default_value = 0.30
    fmap.inputs['To Max'].default_value = 1.55

    # driven off the rotating coords, so they travel with the loop
    nt.links.new(warp_map.outputs['Vector'], billow.inputs['Vector'])
    nt.links.new(warp_map.outputs['Vector'], fila.inputs['Vector'])
    nt.links.new(billow.outputs['Fac'], bmap.inputs['Value'])
    nt.links.new(fila.outputs['Fac'], fmap.inputs['Value'])
    grain = nt.nodes.new('ShaderNodeMath'); grain.operation = 'MULTIPLY'
    nt.links.new(bmap.outputs['Result'], grain.inputs[0])
    nt.links.new(fmap.outputs['Result'], grain.inputs[1])

    # --- density = picture * depth falloff * circle mask * grain * scale
    m1 = nt.nodes.new('ShaderNodeMath'); m1.operation = 'MULTIPLY'
    m2 = nt.nodes.new('ShaderNodeMath'); m2.operation = 'MULTIPLY'
    mg = nt.nodes.new('ShaderNodeMath'); mg.operation = 'MULTIPLY'
    m3 = nt.nodes.new('ShaderNodeMath'); m3.operation = 'MULTIPLY'
    m3.inputs[1].default_value = A.density
    nt.links.new(lum.outputs['Val'], m1.inputs[0])
    nt.links.new(dfall.outputs['Result'], m1.inputs[1])
    nt.links.new(m1.outputs['Value'], m2.inputs[0])
    nt.links.new(rfall.outputs['Result'], m2.inputs[1])
    nt.links.new(m2.outputs['Value'], mg.inputs[0])
    nt.links.new(grain.outputs['Value'], mg.inputs[1])
    nt.links.new(mg.outputs['Value'], m3.inputs[0])
    nt.links.new(m3.outputs['Value'], vol.inputs['Density'])

    # --- colour: the picture drives the glow, so the neon survives
    setv(vol, 'Emission Strength', A.glow)
    setv(vol, 'Color', (0.06, 0.07, 0.10, 1))    # cool scatter in the thick parts
    setv(vol, 'Anisotropy', 0.32)                # forward scatter, like real smoke
    nt.links.new(img.outputs['Color'], vol.inputs['Emission Color'])
    nt.links.new(vol.outputs['Volume'], out.inputs['Volume'])
    box.data.materials.append(m)

    # --- drift: walk the noise field around a small circle.
    #
    # A circle returns to its start, so the loop closes exactly -- but unlike
    # spinning the field a whole turn, the distance travelled is set by the
    # radius rather than by the size of the box. Rotating swept the scale-15
    # filaments past the lens fast enough to boil; a 0.14-radius orbit moves
    # them about two feature-widths a second, which reads as smoke turning over
    # in still air. The picture itself never moves, so the hands hold their
    # shape while the smoke inside them lives.
    if LOOP > 1:
        loc = warp_map.inputs['Location']
        STEPS = 24
        for i in range(STEPS + 1):
            th = TAU * i / STEPS
            frame = 1 + (LOOP * i) / STEPS
            loc.default_value[0] = A.drift * math.cos(th)
            loc.default_value[1] = A.drift * math.sin(th) * 0.6   # less in depth
            loc.default_value[2] = A.drift * math.sin(th)
            for idx in (0, 1, 2):
                loc.keyframe_insert('default_value', index=idx, frame=frame)
        for fc in m.node_tree.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = 'BEZIER'      # a polygon would tick per key
            fc.extrapolation = 'LINEAR'

        # --- swing: turn the whole slab through a full sine cycle.
        #
        # Drifting the noise can only ever shimmer, because the handshake comes
        # from a static picture -- warping it hard enough to visibly flow is
        # what dissolved the hands earlier. Turning the volume instead moves the
        # SHAPE without touching it: the slab has real depth, so a few degrees
        # of yaw parallaxes its near wisps against its far ones and the smoke
        # reads as a solid thing in space. A whole sine cycle returns to its
        # start in both position and velocity, so the loop stays seamless.
        for i in range(STEPS + 1):
            th = TAU * i / STEPS
            frame = 1 + (LOOP * i) / STEPS
            box.rotation_euler = (A.swing * 0.30 * math.sin(th + 1.2),
                                  0.0,
                                  A.swing * math.sin(th))
            box.keyframe_insert('rotation_euler', frame=frame)
        for fc in box.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = 'BEZIER'
            fc.extrapolation = 'LINEAR'
    return box


# -------------------------------------------------------------------- render

def main():
    if not os.path.isfile(A.src):
        raise SystemExit('no such image: ' + A.src)
    scene, dev = configure()
    black_world()
    backdrop()
    smoke(scene)
    camera(scene, radius=1.0)

    # --still wins over --frames. You need both together to preview one frame of
    # the animated version -- the drift keys only exist when a loop length is
    # set -- so if --frames took precedence here, asking for a single test frame
    # would quietly render the whole sequence instead.
    if A.still:
        scene.frame_set(A.still)
        out = os.path.join(ROOT, 'assets', '3d', A.name + '-still.png')
        scene.render.filepath = out
        print('[smoke-orb] %s %dpx frame %d on %s' % (A.name, A.size, A.still, dev))
        bpy.ops.render.render(write_still=True)
    elif LOOP > 1:
        out = os.path.join(ROOT, 'assets', '3d', 'frames', A.name) + os.sep
        scene.render.filepath = out
        print('[smoke-orb] %s %dpx x%d on %s' % (A.name, A.size, LOOP, dev))
        bpy.ops.render.render(animation=True)
    else:
        out = os.path.join(ROOT, 'assets', '3d', A.name + '-still.png')
        scene.render.filepath = out
        print('[smoke-orb] %s %dpx still on %s' % (A.name, A.size, dev))
        bpy.ops.render.render(write_still=True)


main()
