import os
import subprocess
import shutil
import zipfile
from typing import Dict, Any, Optional
from config import SystemConfig
from qc_pipeline import RobloxQualityController

def run_headless_blender_optimizer(input_raw: str, output_fbx: str, tex_dir: str, max_tris: int, res: int) -> int:
    cmd = [
        "blender", "-b", "--python", "roblox_optimizer.py", "--",
        "--input", input_raw,
        "--output_fbx", output_fbx,
        "--output_tex_dir", tex_dir,
        "--max_tris", str(max_tris),
        "--tex_res", str(res)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    final_tris = max_tris
    for line in result.stdout.splitlines():
        if "[OPTIMIZER_METRIC]" in line:
            try:
                final_tris = int(line.split(":")[-1].strip())
            except ValueError:
                pass
    return final_tris

def run_headless_studio_renderer(fbx_path: str, renders_dir: str) -> Dict[str, str]:
    cmd = [
        "blender", "-b", "--python", "studio_renderer.py", "--",
        "--fbx", fbx_path,
        "--out_dir", renders_dir
    ]
    subprocess.run(cmd, check=True)
    return {
        "iso_3_4": os.path.join(renders_dir, "render_iso_3_4.png"),
        "front": os.path.join(renders_dir, "render_front.png"),
        "side_right": os.path.join(renders_dir, "render_side_right.png"),
        "rear": os.path.join(renders_dir, "render_rear.png"),
        "top": os.path.join(renders_dir, "render_top.png"),
        "wireframe": os.path.join(renders_dir, "render_wireframe.png")
    }

def generate_mock_starter_obj(target_obj_path: str):
    """Fallback generator for local demo testing when backend 3D API is not configured."""
    with open(target_obj_path, "w") as f:
        f.write("""# Demo High-Poly Capsule/Helmet Mesh
v -1.0 -1.0  1.0
v  1.0 -1.0  1.0
v -1.0  1.0  1.0
v  1.0  1.0  1.0
v -1.0  1.0 -1.0
v  1.0  1.0 -1.0
v -1.0 -1.0 -1.0
v  1.0 -1.0 -1.0
vt 0.0 0.0
vt 1.0 0.0
vt 1.0 1.0
vt 0.0 1.0
vn 0.0 0.0 1.0
vn 0.0 0.0 -1.0
vn 0.0 1.0 0.0
vn 0.0 -1.0 0.0
vn 1.0 0.0 0.0
vn -1.0 0.0 0.0
f 1/1/1 2/2/1 4/3/1
f 1/1/1 4/3/1 3/4/1
f 3/1/3 4/2/3 6/3/3
f 3/1/3 6/3/3 5/4/3
f 7/1/2 6/2/2 8/3/2
f 7/1/2 5/4/2 6/2/2
f 2/1/4 8/2/4 7/3/4
f 2/1/4 7/3/4 1/4/4
f 2/1/5 6/2/5 4/3/5
f 2/1/5 8/4/5 6/2/5
f 7/1/6 3/2/6 5/3/6
f 7/1/6 1/4/6 3/2/6
""")

def generate_roblox_asset_pipeline(prompt: str, ref_image: Optional[str], config: SystemConfig, workspace: str) -> Dict[str, Any]:
    os.makedirs(workspace, exist_ok=True)
    qc_agent = RobloxQualityController(api_key=config.gemini_api_key)
    
    raw_mesh_path = os.path.join(workspace, "raw_dense_mesh.obj")
    output_fbx = os.path.join(workspace, "Roblox_Asset_Final.fbx")
    tex_dir = os.path.join(workspace, "Textures")
    renders_dir = os.path.join(workspace, "QC_Renders")
    
    # Generate initial high-poly mesh (API or local seed)
    if not os.path.exists(raw_mesh_path):
        generate_mock_starter_obj(raw_mesh_path)

    attempt = 0
    validated = False
    final_report = None
    actual_tris = 0
    current_prompt = prompt
    renders = {}

    while attempt < config.max_qc_iterations and not validated:
        attempt += 1
        print(f"[PIPELINE] Execution Pass {attempt}/{config.max_qc_iterations}...")

        # 1. Headless Blender decimation & PBR baking
        actual_tris = run_headless_blender_optimizer(
            raw_mesh_path, output_fbx, tex_dir, config.max_poly_limit, config.target_texture_res
        )

        # 2. Automated Studio 6-Angle Turntable Renders
        renders = run_headless_studio_renderer(output_fbx, renders_dir)

        # 3. 3-Pass QC Evaluation
        try:
            final_report = qc_agent.evaluate_model(
                prompt=current_prompt,
                ref_img=ref_image,
                renders=renders,
                actual_triangles=actual_tris,
                max_limit=config.max_poly_limit,
                material_style=config.material_style
            )
            validated = final_report.is_fully_validated
        except Exception as e:
            print(f"[PIPELINE] QC Engine Evaluation Note: {e}")
            # If API key is placeholder or network issue, maintain integrity: do not claim passed
            validated = False
            break

        if validated:
            break
        else:
            if final_report and final_report.required_regeneration_directives:
                current_prompt = f"{prompt}. Correcting issues: {final_report.required_regeneration_directives}"

    # Package export zip
    export_zip_path = os.path.join(workspace, "Roblox_Package.zip")
    with zipfile.ZipFile(export_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        if os.path.exists(output_fbx):
            zf.write(output_fbx, arcname="Roblox_Asset_Final.fbx")
        if os.path.exists(tex_dir):
            for t_file in os.listdir(tex_dir):
                zf.write(os.path.join(tex_dir, t_file), arcname=os.path.join("Textures", t_file))
        if os.path.exists(renders_dir):
            for r_file in os.listdir(renders_dir):
                zf.write(os.path.join(renders_dir, r_file), arcname=os.path.join("QC_Renders", r_file))

    return {
        "fbx_path": output_fbx,
        "export_zip_path": export_zip_path,
        "texture_directory": tex_dir,
        "final_triangle_count": actual_tris,
        "is_validated": validated,
        "qc_report": final_report.model_dump() if final_report else None,
        "preview_renders": renders
    }
