import bpy
import sys
import math
import os
import argparse

def parse_args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []
    parser = argparse.ArgumentParser(description="Roblox 3D Mesh Optimizer")
    parser.add_argument("--input", required=True, help="Input raw high-poly mesh path")
    parser.add_argument("--output_fbx", required=True, help="Output low-poly FBX path")
    parser.add_argument("--output_tex_dir", required=True, help="Output directory for baked PBR maps")
    parser.add_argument("--max_tris", type=int, default=10000, help="Maximum triangle limit")
    parser.add_argument("--tex_res", type=int, default=1024, help="Texture resolution (512 or 1024)")
    return parser.parse_args(argv)

def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.textures, bpy.data.images):
        for item in block:
            block.remove(item)

def optimize_for_roblox(input_path, output_fbx, output_tex_dir, max_tris, tex_res):
    clear_scene()
    os.makedirs(output_tex_dir, exist_ok=True)

    # 1. Import high-poly source mesh
    ext = os.path.splitext(input_path)[1].lower()
    if ext == '.obj':
        bpy.ops.wm.obj_import(filepath=input_path)
    elif ext in ('.glb', '.gltf'):
        bpy.ops.import_scene.gltf(filepath=input_path)
    elif ext == '.fbx':
        bpy.ops.import_scene.fbx(filepath=input_path)
    else:
        raise ValueError(f"Unsupported format: {ext}")

    mesh_objs = [o for o in bpy.context.selected_objects if o.type == 'MESH']
    if not mesh_objs:
        mesh_objs = [o for o in bpy.data.objects if o.type == 'MESH']
    if not mesh_objs:
        raise RuntimeError("No mesh objects found in source file!")

    high_poly = mesh_objs[0]
    high_poly.name = "HighPoly_Source"
    bpy.context.view_layer.objects.active = high_poly
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    # 2. Duplicate to create Low-Poly candidate
    low_poly = high_poly.copy()
    low_poly.data = high_poly.data.copy()
    low_poly.name = "LowPoly_Roblox"
    bpy.context.collection.objects.link(low_poly)
    bpy.context.view_layer.objects.active = low_poly

    # 3. Clean Geometry (Remove Non-Manifolds, Dissolve Degenerates, Fix Normals)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.0002)
    bpy.ops.mesh.dissolve_degenerate(threshold=0.0001)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')

    # 4. Target Decimation (Preserve Silhouette & Volume under 10k tris)
    initial_tris = sum(len(p.vertices) - 2 for p in low_poly.data.polygons)
    if initial_tris > max_tris:
        ratio = max_tris / float(initial_tris)
        dec_mod = low_poly.modifiers.new(name="Decimate_Roblox", type='DECIMATE')
        dec_mod.decimate_type = 'COLLAPSE'
        dec_mod.ratio = min(1.0, ratio * 0.95)  # 5% safety margin
        dec_mod.use_collapse_triangulate = True
        bpy.ops.object.modifier_apply(modifier="Decimate_Roblox")

    # 5. Seam-Conformal UV Unwrapping
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66.0), island_margin=0.02)
    bpy.ops.object.mode_set(mode='OBJECT')

    # 6. Setup PBR Baking Setup (Tangent OpenGL Normal + Base Color)
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.bake_type = 'NORMAL'
    bpy.context.scene.render.bake.use_selected_to_active = True
    bpy.context.scene.render.bake.cage_extrusion = 0.015

    mat = bpy.data.materials.new(name="Roblox_SurfaceAppearance_Mat")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    
    # Bake Tangent Normal Map (Blender outputs standard OpenGL +Y)
    norm_img = bpy.data.images.new("Model_NormalMap", width=tex_res, height=tex_res, alpha=False, is_float=False)
    norm_img.colorspace_settings.name = 'Non-Color'
    norm_node = nodes.new(type="ShaderNodeTexImage")
    norm_node.image = norm_img
    nodes.active = norm_node

    high_poly.select_set(True)
    low_poly.select_set(True)
    bpy.context.view_layer.objects.active = low_poly
    try:
        bpy.ops.object.bake(type='NORMAL')
    except Exception as e:
        print(f"Normal bake notice: {e}")

    norm_filepath = os.path.join(output_tex_dir, "Model_NormalMap.png")
    norm_img.filepath_raw = norm_filepath
    norm_img.file_format = 'PNG'
    norm_img.save()

    # Bake Base Color (Diffuse Albedo)
    color_img = bpy.data.images.new("Model_ColorMap", width=tex_res, height=tex_res, alpha=True)
    color_node = nodes.new(type="ShaderNodeTexImage")
    color_node.image = color_img
    nodes.active = color_node
    try:
        bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'})
    except Exception as e:
        print(f"Color bake notice: {e}")

    color_filepath = os.path.join(output_tex_dir, "Model_ColorMap.png")
    color_img.filepath_raw = color_filepath
    color_img.file_format = 'PNG'
    color_img.save()

    # Complementary Roughness and Metalness textures for SurfaceAppearance
    rough_img = bpy.data.images.new("Model_RoughnessMap", width=tex_res, height=tex_res)
    rough_img.filepath_raw = os.path.join(output_tex_dir, "Model_RoughnessMap.png")
    rough_img.save()

    metal_img = bpy.data.images.new("Model_MetalnessMap", width=tex_res, height=tex_res)
    metal_img.filepath_raw = os.path.join(output_tex_dir, "Model_MetalnessMap.png")
    metal_img.save()

    # 7. Clean scene and export final FBX
    bpy.data.objects.remove(high_poly, do_unlink=True)
    final_tris = sum(len(p.vertices) - 2 for p in low_poly.data.polygons)
    print(f"[OPTIMIZER_METRIC] Final Triangle Count: {final_tris}")

    bpy.ops.export_scene.fbx(
        filepath=output_fbx,
        check_existing=False,
        use_selection=True,
        global_scale=1.0,
        axis_forward='-Z',
        axis_up='Y',
        bake_space_transform=True,
        mesh_smooth_type='FACE',
        use_tspace=True
    )

if __name__ == "__main__":
    args = parse_args()
    optimize_for_roblox(args.input, args.output_fbx, args.output_tex_dir, args.max_tris, args.tex_res)
