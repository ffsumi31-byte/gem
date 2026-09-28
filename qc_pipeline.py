import json
import os
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List, Optional

class QCPassResult(BaseModel):
    pass_name: str
    passed: bool
    score: float = Field(..., ge=0.0, le=10.0, description="Quality score from 0.0 to 10.0")
    detected_issues: List[str]
    corrective_actions: List[str]

class OverallQCReport(BaseModel):
    is_fully_validated: bool
    triangle_count_verified: bool
    pass_results: List[QCPassResult]
    required_regeneration_directives: Optional[str] = None

class RobloxQualityController:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.model_name = "gemini-2.5-flash"

    def execute_pass_1_semantics(self, prompt: str, ref_img_path: Optional[str], renders: dict) -> QCPassResult:
        contents = [
            "You are a Senior 3D Character & Prop Artist inspecting an AI-generated model for Roblox.",
            f"ORIGINAL USER PROMPT: '{prompt}'",
            "INSPECTION TASK - PASS 1 (Semantic & Proportions):",
            "1. Do the silhouette and proportions strictly reflect the prompt and reference?",
            "2. Are any major parts, appendages, or iconic components missing or warped?",
            "Score from 0.0 to 10.0. Pass requires >= 8.0.",
            types.Part.from_bytes(data=open(renders['iso_3_4'], "rb").read(), mime_type="image/png"),
            types.Part.from_bytes(data=open(renders['front'], "rb").read(), mime_type="image/png"),
        ]
        if ref_img_path and os.path.exists(ref_img_path):
            contents.append("REFERENCE IMAGE:")
            contents.append(types.Part.from_bytes(data=open(ref_img_path, "rb").read(), mime_type="image/png"))

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=QCPassResult,
                temperature=0.1
            )
        )
        return QCPassResult.model_validate_json(response.text)

    def execute_pass_2_geometry(self, renders: dict) -> QCPassResult:
        contents = [
            "INSPECTION TASK - PASS 2 (Geometric & Topological Health):",
            "Inspect the shaded renders and the DIAGNOSTIC WIREFRAME render.",
            "1. Are there disconnected, floating loose vertices or parts?",
            "2. Are there degenerate triangles, extreme polygon clustering, or self-clipping geometry?",
            "3. Is the mesh clean, manifold, and suitable for the Roblox physics engine?",
            "Score from 0.0 to 10.0. Pass requires >= 8.0.",
            types.Part.from_bytes(data=open(renders['wireframe'], "rb").read(), mime_type="image/png"),
            types.Part.from_bytes(data=open(renders['rear'], "rb").read(), mime_type="image/png"),
        ]
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=QCPassResult,
                temperature=0.1
            )
        )
        return QCPassResult.model_validate_json(response.text)

    def execute_pass_3_textures(self, renders: dict, material_style: str) -> QCPassResult:
        contents = [
            f"INSPECTION TASK - PASS 3 (Textures, UVs & Shading for Roblox SurfaceAppearance):",
            f"TARGET MATERIAL STYLE: {material_style}",
            "1. Is there noticeable UV seam tearing, pixel stretching, or texture distortion?",
            "2. Does the normal map shading look convex where it should be convex? (Roblox expects OpenGL +Y normal orientation).",
            "3. Are the material values convincing and free of diffuse bake artifacts?",
            "Score from 0.0 to 10.0. Pass requires >= 8.0.",
            types.Part.from_bytes(data=open(renders['iso_3_4'], "rb").read(), mime_type="image/png"),
            types.Part.from_bytes(data=open(renders['side_right'], "rb").read(), mime_type="image/png"),
        ]
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=QCPassResult,
                temperature=0.1
            )
        )
        return QCPassResult.model_validate_json(response.text)

    def evaluate_model(self, prompt: str, ref_img: Optional[str], renders: dict, actual_triangles: int, max_limit: int, material_style: str) -> OverallQCReport:
        p1 = self.execute_pass_1_semantics(prompt, ref_img, renders)
        p2 = self.execute_pass_2_geometry(renders)
        p3 = self.execute_pass_3_textures(renders, material_style)

        tri_verified = actual_triangles <= max_limit
        all_passed = p1.passed and p2.passed and p3.passed and tri_verified

        directives = []
        if not tri_verified:
            directives.append(f"Model exceeds triangle budget: {actual_triangles} > {max_limit}.")
        if not p1.passed:
            directives.extend(p1.corrective_actions)
        if not p2.passed:
            directives.extend(p2.corrective_actions)
        if not p3.passed:
            directives.extend(p3.corrective_actions)

        return OverallQCReport(
            is_fully_validated=all_passed,
            triangle_count_verified=tri_verified,
            pass_results=[p1, p2, p3],
            required_regeneration_directives=" | ".join(directives) if directives else None
        )
