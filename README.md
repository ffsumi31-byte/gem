# Roblox AI 3D Studio - Turnkey Deployment Package

An end-to-end automated 3D modeling and optimization pipeline purpose-built for Roblox Studio `MeshPart` and `SurfaceAppearance` workflows.

---

## Key Features
- **Strict Triangle Budget Enforcement**: Guarantees geometry is decimated $\le 10,000$ triangles (customizable down to 500) using Quadric Error decimation with volume preservation.
- **SurfaceAppearance PBR Baking**: Headless Blender bakes Tangent OpenGL Normal Maps (+Y Up), BaseColor Albedo, Roughness, and Metalness maps.
- **Automated 6-View Studio Rig**: Automatically calculates bounding box extents and renders 5 photographic viewpoints + 1 diagnostic wireframe pass without manual lighting setup.
- **3-Pass Multimodal QC (Gemini Vision)**:
  - *Pass 1*: Proportions & Semantic Fidelity.
  - *Pass 2*: Non-manifold geometry, loose vertices, self-intersections.
  - *Pass 3*: UV stretching and OpenGL normal orientation.
  - *Integrity Rule*: Never flags assets as 'Passed' unless all three passes strictly succeed.
- **Zero-Friction Roblox Export**: Pre-scaled Y-up, -Z forward FBX with embedded vertex tangents ready for Roblox Studio's 3D Importer.

---

## 1-Click Deploy to Render.com

1. Push this repository to GitHub or GitLab.
2. In [Render Dashboard](https://dashboard.render.com/), click **New +** -> **Blueprint**.
3. Select this repository. Render will automatically detect `render.yaml` and `Dockerfile`.
4. Add your `GEMINI_API_KEY` under Environment Variables.
5. Click **Apply Blueprint**. Render will build the Docker container with Blender headless and spin up the Streamlit UI.

---

## Running Locally with Docker

```bash
docker build -t roblox-3d-studio .
docker run -p 8501:8501 -e GEMINI_API_KEY="your-api-key" roblox-3d-studio
```
Open `http://localhost:8501` in your browser.

---

## Running Locally with Python & Blender

Ensure Blender 3.6+ is installed and on your system `$PATH`.

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## Importing into Roblox Studio

1. In Roblox Studio, open **Asset Manager** -> **Bulk Import** (or click the **3D Importer** tool).
2. Select `Roblox_Asset_Final.fbx`.
3. In the 3D Importer settings, confirm **Import Tangents** is checked.
4. Insert a `SurfaceAppearance` object inside the generated `MeshPart`.
5. Map the 4 baked textures from the `Textures/` directory:
   - `ColorMap` -> `Model_ColorMap.png`
   - `NormalMap` -> `Model_NormalMap.png` (OpenGL +Y standard)
   - `RoughnessMap` -> `Model_RoughnessMap.png`
   - `MetalnessMap` -> `Model_MetalnessMap.png`
