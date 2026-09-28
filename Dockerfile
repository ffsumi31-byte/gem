# Dockerfile for Deploying Roblox AI 3D Studio on Render.com
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV BLENDER_VERSION=3.6.18
ENV PATH="/usr/local/blender:${PATH}"

# Install system dependencies, OpenGL, X11 virtual framebuffers, Python
RUN apt-get update && apt-get install -y --no-install-recommends     wget     curl     xz-utils     libgl1     libgl1-mesa-dri     libgl1-mesa-glx     libglu1-mesa     libxi6     libxrender1     libxfixes3     libxcursor1     libxinerama1     libxkbcommon0     libsm6     libxext6     xvfb     python3     python3-pip     python3-dev     git     && rm -rf /var/lib/apt/lists/*

# Install official Blender binary (headless capable)
RUN mkdir -p /usr/local/blender &&     wget -q https://download.blender.org/release/Blender3.6/blender-${BLENDER_VERSION}-linux-x64.tar.xz -O /tmp/blender.tar.xz &&     tar -xJf /tmp/blender.tar.xz -C /usr/local/blender --strip-components=1 &&     rm /tmp/blender.tar.xz &&     ln -s /usr/local/blender/blender /usr/bin/blender

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip3 install --no-cache-dir --upgrade pip &&     pip3 install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Ensure storage directories exist
RUN mkdir -p /app/workspace /app/output /app/renders

EXPOSE 8501 8000

# Default entrypoint starts Streamlit dashboard (or swap to FastAPI in render.yaml)
CMD ["sh", "-c", "streamlit run app.py --server.port=${PORT:-8501} --server.address=0.0.0.0"]
