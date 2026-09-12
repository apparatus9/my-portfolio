# Turn any rig in this folder into a .blend you can open and edit by hand.
#
#   blender -b -P tools/blender/to-blend.py -- <rig.py> <out.blend> [rig flags...]
#
# e.g.
#   blender -b -P tools/blender/to-blend.py -- tools/blender/word-orb.py \
#           blend/word.blend --word Ejay --hue acid
#
# The rigs build their scene and then immediately render it, which is what you
# want headless and not what you want here -- rendering a full frame just to
# throw it away can cost minutes. So the rig's source is read, its render call
# is swapped for a no-op, and the rest runs untouched: same geometry, same
# materials, same lights, same keyframes. Then the scene is saved.
#
# Everything the rig would have done to the scene has been done. Open the file
# and it is all there to poke at.

import bpy, sys, os

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
if len(argv) < 2:
    raise SystemExit('usage: -- <rig.py> <out.blend> [rig flags...]')

rig, out, rest = argv[0], argv[1], argv[2:]
rig = os.path.abspath(rig)
out = os.path.abspath(out)
os.makedirs(os.path.dirname(out), exist_ok=True)

src = open(rig, encoding='utf-8').read()
# the only edit: don't actually render
src = src.replace('bpy.ops.render.render(', '(lambda *a, **k: None)(')

# the rig parses its own flags out of sys.argv, so hand it a clean set
sys.argv = ['blender', '--'] + rest

exec(compile(src, rig, 'exec'), {'__name__': '__main__', '__file__': rig})

# Open in Rendered shading. This has to go through bpy.data.screens, not
# through the window manager: running headless there ARE no windows, so
# iterating wm.windows silently does nothing and the file opens in Solid --
# which shows the glass sphere as a grey ball with everything hidden inside it.
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type != 'VIEW_3D':
            continue
        for space in area.spaces:
            if space.type == 'VIEW_3D':
                space.shading.type = 'RENDERED'
                space.clip_end = 100.0

bpy.ops.wm.save_as_mainfile(filepath=out)
print('[to-blend] wrote ' + out)
