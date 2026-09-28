import bpy
import math
import mathutils
import os
import sys
import argparse

def parse_args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []
    parser = argparse.ArgumentParser(description="Automated Studio Renderer")
    parser.add_argument("--fbx", required=True, help="Input FBX path")
    parser.add_argument("--out_dir", required=True, help="Output directory for renders")
    return parser.parse_args(argv)

def render_studio_views(fbx_path: str, output_folder: str):
    os.makedirs(output_folder, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=fbx_path)

    mesh_objs = [o for o in bpy.data.objects if o.type == 'MESH']
    if not mesh_objs:
        raise RuntimeError("No mesh object found to render!")
    obj = mesh_objs[0]
    bpy.context.view_layer.objects.active = obj

    bbox_corners = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
    center = sum(bbox_corners, mathutils.Vector((0, 0, 0))) / 8.0
    dims = obj.dimensions
    max_dim = max(dims.x, dims.y, dims.z, 0.5)

    # 3-Point Lighting Rig
    key_light = bpy.data.lights.new(name="KeyLight", type='AREA')
    key_light.energy = 600 * (max_dim ** 2)
    key_light.size = max_dim * 2
    key_obj = bpy.data.objects.new("KeyLight", key_light)
    key_obj.location = center + mathutils.Vector((max_dim * 2, -max_dim * 2.5, max_dim * 2))
    bpy.context.collection.objects.link(key_obj)

    fill_light = bpy.data.lights.new(name="FillLight", type='AREA')
    fill_light.energy = 300 * (max_dim ** 2)
    fill_light.size = max_dim * 3
    fill_obj = bpy.data.objects.new("FillLight", fill_light)
    fill_obj.location = center + mathutils.Vector((-max_dim * 2.5, -max_dim * 2, max_dim))
    bpy.context.collection.objects.link(fill_obj)

    rim_light = bpy.data.lights.new(name="RimLight", type='SPOT')
    rim_light.energy = 800 * (max_dim ** 2)
    rim_obj = bpy.data.objects.new("RimLight", rim_light)
    rim_obj.location = center + mathutils.Vector((0, max_dim * 3, max_dim * 2.5))
    bpy.context.collection.objects.link(rim_obj)

    # Setup Camera
    cam_data = bpy.data.cameras.new("InspectorCam")
    cam_data.lens = 65
    cam_obj = bpy.data.objects.new("InspectorCam", cam_data)
    bpy.context.collection.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj

    track = cam_obj.constraints.new(type='TRACK_TO')
    track.target = obj
    track.track_axis = 'TRACK_NEGATIVE_Z'
    track.up_axis = 'UP_Y'

    dist = max_dim * 2.6
    angles = {
        "front": (0, -dist, max_dim * 0.2),
        "iso_3_4": (dist * 0.7, -dist * 0.7, max_dim * 0.5),
        "side_right": (dist, 0, max_dim * 0.2),
        "rear": (0, dist, max_dim * 0.2),
        "top": (0.01, -0.01, dist * 1.3),
    }

    bpy.context.scene.render.resolution_x = 1024
    bpy.context.scene.render.resolution_y = 1024
    bpy.context.scene.render.image_settings.file_format = 'PNG'

    render_paths = {}
    for name, loc in angles.items():
        cam_obj.location = center + mathutils.Vector(loc)
        filepath = os.path.join(output_folder, f"render_{name}.png")
        bpy.context.scene.render.filepath = filepath
        bpy.ops.render.render(write_still=True)
        render_paths[name] = filepath

    # Render Diagnostic Wireframe pass
    wire_mod = obj.modifiers.new(name="DiagnosticWire", type='WIREFRAME')
    wire_mod.thickness = 0.005 * max_dim
    wire_path = os.path.join(output_folder, "render_wireframe.png")
    bpy.context.scene.render.filepath = wire_path
    bpy.ops.render.render(write_still=True)
    render_paths["wireframe"] = wire_path
    obj.modifiers.remove(wire_mod)

    print("[RENDER_COMPLETE] All 6 diagnostic camera angles saved.")
    return render_paths

if __name__ == "__main__":
    args = parse_args()
    render_studio_views(args.fbx, args.out_dir)
