import bpy, sys
argv = sys.argv[sys.argv.index("--") + 1:]
out, a, b = argv[0], int(argv[1]), int(argv[2])
sc = bpy.context.scene
sc.cycles.samples = int(argv[3]) if len(argv) > 3 else 32
sc.frame_start, sc.frame_end = a, b
sc.render.filepath = out + "/f"
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGB'; sc.render.image_settings.color_depth = '8'
sc.render.use_overwrite = False; sc.render.use_placeholder = True
bpy.ops.render.render(animation=True)
