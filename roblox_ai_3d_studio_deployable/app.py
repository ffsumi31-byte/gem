import streamlit as st
import os
from config import SystemConfig
from orchestrator import generate_roblox_asset_pipeline

st.set_page_config(page_title="RobloxCraft AI 3D Studio", layout="wide", page_icon="🎮")

st.sidebar.title("Configuration & API Vault")
gemini_key = st.sidebar.text_input("Gemini API Key", type="password", value=os.environ.get("GEMINI_API_KEY", ""))
poly_limit = st.sidebar.slider("Polygon / Triangle Limit", min_value=500, max_value=20000, value=10000, step=500)
texture_res = st.sidebar.selectbox("Texture Resolution", options=[512, 1024], index=1)
material_style = st.sidebar.selectbox("Material Style", options=["PBR Realistic", "Roblox SmoothPlastic", "Stylized / Handpainted", "Metallic"])

st.title("Roblox AI 3D Asset Generator")
st.caption("Game-Ready, Retopologized, SurfaceAppearance-Compliant FBX Generator for Roblox Studio")

col1, col2 = st.columns([1, 1])

with col1:
    prompt = st.text_area("Asset Description", placeholder="e.g., A tactical cyberpunk helmet with a glowing cyan visor, carbon fiber plating, and side antenna.")
    ref_image = st.file_uploader("Reference Image (Optional)", type=["png", "jpg", "jpeg", "webp"])
    generate_btn = st.button("Generate & Optimize for Roblox", type="primary", use_container_width=True)

if generate_btn:
    if not gemini_key:
        st.error("Please enter a valid Gemini API Key in the sidebar.")
    elif not prompt:
        st.error("Please enter an asset description prompt.")
    else:
        with st.spinner("Processing asset: Decimating to <= 10k tris, baking PBR maps, and running 3-Pass QC..."):
            cfg = SystemConfig(
                gemini_api_key=gemini_key,
                max_poly_limit=poly_limit,
                target_texture_res=texture_res,
                material_style=material_style
            )
            workspace = "/tmp/roblox_build_cache" if os.path.exists("/tmp") else "./build_cache"
            os.makedirs(workspace, exist_ok=True)
            
            ref_path = None
            if ref_image:
                ref_path = os.path.join(workspace, "ref_input.png")
                with open(ref_path, "wb") as f:
                    f.write(ref_image.getbuffer())

            results = generate_roblox_asset_pipeline(prompt, ref_path, cfg, workspace)

        with col2:
            st.subheader("Asset Validation & Metrics")
            if results["is_validated"]:
                st.success("MODEL PASSED ALL 3 QUALITY CONTROL PASSES")
            else:
                st.error("MODEL FAILED VALIDATION (See QC Audit Details)")

            m1, m2, m3 = st.columns(3)
            m1.metric("Triangle Count", f"{results['final_triangle_count']} / {poly_limit}")
            m2.metric("Texture Resolution", f"{texture_res}x{texture_res}")
            m3.metric("Normal Map Format", "OpenGL (+Y)")

            st.subheader("Automated Studio Inspection Views")
            r1, r2 = st.columns(2)
            renders = results["preview_renders"]
            if os.path.exists(renders.get("iso_3_4", "")):
                r1.image(renders["iso_3_4"], caption="3/4 Isometric Beauty")
            if os.path.exists(renders.get("wireframe", "")):
                r2.image(renders["wireframe"], caption="Diagnostic Wireframe")

            if results["qc_report"]:
                with st.expander("Detailed 3-Pass QC Audit Trail", expanded=True):
                    for p in results["qc_report"]["pass_results"]:
                        tag = "PASSED" if p["passed"] else "FAILED"
                        st.markdown(f"**{p['pass_name']}**: `{tag}` (Score: {p['score']}/10.0)")
                        if p["detected_issues"]:
                            st.caption("Issues: " + ", ".join(p["detected_issues"]))
                        if p["corrective_actions"]:
                            st.caption("Directives: " + ", ".join(p["corrective_actions"]))

            if os.path.exists(results["export_zip_path"]):
                with open(results["export_zip_path"], "rb") as zf:
                    st.download_button(
                        label="Download Complete Roblox Asset Bundle (ZIP)",
                        data=zf,
                        file_name="Roblox_Asset_Bundle.zip",
                        mime="application/zip",
                        use_container_width=True
                    )
