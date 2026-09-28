from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
import os
import shutil
from typing import Optional
from config import SystemConfig
from orchestrator import generate_roblox_asset_pipeline

app = FastAPI(title="Roblox AI 3D Engine API", version="1.0.0")

@app.get("/")
def health_check():
    return {"status": "online", "engine": "Blender Headless + Gemini QC"}

@app.post("/generate")
async def generate_asset(
    prompt: str = Form(...),
    gemini_api_key: str = Form(...),
    max_poly_limit: int = Form(10000),
    texture_res: int = Form(1024),
    material_style: str = Form("PBR Realistic"),
    ref_file: Optional[UploadFile] = File(None)
):
    workspace = f"/tmp/roblox_job_{os.getpid()}"
    os.makedirs(workspace, exist_ok=True)
    
    ref_path = None
    if ref_file:
        ref_path = os.path.join(workspace, ref_file.filename)
        with open(ref_path, "wb") as buffer:
            shutil.copyfileobj(ref_file.file, buffer)

    cfg = SystemConfig(
        gemini_api_key=gemini_api_key,
        max_poly_limit=max_poly_limit,
        target_texture_res=texture_res,
        material_style=material_style
    )

    result = generate_roblox_asset_pipeline(prompt, ref_path, cfg, workspace)
    return {
        "status": "completed",
        "is_validated": result["is_validated"],
        "triangle_count": result["final_triangle_count"],
        "qc_report": result["qc_report"],
        "download_url": f"/download?workspace={workspace}"
    }

@app.get("/download")
def download_bundle(workspace: str):
    zip_path = os.path.join(workspace, "Roblox_Package.zip")
    if not os.path.exists(zip_path):
        raise HTTPException(status_code=404, detail="File bundle not found")
    return FileResponse(zip_path, filename="Roblox_Asset_Bundle.zip", media_type="application/zip")
