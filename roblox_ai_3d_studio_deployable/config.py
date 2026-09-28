import os
from pydantic import BaseModel, Field
from typing import Optional

class SystemConfig(BaseModel):
    gemini_api_key: str = Field(..., description="Google Gemini Vision API key")
    mesh_gen_api_key: Optional[str] = Field(None, description="Backend 3D generation API key")
    
    # Generation & Roblox Constraints
    max_poly_limit: int = 10000
    target_texture_res: int = 1024  # Roblox SurfaceAppearance max is 1024
    preserve_volume: bool = True
    material_style: str = "PBR Realistic"  # PBR Realistic, Stylized, Plastic, Metallic
    max_qc_iterations: int = 3
    qc_pass_threshold: float = 8.0

    @classmethod
    def from_env(cls) -> "SystemConfig":
        return cls(
            gemini_api_key=os.environ.get("GEMINI_API_KEY", ""),
            mesh_gen_api_key=os.environ.get("MESH_GEN_API_KEY", ""),
            max_poly_limit=int(os.environ.get("MAX_POLY_LIMIT", 10000)),
            target_texture_res=int(os.environ.get("TEXTURE_RES", 1024)),
            material_style=os.environ.get("MATERIAL_STYLE", "PBR Realistic")
        )
