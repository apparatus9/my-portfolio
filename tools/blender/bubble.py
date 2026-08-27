# Wraps a flat clip in a real Cycles soap bubble.
#
#   blender -b -P tools/blender/bubble.py -- --src <dir of ####.png> --frames 240
#
# The source clip already shows phones in a bubble, but that bubble is painted
# on by the generator: it is clipped off at the top and bottom of frame, and its
# gloss does not respond to anything. This rebuilds the shell for real -- the
# rim reflection is raytraced from actual lights, and the colour banding is
# physical thin-film interference, not a gradient someone chose.
#
# The clip goes in as an emissive disc at the centre of the sphere. The shell
# over it is Transparent mixed into an iridescent specular lobe by Fresnel,
# which is what a soap film actually is: nearly invisible face-on, a bright
# coloured mirror at grazing angles. Modelling it as glass instead would refract
# the phones into unreadable mush -- a real bubble wall is far too thin to bend
# light that way.

import sys, os, math, argparse
import bpy
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument('--src', required=True)            # dir holding 0000.png ...
ap.add_argument('--name', default='world-phones')
ap.add_argument('--size', type=int, default=512)
ap.add_argument('--frames', type=int, default=240)
ap.add_argument('--samples', type=int, default=96)
ap.add_argument('--fill', type=float, default=0.92)   # disc size vs bubble
ap.add_argument('--still', type=int, default=0)       # render just this frame
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
    c.max_bounces = 16
    c.transmission_bounces = 12
    c.transparent_max_bounces = 24     # the shell is transparent: needs headroom
    c.glossy_bounces = 6
    c.blur_glossy = 0.5

    r = scene.render
    r.resolution_x = r.resolution_y = A.size
    r.resolution_percentage = 100
    r.film_transparent = True
    r.image_settings.file_format = 'PNG'
    r.image_settings.color_mode = 'RGBA'
    r.image_settings.compression = 20

    scene.frame_start = 1
    scene.frame_end = LOOP

    # Standard, not AgX: the clip is already graded and the phones are neutral
    # metal. AgX would desaturate the iridescence to chalk.
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
    """A bubble is almost entirely reflection, so the lights ARE the look. Long
    thin strips, because the rim shows each source's actual shape."""
    # Big and dim beats small and hot. Blown-out sources reflect as hard white
    # rectangles sitting on top of the phones like stickers; widening them and
    # pulling the power down turns the same reflections into soft sweeps.
    area(scene, 'key',   (-3.2, -2.6,  3.4), 8.0, 420, (1.0, 0.97, 0.93))
    area(scene, 'rim',   ( 2.4,  3.6,  2.0), 7.0, 650, (0.95, 0.98, 1.0))
    area(scene, 'under', (-1.4, -1.8, -3.2), 5.0, 240, (1.0, 0.92, 0.98))


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


def setv(node, key, value):
    if key in node.inputs:
        node.inputs[key].default_value = value
        return True
    return False


# --------------------------------------------------------------- the clip disc

def content(scene, radius):
    """The source clip as an emissive disc at the centre of the bubble.

    Emissive rather than lit: the clip is already fully shaded, so relighting it
    would double up the shading it was rendered with."""
    first = sorted(f for f in os.listdir(A.src) if f.endswith('.png'))[0]
    path = os.path.join(A.src, first)

    bpy.ops.mesh.primitive_plane_add(size=2 * radius)
    ob = bpy.context.active_object
    ob.name = 'clip'
    ob.rotation_euler = (math.pi / 2, 0, 0)      # stand it up to face the lens

    m = bpy.data.materials.new('clip')
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')

    img = nt.nodes.new('ShaderNodeTexImage')
    img.image = bpy.data.images.load(path)
    img.image.source = 'SEQUENCE'
    img.interpolation = 'Cubic'
    iu = img.image_user
    iu.frame_duration = LOOP
    iu.frame_start = 1
    iu.frame_offset = -1        # scene frame 1 -> 0000.png
    iu.use_cyclic = True
    iu.use_auto_refresh = True

    emit = nt.nodes.new('ShaderNodeEmission')
    emit.inputs['Strength'].default_value = 1.0
    clear = nt.nodes.new('ShaderNodeBsdfTransparent')
    mix = nt.nodes.new('ShaderNodeMixShader')

    nt.links.new(img.outputs['Color'], emit.inputs['Color'])
    nt.links.new(img.outputs['Alpha'], mix.inputs['Fac'])   # circular cut
    nt.links.new(clear.outputs['BSDF'], mix.inputs[1])
    nt.links.new(emit.outputs['Emission'], mix.inputs[2])
    nt.links.new(mix.outputs['Shader'], out.inputs['Surface'])
    ob.data.materials.append(m)

    # It lights nothing and casts nothing -- it is a picture, not an object.
    ob.visible_shadow = False
    ob.visible_diffuse = False
    return ob


# ------------------------------------------------------------------ the shell

def shell(scene, radius=1.0):
    """Transparent, mixed into an iridescent specular lobe by Fresnel.

    Thin Film Thickness is a real nanometre figure here: interference across a
    200-750nm film is what produces the sweep from magenta through teal, so the
    banding follows the curvature of the sphere the way it does on real soap
    instead of being a ramp painted around the edge."""
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=6, radius=radius)
    ob = bpy.context.active_object
    ob.name = 'shell'
    bpy.ops.object.shade_smooth()

    m = bpy.data.materials.new('bubble')
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')

    # Metallic white, NOT black dielectric. A black base colour leaves a pure
    # black diffuse lobe under the specular, and the Fresnel mix fades that in
    # around the rim before the reflection takes over -- which renders the
    # bubble with a black ring around it. A soap film has no diffuse term at
    # all, so drive it as a mirror and let thin film colour the reflection.
    film = nt.nodes.new('ShaderNodeBsdfPrincipled')
    setv(film, 'Base Color', (1, 1, 1, 1))
    setv(film, 'Metallic', 1.0)
    setv(film, 'Roughness', 0.09)     # a touch of spread, or the strips are razors
    setv(film, 'IOR', 1.33)
    setv(film, 'Transmission Weight', 0.0)
    setv(film, 'Thin Film IOR', 1.52)

    # Thickness drifts over the surface, and drains downward under gravity the
    # way a real film thins at the top. That vertical bias is what stops the
    # banding reading as a decal.
    coord = nt.nodes.new('ShaderNodeTexCoord')
    noise = nt.nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = 3.0
    noise.inputs['Detail'].default_value = 4.0
    noise.inputs['Roughness'].default_value = 0.5
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    drain = nt.nodes.new('ShaderNodeMapRange')       # -1..1 height -> thickness
    drain.inputs['From Min'].default_value = -1.0
    drain.inputs['From Max'].default_value = 1.0
    drain.inputs['To Min'].default_value = 1.0
    drain.inputs['To Max'].default_value = 0.35
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
    fres.inputs['IOR'].default_value = 1.38       # wider coloured band into the rim
    mix = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(fres.outputs['Fac'], mix.inputs['Fac'])
    nt.links.new(clear.outputs['BSDF'], mix.inputs[1])
    nt.links.new(film.outputs['BSDF'], mix.inputs[2])
    nt.links.new(mix.outputs['Shader'], out.inputs['Surface'])
    ob.data.materials.append(m)

    ob.visible_shadow = False      # a soap film does not shade what is inside it
    return ob


# -------------------------------------------------------------------- render

def main():
    if not os.path.isdir(A.src):
        raise SystemExit('no such source dir: ' + A.src)
    scene, dev = configure()
    # Bright all round, on purpose. The rim of a bubble is almost pure
    # reflection, so a dark environment renders as a black ring and the
    # interference colours have no light to tint. Thin film cannot invent
    # brightness -- it can only colour what the film reflects.
    world_gradient(top=(1.0, 1.0, 1.0), bottom=(0.72, 0.76, 0.90), strength=1.5)
    lights(scene)
    content(scene, radius=A.fill)
    shell(scene, radius=1.0)
    camera(scene, radius=1.0)

    if A.still:
        scene.frame_set(A.still)
        out = os.path.join(ROOT, 'assets', '3d', A.name + '-still.png')
        scene.render.filepath = out
        print('[bubble] %s frame %d on %s' % (A.name, A.still, dev))
        bpy.ops.render.render(write_still=True)
    else:
        out = os.path.join(ROOT, 'assets', '3d', 'frames', A.name) + os.sep
        scene.render.filepath = out
        print('[bubble] %s %dpx x%d on %s -> %s' % (A.name, A.size, LOOP, dev, out))
        bpy.ops.render.render(animation=True)


main()
