"""Portrait (9:16) variant of glass_icon.blend for the vertical cut. Same animation and timing; the frame is
1080x1920 (sensor fit AUTO keeps the icon the same size against the short side), and the camera pulls back
while the release-cover ring is up so the ring stays in frame."""
import bpy, math, os
HERE = os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, "glass_icon.blend"))
sc = bpy.context.scene
sc.render.resolution_x, sc.render.resolution_y = 1080, 1920
cam = bpy.data.objects["Cam"]
from bpy_extras import anim_utils
cb = anim_utils.action_get_channelbag_for_slot(cam.animation_data.action, cam.animation_data.action_slot)
ycurve = [c for c in cb.fcurves if c.data_path == "location" and c.array_index == 1][0]
F = lambda t: round(t * 60)
# keep the intro close-up, but back off during bars 6-8 so the orbit ring reads in a tall frame
for kp in ycurve.keyframe_points:
    t = kp.co.x / 60
    if 12.0 < t < 16.7:
        kp.co.y -= 2.6; kp.handle_left.y -= 2.6; kp.handle_right.y -= 2.6
# the ring turns upright in portrait (orbits top-to-bottom instead of side-to-side)
orbit = bpy.data.objects["Orbit"]
orbit.rotation_euler[1] = math.radians(82)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "glass_icon_v.blend"))
print("saved portrait")
